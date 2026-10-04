import { useEffect, useState, useMemo, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import Editor from "@monaco-editor/react"
import AntiCheatingMonitor from "../components/AntiCheatingMonitor"
import {
  getContestDetail,
  getContestProblems,
  getContestProblemDetail,
  runContestProblem,
  runContestCustom,
  submitContestProblem,
  getContestMyStatus,
  type ContestDetail,
  type ContestProblemItem,
  type ContestProblemDetail,
  type RunCodeResponse,
  type RunCustomCodeResponse,
  type ContestSubmitResponse,
  type ContestMyStatusResponse,
} from "../services/api"
import "./ContestWorkspace.css"

const SUPPORTED_LANGUAGES = [
  { id: "python", name: "Python 3", monaco: "python" },
  { id: "javascript", name: "JavaScript (Node.js)", monaco: "javascript" },
  { id: "cpp", name: "C++ (g++)", monaco: "cpp" },
  { id: "java", name: "Java (OpenJDK)", monaco: "java" },
]

export default function ContestWorkspace() {
  const { contestId } = useParams<{ contestId: string }>()
  const navigate = useNavigate()

  // Contest metadata & problems
  const [contest, setContest] = useState<ContestDetail | null>(null)
  const [problems, setProblems] = useState<ContestProblemItem[]>([])
  const [activeProblemIndex, setActiveProblemIndex] = useState<number>(0)
  const [problemDetail, setProblemDetail] = useState<ContestProblemDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // User contest status
  const [myStatus, setMyStatus] = useState<ContestMyStatusResponse | null>(null)

  // Language & Code
  const [language, setLanguage] = useState<string>("python")
  const [code, setCode] = useState<string>("")

  // Test & Output Tabs
  const [activeBottomTab, setActiveBottomTab] = useState<"cases" | "run_output" | "custom" | "submission">("cases")
  const [selectedCaseIndex, setSelectedCaseIndex] = useState<number>(0)

  // Actions state
  const [running, setRunning] = useState(false)
  const [runningCustom, setRunningCustom] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [runResult, setRunResult] = useState<RunCodeResponse | null>(null)
  const [customInput, setCustomInput] = useState<string>("")
  const [customResult, setCustomResult] = useState<RunCustomCodeResponse | null>(null)
  const [submitResult, setSubmitResult] = useState<ContestSubmitResponse | null>(null)

  // Countdown timer state
  const [timeLeftStr, setTimeLeftStr] = useState<string>("--:--:--")
  const [isTimeUp, setIsTimeUp] = useState(false)

  // Anti-cheating proctored violations state
  const [violationCount, setViolationCount] = useState<number>(0)

  // Active problem item
  const currentProblemItem = problems[activeProblemIndex] || null

  // Fetch initial contest data & problem list
  const loadWorkspaceData = useCallback(async () => {
    if (!contestId) return
    try {
      setLoading(true)
      setError(null)

      const [contestData, problemsData] = await Promise.all([
        getContestDetail(contestId),
        getContestProblems(contestId),
      ])

      setContest(contestData)
      setProblems(problemsData.problems || [])

      // Fetch user contest status
      try {
        const statusRes = await getContestMyStatus(contestId)
        setMyStatus(statusRes)
      } catch {
        // non-blocking
      }

      // Check contest status
      if (contestData.status === "UPCOMING") {
        setError(`This contest has not started yet. Starts at ${new Date(contestData.start_time).toLocaleString()}`)
      } else if (contestData.status === "ENDED") {
        setIsTimeUp(true)
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load contest workspace")
    } finally {
      setLoading(false)
    }
  }, [contestId])

  useEffect(() => {
    loadWorkspaceData()
  }, [loadWorkspaceData])

  // Load problem details when active problem changes
  useEffect(() => {
    if (!contestId || !currentProblemItem) return

    let isSubscribed = true
    const fetchDetail = async () => {
      try {
        setLoadingDetail(true)
        const detail = await getContestProblemDetail(contestId, currentProblemItem.problem_id)
        if (!isSubscribed) return
        setProblemDetail(detail)

        // Load saved code or starter code
        const key = `contest_${contestId}_prob_${detail.problem_id}_${language}`
        const saved = localStorage.getItem(key)
        if (saved) {
          setCode(saved)
        } else if (detail.starter_code && detail.starter_code[language]) {
          setCode(detail.starter_code[language])
        } else {
          setCode("")
        }
      } catch (err: any) {
        if (isSubscribed) {
          console.error("Failed to load problem detail:", err)
        }
      } finally {
        if (isSubscribed) setLoadingDetail(false)
      }
    }

    fetchDetail()
    return () => {
      isSubscribed = false
    }
  }, [contestId, currentProblemItem, language])

  // Countdown timer effect
  useEffect(() => {
    if (!contest) return

    const updateTimer = () => {
      const now = new Date().getTime()
      const end = new Date(contest.end_time).getTime()
      const diff = end - now

      if (diff <= 0) {
        setTimeLeftStr("00:00:00")
        setIsTimeUp(true)
        return
      }

      const hours = Math.floor(diff / (1000 * 60 * 60))
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
      const seconds = Math.floor((diff % (1000 * 60)) / 1000)

      const pad = (n: number) => n.toString().padStart(2, "0")
      setTimeLeftStr(`${pad(hours)}:${pad(minutes)}:${pad(seconds)}`)
    }

    updateTimer()
    const timer = setInterval(updateTimer, 1000)
    return () => clearInterval(timer)
  }, [contest])

  // Handle language switch
  const handleLanguageChange = (newLang: string) => {
    if (!problemDetail || !contestId) return
    localStorage.setItem(`contest_${contestId}_prob_${problemDetail.problem_id}_${language}`, code)
    setLanguage(newLang)
  }

  // Handle code edit
  const handleCodeChange = (newCode: string | undefined) => {
    const val = newCode ?? ""
    setCode(val)
    if (problemDetail && contestId) {
      localStorage.setItem(`contest_${contestId}_prob_${problemDetail.problem_id}_${language}`, val)
    }
  }

  // Reset code to starter template
  const handleResetCode = () => {
    if (!problemDetail) return
    if (window.confirm("Reset your code to the default starter template for this problem?")) {
      const template = problemDetail.starter_code?.[language] || ""
      setCode(template)
      if (contestId) {
        localStorage.removeItem(`contest_${contestId}_prob_${problemDetail.problem_id}_${language}`)
      }
    }
  }

  // RUN SAMPLE TESTS
  const handleRunCode = useCallback(async () => {
    if (!contestId || !currentProblemItem || running || submitting) return
    try {
      setRunning(true)
      setActiveBottomTab("run_output")
      const res = await runContestProblem(contestId, currentProblemItem.problem_id, language, code)
      setRunResult(res)
      setSelectedCaseIndex(0)
    } catch (err: any) {
      alert(`Run Error: ${err?.message || "Execution failed"}`)
    } finally {
      setRunning(false)
    }
  }, [contestId, currentProblemItem, running, submitting, language, code])

  // RUN CUSTOM INPUT
  const handleRunCustom = async () => {
    if (!contestId || !currentProblemItem || runningCustom || submitting) return
    try {
      setRunningCustom(true)
      const res = await runContestCustom(contestId, currentProblemItem.problem_id, language, code, customInput)
      setCustomResult(res)
    } catch (err: any) {
      alert(`Custom Input Error: ${err?.message || "Execution failed"}`)
    } finally {
      setRunningCustom(false)
    }
  }

  // SUBMIT SOLUTION TO CONTEST
  const handleSubmitCode = async () => {
    if (!contestId || !currentProblemItem || running || submitting) return
    if (isTimeUp) {
      alert("Contest has ended! Submissions are no longer accepted.")
      return
    }

    try {
      setSubmitting(true)
      setActiveBottomTab("submission")
      const res = await submitContestProblem(contestId, currentProblemItem.problem_id, language, code)
      setSubmitResult(res)

      // Refresh candidate contest status & standings
      try {
        const updatedStatus = await getContestMyStatus(contestId)
        setMyStatus(updatedStatus)
      } catch {
        // non-blocking
      }
    } catch (err: any) {
      alert(`Contest Submission Error: ${err?.message || "Submission failed"}`)
    } finally {
      setSubmitting(false)
    }
  }

  // Keyboard shortcut Ctrl+Enter to Run
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
    const item = SUPPORTED_LANGUAGES.find((l) => l.id === language)
    return item ? item.monaco : "python"
  }, [language])

  if (loading) {
    return (
      <div className="contest-workspace-loading">
        <div className="contest-loading-spinner" />
        <h2>Entering Contest Arena...</h2>
        <p>Synchronizing contest clock, problem statements, and secure sandbox.</p>
      </div>
    )
  }

  if (error || !contest) {
    return (
      <div className="contest-workspace-error">
        <h2>Contest Arena Unavailable</h2>
        <p>{error || "Contest could not be found."}</p>
        <div className="error-actions">
          <button className="cw-btn cw-btn-secondary" onClick={() => navigate(`/contests/${contestId}`)}>
            Back to Contest Details
          </button>
          <button className="cw-btn cw-btn-primary" onClick={() => navigate("/contests")}>
            Browse Contests
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="contest-workspace-page">
      {/* Top Navigation Bar */}
      <header className="cw-top-nav">
        <div className="cw-nav-left">
          <button className="cw-back-btn" onClick={() => navigate(`/contests/${contestId}`)} title="Exit Workspace">
            ← Exit
          </button>
          <div className="cw-title-wrap">
            <h1 className="cw-contest-title">{contest.title}</h1>
            <span className={`cw-contest-badge badge-${contest.status.toLowerCase()}`}>
              {contest.status}
            </span>
            {contest.is_proctored && (
              <span className="cw-proctored-badge" title="AI Proctored Contest">
                🔒 Proctored
              </span>
            )}
          </div>
        </div>

        {/* Problem Selector Bar */}
        <div className="cw-problem-nav">
          {problems.map((p, idx) => {
            const probPerformance = myStatus?.problems?.find((item) => item.label === p.label)
            const isSolved = probPerformance?.solved || p.is_solved
            const hasAttempts = (probPerformance?.attempts || p.attempts_count || 0) > 0
            const isActive = idx === activeProblemIndex

            return (
              <button
                key={p.problem_id}
                className={`cw-prob-tab ${isActive ? "active" : ""} ${isSolved ? "solved" : hasAttempts ? "attempted" : ""}`}
                onClick={() => {
                  setActiveProblemIndex(idx)
                  setActiveBottomTab("cases")
                  setRunResult(null)
                  setSubmitResult(null)
                }}
              >
                <span className="prob-label">{p.label}</span>
                <span className="prob-points">{p.points} pts</span>
                {isSolved && <span className="prob-check">✓</span>}
              </button>
            )
          })}
        </div>

        {/* Right Actions: Timer, Standings, Score */}
        <div className="cw-nav-right">
          <div className={`cw-timer-box ${isTimeUp ? "expired" : ""}`}>
            <span className="timer-icon">⏱</span>
            <span className="timer-text">{timeLeftStr}</span>
          </div>

          {myStatus && (
            <div className="cw-user-stats-pill">
              <span className="stat-item">
                <strong>{myStatus.solved_count}</strong>/{problems.length} Solved
              </span>
              <span className="stat-separator">•</span>
              <span className="stat-item">
                <strong>{myStatus.total_score}</strong> pts
              </span>
              {myStatus.rank && (
                <>
                  <span className="stat-separator">•</span>
                  <span className="stat-item">Rank #{myStatus.rank}</span>
                </>
              )}
            </div>
          )}

          <button
            className="cw-standings-btn"
            onClick={() => window.open(`/contests/${contestId}/leaderboard`, "_blank")}
            title="Open Live Standings"
          >
            📊 Standings
          </button>
        </div>
      </header>

      {/* Main Split Grid */}
      <div className="cw-main-grid">
        {/* Left Column: Problem Statement & Constraints */}
        <section className="cw-left-panel">
          {loadingDetail ? (
            <div className="execution-spinner">Loading problem specification...</div>
          ) : problemDetail ? (
            <div className="cw-problem-sheet">
              <div className="cw-sheet-header">
                <div className="cw-sheet-title-row">
                  <span className="prob-order-badge">Problem {problemDetail.label}</span>
                  <h2>{problemDetail.title}</h2>
                </div>
                <div className="cw-sheet-meta">
                  <span className={`diff-pill diff-${problemDetail.difficulty.toLowerCase()}`}>
                    {problemDetail.difficulty}
                  </span>
                  <span className="meta-pill">{problemDetail.points} Points</span>
                  <span className="meta-pill">{problemDetail.topic}</span>
                  <span className="meta-pill">Time Limit: {problemDetail.time_limit_seconds}s</span>
                </div>
              </div>

              <div className="cw-sheet-body">
                <div className="problem-description markdown-content">
                  {problemDetail.description.split("\n\n").map((para: string, i: number) => (
                    <p key={i}>{para}</p>
                  ))}
                </div>

                {/* Sample Test Cases */}
                {problemDetail.test_cases && problemDetail.test_cases.length > 0 && (
                  <div className="cw-sample-cases">
                    <h3>Sample Cases</h3>
                    {problemDetail.test_cases.map((tc: any, idx: number) => (
                      <div key={idx} className="sample-case-card">
                        <div className="case-title">Example {idx + 1}</div>
                        <div className="case-io-grid">
                          <div>
                            <span className="io-label">Input</span>
                            <pre>{tc.input}</pre>
                          </div>
                          <div>
                            <span className="io-label">Expected Output</span>
                            <pre>{tc.output || tc.expected_output}</pre>
                          </div>
                        </div>
                        {tc.explanation && (
                          <div className="case-explanation">
                            <strong>Explanation:</strong> {tc.explanation}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="cw-no-problem">Select a problem to begin.</div>
          )}
        </section>

        {/* Right Column: Code Editor & Execution Panels */}
        <section className="cw-right-panel">
          {/* Editor Header Toolbar */}
          <div className="cw-editor-toolbar">
            <div className="toolbar-left">
              <label htmlFor="cw-lang-select" className="sr-only">Programming Language</label>
              <select
                id="cw-lang-select"
                className="cw-lang-dropdown"
                value={language}
                onChange={(e) => handleLanguageChange(e.target.value)}
              >
                {SUPPORTED_LANGUAGES.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="toolbar-right">
              <button className="cw-tool-btn" onClick={handleResetCode} title="Reset to Starter Code">
                Reset
              </button>
            </div>
          </div>

          {/* Monaco Editor Container */}
          <div className="cw-editor-frame">
            <Editor
              height="100%"
              language={monacoLanguage}
              theme="vs-dark"
              value={code}
              onChange={handleCodeChange}
              options={{
                fontSize: 14,
                fontFamily: "'Fira Code', 'JetBrains Mono', Consolas, monospace",
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                lineNumbers: "on",
                automaticLayout: true,
                tabSize: 4,
                wordWrap: "on",
              }}
            />
          </div>

          {/* Bottom Execution Panel */}
          <div className="cw-bottom-panel">
            <div className="cw-bottom-tabs">
              <button
                className={`tab-btn ${activeBottomTab === "cases" ? "active" : ""}`}
                onClick={() => setActiveBottomTab("cases")}
              >
                Sample Tests
              </button>
              <button
                className={`tab-btn ${activeBottomTab === "run_output" ? "active" : ""}`}
                onClick={() => setActiveBottomTab("run_output")}
              >
                Run Output {runResult && (runResult.total_passed === runResult.total_tests ? "✓" : "✗")}
              </button>
              <button
                className={`tab-btn ${activeBottomTab === "custom" ? "active" : ""}`}
                onClick={() => setActiveBottomTab("custom")}
              >
                Custom Input
              </button>
              <button
                className={`tab-btn ${activeBottomTab === "submission" ? "active" : ""}`}
                onClick={() => setActiveBottomTab("submission")}
              >
                Contest Verdict {submitResult && (submitResult.status === "Accepted" ? "🏆" : "⚠")}
              </button>

              <div className="action-buttons-wrap">
                <button
                  className="cw-btn cw-btn-run"
                  onClick={handleRunCode}
                  disabled={running || submitting}
                  title="Run sample test cases (Ctrl + Enter)"
                >
                  {running ? "Running..." : "▶ Run Code"}
                </button>
                <button
                  className="cw-btn cw-btn-submit"
                  onClick={handleSubmitCode}
                  disabled={running || submitting || isTimeUp}
                  title="Submit to Contest (Evaluates full hidden test suite)"
                >
                  {submitting ? "Evaluating..." : "🚀 Submit Solution"}
                </button>
              </div>
            </div>

            <div className="cw-bottom-content">
              {/* Tab 1: Sample Test Cases */}
              {activeBottomTab === "cases" && (
                <div className="tab-pane-cases">
                  {problemDetail?.test_cases && problemDetail.test_cases.length > 0 ? (
                    <div className="cases-selector">
                      <div className="case-pills">
                        {problemDetail.test_cases.map((_: any, i: number) => (
                          <button
                            key={i}
                            className={`case-pill ${selectedCaseIndex === i ? "active" : ""}`}
                            onClick={() => setSelectedCaseIndex(i)}
                          >
                            Case {i + 1}
                          </button>
                        ))}
                      </div>
                      <div className="case-preview">
                        <div className="io-block">
                          <label>Input:</label>
                          <pre>{problemDetail.test_cases[selectedCaseIndex]?.input}</pre>
                        </div>
                        <div className="io-block">
                          <label>Expected Output:</label>
                          <pre>{problemDetail.test_cases[selectedCaseIndex]?.output || (problemDetail.test_cases[selectedCaseIndex] as any)?.expected_output}</pre>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="no-cases-msg">No sample cases specified for this problem.</p>
                  )}
                </div>
              )}

              {/* Tab 2: Run Output */}
              {activeBottomTab === "run_output" && (
                <div className="tab-pane-output">
                  {running ? (
                    <div className="execution-spinner">Executing against sample test cases in secure sandbox...</div>
                  ) : runResult ? (
                    <div className="output-result">
                      <div className={`verdict-banner ${runResult.total_passed === runResult.total_tests ? "banner-pass" : "banner-fail"}`}>
                        {runResult.total_passed === runResult.total_tests ? "✓ All Sample Tests Passed" : `✗ Passed ${runResult.total_passed} / ${runResult.total_tests} Sample Tests`}
                        <span className="exec-time">Verdict: {runResult.status}</span>
                      </div>

                      {runResult.compile_error && (
                        <div className="compile-error-box">
                          <strong>Compilation / Runtime Error:</strong>
                          <pre>{runResult.compile_error}</pre>
                        </div>
                      )}

                      {runResult.results && (
                        <div className="case-results-list">
                          {runResult.results.map((r, i) => (
                            <div key={i} className={`case-result-row ${r.passed ? "pass" : "fail"}`}>
                              <span className="case-index">Case {i + 1}:</span>
                              <span className="case-badge">{r.passed ? "PASSED" : "FAILED"}</span>
                              <div className="case-io-details">
                                <div><strong>Output:</strong> <code>{r.actual_output || "<none>"}</code></div>
                                <div><strong>Expected:</strong> <code>{r.expected_output}</code></div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="empty-output-msg">Click "Run Code" to test your solution against sample cases.</p>
                  )}
                </div>
              )}

              {/* Tab 3: Custom Input */}
              {activeBottomTab === "custom" && (
                <div className="tab-pane-custom">
                  <div className="custom-input-form">
                    <label>Standard Input (stdin):</label>
                    <textarea
                      value={customInput}
                      onChange={(e) => setCustomInput(e.target.value)}
                      placeholder="Paste or type custom test input here..."
                      rows={3}
                    />
                    <button
                      className="cw-btn cw-btn-custom-run"
                      onClick={handleRunCustom}
                      disabled={runningCustom}
                    >
                      {runningCustom ? "Running..." : "Test Custom Input"}
                    </button>
                  </div>

                  {customResult && (
                    <div className="custom-output-box">
                      <label>Program Output (stdout):</label>
                      <pre>{customResult.stdout || "<No stdout produced>"}</pre>
                      {customResult.stderr && (
                        <div className="custom-error">
                          <label>Stderr / Diagnostic:</label>
                          <pre>{customResult.stderr}</pre>
                        </div>
                      )}
                      <span className="time-tag">Executed in {customResult.runtime.toFixed(1)} ms</span>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 4: Contest Submission Result */}
              {activeBottomTab === "submission" && (
                <div className="tab-pane-submission">
                  {submitting ? (
                    <div className="execution-spinner">Running solution against all hidden contest tests...</div>
                  ) : submitResult ? (
                    <div className="submission-result-card">
                      <div className={`verdict-header ${submitResult.status === "Accepted" ? "verdict-accepted" : "verdict-rejected"}`}>
                        <div className="verdict-name">{submitResult.status}</div>
                        <div className="verdict-score">
                          Score Awarded: <strong>{submitResult.points_awarded || submitResult.score} pts</strong>
                        </div>
                      </div>

                      <div className="submission-metrics-grid">
                        <div className="metric-cell">
                          <span className="label">Tests Passed</span>
                          <span className="val">{submitResult.passed_tests} / {submitResult.total_tests}</span>
                        </div>
                        <div className="metric-cell">
                          <span className="label">Execution Time</span>
                          <span className="val">{submitResult.execution_time.toFixed(1)} ms</span>
                        </div>
                        <div className="metric-cell">
                          <span className="label">Penalty Added</span>
                          <span className="val">{submitResult.penalty_minutes} mins</span>
                        </div>
                        <div className="metric-cell">
                          <span className="label">Contest Standings</span>
                          <button
                            className="standings-link-btn"
                            onClick={() => window.open(`/contests/${contestId}/leaderboard`, "_blank")}
                          >
                            View Leaderboard →
                          </button>
                        </div>
                      </div>

                      {submitResult.compile_error && (
                        <div className="compile-error-box">
                          <strong>Compiler Diagnostic:</strong>
                          <pre>{submitResult.compile_error}</pre>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="empty-output-msg">
                      No contest submission yet. Click "Submit Solution" to trigger competitive evaluation.
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        </section>
      </div>

      {/* Phase 7 Anti-Cheating Integration: Proctored Contest Mode */}
      {contest.is_proctored && (
        <aside className="cw-proctor-overlay" aria-label="Contest Integrity Monitoring">
          <div className="proctor-badge">
            <span className="pulse-dot" />
            LIVE PROCTOR ACTIVE
          </div>
          <AntiCheatingMonitor
            interviewId={`contest-${contest.id}`}
            onIncidentDetected={() => setViolationCount((c) => c + 1)}
          />
          {violationCount > 0 && (
            <div className="proctor-warning-pill">
              ⚠ {violationCount} Integrity Flag{violationCount > 1 ? "s" : ""}
            </div>
          )}
        </aside>
      )}
    </div>
  )
}
