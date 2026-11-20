import asyncio
import subprocess

def run_test(name: str, script_path: str):
    print(f"\n============================================================")
    print(f"RUNNING REMEDIATION REGRESSION TEST: {name}")
    print(f"============================================================")
    res = subprocess.run(
        [r"C:\Users\goura\Downloads\Interview_platform\backend\venv\Scripts\python.exe", script_path],
        cwd=r"C:\Users\goura\Downloads\Interview_platform\backend",
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "."}
    )
    if res.returncode == 0:
        print(f"[PASSED] {name}")
    else:
        print(f"[FAILED] {name}")
        print(res.stdout)
        print(res.stderr)
        raise RuntimeError(f"Remediation Regression Failed for {name}")

def main():
    print("=== FINAL CONSOLIDATED DEFECT REMEDIATION REGRESSION SUITE ===")
    run_test("DEFECT-01 (Admin Coding Problems Count)", "scratch/test_fix_defect_01.py")
    run_test("DEFECT-02 (Skill Targeting)", "scratch/test_fix_defect_02.py")
    run_test("DEFECT-03 (Free Subscription Targeting)", "scratch/test_fix_defect_03.py")
    run_test("DEFECT-04 (Company Targeting Fallthrough)", "scratch/test_fix_defect_04.py")
    run_test("DEFECT-05 (Concurrent Submission)", "scratch/test_fix_defect_05.py")
    run_test("DEFECT-06 (Dashboard Summary Resume Attribute)", "scratch/test_fix_defect_06.py")
    print("\n============================================================")
    print("ALL 6 DEFECT REMEDIATION TESTS PASSED 100% CLEANLY!")
    print("============================================================")

if __name__ == "__main__":
    main()
