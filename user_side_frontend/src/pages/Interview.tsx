import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react"

import {
  useNavigate,
  useParams,
} from "react-router-dom"

import DIDAvatar from "../components/DIDAvatar"

import "./Interview.css"

const API_BASE_URL =
  "http://127.0.0.1:8000/api/v1"

const SILENCE_DELAY = 1500
const NEXT_QUESTION_DELAY = 2000

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

interface SpeechRecognitionResultLike {
  [index: number]: {
    transcript: string
  }
}

interface SpeechRecognitionEventLike {
  results: {
    [index: number]: SpeechRecognitionResultLike
  }
}

interface SpeechRecognitionLike {
  continuous: boolean
  interimResults: boolean
  lang: string
  start: () => void
  stop: () => void
  onresult:
    | ((event: SpeechRecognitionEventLike) => void)
    | null
  onend: (() => void) | null
  onerror: (() => void) | null
}

interface SpeechRecognitionConstructor {
  new (): SpeechRecognitionLike
}

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor
    webkitSpeechRecognition?: SpeechRecognitionConstructor
  }
}

function Interview() {
  const { interviewId } = useParams()
  const navigate = useNavigate()

  const [interview, setInterview] =
    useState<InterviewData | null>(null)

  const [questions, setQuestions] =
    useState<string[]>([])

  const [answers, setAnswers] =
    useState<string[]>([])

  const [currentQuestion, setCurrentQuestion] =
    useState(0)

  const [answer, setAnswer] =
    useState("")

  const [loading, setLoading] =
    useState(true)

  const [starting, setStarting] =
    useState(false)

  const [submitting, setSubmitting] =
    useState(false)

  const [isListening, setIsListening] =
    useState(false)

  const [isSpeaking, setIsSpeaking] =
    useState(false)

  const [microphoneEnabled, setMicrophoneEnabled] =
    useState(false)

  const [answerCaptured, setAnswerCaptured] =
    useState(false)

  const [autoListening, setAutoListening] =
    useState(false)

  const [autoMovingNext, setAutoMovingNext] =
    useState(false)

  const [time, setTime] =
    useState(0)

  const [error, setError] =
    useState("")

  const recognitionRef =
    useRef<SpeechRecognitionLike | null>(null)

  const silenceTimerRef =
    useRef<number | null>(null)

  const nextQuestionTimerRef =
    useRef<number | null>(null)

  const hasSpeechRef =
    useRef(false)

  const questionRef =
    useRef(currentQuestion)

  const answerRef =
    useRef(answer)

  useEffect(() => {
    questionRef.current =
      currentQuestion
  }, [currentQuestion])

  useEffect(() => {
    answerRef.current =
      answer
  }, [answer])

  /*
   * =====================================================
   * LOAD INTERVIEW
   * =====================================================
   */

  useEffect(() => {
    async function loadInterview() {
      const token =
        localStorage.getItem(
          "access_token",
        )

      if (!token) {
        navigate("/login")
        return
      }

      if (!interviewId) {
        setError(
          "Interview ID is missing",
        )

        setLoading(false)

        return
      }

      try {
        const response =
          await fetch(
            `${API_BASE_URL}/interview/${interviewId}`,
            {
              method: "GET",
              headers: {
                Accept:
                  "application/json",
                Authorization:
                  `Bearer ${token}`,
              },
            },
          )

        if (
          response.status === 401
        ) {
          localStorage.removeItem(
            "access_token",
          )

          navigate("/login")
          return
        }

        const data =
          await response.json()

        if (!response.ok) {
          throw new Error(
            data.detail ||
              "Failed to load interview",
          )
        }

        setInterview(data)

        if (!data.questions) {
          setQuestions([])
          return
        }

        let parsedQuestions: unknown

        try {
          parsedQuestions =
            JSON.parse(
              data.questions,
            )
        } catch {
          throw new Error(
            "Unable to parse interview questions",
          )
        }

        if (
          !Array.isArray(
            parsedQuestions,
          )
        ) {
          throw new Error(
            "Invalid interview questions format",
          )
        }

        const normalizedQuestions =
          parsedQuestions.map(
            (item: unknown) => {
              if (
                typeof item ===
                "string"
              ) {
                return item
              }

              if (
                typeof item ===
                  "object" &&
                item !== null &&
                "question" in item
              ) {
                const question =
                  (
                    item as {
                      question?: unknown
                    }
                  ).question

                if (
                  typeof question ===
                  "string"
                ) {
                  return question
                }
              }

              return String(item)
            },
          )

        setQuestions(
          normalizedQuestions,
        )

        const restoredAnswers =
          new Array(
            normalizedQuestions.length,
          ).fill("")

        if (data.answers) {
          const storedAnswers =
            String(data.answers)

          const blocks =
            storedAnswers.split(
              /\n\n(?=Question\s+\d+:)/,
            )

          blocks.forEach(
            (
              block: string,
              index: number,
            ) => {
              const match =
                block.match(
                  /^Question\s+\d+:\n([\s\S]*)$/,
                )

              if (match) {
                restoredAnswers[
                  index
                ] =
                  match[1].trim()
              }
            },
          )
        }

        setAnswers(
          restoredAnswers,
        )

        setAnswer(
          restoredAnswers[0] ||
            "",
        )
      } catch (err) {
        console.error(
          "Interview loading error:",
          err,
        )

        setError(
          err instanceof Error
            ? err.message
            : "Something went wrong",
        )
      } finally {
        setLoading(false)
      }
    }

    void loadInterview()
  }, [
    interviewId,
    navigate,
  ])

  /*
   * =====================================================
   * TIMER
   * =====================================================
   */

  useEffect(() => {
    if (
      !interview ||
      interview.status !==
        "started"
    ) {
      return
    }

    const timer =
      window.setInterval(() => {
        setTime(
          (previous) =>
            previous + 1,
        )
      }, 1000)

    return () => {
      window.clearInterval(
        timer,
      )
    }
  }, [interview])

  function formatTime(
    seconds: number,
  ) {
    const minutes =
      Math.floor(
        seconds / 60,
      )

    const remaining =
      seconds % 60

    return `${String(
      minutes,
    ).padStart(
      2,
      "0",
    )}:${String(
      remaining,
    ).padStart(
      2,
      "0",
    )}`
  }

  /*
   * =====================================================
   * CLEAR TIMERS
   * =====================================================
   */

  function clearSilenceTimer() {
    if (
      silenceTimerRef.current !==
      null
    ) {
      window.clearTimeout(
        silenceTimerRef.current,
      )

      silenceTimerRef.current =
        null
    }
  }

  function clearNextQuestionTimer() {
    if (
      nextQuestionTimerRef.current !==
      null
    ) {
      window.clearTimeout(
        nextQuestionTimerRef.current,
      )

      nextQuestionTimerRef.current =
        null
    }
  }

  /*
   * =====================================================
   * ENABLE MICROPHONE
   * =====================================================
   */

  async function enableMicrophone() {
    try {
      setError("")

      const stream =
        await navigator.mediaDevices.getUserMedia(
          {
            audio: true,
          },
        )

      stream
        .getTracks()
        .forEach(
          (track) =>
            track.stop(),
        )

      setMicrophoneEnabled(
        true,
      )
    } catch (err) {
      console.error(
        "Microphone permission error:",
        err,
      )

      setError(
        "Microphone permission is required. Please allow microphone access in your browser.",
      )
    }
  }

  /*
   * =====================================================
   * START INTERVIEW
   * =====================================================
   */

  async function startInterview() {
    const token =
      localStorage.getItem(
        "access_token",
      )

    if (
      !token ||
      !interviewId
    ) {
      navigate("/login")
      return
    }

    setStarting(true)
    setError("")

    try {
      const response =
        await fetch(
          `${API_BASE_URL}/interview/${interviewId}/start`,
          {
            method: "POST",
            headers: {
              Accept:
                "application/json",
              Authorization:
                `Bearer ${token}`,
            },
          },
        )

      const data =
        await response.json()

      if (
        response.status ===
        401
      ) {
        localStorage.removeItem(
          "access_token",
        )

        navigate("/login")
        return
      }

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Unable to start interview",
        )
      }

      setInterview(
        data.interview,
      )
    } catch (err) {
      console.error(
        "Start interview error:",
        err,
      )

      setError(
        err instanceof Error
          ? err.message
          : "Unable to start interview",
      )
    } finally {
      setStarting(false)
    }
  }

  /*
   * =====================================================
   * AUTOMATIC NEXT QUESTION
   * =====================================================
   */

  function scheduleNextQuestion() {
    const index =
      questionRef.current

    if (
      index >=
      questions.length - 1
    ) {
      return
    }

    if (
      !hasSpeechRef.current
    ) {
      return
    }

    clearNextQuestionTimer()

    setAutoMovingNext(
      true,
    )

    nextQuestionTimerRef.current =
      window.setTimeout(
        () => {
          setAutoMovingNext(
            false,
          )

          hasSpeechRef.current =
            false

          setCurrentQuestion(
            (previous) =>
              previous + 1,
          )
        },
        NEXT_QUESTION_DELAY,
      )
  }

  /*
   * =====================================================
   * SILENCE DETECTION
   * =====================================================
   */

  function stopListeningAfterSilence() {
    clearSilenceTimer()

    if (
      !recognitionRef.current
    ) {
      return
    }

    if (
      !hasSpeechRef.current
    ) {
      return
    }

    const currentAnswer =
      answerRef.current.trim()

    if (!currentAnswer) {
      return
    }

    recognitionRef.current.stop()

    recognitionRef.current =
      null

    setIsListening(false)
    setAutoListening(false)
    setAnswerCaptured(true)

    /*
     * Move automatically unless this
     * is the final question.
     */

    if (
      questionRef.current <
      questions.length - 1
    ) {
      scheduleNextQuestion()
    }
  }

  function resetSilenceTimer() {
    clearSilenceTimer()

    if (
      !hasSpeechRef.current
    ) {
      return
    }

    silenceTimerRef.current =
      window.setTimeout(
        () => {
          stopListeningAfterSilence()
        },
        SILENCE_DELAY,
      )
  }

  /*
   * =====================================================
   * START LISTENING
   * =====================================================
   */

  function startListening() {
    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition

    if (!SpeechRecognition) {
      setError(
        "Voice recognition is not supported. Please use Google Chrome or Microsoft Edge.",
      )

      return
    }

    if (
      !microphoneEnabled
    ) {
      setError(
        "Please enable your microphone first.",
      )

      return
    }

    if (isSpeaking) {
      return
    }

    if (isListening) {
      return
    }

    if (autoMovingNext) {
      return
    }

    clearSilenceTimer()
    clearNextQuestionTimer()

    setAutoMovingNext(false)
    setError("")
    setAnswerCaptured(false)

    hasSpeechRef.current =
      false

    const recognition =
      new SpeechRecognition()

    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = "en-IN"

    const baseAnswer =
      answerRef.current.trim()

    recognition.onresult =
      (event) => {
        let transcript =
          ""

        const resultCount =
          Object.keys(
            event.results,
          ).length

        for (
          let i = 0;
          i < resultCount;
          i++
        ) {
          const result =
            event.results[i]

          if (
            result?.[0]
          ) {
            transcript +=
              result[0]
                .transcript
          }
        }

        transcript =
          transcript.trim()

        if (!transcript) {
          return
        }

        hasSpeechRef.current =
          true

        const combined =
          baseAnswer
            ? `${baseAnswer} ${transcript}`.trim()
            : transcript

        answerRef.current =
          combined

        setAnswer(
          combined,
        )

        setAnswers(
          (previous) => {
            const updated =
              [...previous]

            updated[
              questionRef.current
            ] = combined

            return updated
          },
        )

        setAnswerCaptured(
          true,
        )

        /*
         * New speech = reset silence countdown.
         */

        resetSilenceTimer()
      }

    recognition.onend =
      () => {
        setIsListening(false)
        setAutoListening(false)

        recognitionRef.current =
          null
      }

    recognition.onerror =
      () => {
        clearSilenceTimer()

        setIsListening(false)
        setAutoListening(false)

        recognitionRef.current =
          null
      }

    recognitionRef.current =
      recognition

    try {
      recognition.start()

      setIsListening(true)
      setAutoListening(
        true,
      )
    } catch (err) {
      console.error(
        "Speech recognition error:",
        err,
      )

      recognitionRef.current =
        null

      setIsListening(false)
      setAutoListening(false)
    }
  }

  /*
   * =====================================================
   * MANUAL STOP
   * =====================================================
   */

  function stopListening() {
    clearSilenceTimer()

    recognitionRef.current?.stop()

    recognitionRef.current =
      null

    setIsListening(false)
    setAutoListening(false)

    if (
      answerRef.current.trim()
    ) {
      setAnswerCaptured(
        true,
      )
    }
  }

  /*
   * =====================================================
   * AUTOMATIC LISTENING
   * =====================================================
   */

  useEffect(() => {
    if (
      !interview ||
      interview.status !==
        "started"
    ) {
      return
    }

    if (
      !microphoneEnabled
    ) {
      return
    }

    if (isSpeaking) {
      return
    }

    if (isListening) {
      return
    }

    if (autoMovingNext) {
      return
    }

    if (
      answerRef.current.trim()
    ) {
      return
    }

    const timer =
      window.setTimeout(
        () => {
          startListening()
        },
        900,
      )

    return () => {
      window.clearTimeout(
        timer,
      )
    }
  }, [
    isSpeaking,
    isListening,
    microphoneEnabled,
    currentQuestion,
    interview,
    autoMovingNext,
  ])

  /*
   * =====================================================
   * QUESTION CHANGE
   * =====================================================
   */

  useEffect(() => {
    clearSilenceTimer()
    clearNextQuestionTimer()

    setAutoMovingNext(false)

    const savedAnswer =
      answers[currentQuestion] ||
      ""

    answerRef.current =
      savedAnswer

    hasSpeechRef.current =
      false

    setAnswer(
      savedAnswer,
    )

    setAnswerCaptured(
      Boolean(
        savedAnswer.trim(),
      ),
    )

    recognitionRef.current?.stop()

    recognitionRef.current =
      null

    setIsListening(false)
    setAutoListening(false)
  }, [
    currentQuestion,
  ])

  /*
   * =====================================================
   * ANSWER CHANGE
   * =====================================================
   */

  function handleAnswerChange(
    value: string,
  ) {
    answerRef.current =
      value

    setAnswer(value)

    setAnswers(
      (previous) => {
        const updated =
          [...previous]

        updated[
          currentQuestion
        ] = value

        return updated
      },
    )

    setAnswerCaptured(
      Boolean(value.trim()),
    )
  }

  /*
   * =====================================================
   * NEXT QUESTION MANUALLY
   * =====================================================
   */

  function nextQuestion() {
    if (
      !answerRef.current.trim()
    ) {
      setError(
        "Please answer the question before continuing.",
      )

      return
    }

    stopListening()

    clearNextQuestionTimer()

    setAutoMovingNext(false)
    setError("")

    if (
      currentQuestion <
      questions.length - 1
    ) {
      setCurrentQuestion(
        (previous) =>
          previous + 1,
      )
    }
  }

  /*
   * =====================================================
   * PREVIOUS QUESTION
   * =====================================================
   */

  function previousQuestion() {
    if (
      currentQuestion ===
      0
    ) {
      return
    }

    stopListening()

    clearNextQuestionTimer()

    setAutoMovingNext(false)
    setError("")

    setCurrentQuestion(
      (previous) =>
        previous - 1,
    )
  }

  /*
   * =====================================================
   * COMPLETE INTERVIEW
   * =====================================================
   */

  async function completeInterview() {
    const token =
      localStorage.getItem(
        "access_token",
      )

    if (
      !token ||
      !interviewId
    ) {
      navigate("/login")
      return
    }

    const currentAnswer =
      answerRef.current.trim()

    if (!currentAnswer) {
      setError(
        "Please answer the final question.",
      )

      return
    }

    stopListening()

    clearSilenceTimer()
    clearNextQuestionTimer()

    const finalAnswers =
      [...answers]

    finalAnswers[
      currentQuestion
    ] = currentAnswer

    setSubmitting(true)
    setError("")

    try {
      const answerText =
        finalAnswers
          .map(
            (
              item,
              index,
            ) =>
              `Question ${
                index + 1
              }:\n${
                item.trim() ||
                "No answer provided"
              }`,
          )
          .join("\n\n")

      /*
       * SAVE ANSWERS
       */

      const saveResponse =
        await fetch(
          `${API_BASE_URL}/interview/${interviewId}/answers`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",

              Accept:
                "application/json",

              Authorization:
                `Bearer ${token}`,
            },

            body: JSON.stringify({
              answers:
                answerText,
            }),
          },
        )

      const saveData =
        await saveResponse.json()

      if (
        saveResponse.status ===
        401
      ) {
        localStorage.removeItem(
          "access_token",
        )

        navigate("/login")

        return
      }

      if (!saveResponse.ok) {
        throw new Error(
          saveData.detail ||
            "Failed to save answers",
        )
      }

      /*
       * COMPLETE INTERVIEW
       */

      const completeResponse =
        await fetch(
          `${API_BASE_URL}/interview/${interviewId}/complete`,
          {
            method: "POST",

            headers: {
              Accept:
                "application/json",

              Authorization:
                `Bearer ${token}`,
            },
          },
        )

      const completeData =
        await completeResponse.json()

      if (
        completeResponse.status ===
        401
      ) {
        localStorage.removeItem(
          "access_token",
        )

        navigate("/login")

        return
      }

      if (
        !completeResponse.ok
      ) {
        throw new Error(
          completeData.detail ||
            "Failed to complete interview",
        )
      }

      navigate(
        `/results/${interviewId}`,
      )
    } catch (err) {
      console.error(
        "Complete interview error:",
        err,
      )

      setError(
        err instanceof Error
          ? err.message
          : "Failed to complete interview",
      )
    } finally {
      setSubmitting(false)
    }
  }

  /*
   * =====================================================
   * FORM SUBMIT
   * =====================================================
   */

  function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    if (
      currentQuestion ===
      questions.length - 1
    ) {
      void completeInterview()
    } else {
      nextQuestion()
    }
  }

  /*
   * =====================================================
   * CLEANUP
   * =====================================================
   */

  useEffect(() => {
    return () => {
      clearSilenceTimer()
      clearNextQuestionTimer()

      recognitionRef.current?.stop()

      recognitionRef.current =
        null
    }
  }, [])

  /*
   * =====================================================
   * LOADING
   * =====================================================
   */

  if (loading) {
    return (
      <main className="interview-page">

        <div className="interview-loading">

          <div className="loading-spinner" />

          <p>
            Preparing your AI interview...
          </p>

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

          <h2>
            Unable to load interview
          </h2>

          <p>
            {error ||
              "Something went wrong."}
          </p>

          <button
            type="button"
            onClick={() =>
              navigate(
                "/dashboard",
              )
            }
          >
            Back to Dashboard
          </button>

        </div>

      </main>
    )
  }

  /*
   * =====================================================
   * PRE-INTERVIEW SCREEN
   * =====================================================
   */

  if (
    interview.status ===
    "created"
  ) {
    return (
      <main className="interview-page">

        <div className="pre-interview-card">

          <div className="ai-human-avatar compact">

            <div className="avatar-glow" />

            <div className="avatar-head">

              <div className="avatar-hair" />

              <div className="avatar-face">

                <div className="avatar-eyes">
                  <span />
                  <span />
                </div>

                <div className="avatar-nose" />

                <div className="avatar-mouth" />

              </div>

            </div>

          </div>

          <div className="ai-badge">
            AI INTERVIEWER
          </div>

          <h1>
            Your interviewer is ready
          </h1>

          <p>
            You are about to begin an
            AI-powered interview for the{" "}
            <strong>
              {interview.job_role}
            </strong>{" "}
            position.
          </p>

          <div className="interview-info">

            <div>
              <span>
                ROLE
              </span>

              <strong>
                {interview.job_role}
              </strong>
            </div>

            <div>
              <span>
                DIFFICULTY
              </span>

              <strong>
                {interview.difficulty}
              </strong>
            </div>

            <div>
              <span>
                QUESTIONS
              </span>

              <strong>
                {questions.length}
              </strong>
            </div>

          </div>

          <div className="voice-notice">

            <span>
              🎙️
            </span>

            <p>
              Your AI interviewer will ask
              questions using voice. You can
              answer using your microphone or
              by typing.
            </p>

          </div>

          {error && (
            <div className="interview-alert">
              {error}
            </div>
          )}

          <button
            type="button"
            className="begin-button"
            onClick={() => {
              void startInterview()
            }}
            disabled={
              starting
            }
          >
            {starting
              ? "Starting Interview..."
              : "Begin Interview →"}
          </button>

          <button
            type="button"
            className="cancel-button"
            onClick={() =>
              navigate(
                "/dashboard",
              )
            }
          >
            Back to Dashboard
          </button>

        </div>

      </main>
    )
  }

  /*
   * =====================================================
   * NO QUESTIONS
   * =====================================================
   */

  if (
    questions.length ===
    0
  ) {
    return (
      <main className="interview-page">

        <div className="interview-error">

          <h2>
            No questions available
          </h2>

          <p>
            The AI interviewer did not
            generate any questions.
          </p>

          <button
            type="button"
            onClick={() =>
              navigate(
                "/dashboard",
              )
            }
          >
            Back to Dashboard
          </button>

        </div>

      </main>
    )
  }

  /*
   * =====================================================
   * MAIN INTERVIEW
   * =====================================================
   */

  const progress =
    ((currentQuestion + 1) /
      questions.length) *
    100

  const currentQuestionText =
    questions[
      currentQuestion
    ]

  const isLastQuestion =
    currentQuestion ===
    questions.length - 1

  return (
    <main className="interview-page">

      {/* HEADER */}

      <header className="interview-header">

        <button
          type="button"
          className="exit-button"
          onClick={() =>
            navigate(
              "/dashboard",
            )
          }
        >
          ← Exit
        </button>

        <div className="header-title">

          <span>
            AI INTERVIEW
          </span>

          <strong>
            {interview.job_role}
          </strong>

        </div>

        <div className="timer">
          ⏱ {formatTime(time)}
        </div>

      </header>

      {/* PROGRESS */}

      <div className="progress-container">

        <div
          className="progress-bar"
          style={{
            width: `${progress}%`,
          }}
        />

      </div>

      {/* MICROPHONE PERMISSION */}

      {!microphoneEnabled && (
        <div className="microphone-permission-card">

          <div className="permission-icon">
            🎙️
          </div>

          <div className="permission-content">

            <strong>
              Enable your microphone
            </strong>

            <p>
              The AI interviewer will listen
              to your spoken answers.
            </p>

          </div>

          <button
            type="button"
            onClick={() => {
              void enableMicrophone()
            }}
          >
            Enable Microphone
          </button>

        </div>
      )}

      {/* MAIN INTERVIEW */}

      <section className="interview-content">

        {/* D-ID AVATAR */}

        <div
          className={`ai-human-avatar did-avatar-container ${
            isSpeaking
              ? "ai-is-speaking"
              : ""
          }`}
        >

          <DIDAvatar
            text={
              interview.status ===
              "started"
                ? currentQuestionText
                : ""
            }
            onSpeakingChange={
              setIsSpeaking
            }
          />

          {/* AI STATUS */}

          <div className="ai-speaking-indicator">

            <span
              className={
                isSpeaking
                  ? "speaking-dot active"
                  : "speaking-dot"
              }
            />

            <span>
              {isSpeaking
                ? "AI Interviewer is speaking..."

                : autoMovingNext
                  ? "Preparing next question..."

                  : isListening
                    ? autoListening
                      ? "Listening automatically..."
                      : "Listening to you..."

                    : answerCaptured
                      ? isLastQuestion
                        ? "Answer captured ✓"
                        : "Answer captured — next question coming..."

                      : microphoneEnabled
                        ? "AI Interviewer ready"
                        : "Enable microphone to answer"}
            </span>

          </div>

        </div>

        {/* QUESTION CARD */}

        <div className="question-card">

          <div className="question-number">
            QUESTION{" "}
            {currentQuestion + 1}{" "}
            OF{" "}
            {questions.length}
          </div>

          <h1>
            {currentQuestionText}
          </h1>

          <div className="question-line" />

          <form
            onSubmit={
              handleSubmit
            }
          >

            {/* ANSWER HEADER */}

            <div className="answer-header">

              <span>
                YOUR ANSWER
              </span>

              <span>
                {answer.length} characters
              </span>

            </div>

            {/* TEXT ANSWER */}

            <textarea
              value={answer}
              onChange={(event) =>
                handleAnswerChange(
                  event.target.value,
                )
              }
              placeholder="Type your answer here or use the microphone below..."
              disabled={
                submitting ||
                autoMovingNext
              }
            />

            {/* VOICE AREA */}

            <div className="voice-area">

              <button
                type="button"
                className={`mic-button ${
                  isListening
                    ? "recording"
                    : ""
                }`}
                onClick={() => {
                  if (
                    isListening
                  ) {
                    stopListening()
                  } else {
                    startListening()
                  }
                }}
                disabled={
                  submitting ||
                  !microphoneEnabled ||
                  isSpeaking ||
                  autoMovingNext
                }
              >

                <span className="mic-icon">
                  🎙️
                </span>

                <span>
                  {isListening
                    ? "Stop Recording"

                    : isSpeaking
                      ? "AI is Speaking..."

                      : autoMovingNext
                        ? "Next Question..."

                        : "Answer by Voice"}
                </span>

              </button>

              {/* RECORDING STATUS */}

              {isListening && (
                <div className="recording-status">

                  <span className="recording-dot" />

                  <span>
                    Listening... speak clearly
                  </span>

                  <span>
                    • silence detection ON
                  </span>

                </div>
              )}

              {/* AUTO NEXT STATUS */}

              {autoMovingNext && (
                <div className="recording-status">

                  <span>
                    ✓ Answer captured
                  </span>

                  <span>
                    • Next question in 2 seconds
                  </span>

                </div>
              )}

            </div>

            {/* ERROR */}

            {error && (
              <div className="interview-alert">
                {error}
              </div>
            )}

            {/* NAVIGATION */}

            <div className="answer-footer">

              <button
                type="button"
                className="previous-button"
                onClick={
                  previousQuestion
                }
                disabled={
                  currentQuestion ===
                    0 ||
                  submitting ||
                  autoMovingNext
                }
              >
                ← Previous
              </button>

              {isLastQuestion ? (

                <button
                  type="submit"
                  className="submit-button"
                  disabled={
                    submitting ||
                    autoMovingNext ||
                    !answer.trim()
                  }
                >
                  {submitting
                    ? "AI Evaluating..."
                    : "Finish Interview ✓"}
                </button>

              ) : (

                <button
                  type="submit"
                  className="next-button"
                  disabled={
                    submitting ||
                    autoMovingNext ||
                    !answer.trim()
                  }
                >
                  Next Question →
                </button>

              )}

            </div>

          </form>

        </div>

      </section>

    </main>
  )
}

export default Interview