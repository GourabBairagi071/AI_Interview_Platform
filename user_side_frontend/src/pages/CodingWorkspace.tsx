import { useEffect, useState, useMemo, useCallback } from "react"
import { useParams, useNavigate, useSearchParams } from "react-router-dom"
import Editor from "@monaco-editor/react"
import AntiCheatingMonitor from "../components/AntiCheatingMonitor"
import {
  getCodingProblem,
  runCodingProblem,
  submitCodingProblem,
  getCodingSubmissions,
  runCustomCode,
  getAIAssistance,
  type CodingProblemDetail,
  type RunCodeResponse,
  type CodingSubmission,
  type CustomCodeResponse,
  type AIAssistanceResponse,
} from "../services/api"
import "./CodingWorkspace.css"

const SUPPORTED_LANGUAGES = [
  { id: "python", name: "Python 3", monaco: "python" },
  { id: "javascript", name: "JavaScript (Node.js)", monaco: "javascript" },
  { id: "cpp", name: "C++ (g++)", monaco: "cpp" },
  { id: "java", name: "Java (OpenJDK)", monaco: "java" },
]

export default function CodingWorkspace() {
  const { problemId } = useParams<{ problemId: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // Proctored mode check (Phase 8B-10)
  const interviewId = searchParams.get("interviewId") || searchParams.get("interview_id")

  const [problem, setProblem] = useState<CodingProblemDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Language & Code State
  const [language, setLanguage] = useState<string>("python")
  const [code, setCode] = useState<string>("")

  // Tabs
  const [activeLeftTab, setActiveLeftTab] = useState<"description" | "submissions">("description")
  const [activeBottomTab, setActiveBottomTab] = useState<"cases" | "run_output" | "custom" | "submission">("cases")
  const [selectedCaseIndex, setSelectedCaseIndex] = useState<number>(0)

  // Actions state
  const [running, setRunning] = useState<boolean>(false)
  const [submitting, setSubmitting] = useState<boolean>(false)
  const [runResult, setRunResult] = useState<RunCodeResponse | null>(null)
  const [submissionResult, setSubmissionResult] = useState<CodingSubmission | null>(null)
  const [pastSubmissions, setPastSubmissions] = useState<CodingSubmission[]>([])

  // Custom Input State (Phase 8B-6)
  const [customInput, setCustomInput] = useState<string>("")
  const [runningCustom, setRunningCustom] = useState<boolean>(false)
  const [customResult, setCustomResult] = useState<CustomCodeResponse | null>(null)

  // AI Assistant State (Phase 8B-11)
  const [isAssistantOpen, setIsAssistantOpen] = useState<boolean>(false)
  const [assistantLoading, setAssistantLoading] = useState<boolean>(false)
  const [assistantResponse, setAssistantResponse] = useState<AIAssistanceResponse | null>(null)
  const [activeAction, setActiveAction] = useState<string>("hint")
  const [hintLevel, setHintLevel] = useState<number>(1)

  // Load problem details & past submissions
  useEffect(() => {
    if (!problemId) return
    loadProblemData(problemId)
  }, [problemId])

  const loadProblemData = async (id: string) => {
    try {
      setLoading(true)
      setError(null)
      const data = await getCodingProblem(id)
      setProblem(data)

      // Initialize code from draft or starter code
      const savedDraft = localStorage.getItem(`coding_draft_${data.id}_${language}`)
      if (savedDraft) {
        setCode(savedDraft)
      } else if (data.starter_code && data.starter_code[language]) {
        setCode(data.starter_code[language])
      }

      // Load past submissions
      loadPastSubmissions(data.id)
    } catch (err: any) {
      setError(err?.message || "Failed to load problem")
    } finally {
      setLoading(false)
    }
  }

  const loadPastSubmissions = async (pid: string) => {
    try {
      const res = await getCodingSubmissions({ problem_id: pid })
      setPastSubmissions(res.submissions || [])
    } catch {
      // non-blocking
    }
  }

  // Handle language switch
  const handleLanguageChange = (newLang: string) => {
    if (!problem) return
    // Save draft of current code
    if (code) {
      localStorage.setItem(`coding_draft_${problem.id}_${language}`, code)
    }

    setLanguage(newLang)
    const savedDraft = localStorage.getItem(`coding_draft_${problem.id}_${newLang}`)
    if (savedDraft) {
      setCode(savedDraft)
    } else if (problem.starter_code && problem.starter_code[newLang]) {
      setCode(problem.starter_code[newLang])
    } else {
      setCode("")
    }
  }

  // Handle code change
  const handleCodeChange = (newCode: string | undefined) => {
    const val = newCode ?? ""
    setCode(val)
    if (problem) {
      localStorage.setItem(`coding_draft_${problem.id}_${language}`, val)
    }
  }

  // Reset code to starter template
  const handleResetCode = () => {
    if (!problem) return
    if (window.confirm("Reset your solution to the original starter template?")) {
      const template = problem.starter_code?.[language] || ""
      setCode(template)
      localStorage.removeItem(`coding_draft_${problem.id}_${language}`)
    }
  }

  // RUN CODE (Public Sample Tests)
  const handleRunCode = useCallback(async () => {
    if (!problem || running || submitting) return
    try {
      setRunning(true)
      setActiveBottomTab("run_output")
      const result = await runCodingProblem(problem.id, language, code)
      setRunResult(result)
      setSelectedCaseIndex(0)
    } catch (err: any) {
      alert(`Execution Error: ${err?.message || "Failed to execute code"}`)
    } finally {
      setRunning(false)
    }
  }, [problem, language, code, running, submitting])

  // SUBMIT SOLUTION (Full Test Suite + Deterministic Scoring + AI Review)
  const handleSubmitCode = useCallback(async () => {
    if (!problem || running || submitting) return
    try {
      setSubmitting(true)
      setActiveBottomTab("submission")
      const result = await submitCodingProblem(problem.id, language, code)
      setSubmissionResult(result)
      // Refresh submissions history
      loadPastSubmissions(problem.id)
    } catch (err: any) {
      alert(`Submission Error: ${err?.message || "Failed to submit solution"}`)
    } finally {
      setSubmitting(false)
    }
  }, [problem, language, code, running, submitting])

  // RUN CUSTOM INPUT (Phase 8B-6)
  const handleRunCustomInput = useCallback(async () => {
    if (!problem || runningCustom) return
    try {
      setRunningCustom(true)
      const res = await runCustomCode(problem.id, language, code, customInput)
      setCustomResult(res)
    } catch (err: any) {
      alert(`Custom execution failed: ${err?.message || "Execution error"}`)
    } finally {
      setRunningCustom(false)
    }
  }, [problem, language, code, customInput, runningCustom])

  // CALL AI CODING ASSISTANT (Phase 8B-11)
  const handleAIAssist = useCallback(
    async (action: string, specificHintLevel?: number) => {
      if (!problem || assistantLoading) return
      try {
        setAssistantLoading(true)
        setActiveAction(action)
        const levelToUse = specificHintLevel ?? (action === "hint" ? hintLevel : undefined)
        const errMsg =
          runResult?.compile_error ||
          submissionResult?.compile_error ||
          (runResult?.results?.find((r) => !r.passed)?.error ?? undefined)

        const res = await getAIAssistance({
          problem_id: problem.id,
          language,
          code,
          action,
          hint_level: levelToUse,
          error_message: errMsg,
        })
        setAssistantResponse(res)
        if (action === "hint" && res.hint_level) {
          setHintLevel(Math.min(res.hint_level + 1, 5))
        }
      } catch (err: any) {
        alert(`AI Assistant Error: ${err?.message || "Failed to reach AI Assistant"}`)
      } finally {
        setAssistantLoading(false)
      }
    },
    [problem, assistantLoading, language, code, hintLevel, runResult, submissionResult]
  )

  // Keyboard shortcut: Ctrl+Enter to Run
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault()
        handleRunCode()
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [handleRunCode])

  const monacoLanguage = useMemo(() => {
    const langObj = SUPPORTED_LANGUAGES.find((l) => l.id === language)
    return langObj ? langObj.monaco : "python"
  }, [language])

  if (loading) {
    return (
      <div className="coding-workspace" style={{ justifyContent: "center", alignItems: "center" }}>
        <h2>Loading Coding Arena...</h2>
        <p style={{ color: "#94a3b8" }}>Preparing compiler sandbox and question specifications.</p>
      </div>
    )
  }

  if (error || !problem) {
    return (
      <div className="coding-workspace" style={{ justifyContent: "center", alignItems: "center" }}>
        <h2 style={{ color: "#fb7185" }}>{error || "Problem Not Found"}</h2>
        <button
          type="button"
          className="workspace-back-btn"
          style={{ marginTop: "1rem" }}
          onClick={() => navigate("/coding")}
        >
          ← Return to Problems
        </button>
      </div>
    )
  }

  const sampleCases = problem.sample_test_cases || []

  return (
    <div className="coding-workspace">
      {/* ------------------------------------------------------------
          TOP CONTROL BAR
      ------------------------------------------------------------ */}
      <header className="workspace-topbar">
        <div className="topbar-left">
          <button
            type="button"
            className="workspace-back-btn"
            onClick={() => navigate("/coding")}
          >
            ← Problems
          </button>
          <div className="workspace-title-wrap">
            <span className="workspace-problem-title">{problem.title}</span>
            <span className={`difficulty-badge ${problem.difficulty.toLowerCase()}`}>
              {problem.difficulty}
            </span>
          </div>
        </div>

        <div className="topbar-center">
          <div className="lang-select-wrapper">
            <select
              className="lang-select"
              value={language}
              onChange={(e) => handleLanguageChange(e.target.value)}
            >
              {SUPPORTED_LANGUAGES.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
            <span className="lang-select-arrow">▼</span>
          </div>

          <button
            type="button"
            className="reset-code-btn"
            onClick={handleResetCode}
            title="Reset code to original starter template"
          >
            Reset
          </button>
        </div>

        <div className="topbar-right">
          {interviewId && (
            <div className="proctor-status-pill">
              <span className="proctor-pulse-beacon" />
              <span>Proctored Session</span>
            </div>
          )}

          <button
            type="button"
            className={`ai-assistant-toggle-btn ${isAssistantOpen ? "active" : ""}`}
            onClick={() => setIsAssistantOpen((prev) => !prev)}
            title="Open AI Coding Assistant for hints, explanations, and reviews"
          >
            <span>✨</span>
            <span>AI Assistant</span>
          </button>

          <button
            type="button"
            className="run-btn"
            onClick={handleRunCode}
            disabled={running || submitting}
            title="Run against sample test cases (Ctrl + Enter)"
          >
            <span>▶</span>
            <span>{running ? "Running..." : "Run Code"}</span>
          </button>

          <button
            type="button"
            className="submit-btn"
            onClick={handleSubmitCode}
            disabled={running || submitting}
            title="Evaluate against all test cases and receive AI code review"
          >
            <span>⚡</span>
            <span>{submitting ? "Evaluating..." : "Submit Solution"}</span>
          </button>
        </div>
      </header>

      {/* ------------------------------------------------------------
          MAIN SPLIT VIEW
      ------------------------------------------------------------ */}
      <div className="workspace-body">
        {/* LEFT PANE: DESCRIPTION & SUBMISSIONS */}
        <section className="workspace-left-pane">
          <div className="pane-nav-tabs">
            <button
              type="button"
              className={`pane-tab-btn ${activeLeftTab === "description" ? "active" : ""}`}
              onClick={() => setActiveLeftTab("description")}
            >
              <span>📄</span>
              <span>Description</span>
            </button>
            <button
              type="button"
              className={`pane-tab-btn ${activeLeftTab === "submissions" ? "active" : ""}`}
              onClick={() => setActiveLeftTab("submissions")}
            >
              <span>🕒</span>
              <span>Submissions ({pastSubmissions.length})</span>
            </button>
          </div>

          <div className="pane-scrollable-content">
            {activeLeftTab === "description" ? (
              <div className="problem-desc-content">
                <div className="problem-header-block">
                  <h2>{problem.title}</h2>
                  <div className="problem-badges-row">
                    <span className={`difficulty-badge ${problem.difficulty.toLowerCase()}`}>
                      {problem.difficulty}
                    </span>
                    <span className="topic-tag">🏷 {problem.topic}</span>
                  </div>
                </div>

                <div className="problem-markdown-body">
                  {problem.description}
                </div>

                {/* Examples */}
                {problem.examples && problem.examples.length > 0 && (
                  <div className="examples-section">
                    <h4>Examples</h4>
                    {problem.examples.map((ex, idx) => (
                      <div key={idx} className="example-card">
                        <div className="example-title">Example {idx + 1}:</div>
                        <div className="code-snippet-box">
                          <span className="snippet-label">Input:</span>
                          {ex.input}
                        </div>
                        <div className="code-snippet-box">
                          <span className="snippet-label">Output:</span>
                          {ex.output}
                        </div>
                        {ex.explanation && (
                          <div className="example-explanation">
                            <strong>Explanation: </strong> {ex.explanation}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Constraints */}
                {problem.constraints && (
                  <div className="constraints-section">
                    <h4>Constraints</h4>
                    <ul className="constraints-list">
                      {Array.isArray(problem.constraints) ? (
                        problem.constraints.map((c, i) => (
                          <li key={i}>
                            <code>{c}</code>
                          </li>
                        ))
                      ) : (
                        <li>
                          <code>{problem.constraints}</code>
                        </li>
                      )}
                    </ul>
                  </div>
                )}

                {/* I/O Format Details */}
                {(problem.input_format || problem.output_format) && (
                  <div className="io-section">
                    {problem.input_format && (
                      <div style={{ marginBottom: "0.75rem" }}>
                        <h4>Input Format</h4>
                        <p style={{ fontSize: "0.85rem", color: "#94a3b8", margin: 0 }}>
                          {problem.input_format}
                        </p>
                      </div>
                    )}
                    {problem.output_format && (
                      <div>
                        <h4>Output Format</h4>
                        <p style={{ fontSize: "0.85rem", color: "#94a3b8", margin: 0 }}>
                          {problem.output_format}
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Target Complexity */}
                {(problem.expected_time_complexity || problem.expected_space_complexity) && (
                  <div className="complexity-spec-section">
                    <h4>Target Complexity</h4>
                    <div className="complexity-pills-row">
                      {problem.expected_time_complexity && (
                        <span className="complexity-spec-badge">
                          ⏱ Time: <code>{problem.expected_time_complexity}</code>
                        </span>
                      )}
                      {problem.expected_space_complexity && (
                        <span className="complexity-spec-badge">
                          💾 Space: <code>{problem.expected_space_complexity}</code>
                        </span>
                      )}
                    </div>
                  </div>
                )}

                {/* Tags, Companies, and Roles */}
                {((problem.company_tags && problem.company_tags.length > 0) ||
                  (problem.role_tags && problem.role_tags.length > 0) ||
                  (problem.tags && problem.tags.length > 0)) && (
                  <div className="meta-tags-section">
                    <h4>Target Roles & Companies</h4>
                    <div className="tags-flex-wrap">
                      {problem.company_tags?.map((c, i) => (
                        <span key={`company-${i}`} className="meta-badge-pill company">
                          🏢 {c}
                        </span>
                      ))}
                      {problem.role_tags?.map((r, i) => (
                        <span key={`role-${i}`} className="meta-badge-pill role">
                          💼 {r}
                        </span>
                      ))}
                      {problem.tags?.map((t, i) => (
                        <span key={`tag-${i}`} className="meta-badge-pill general">
                          #{t}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* Submissions History */
              <div className="submissions-history-list">
                {pastSubmissions.length === 0 ? (
                  <p style={{ color: "#94a3b8", fontSize: "0.875rem" }}>
                    No submissions recorded yet for this challenge. Click <strong>Submit Solution</strong> to test your code!
                  </p>
                ) : (
                  pastSubmissions.map((sub) => {
                    const isAcc = sub.status === "Accepted"
                    return (
                      <div
                        key={sub.id}
                        className="sub-item-card"
                        onClick={() => {
                          setSubmissionResult(sub)
                          setActiveBottomTab("submission")
                        }}
                      >
                        <div className="sub-item-top">
                          <span className={`sub-status-pill ${isAcc ? "accepted" : "failed"}`}>
                            {sub.status}
                          </span>
                          <span className="sub-score">{sub.score} / 100</span>
                        </div>
                        <div className="sub-item-bottom">
                          <span>
                            {sub.language} • {sub.passed_tests}/{sub.total_tests} Passed
                          </span>
                          <span>{new Date(sub.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    )
                  })
                )}
              </div>
            )}
          </div>
        </section>

        {/* RIGHT PANE: MONACO EDITOR & LOWER CONSOLE */}
        <section className="workspace-right-pane">
          {/* Monaco Editor */}
          <div className="editor-container-wrapper">
            <Editor
              height="100%"
              language={monacoLanguage}
              value={code}
              theme="vs-dark"
              onChange={handleCodeChange}
              options={{
                fontSize: 14,
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                lineNumbers: "on",
                roundedSelection: false,
                scrollBeyondLastLine: false,
                readOnly: false,
                automaticLayout: true,
                tabSize: 4,
                minimap: { enabled: true },
                wordWrap: "on",
              }}
            />
          </div>

          {/* LOWER CONSOLE / TEST RESULTS / AI REVIEW */}
          <div className="workspace-bottom-pane">
            <div className="bottom-pane-tabs">
              <button
                type="button"
                className={`pane-tab-btn ${activeBottomTab === "cases" ? "active" : ""}`}
                onClick={() => setActiveBottomTab("cases")}
              >
                <span>🧪</span>
                <span>Test Cases</span>
              </button>

              <button
                type="button"
                className={`pane-tab-btn ${activeBottomTab === "run_output" ? "active" : ""}`}
                onClick={() => setActiveBottomTab("run_output")}
              >
                <span>▶</span>
                <span>
                  Run Output{" "}
                  {runResult && (
                    <span style={{ color: runResult.status === "Accepted" ? "#34d399" : "#fb7185" }}>
                      ({runResult.total_passed}/{runResult.total_tests})
                    </span>
                  )}
                </span>
              </button>

              <button
                type="button"
                className={`pane-tab-btn ${activeBottomTab === "custom" ? "active" : ""}`}
                onClick={() => setActiveBottomTab("custom")}
              >
                <span>⌨️</span>
                <span>Custom Input</span>
              </button>

              <button
                type="button"
                className={`pane-tab-btn ${activeBottomTab === "submission" ? "active" : ""}`}
                onClick={() => setActiveBottomTab("submission")}
              >
                <span>⚡</span>
                <span>
                  Submission & AI Review{" "}
                  {submissionResult && (
                    <span style={{ color: submissionResult.status === "Accepted" ? "#34d399" : "#fb7185" }}>
                      ({submissionResult.score} pts)
                    </span>
                  )}
                </span>
              </button>
            </div>

            <div className="bottom-pane-content">
              {/* TAB 1: SAMPLE TEST CASES */}
              {activeBottomTab === "cases" && (
                <div>
                  <div className="tc-case-tabs">
                    {sampleCases.map((_, idx) => (
                      <button
                        key={idx}
                        type="button"
                        className={`tc-case-btn ${selectedCaseIndex === idx ? "active" : ""}`}
                        onClick={() => setSelectedCaseIndex(idx)}
                      >
                        Case {idx + 1}
                      </button>
                    ))}
                  </div>

                  {sampleCases[selectedCaseIndex] && (
                    <div className="tc-detail-grid">
                      <div className="tc-io-block">
                        <span className="tc-io-label">Input</span>
                        <div className="tc-io-val">
                          {sampleCases[selectedCaseIndex].input}
                        </div>
                      </div>
                      <div className="tc-io-block">
                        <span className="tc-io-label">Expected Output</span>
                        <div className="tc-io-val">
                          {sampleCases[selectedCaseIndex].output}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: RUN OUTPUT */}
              {activeBottomTab === "run_output" && (
                <div>
                  {!runResult ? (
                    <p style={{ color: "#94a3b8", fontSize: "0.875rem" }}>
                      Click <strong>Run Code</strong> (Ctrl + Enter) to execute your code against public sample cases.
                    </p>
                  ) : runResult.compile_error ? (
                    <div className="error-console-box">
                      <strong>Compilation / Syntax Error:</strong>
                      <br />
                      {runResult.compile_error}
                    </div>
                  ) : (
                    <div>
                      <div className="tc-case-tabs">
                        {runResult.results.map((res, idx) => (
                          <button
                            key={idx}
                            type="button"
                            className={`tc-case-btn ${selectedCaseIndex === idx ? "active" : ""}`}
                            onClick={() => setSelectedCaseIndex(idx)}
                          >
                            <span className={`tc-indicator ${res.passed ? "pass" : "fail"}`} />
                            Case {idx + 1}
                          </button>
                        ))}
                      </div>

                      {runResult.results[selectedCaseIndex] && (
                        <div className="tc-detail-grid">
                          <div className="tc-io-block">
                            <span className="tc-io-label">Input</span>
                            <div className="tc-io-val">
                              {runResult.results[selectedCaseIndex].input}
                            </div>
                          </div>
                          <div className="tc-io-block">
                            <span className="tc-io-label">Expected Output</span>
                            <div className="tc-io-val">
                              {runResult.results[selectedCaseIndex].expected_output}
                            </div>
                          </div>
                          <div className="tc-io-block">
                            <span className="tc-io-label">Actual Output</span>
                            <div
                              className={`tc-io-val ${
                                runResult.results[selectedCaseIndex].passed
                                  ? "actual-pass"
                                  : "actual-fail"
                              }`}
                            >
                              {runResult.results[selectedCaseIndex].actual_output ||
                                runResult.results[selectedCaseIndex].error ||
                                "[Empty Output]"}
                            </div>
                          </div>
                          <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                            Runtime: {runResult.results[selectedCaseIndex].execution_time}ms
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* TAB: CUSTOM INPUT (Phase 8B-6) */}
              {activeBottomTab === "custom" && (
                <div className="custom-input-panel">
                  <div className="custom-input-top-bar">
                    <span className="custom-input-guidance">
                      Execute solution with custom raw input (stdin):
                    </span>
                    <button
                      type="button"
                      className="run-custom-action-btn"
                      onClick={handleRunCustomInput}
                      disabled={runningCustom || !customInput.trim()}
                    >
                      <span>▶</span>
                      <span>{runningCustom ? "Executing..." : "Run Custom Input"}</span>
                    </button>
                  </div>

                  <div className="custom-input-grid">
                    <div className="custom-input-entry">
                      <label className="custom-field-label">Custom Test Input</label>
                      <textarea
                        className="custom-input-textarea"
                        value={customInput}
                        onChange={(e) => setCustomInput(e.target.value)}
                        placeholder="Enter custom input values (e.g. [2, 7, 11, 15]&#10;9)"
                        rows={4}
                      />
                    </div>

                    <div className="custom-output-display">
                      <label className="custom-field-label">Execution Results</label>
                      {!customResult ? (
                        <div className="custom-waiting-box">
                          Enter input above and click <strong>Run Custom Input</strong> to evaluate your code.
                        </div>
                      ) : (
                        <div className="custom-result-container">
                          <div className="custom-result-status-bar">
                            <span
                              className={`custom-status-badge ${
                                customResult.status === "Accepted" ? "accepted" : "failed"
                              }`}
                            >
                              {customResult.status}
                            </span>
                            <span className="custom-runtime-tag">
                              Runtime: {customResult.runtime} ms
                            </span>
                          </div>

                          {customResult.stdout && (
                            <div className="custom-io-section">
                              <span className="custom-section-sub">Standard Output:</span>
                              <pre className="custom-stdout-code">{customResult.stdout}</pre>
                            </div>
                          )}

                          {customResult.stderr && (
                            <div className="custom-io-section error">
                              <span className="custom-section-sub">Standard Error:</span>
                              <pre className="custom-stderr-code">{customResult.stderr}</pre>
                            </div>
                          )}

                          {!customResult.stdout && !customResult.stderr && (
                            <div className="custom-empty-notice">
                              Execution completed with no standard output.
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 3: SUBMISSION RESULT & AI REVIEW */}
              {activeBottomTab === "submission" && (
                <div>
                  {!submissionResult ? (
                    <p style={{ color: "#94a3b8", fontSize: "0.875rem" }}>
                      Click <strong>Submit Solution</strong> to run against all hidden and edge-case test suites, generate a deterministic score, and receive instant AI analysis.
                    </p>
                  ) : (
                    <div>
                      {/* Overall Banner */}
                      <div className="submission-banner">
                        <div className="submission-banner-top">
                          <div
                            className={`submission-status-large ${
                              submissionResult.status === "Accepted" ? "accepted" : "failed"
                            }`}
                          >
                            <span>
                              {submissionResult.status === "Accepted" ? "✓" : "✗"}
                            </span>
                            <span>{submissionResult.status}</span>
                          </div>

                          <div className="submission-score-box">
                            <span className="score-num">{submissionResult.score}</span>
                            <span className="score-max">/ 100 pts</span>
                          </div>
                        </div>

                        <div className="submission-metrics-row">
                          <div className="sub-metric">
                            Tests Passed:
                            <strong>
                              {submissionResult.passed_tests} / {submissionResult.total_tests}
                            </strong>
                          </div>
                          <div className="sub-metric">
                            Avg Runtime:
                            <strong>{submissionResult.execution_time} ms</strong>
                          </div>
                          <div className="sub-metric">
                            Time Complexity:
                            <strong>{submissionResult.complexity_time || "O(n)"}</strong>
                          </div>
                          <div className="sub-metric">
                            Space Complexity:
                            <strong>{submissionResult.complexity_space || "O(1)"}</strong>
                          </div>
                        </div>
                      </div>

                      {/* Error Console if failed */}
                      {submissionResult.compile_error && (
                        <div className="error-console-box">
                          {submissionResult.compile_error}
                        </div>
                      )}

                      {/* AI Code Review Block */}
                      {submissionResult.ai_review && (
                        <div className="ai-review-block">
                          <div className="ai-review-header">
                            <div className="ai-avatar">🤖</div>
                            <span className="ai-review-title">
                              AI Senior Engineer Review & Analysis
                            </span>
                          </div>

                          <p className="ai-summary-text">
                            {submissionResult.ai_review.summary}
                          </p>

                          <div className="ai-feedback-grid">
                            {submissionResult.ai_review.strengths &&
                              submissionResult.ai_review.strengths.length > 0 && (
                                <div className="feedback-column strengths">
                                  <h5>Key Strengths</h5>
                                  <ul>
                                    {submissionResult.ai_review.strengths.map((s, idx) => (
                                      <li key={idx}>{s}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}

                            {submissionResult.ai_review.issues &&
                              submissionResult.ai_review.issues.length > 0 && (
                                <div className="feedback-column issues">
                                  <h5>Potential Bottlenecks & Edge Cases</h5>
                                  <ul>
                                    {submissionResult.ai_review.issues.map((issue, idx) => (
                                      <li key={idx}>{issue}</li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                          </div>

                          {submissionResult.ai_review.optimization_suggestions &&
                            submissionResult.ai_review.optimization_suggestions.length > 0 && (
                              <div className="suggestions-block">
                                <h5>Optimization Suggestions</h5>
                                <ul>
                                  {submissionResult.ai_review.optimization_suggestions.map(
                                    (opt, idx) => (
                                      <li key={idx}>{opt}</li>
                                    ),
                                  )}
                                </ul>
                              </div>
                            )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </section>
      </div>

      {/* ------------------------------------------------------------
          AI CODING ASSISTANT SLIDE-OVER DRAWER (Phase 8B-11)
      ------------------------------------------------------------ */}
      {isAssistantOpen && (
        <aside className="ai-assistant-drawer" aria-label="AI Coding Assistant">
          <div className="ai-assistant-header">
            <div className="ai-header-left">
              <span className="ai-glow-icon">✨</span>
              <div>
                <h3>AI Assistant</h3>
                <small>Intelligent Code Mentor • Powered by Groq</small>
              </div>
            </div>
            <button
              type="button"
              className="ai-close-drawer-btn"
              onClick={() => setIsAssistantOpen(false)}
            >
              ✕
            </button>
          </div>

          <div className="ai-actions-toolbar">
            <button
              type="button"
              className={`ai-action-button ${activeAction === "hint" ? "active" : ""}`}
              onClick={() => handleAIAssist("hint")}
              disabled={assistantLoading}
            >
              💡 Give Hint ({hintLevel <= 3 ? `Hint ${hintLevel}/3` : hintLevel === 4 ? "Approach" : "Full"})
            </button>
            <button
              type="button"
              className={`ai-action-button ${activeAction === "explain_problem" ? "active" : ""}`}
              onClick={() => handleAIAssist("explain_problem")}
              disabled={assistantLoading}
            >
              📖 Explain Problem
            </button>
            <button
              type="button"
              className={`ai-action-button ${activeAction === "review_approach" ? "active" : ""}`}
              onClick={() => handleAIAssist("review_approach")}
              disabled={assistantLoading}
            >
              🔍 Review Approach
            </button>
            <button
              type="button"
              className={`ai-action-button ${activeAction === "complexity" ? "active" : ""}`}
              onClick={() => handleAIAssist("complexity")}
              disabled={assistantLoading}
            >
              ⚡ Complexity
            </button>
            <button
              type="button"
              className={`ai-action-button ${activeAction === "edge_cases" ? "active" : ""}`}
              onClick={() => handleAIAssist("edge_cases")}
              disabled={assistantLoading}
            >
              🛡️ Edge Cases
            </button>
            <button
              type="button"
              className={`ai-action-button ${activeAction === "explain_error" ? "active" : ""}`}
              onClick={() => handleAIAssist("explain_error")}
              disabled={assistantLoading}
            >
              🐞 Diagnose Error
            </button>
            <button
              type="button"
              className={`ai-action-button ${activeAction === "suggest_optimization" ? "active" : ""}`}
              onClick={() => handleAIAssist("suggest_optimization")}
              disabled={assistantLoading}
            >
              🚀 Optimization
            </button>
          </div>

          <div className="ai-assistant-body">
            {assistantLoading ? (
              <div className="ai-drawer-loader">
                <div className="ai-loader-spinner" />
                <p>Analyzing problem logic and candidate code...</p>
              </div>
            ) : assistantResponse ? (
              <div className="ai-response-card">
                {assistantResponse.action === "hint" && (
                  <div className="hint-progression-bar">
                    {[1, 2, 3, 4, 5].map((lvl) => (
                      <button
                        key={lvl}
                        type="button"
                        className={`hint-pill-step ${
                          (assistantResponse.hint_level || 1) >= lvl ? "active" : ""
                        }`}
                        onClick={() => handleAIAssist("hint", lvl)}
                      >
                        {lvl <= 3 ? `Hint ${lvl}` : lvl === 4 ? "Approach" : "Explanation"}
                      </button>
                    ))}
                  </div>
                )}
                <div className="ai-markdown-output">
                  <pre className="ai-pre-formatted">{assistantResponse.content || (assistantResponse as any).response}</pre>
                </div>
              </div>
            ) : (
              <div className="ai-empty-state">
                <div className="ai-empty-illustration">💡</div>
                <h4>How can I help you?</h4>
                <p>
                  Get progressive hints without spoiling the full solution, analyze time/space bottlenecks, or diagnose runtime errors.
                </p>
              </div>
            )}
          </div>
        </aside>
      )}

      {/* ------------------------------------------------------------
          PROCTORED INTERVIEW SURVEILLANCE OVERLAY (Phase 8B-10)
      ------------------------------------------------------------ */}
      {interviewId && (
        <div className="proctor-floating-monitor-card">
          <div className="proctor-floating-top">
            <span className="proctor-red-beacon" />
            <span className="proctor-title">AI Proctor Active</span>
            <span className="proctor-id-tag">ID: {interviewId.slice(0, 8)}</span>
          </div>
          <div className="proctor-camera-mount">
            <AntiCheatingMonitor interviewId={interviewId} isActive={true} />
          </div>
        </div>
      )}
    </div>
  )
}
