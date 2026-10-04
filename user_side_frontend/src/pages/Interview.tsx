import {
  useEffect,
  useRef,
  useState,
  useCallback,
  type FormEvent,
} from "react"
import {
  useNavigate,
  useParams,
} from "react-router-dom"
import {
  generateFollowup,
  syncInterviewTranscript,
  type FollowupResponse,
  type TranscriptEntry,
} from "../services/api"
import AntiCheatingMonitor from "../components/AntiCheatingMonitor"
import AIAvatar, { type AvatarState } from "../components/AIAvatar"
import { useTextToSpeech } from "../hooks/useTextToSpeech"
import { useSpeechToText } from "../hooks/useSpeechToText"
import "./Interview.css"

const API_BASE_URL = "http://127.0.0.1:8000/api/v1"

interface InterviewData {
  id: string
  user_id?: string
  job_role: string
  difficulty: string
  status: string
  questions: string | null
  answers: string | null
  score: number | null
  feedback?: string | null
  strengths?: string | null
  weaknesses?: string | null
  started_at?: string | null
  completed_at?: string | null
  created_at?: string
  updated_at?: string
}

export interface InterviewQuestion {
  text: string
  isFollowUp?: boolean
  difficulty?: string
  reason?: string
}

export default function Interview() {
  const { interviewId } = useParams()
  const navigate = useNavigate()

  // Interview state
  const [interview, setInterview] = useState<InterviewData | null>(null)
  const [questions, setQuestions] = useState<InterviewQuestion[]>([])
  const [answers, setAnswers] = useState<string[]>([])
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [answer, setAnswer] = useState("")

  // Loading & status states
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [isEvaluating, setIsEvaluating] = useState(false)

  // Voice engine & mode states (Voice-first by default)
  const [voiceMode, setVoiceMode] = useState(true)
  const [microphoneEnabled, setMicrophoneEnabled] = useState(false)
  const [textFallback, setTextFallback] = useState(false)
  const [answerCaptured, setAnswerCaptured] = useState(false)
  const [adaptiveEnabled, setAdaptiveEnabled] = useState(true)
  const [isManualEditing, setIsManualEditing] = useState(false)
  const [autoSubmitSeconds, setAutoSubmitSeconds] = useState<number | null>(null)
  const [autoplayBlocked, setAutoplayBlocked] = useState(false)

  // Timer & alerts
  const [time, setTime] = useState(0)
  const [error, setError] = useState("")

  // Keep references for async callbacks and timer closures
  const questionRef = useRef(currentQuestion)
  const answerRef = useRef(answer)
  const questionsRef = useRef(questions)
  const answersRef = useRef(answers)
  const isEvaluatingRef = useRef(isEvaluating)
  const voiceModeRef = useRef(voiceMode)
  const microphoneEnabledRef = useRef(microphoneEnabled)
  const isManualEditingRef = useRef(isManualEditing)
  const followedUpIndicesRef = useRef<Set<number>>(new Set())
  const hasSpokenCurrentQRef = useRef(false)
  const evaluateAndAdvanceRef = useRef<(() => Promise<void>) | null>(null)
  const audioStartedRef = useRef(false)

  // Keep refs in sync
  useEffect(() => {
    questionRef.current = currentQuestion
  }, [currentQuestion])

  useEffect(() => {
    answerRef.current = answer
  }, [answer])

  useEffect(() => {
    questionsRef.current = questions
  }, [questions])

  useEffect(() => {
    answersRef.current = answers
  }, [answers])

  useEffect(() => {
    isEvaluatingRef.current = isEvaluating
  }, [isEvaluating])

  useEffect(() => {
    voiceModeRef.current = voiceMode
  }, [voiceMode])

  useEffect(() => {
    microphoneEnabledRef.current = microphoneEnabled
  }, [microphoneEnabled])

  useEffect(() => {
    isManualEditingRef.current = isManualEditing
  }, [isManualEditing])

  /*
   * =====================================================
   * SPEECH-TO-TEXT (STT) HOOK INTEGRATION
   * =====================================================
   */
  const handleTranscriptUpdate = useCallback((fullText: string) => {
    if (!fullText) return
    hasSpokenCurrentQRef.current = true
    answerRef.current = fullText
    setAnswer(fullText)
    setAnswerCaptured(true)

    // Save progress to state and localStorage
    setAnswers((prev) => {
      const copy = [...prev]
      copy[questionRef.current] = fullText
      return copy
    })
  }, [])

  const handleSpeechSilence = useCallback(() => {
    // If voiceMode is active, not manually editing, and candidate has provided an answer
    if (
      voiceModeRef.current &&
      !isManualEditingRef.current &&
      !isEvaluatingRef.current &&
      answerRef.current.trim().length >= 8
    ) {
      // Trigger a smooth 2-second auto-submit countdown
      setAutoSubmitSeconds(2)
    }
  }, [])

  const stt = useSpeechToText({
    silenceDelayMs: 2500,
    onTranscriptUpdate: handleTranscriptUpdate,
    onSilence: handleSpeechSilence,
    onError: (err) => {
      console.warn("STT notice:", err)
      if (err.includes("denied")) {
        setTextFallback(true)
        setVoiceMode(false)
      }
    },
  })

  /*
   * =====================================================
   * TEXT-TO-SPEECH (TTS) HOOK INTEGRATION
   * =====================================================
   */
  const handleTTSStart = useCallback(() => {
    // When AI starts speaking, strictly stop candidate mic to prevent audio collision/echo
    stt.stopListening()
    setAutoSubmitSeconds(null)
  }, [stt])

  const handleTTSEnd = useCallback(() => {
    // Once AI finishes speaking, auto-start microphone with a 300ms safety buffer
    if (
      voiceModeRef.current &&
      !isManualEditingRef.current &&
      !isEvaluatingRef.current
    ) {
      window.setTimeout(() => {
        if (
          voiceModeRef.current &&
          !isManualEditingRef.current &&
          !isEvaluatingRef.current
        ) {
          stt.resetTranscript()
          void stt.startListening()
        }
      }, 300)
    }
  }, [stt])

  const tts = useTextToSpeech({
    onStart: handleTTSStart,
    onEnd: handleTTSEnd,
    onError: (errMsg) => {
      if (errMsg.includes("not-allowed") || errMsg.includes("interrupted")) {
        setAutoplayBlocked(true)
      } else {
        setTextFallback(true)
      }
    },
  })

  /*
   * =====================================================
   * DYNAMIC AVATAR STATE
   * =====================================================
   */
  const avatarState: AvatarState = isEvaluating
    ? "processing"
    : tts.isSpeaking
      ? "speaking"
      : stt.isListening
        ? "listening"
        : starting
          ? "thinking"
          : "idle"

  /*
   * =====================================================
   * LOAD INTERVIEW
   * =====================================================
   */
  useEffect(() => {
    async function loadInterview() {
      const token = localStorage.getItem("access_token")

      if (!token) {
        navigate("/login")
        return
      }

      if (!interviewId) {
        setError("Interview ID is missing")
        setLoading(false)
        return
      }

      try {
        const response = await fetch(`${API_BASE_URL}/interview/${interviewId}`, {
          method: "GET",
          headers: {
            Accept: "application/json",
            Authorization: `Bearer ${token}`,
          },
        })

        if (response.status === 401) {
          localStorage.removeItem("access_token")
          navigate("/login")
          return
        }

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.detail || "Failed to load interview")
        }

        if (data.status === "completed") {
          navigate(`/results/${interviewId}`, { replace: true })
          return
        }

        setInterview(data)

        if (!data.questions) {
          setQuestions([])
          return
        }

        let parsedQuestions: unknown
        try {
          parsedQuestions = JSON.parse(data.questions)
        } catch {
          throw new Error("Unable to parse interview questions")
        }

        if (!Array.isArray(parsedQuestions)) {
          throw new Error("Invalid interview questions format")
        }

        const normalizedQuestions: InterviewQuestion[] = parsedQuestions.map(
          (item: unknown) => {
            if (typeof item === "string") {
              return { text: item, isFollowUp: false }
            }
            if (
              typeof item === "object" &&
              item !== null &&
              "question" in item
            ) {
              const qObj = item as { question?: unknown; difficulty?: unknown }
              return {
                text: typeof qObj.question === "string" ? qObj.question : String(qObj.question),
                isFollowUp: false,
                difficulty: typeof qObj.difficulty === "string" ? qObj.difficulty : undefined,
              }
            }
            return { text: String(item), isFollowUp: false }
          },
        )

        setQuestions(normalizedQuestions)

        const restoredAnswers = new Array(normalizedQuestions.length).fill("")

        if (data.answers) {
          const storedAnswers = String(data.answers)
          const blocks = storedAnswers.split(/\n\n(?=Question\s+\d+:)/)

          blocks.forEach((block: string, index: number) => {
            const match = block.match(/^Question\s+\d+.*:\n([\s\S]*)$/)
            if (match && index < normalizedQuestions.length) {
              restoredAnswers[index] = match[1].trim()
            }
          })
        }

        // Restore local draft answers & question index if available
        let initialQuestionIndex = 0
        try {
          const localDraftRaw = localStorage.getItem(`interview_progress_${interviewId}`)
          if (localDraftRaw) {
            const localDraft = JSON.parse(localDraftRaw)
            if (Array.isArray(localDraft.answers)) {
              localDraft.answers.forEach((ans: string, idx: number) => {
                if (ans && !restoredAnswers[idx] && idx < normalizedQuestions.length) {
                  restoredAnswers[idx] = ans
                }
              })
            }
            if (
              typeof localDraft.currentQuestion === "number" &&
              localDraft.currentQuestion >= 0 &&
              localDraft.currentQuestion < normalizedQuestions.length
            ) {
              initialQuestionIndex = localDraft.currentQuestion
            }
          }
        } catch {
          // non-blocking
        }

        if (initialQuestionIndex === 0 && data.status === "started") {
          const firstUnanswered = restoredAnswers.findIndex((ans) => !ans.trim())
          if (firstUnanswered > 0) {
            initialQuestionIndex = firstUnanswered
          }
        }

        setAnswers(restoredAnswers)
        setCurrentQuestion(initialQuestionIndex)
        setAnswer(restoredAnswers[initialQuestionIndex] || "")
      } catch (err) {
        console.error("Interview loading error:", err)
        setError(err instanceof Error ? err.message : "Something went wrong")
      } finally {
        setLoading(false)
      }
    }

    void loadInterview()
  }, [interviewId, navigate])

  /*
   * =====================================================
   * TIMER
   * =====================================================
   */
  useEffect(() => {
    if (!interview || interview.status !== "started") {
      return
    }

    const timer = window.setInterval(() => {
      setTime((prev) => prev + 1)
    }, 1000)

    return () => {
      window.clearInterval(timer)
    }
  }, [interview])

  function formatTime(seconds: number) {
    const minutes = Math.floor(seconds / 60)
    const remaining = seconds % 60
    return `${String(minutes).padStart(2, "0")}:${String(remaining).padStart(2, "0")}`
  }

  /*
   * =====================================================
   * AUTO-SPEAK QUESTION ON QUESTION CHANGE OR START
   * =====================================================
   */
  useEffect(() => {
    if (interview?.status === "started" && questions[currentQuestion]?.text) {
      setAutoSubmitSeconds(null)
      setIsManualEditing(false)
      hasSpokenCurrentQRef.current = false
      setAnswerCaptured(false)
      setAutoplayBlocked(false)

      // Automatically speak the current question
      try {
        tts.speak(questions[currentQuestion].text)
        audioStartedRef.current = true
      } catch (err) {
        console.warn("Autoplay notice:", err)
        setAutoplayBlocked(true)
      }
    }
  }, [currentQuestion, interview?.status, questions, tts])

  /*
   * =====================================================
   * AUTO-SUBMIT COUNTDOWN TIMER
   * =====================================================
   */
  useEffect(() => {
    if (autoSubmitSeconds === null) return

    if (autoSubmitSeconds <= 0) {
      setAutoSubmitSeconds(null)
      if (evaluateAndAdvanceRef.current) {
        void evaluateAndAdvanceRef.current()
      }
      return
    }

    const timer = window.setTimeout(() => {
      setAutoSubmitSeconds((prev) => (prev !== null ? prev - 1 : null))
    }, 1000)

    return () => window.clearTimeout(timer)
  }, [autoSubmitSeconds])

  /*
   * =====================================================
   * ENABLE MICROPHONE PERMISSION
   * =====================================================
   */
  const enableMicrophone = useCallback(async (): Promise<boolean> => {
    try {
      setError("")
      const granted = await stt.requestPermission()
      if (granted) {
        setMicrophoneEnabled(true)
        setVoiceMode(true)
        return true
      } else {
        setTextFallback(true)
        setVoiceMode(false)
        return false
      }
    } catch (err) {
      console.error("Microphone permission error:", err)
      setError("Microphone permission required for voice answers. Text fallback available.")
      setTextFallback(true)
      setVoiceMode(false)
      return false
    }
  }, [stt])

  /*
   * =====================================================
   * SYNC STRUCTURED TRANSCRIPT & ANSWERS HELPER
   * =====================================================
   */
  const syncAnswersToBackend = useCallback(async (updatedAnswers: string[]) => {
    const token = localStorage.getItem("access_token")
    if (!token || !interviewId) return

    const answerText = updatedAnswers
      .map((item, index) => {
        const q = questionsRef.current[index]
        const prefix = q?.isFollowUp ? `Question ${index + 1} (Follow-up)` : `Question ${index + 1}`
        return `${prefix}:\n${item.trim() || "No answer provided"}`
      })
      .join("\n\n")

    try {
      // 1. Sync legacy answers text
      await fetch(`${API_BASE_URL}/interview/${interviewId}/answers`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ answers: answerText }),
      })

      // 2. Sync persistent structured conversation transcript
      const transcriptEntries: TranscriptEntry[] = questionsRef.current.map((q, idx) => ({
        question: q.text,
        candidate_answer: updatedAnswers[idx] || "",
        timestamp: new Date().toISOString(),
        question_index: idx + 1,
        question_type: q.difficulty || "technical",
        is_followup: Boolean(q.isFollowUp),
      }))

      void syncInterviewTranscript(interviewId, transcriptEntries).catch(() => {})
    } catch {
      // non-blocking background sync
    }
  }, [interviewId])

  /*
   * =====================================================
   * COMPLETE INTERVIEW
   * =====================================================
   */
  const completeInterview = useCallback(async () => {
    const token = localStorage.getItem("access_token")
    if (!token || !interviewId) {
      navigate("/login")
      return
    }

    tts.stop()
    stt.stopListening()
    setAutoSubmitSeconds(null)

    const currentAnswer = answerRef.current.trim()
    const finalAnswers = [...answersRef.current]
    finalAnswers[questionRef.current] = currentAnswer || finalAnswers[questionRef.current] || ""

    setSubmitting(true)
    setError("")

    try {
      const answerText = finalAnswers
        .map((item, index) => {
          const q = questionsRef.current[index]
          const prefix = q?.isFollowUp ? `Question ${index + 1} (Follow-up)` : `Question ${index + 1}`
          return `${prefix}:\n${item.trim() || "No answer provided"}`
        })
        .join("\n\n")

      // 1. Save final answers
      const saveResponse = await fetch(
        `${API_BASE_URL}/interview/${interviewId}/answers`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ answers: answerText }),
        },
      )

      if (saveResponse.status === 401) {
        localStorage.removeItem("access_token")
        navigate("/login")
        return
      }

      const saveData = await saveResponse.json()
      if (!saveResponse.ok) {
        throw new Error(saveData.detail || "Failed to save answers")
      }

      // 2. Sync final structured transcript
      const finalTranscriptEntries: TranscriptEntry[] = questionsRef.current.map((q, idx) => ({
        question: q.text,
        candidate_answer: finalAnswers[idx] || "",
        timestamp: new Date().toISOString(),
        question_index: idx + 1,
        question_type: q.difficulty || "technical",
        is_followup: Boolean(q.isFollowUp),
      }))

      await syncInterviewTranscript(interviewId, finalTranscriptEntries).catch(() => {})

      // 3. Complete interview (triggers scoring evaluation)
      const completeResponse = await fetch(
        `${API_BASE_URL}/interview/${interviewId}/complete`,
        {
          method: "POST",
          headers: {
            Accept: "application/json",
            Authorization: `Bearer ${token}`,
          },
        },
      )

      if (completeResponse.status === 401) {
        localStorage.removeItem("access_token")
        navigate("/login")
        return
      }

      const completeData = await completeResponse.json()
      if (!completeResponse.ok) {
        throw new Error(completeData.detail || "Failed to complete interview")
      }

      try {
        localStorage.removeItem(`interview_progress_${interviewId}`)
      } catch {}

      navigate(`/results/${interviewId}`)
    } catch (err) {
      console.error("Complete interview error:", err)
      setError(err instanceof Error ? err.message : "Failed to complete interview")
    } finally {
      setSubmitting(false)
    }
  }, [interviewId, navigate, tts, stt])

  /*
   * =====================================================
   * EVALUATE ANSWER & ADAPTIVE FOLLOW-UP FLOW
   * =====================================================
   */
  const evaluateAndAdvance = useCallback(async () => {
    const currentIdx = questionRef.current
    const currentVal = answerRef.current.trim()

    if (!currentVal) {
      return
    }

    setAutoSubmitSeconds(null)
    tts.stop()
    stt.stopListening()

    // Save current answer
    const updatedAnswers = [...answersRef.current]
    updatedAnswers[currentIdx] = currentVal
    setAnswers(updatedAnswers)
    answersRef.current = updatedAnswers

    try {
      localStorage.setItem(
        `interview_progress_${interviewId}`,
        JSON.stringify({
          currentQuestion: currentIdx + 1,
          answers: updatedAnswers,
        }),
      )
    } catch {}

    void syncAnswersToBackend(updatedAnswers)

    const currentQ = questionsRef.current[currentIdx]
    const alreadyFollowedUp = followedUpIndicesRef.current.has(currentIdx)

    // Check if we should generate an adaptive follow-up
    if (
      adaptiveEnabled &&
      interviewId &&
      currentQ &&
      !currentQ.isFollowUp &&
      !alreadyFollowedUp &&
      currentVal.length >= 10
    ) {
      setIsEvaluating(true)
      try {
        const history = questionsRef.current.slice(0, currentIdx).map((q, idx) => ({
          role: "assistant",
          content: `${q.text} (Candidate answered: ${answersRef.current[idx] || ""})`,
        }))

        const followup: FollowupResponse = await generateFollowup(
          interviewId,
          currentQ.text,
          currentVal,
          history,
        )

        if (followup && followup.should_follow_up && followup.question) {
          followedUpIndicesRef.current.add(currentIdx)

          const newQuestionItem: InterviewQuestion = {
            text: followup.question,
            isFollowUp: true,
            difficulty: followup.difficulty || "medium",
            reason: followup.reason,
          }

          const newQuestions = [...questionsRef.current]
          newQuestions.splice(currentIdx + 1, 0, newQuestionItem)
          setQuestions(newQuestions)
          questionsRef.current = newQuestions

          const newAnswersList = [...updatedAnswers]
          newAnswersList.splice(currentIdx + 1, 0, "")
          setAnswers(newAnswersList)
          answersRef.current = newAnswersList

          setCurrentQuestion(currentIdx + 1)
          setAnswer("")
          answerRef.current = ""
          setAnswerCaptured(false)
          setIsManualEditing(false)
          hasSpokenCurrentQRef.current = false
          setIsEvaluating(false)
          return
        }
      } catch (err) {
        console.warn("Follow-up generation failed, proceeding to next question:", err)
      } finally {
        setIsEvaluating(false)
      }
    }

    // Advance to next question or complete interview
    if (currentIdx < questionsRef.current.length - 1) {
      setCurrentQuestion(currentIdx + 1)
      const nextSavedAnswer = answersRef.current[currentIdx + 1] || ""
      setAnswer(nextSavedAnswer)
      answerRef.current = nextSavedAnswer
      setAnswerCaptured(Boolean(nextSavedAnswer.trim()))
      setIsManualEditing(false)
      hasSpokenCurrentQRef.current = false
      setIsEvaluating(false)
    } else {
      void completeInterview()
    }
  }, [adaptiveEnabled, completeInterview, interviewId, syncAnswersToBackend, tts, stt])

  // Keep ref up to date for closure timers
  useEffect(() => {
    evaluateAndAdvanceRef.current = evaluateAndAdvance
  }, [evaluateAndAdvance])

  /*
   * =====================================================
   * START INTERVIEW (USER GESTURE TRIGGERS AUTOPLAY & MIC)
   * =====================================================
   */
  async function startInterview() {
    const token = localStorage.getItem("access_token")
    if (!token || !interviewId) {
      navigate("/login")
      return
    }

    setStarting(true)
    setError("")

    try {
      // 1. Request microphone permission on user gesture
      const micGranted = await enableMicrophone()

      // 2. Start session via API
      const response = await fetch(`${API_BASE_URL}/interview/${interviewId}/start`, {
        method: "POST",
        headers: {
          Accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
      })

      const data = await response.json()

      if (response.status === 401) {
        localStorage.removeItem("access_token")
        navigate("/login")
        return
      }

      if (!response.ok) {
        throw new Error(data.detail || "Unable to start interview")
      }

      setInterview(data.interview)
      setVoiceMode(micGranted)

      // 3. Immediately speak Question 1 on user gesture
      const firstQ = questionsRef.current[0]?.text
      if (firstQ) {
        tts.speak(firstQ)
        audioStartedRef.current = true
      }
    } catch (err) {
      console.error("Start interview error:", err)
      setError(err instanceof Error ? err.message : "Unable to start interview")
    } finally {
      setStarting(false)
    }
  }

  /*
   * =====================================================
   * UNLOCK AUTOPLAY IF RESTRICTED
   * =====================================================
   */
  const handleUnlockAudio = useCallback(() => {
    setAutoplayBlocked(false)
    const currentQText = questions[currentQuestion]?.text
    if (currentQText) {
      tts.speak(currentQText)
      audioStartedRef.current = true
    }
    if (!microphoneEnabled) {
      void enableMicrophone()
    }
  }, [currentQuestion, enableMicrophone, microphoneEnabled, questions, tts])

  /*
   * =====================================================
   * PREVIOUS QUESTION
   * =====================================================
   */
  function previousQuestion() {
    if (currentQuestion === 0) return

    setAutoSubmitSeconds(null)
    tts.stop()
    stt.stopListening()
    setError("")

    const currentVal = answerRef.current.trim()
    if (currentVal) {
      const updatedAnswers = [...answers]
      updatedAnswers[currentQuestion] = currentVal
      setAnswers(updatedAnswers)
      void syncAnswersToBackend(updatedAnswers)
    }

    const prevIndex = currentQuestion - 1
    setCurrentQuestion(prevIndex)
    const prevAnswer = answers[prevIndex] || ""
    setAnswer(prevAnswer)
    answerRef.current = prevAnswer
    setAnswerCaptured(Boolean(prevAnswer.trim()))
    setIsManualEditing(false)
  }

  /*
   * =====================================================
   * MANUAL NEXT QUESTION CLICK
   * =====================================================
   */
  function handleNextClick() {
    const currentVal = answerRef.current.trim()
    if (!currentVal) {
      setError("Please answer the question before continuing.")
      return
    }
    setError("")
    setAutoSubmitSeconds(null)
    void evaluateAndAdvance()
  }

  /*
   * =====================================================
   * FORM SUBMIT
   * =====================================================
   */
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAutoSubmitSeconds(null)
    if (currentQuestion === questions.length - 1) {
      void completeInterview()
    } else {
      handleNextClick()
    }
  }

  /*
   * =====================================================
   * CLEANUP
   * =====================================================
   */
  useEffect(() => {
    return () => {
      tts.stop()
      stt.stopListening()
    }
  }, [tts, stt])

  /*
   * =====================================================
   * LOADING SCREEN
   * =====================================================
   */
  if (loading) {
    return (
      <main className="interview-page">
        <div className="interview-loading">
          <div className="loading-spinner" />
          <p>Preparing your AI interview...</p>
        </div>
      </main>
    )
  }

  /*
   * =====================================================
   * ERROR SCREEN
   * =====================================================
   */
  if (!interview) {
    return (
      <main className="interview-page">
        <div className="interview-error">
          <h2>Unable to load interview</h2>
          <p>{error || "Something went wrong."}</p>
          <button type="button" onClick={() => navigate("/dashboard")}>
            Back to Dashboard
          </button>
        </div>
      </main>
    )
  }

  /*
   * =====================================================
   * PRE-INTERVIEW SCREEN (START INTERVIEW USER GESTURE)
   * =====================================================
   */
  if (interview.status === "created") {
    return (
      <main className="interview-page">
        <div className="pre-interview-card">
          {/* AI AVATAR PREVIEW */}
          <div style={{ maxWidth: 440, margin: "0 auto 28px" }}>
            <AIAvatar
              state="idle"
              interviewerName="AI Lead Interviewer"
              jobRole={interview.job_role}
            />
          </div>

          <div className="ai-badge">VOICE-FIRST AI INTERVIEW</div>

          <h1>Your AI Interviewer Is Ready</h1>

          <p>
            You are about to begin a live voice interview for the{" "}
            <strong>{interview.job_role}</strong> position.
          </p>

          <div className="interview-info">
            <div>
              <span>ROLE</span>
              <strong>{interview.job_role}</strong>
            </div>
            <div>
              <span>DIFFICULTY</span>
              <strong>{interview.difficulty}</strong>
            </div>
            <div>
              <span>QUESTIONS</span>
              <strong>{questions.length}</strong>
            </div>
          </div>

          <div className="voice-notice">
            <span>🎙️</span>
            <p>
              <strong>Voice-First Experience:</strong> The AI interviewer speaks questions aloud and listens automatically when you reply. Your spoken words are transcribed in real time and automatically submitted when you finish speaking.
            </p>
          </div>

          <div className="voice-notice" style={{ borderColor: "rgba(168, 85, 247, 0.35)", background: "rgba(168, 85, 247, 0.08)" }}>
            <span>🛡️</span>
            <p>
              <strong>Proctoring Active:</strong> Anti-cheating and face monitoring run concurrently to verify session integrity.
            </p>
          </div>

          {error && <div className="interview-alert">{error}</div>}

          <button
            type="button"
            className="begin-button"
            onClick={() => {
              void startInterview()
            }}
            disabled={starting}
          >
            {starting ? "Starting Voice Interview..." : "Start Voice Interview →"}
          </button>

          <button
            type="button"
            className="cancel-button"
            onClick={() => navigate("/dashboard")}
          >
            Back to Dashboard
          </button>
        </div>
      </main>
    )
  }

  /*
   * =====================================================
   * NO QUESTIONS SCREEN
   * =====================================================
   */
  if (questions.length === 0) {
    return (
      <main className="interview-page">
        <div className="interview-error">
          <h2>No questions available</h2>
          <p>The AI interviewer did not generate any questions.</p>
          <button type="button" onClick={() => navigate("/dashboard")}>
            Back to Dashboard
          </button>
        </div>
      </main>
    )
  }

  /*
   * =====================================================
   * MAIN INTERVIEW SCREEN
   * =====================================================
   */
  const progress = ((currentQuestion + 1) / questions.length) * 100
  const currentQuestionItem = questions[currentQuestion] || { text: "", isFollowUp: false }
  const isLastQuestion = currentQuestion === questions.length - 1

  return (
    <main className="interview-page">
      {/* HEADER */}
      <header className="interview-header">
        <button
          type="button"
          className="exit-button"
          onClick={() => navigate("/dashboard")}
        >
          ← Exit
        </button>

        <div className="header-title">
          <div className="voice-first-active-pill">
            <span className="pulse-dot" />
            <span>{voiceMode ? "Voice-First Active" : "Typing Mode"}</span>
          </div>
          <strong>{interview.job_role}</strong>
        </div>

        <div className="timer">⏱ {formatTime(time)}</div>
      </header>

      {/* PROGRESS BAR */}
      <div className="progress-container">
        <div className="progress-bar" style={{ width: `${progress}%` }} />
      </div>

      <section className="interview-content">
        {/* AUTOPLAY UNLOCK BANNER IF BROWSER RESTRICTED AUDIO */}
        {autoplayBlocked && (
          <div className="autoplay-unlock-banner">
            <span>🔊 Browser paused initial audio playback. Click to enable speech synthesis.</span>
            <button type="button" onClick={handleUnlockAudio}>
              Enable Audio & Voice
            </button>
          </div>
        )}

        {/* MICROPHONE PERMISSION PROMPT IF NOT GRANTED */}
        {!microphoneEnabled && !textFallback && (
          <div className="microphone-permission-card">
            <div className="permission-icon">🎙️</div>
            <div className="permission-content">
              <strong>Enable Microphone for Voice-First Mode</strong>
              <p>The AI will automatically listen as soon as it finishes asking each question.</p>
            </div>
            <button
              type="button"
              onClick={() => {
                void enableMicrophone()
              }}
            >
              Allow Microphone
            </button>
          </div>
        )}

        {/* TEXT FALLBACK BANNER */}
        {textFallback && (
          <div className="text-fallback-banner">
            <span>
              ℹ️ Voice mode paused or microphone unavailable. You can type answers smoothly below.
            </span>
            <button
              type="button"
              className="voice-action-btn"
              style={{ padding: "4px 10px", fontSize: 11 }}
              onClick={() => {
                setTextFallback(false)
                void enableMicrophone()
              }}
            >
              Retry Voice
            </button>
          </div>
        )}

        {/* INTERVIEW STAGE GRID: VOICE AI AVATAR + PROCTORING MONITOR */}
        <div className="interview-stage-grid">
          {/* AI INTERVIEWER AVATAR */}
          <AIAvatar
            state={avatarState}
            interviewerName="AI Lead Interviewer"
            jobRole={interview.job_role}
            isMuted={tts.isMuted}
            isSpeaking={tts.isSpeaking}
            isPaused={tts.isPaused}
            onReplay={tts.replay}
            onToggleMute={tts.toggleMute}
            onPauseResume={tts.isPaused ? tts.resume : tts.pause}
          />

          {/* LIVE ANTI-CHEATING PROCTORING MONITOR */}
          <AntiCheatingMonitor
            interviewId={interviewId || ""}
            isActive={!submitting}
          />
        </div>

        {/* QUESTION & ANSWER CARD */}
        <div className="question-card">
          <div className="question-number">
            QUESTION {currentQuestion + 1} OF {questions.length}
          </div>

          {/* ADAPTIVE FOLLOW-UP TAG */}
          {currentQuestionItem.isFollowUp && (
            <div className="adaptive-followup-tag">
              ⚡ Adaptive Follow-up {currentQuestionItem.difficulty ? `• ${currentQuestionItem.difficulty}` : ""}
            </div>
          )}

          {/* QUESTION TEXT DISPLAY */}
          <h1>{currentQuestionItem.text}</h1>

          {currentQuestionItem.reason && (
            <p className="question-hint" style={{ fontStyle: "italic", color: "#94a3b8" }}>
              Focus: {currentQuestionItem.reason}
            </p>
          )}

          <div className="question-line" />

          {/* AUTO-SUBMIT COUNTDOWN BANNER */}
          {autoSubmitSeconds !== null && (
            <div className="auto-submit-pill">
              <span>
                ⚡ Silence detected • Auto-submitting in <strong>{autoSubmitSeconds}s</strong>...
              </span>
              <button
                type="button"
                onClick={() => {
                  setAutoSubmitSeconds(null)
                  setIsManualEditing(true)
                  stt.stopListening()
                }}
              >
                ✏️ Edit Answer (Pause)
              </button>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            {/* ANSWER HEADER */}
            <div className="answer-header">
              <span>
                YOUR ANSWER
                {answerCaptured && (
                  <span style={{ color: "#34d399", marginLeft: 8, fontSize: "0.85em" }}>
                    ✓ Captured via Voice
                  </span>
                )}
                {isManualEditing && (
                  <span style={{ color: "#fbbf24", marginLeft: 8, fontSize: "0.85em" }}>
                    (Editing manually)
                  </span>
                )}
              </span>
              <span>{answer.length} characters</span>
            </div>

            {/* LIVE SPEECH INTERIM TRANSCRIPT BANNER */}
            {stt.isListening && stt.interimTranscript && (
              <div className="live-speech-pill" style={{ marginBottom: 12 }}>
                <span className="live-dot" />
                <span>Transcribing: "{stt.interimTranscript}"</span>
              </div>
            )}

            {/* TEXT ANSWER AREA (CANDIDATE CAN FREELY EDIT TRANSCRIPT) */}
            <textarea
              value={answer}
              onFocus={() => {
                // When candidate manually clicks to type, pause auto-submission
                if (autoSubmitSeconds !== null) {
                  setAutoSubmitSeconds(null)
                }
                setIsManualEditing(true)
              }}
              onChange={(event) => {
                const val = event.target.value
                setAnswer(val)
                answerRef.current = val
                setIsManualEditing(true)
                setAutoSubmitSeconds(null)

                setAnswers((prev) => {
                  const updated = [...prev]
                  updated[currentQuestion] = val
                  try {
                    localStorage.setItem(
                      `interview_progress_${interviewId}`,
                      JSON.stringify({
                        currentQuestion,
                        answers: updated,
                      }),
                    )
                  } catch {}
                  return updated
                })
                setAnswerCaptured(Boolean(val.trim()))
              }}
              placeholder={
                voiceMode
                  ? "Speak your answer naturally — it will be transcribed and auto-submitted..."
                  : "Type your answer here..."
              }
              disabled={submitting || isEvaluating}
            />

            {/* VOICE MIC ACTION BAR */}
            <div className="voice-area">
              <button
                type="button"
                className={`mic-button ${stt.isListening ? "recording" : ""}`}
                onClick={() => {
                  if (stt.isListening) {
                    stt.stopListening()
                    setAutoSubmitSeconds(null)
                  } else {
                    setIsManualEditing(false)
                    void stt.startListening()
                  }
                }}
                disabled={submitting || tts.isSpeaking || isEvaluating}
              >
                <span className="mic-icon">🎙️</span>
                <span>
                  {stt.isListening
                    ? "Listening (Speak Now)"
                    : tts.isSpeaking
                      ? "AI Speaking..."
                      : isEvaluating
                        ? "AI Evaluating..."
                        : "Resume Voice Listening"}
                </span>
              </button>

              {/* TOGGLE MANUAL EDITING / RESUME VOICE */}
              {isManualEditing && (
                <button
                  type="button"
                  className="voice-action-btn"
                  onClick={() => {
                    setIsManualEditing(false)
                    setVoiceMode(true)
                    void stt.startListening()
                  }}
                  style={{ marginLeft: 8 }}
                >
                  🎙️ Resume Voice Mode
                </button>
              )}

              <button
                type="button"
                className={`voice-action-btn ${adaptiveEnabled ? "active" : ""}`}
                onClick={() => setAdaptiveEnabled((prev) => !prev)}
                title="Toggle adaptive follow-up questions"
                style={{ marginLeft: 8 }}
              >
                {adaptiveEnabled ? "⚡ Adaptive: ON" : "⚡ Adaptive: OFF"}
              </button>

              {/* RECORDING STATUS */}
              {stt.isListening && (
                <div className="recording-status">
                  <span className="recording-dot" />
                  <span>Listening naturally • auto-submits when you stop speaking</span>
                </div>
              )}

              {/* EVALUATING STATUS */}
              {isEvaluating && (
                <div className="recording-status">
                  <span className="status-dot-pulse" style={{ background: "#fbbf24" }} />
                  <span>AI evaluating answer & formulating follow-up...</span>
                </div>
              )}
            </div>

            {/* ERROR ALERT */}
            {error && <div className="interview-alert">{error}</div>}

            {/* FOOTER ACTIONS */}
            <div className="answer-footer">
              <button
                type="button"
                className="previous-button"
                onClick={previousQuestion}
                disabled={currentQuestion === 0 || submitting || isEvaluating}
              >
                ← Previous
              </button>

              {isLastQuestion ? (
                <button
                  type="submit"
                  className="submit-button"
                  disabled={submitting || isEvaluating || !answer.trim()}
                >
                  {submitting ? "AI Scoring Results..." : "Finish Interview ✓"}
                </button>
              ) : (
                <button
                  type="submit"
                  className="next-button"
                  disabled={submitting || isEvaluating || !answer.trim()}
                >
                  {isEvaluating ? "Evaluating..." : "Next Question →"}
                </button>
              )}
            </div>
          </form>
        </div>
      </section>
    </main>
  )
}