import asyncio
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any


class SecurityViolationError(Exception):
    pass


# ============================================================
# STATIC SECURITY SCANNER
# NOTE: This static scanner + ephemeral directory + stripped environment
# is a defense-in-depth layer. It does NOT replace container or VM-level
# sandboxing (Docker, gVisor, Firecracker).
# ============================================================

DANGEROUS_PATTERNS = {
    "python": [
        r"\bimport\s+os\b",
        r"\bimport\s+subprocess\b",
        r"\bimport\s+socket\b",
        r"\bimport\s+shutil\b",
        r"\bimport\s+ctypes\b",
        r"\bimport\s+urllib\b",
        r"\bimport\s+requests\b",
        r"\bimport\s+http\b",
        r"\bimport\s+importlib\b",
        r"\bfrom\s+os\s+import\b",
        r"\bfrom\s+subprocess\s+import\b",
        r"\bfrom\s+socket\s+import\b",
        r"\bfrom\s+shutil\s+import\b",
        r"\bfrom\s+ctypes\s+import\b",
        r"\b__import__\b",
        r"\b__builtins__\b",
        r"\b__subclasses__\b",
        r"\bopen\s*\(",
        r"\beval\s*\(",
        r"\bexec\s*\(",
        r"\bbreakpoint\s*\(",
    ],
    "javascript": [
        r"\bchild_process\b",
        r"\bfs\.(?!readFileSync\(0\b)[a-zA-Z0-9_]+",
        r"\bfs/promises\b",
        r"\bnet\b",
        r"\bhttp\b",
        r"\bhttps\b",
        r"\bprocess\.exit\b",
        r"\bprocess\.env\b",
        r"\beval\s*\(",
        r"\bFunction\s*\(",
    ],
    "cpp": [
        r"<cstdlib>",
        r"<unistd\.h>",
        r"<windows\.h>",
        r"<sys/",
        r"\bsystem\s*\(",
        r"\bpopen\s*\(",
        r"\bfork\s*\(",
    ],
    "java": [
        r"\bProcessBuilder\b",
        r"\bRuntime\.getRuntime\b",
        r"\bjava\.io\.File\b",
        r"\bjava\.net\b",
        r"\bSystem\.exit\b",
    ],
}


def sanitize_source_code(language: str, code: str) -> None:
    lang = language.lower()
    patterns = DANGEROUS_PATTERNS.get(lang, [])

    for pattern in patterns:
        if re.search(pattern, code):
            raise SecurityViolationError(
                f"Disallowed system or network operation detected matching pattern: '{pattern}'"
            )


# ============================================================
# CODE EXECUTION SERVICE (ISOLATED SANDBOX WORKER)
# ============================================================

def _run_subproc_sync(
    cmd: list[str],
    cwd: str,
    env: dict[str, str],
    input_str: str | None = None,
    timeout: float = 3.0,
) -> tuple[int, str, str, float]:
    start = time.perf_counter()
    input_bytes = (input_str.strip() + "\n").encode("utf-8") if input_str is not None else None
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    stdout_str = proc.stdout.decode("utf-8", errors="replace")
    stderr_str = proc.stderr.decode("utf-8", errors="replace")
    return proc.returncode, stdout_str, stderr_str, elapsed_ms


class CodeExecutionService:
    def __init__(self, timeout_seconds: float = 3.0, max_output_bytes: int = 32768):
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes

    async def execute_test_cases(
        self,
        language: str,
        source_code: str,
        test_cases: list[dict[str, Any]],
        stop_on_first_failure: bool = False,
    ) -> dict[str, Any]:
        """
        Executes code inside an isolated ephemeral temporary sandbox directory.
        Strict isolation:
        - No host environment variables passed (zero credentials/secrets)
        - Subprocess runs in temporary directory
        - Timeouts enforced
        - Output truncated to prevent memory flooding
        """
        lang = language.lower()

        # 1. Pre-execution static security audit
        try:
            sanitize_source_code(lang, source_code)
        except SecurityViolationError as sec_err:
            return {
                "status": "Security Violation",
                "compile_error": str(sec_err),
                "runtime_error": None,
                "results": [],
                "total_passed": 0,
                "total_tests": len(test_cases),
            }

        # 2. Setup isolated sandbox workspace
        with tempfile.TemporaryDirectory(prefix="sandbox_run_") as sandbox_dir:
            # Build minimal isolated environment (strips all application secrets & DB config)
            safe_env = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONUNBUFFERED": "1",
                "NODE_PATH": os.environ.get("NODE_PATH", ""),
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
                "COMSPEC": os.environ.get("COMSPEC", ""),
            }

            results: list[dict[str, Any]] = []
            total_passed = 0
            overall_status = "Accepted"
            compile_err: str | None = None
            runtime_err: str | None = None

            # Prepare language runner wrapper
            runner_script_name, compile_cmd, run_cmd = self._prepare_commands(
                lang, source_code, sandbox_dir
            )

            # Compile step if needed (e.g. C++ or Java)
            if compile_cmd:
                try:
                    c_rc, c_out, c_err, _ = await asyncio.to_thread(
                        _run_subproc_sync, compile_cmd, sandbox_dir, safe_env, None, 8.0
                    )
                except FileNotFoundError:
                    tool_name = compile_cmd[0]
                    return {
                        "status": "Compilation Error",
                        "compile_error": f"Tool '{tool_name}' is not installed or not found in system PATH.",
                        "runtime_error": None,
                        "results": [],
                        "total_passed": 0,
                        "total_tests": len(test_cases),
                    }
                except subprocess.TimeoutExpired:
                    return {
                        "status": "Compilation Error",
                        "compile_error": "Compilation timed out after 8.0s",
                        "runtime_error": None,
                        "results": [],
                        "total_passed": 0,
                        "total_tests": len(test_cases),
                    }

                if c_rc != 0:
                    err_msg = c_err.strip()
                    return {
                        "status": "Compilation Error",
                        "compile_error": err_msg or "Failed to compile source code.",
                        "runtime_error": None,
                        "results": [],
                        "total_passed": 0,
                        "total_tests": len(test_cases),
                    }

            # Execute test cases sequentially
            for idx, tc in enumerate(test_cases):
                test_input = str(tc.get("input", "")).strip()
                expected_output = str(tc.get("output", "")).strip()

                tc_passed = False
                actual_out = ""
                error_info: str | None = None

                try:
                    p_rc, stdout_str, stderr_str, exec_time_ms = await asyncio.to_thread(
                        _run_subproc_sync, run_cmd, sandbox_dir, safe_env, test_input, self.timeout_seconds
                    )
                    actual_out = stdout_str[: self.max_output_bytes].strip()
                    stderr_clean = stderr_str[: self.max_output_bytes].strip()

                    if p_rc != 0:
                        error_info = stderr_clean or f"Process exited with code {p_rc}"
                        overall_status = "Runtime Error"
                        runtime_err = error_info
                    else:
                        norm_actual = self._normalize_output(actual_out)
                        norm_expected = self._normalize_output(expected_output)

                        if norm_actual == norm_expected:
                            tc_passed = True
                            total_passed += 1
                        else:
                            if overall_status == "Accepted":
                                overall_status = "Wrong Answer"

                except FileNotFoundError:
                    tool_name = run_cmd[0]
                    return {
                        "status": "Runtime Error",
                        "compile_error": None,
                        "runtime_error": f"Tool '{tool_name}' is not installed or not found in system PATH.",
                        "results": results,
                        "total_passed": total_passed,
                        "total_tests": len(test_cases),
                    }
                except subprocess.TimeoutExpired:
                    exec_time_ms = self.timeout_seconds * 1000
                    error_info = f"Time Limit Exceeded ({self.timeout_seconds}s)"
                    overall_status = "Time Limit Exceeded"
                    runtime_err = error_info
                except Exception as ex:
                    exec_time_ms = 0.0
                    error_info = str(ex)
                    overall_status = "Runtime Error"
                    runtime_err = error_info

                results.append({
                    "test_index": idx + 1,
                    "input": test_input,
                    "expected_output": expected_output,
                    "actual_output": actual_out,
                    "passed": tc_passed,
                    "execution_time": exec_time_ms,
                    "error": error_info,
                })

                if not tc_passed and stop_on_first_failure:
                    break

            if total_passed == len(test_cases) and len(test_cases) > 0:
                overall_status = "Accepted"

            return {
                "status": overall_status,
                "compile_error": compile_err,
                "runtime_error": runtime_err,
                "results": results,
                "total_passed": total_passed,
                "total_tests": len(test_cases),
            }

    async def execute_custom_input(
        self,
        language: str,
        source_code: str,
        custom_input: str,
    ) -> dict[str, Any]:
        """
        Executes code against user-provided custom input in an isolated sandbox.
        Returns stdout, stderr, runtime, and execution status.
        """
        lang = language.lower()

        try:
            sanitize_source_code(lang, source_code)
        except SecurityViolationError as sec_err:
            return {
                "stdout": "",
                "stderr": f"Security Violation: {sec_err}",
                "runtime": 0.0,
                "status": "Security Violation",
            }

        with tempfile.TemporaryDirectory(prefix="sandbox_custom_") as sandbox_dir:
            safe_env = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONUNBUFFERED": "1",
                "NODE_PATH": os.environ.get("NODE_PATH", ""),
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
                "COMSPEC": os.environ.get("COMSPEC", ""),
            }

            _, compile_cmd, run_cmd = self._prepare_commands(lang, source_code, sandbox_dir)

            if compile_cmd:
                try:
                    c_rc, c_out, c_err, _ = await asyncio.to_thread(
                        _run_subproc_sync, compile_cmd, sandbox_dir, safe_env, None, 8.0
                    )
                except FileNotFoundError:
                    return {
                        "stdout": "",
                        "stderr": f"Compiler '{compile_cmd[0]}' is not installed on this system.",
                        "runtime": 0.0,
                        "status": "Compilation Error",
                    }
                except subprocess.TimeoutExpired:
                    return {
                        "stdout": "",
                        "stderr": "Compilation timed out after 8.0s",
                        "runtime": 8000.0,
                        "status": "Compilation Error",
                    }

                if c_rc != 0:
                    err_msg = c_err.strip()
                    return {
                        "stdout": "",
                        "stderr": err_msg or "Failed to compile source code.",
                        "runtime": 0.0,
                        "status": "Compilation Error",
                    }

            # Execute with custom input
            try:
                p_rc, stdout_str, stderr_str, exec_time_ms = await asyncio.to_thread(
                    _run_subproc_sync, run_cmd, sandbox_dir, safe_env, custom_input, self.timeout_seconds
                )
                status_str = "Success" if p_rc == 0 else "Runtime Error"
                return {
                    "stdout": stdout_str[: self.max_output_bytes],
                    "stderr": stderr_str[: self.max_output_bytes],
                    "runtime": exec_time_ms,
                    "status": status_str,
                }
            except FileNotFoundError:
                return {
                    "stdout": "",
                    "stderr": f"Runtime '{run_cmd[0]}' is not installed on this system.",
                    "runtime": 0.0,
                    "status": "Runtime Error",
                }
            except subprocess.TimeoutExpired:
                return {
                    "stdout": "",
                    "stderr": f"Time Limit Exceeded (> {self.timeout_seconds}s)",
                    "runtime": self.timeout_seconds * 1000,
                    "status": "Time Limit Exceeded",
                }
            except Exception as e:
                return {
                    "stdout": "",
                    "stderr": f"Execution error: {repr(e)}",
                    "runtime": 0.0,
                    "status": "Runtime Error",
                }

    def _prepare_commands(
        self, language: str, source_code: str, sandbox_dir: str
    ) -> tuple[str, list[str] | None, list[str]]:
        py_exe = sys.executable if sys.executable else "python"
        if language in ("python", "py"):
            filename = os.path.join(sandbox_dir, "solution.py")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(source_code)
            return "solution.py", None, [py_exe, "solution.py"]

        elif language in ("javascript", "js", "node"):
            filename = os.path.join(sandbox_dir, "solution.js")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(source_code)
            return "solution.js", None, ["node", "solution.js"]

        elif language in ("cpp", "c++"):
            filename = os.path.join(sandbox_dir, "solution.cpp")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(source_code)
            exe_path = os.path.join(sandbox_dir, "solution.exe") if os.name == "nt" else os.path.join(sandbox_dir, "solution")
            compile_cmd = ["g++", "-O2", "solution.cpp", "-o", exe_path]
            return "solution.cpp", compile_cmd, [exe_path]

        elif language in ("java",):
            filename = os.path.join(sandbox_dir, "Solution.java")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(source_code)
            compile_cmd = ["javac", "Solution.java"]
            return "Solution.java", compile_cmd, ["java", "Solution"]

        else:
            filename = os.path.join(sandbox_dir, "solution.py")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(source_code)
            return "solution.py", None, [py_exe, "solution.py"]

    def _normalize_output(self, val: str) -> str:
        """Normalizes line endings and trailing whitespace for resilient output comparison."""
        lines = [line.strip() for line in val.replace("\r\n", "\n").split("\n")]
        return "\n".join(lines).strip()


execution_service = CodeExecutionService(timeout_seconds=3.0)
