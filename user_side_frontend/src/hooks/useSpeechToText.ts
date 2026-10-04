import { useState, useEffect, useRef, useCallback } from "react"

interface SpeechRecognitionResultLike {
  [index: number]: {
    transcript: string
  }
  isFinal?: boolean
}

interface SpeechRecognitionEventLike {
  resultIndex: number
  results: {
    length: number
    [index: number]: SpeechRecognitionResultLike
  }
}

interface SpeechRecognitionLike {
  continuous: boolean
  interimResults: boolean
  lang: string
  start: () => void
  stop: () => void
  abort: () => void
  onresult: ((event: SpeechRecognitionEventLike) => void) | null
  onend: (() => void) | null
  onerror: ((event: { error: string; message?: string }) => void) | null
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

export type MicPermissionState = "prompt" | "granted" | "denied" | "unsupported"

export interface UseSpeechToTextOptions {
  lang?: string
  silenceDelayMs?: number
  onSpeechSegment?: (segment: string) => void
  onTranscriptUpdate?: (fullText: string, interim: string) => void
  onSilence?: () => void
  onError?: (errorMessage: string) => void
}

export interface UseSpeechToTextReturn {
  isListening: boolean
  isSupported: boolean
  permissionState: MicPermissionState
  interimTranscript: string
  finalTranscript: string
  error: string | null
  startListening: () => Promise<boolean>
  stopListening: () => void
  resetTranscript: () => void
  requestPermission: () => Promise<boolean>
}

export function useSpeechToText(options: UseSpeechToTextOptions = {}): UseSpeechToTextReturn {
  const {
    lang = "en-US",
    silenceDelayMs = 2800,
    onSpeechSegment,
    onTranscriptUpdate,
    onSilence,
    onError,
  } = options

  const [isListening, setIsListening] = useState(false)
  const [isSupported, setIsSupported] = useState(true)
  const [permissionState, setPermissionState] = useState<MicPermissionState>("prompt")
  const [interimTranscript, setInterimTranscript] = useState("")
  const [finalTranscript, setFinalTranscript] = useState("")
  const [error, setError] = useState<string | null>(null)

  const recognitionRef = useRef<SpeechRecognitionLike | null>(null)
  const silenceTimerRef = useRef<number | null>(null)
  const shouldListenRef = useRef(false)
  const accumulatedFinalRef = useRef("")
  const hasSpokenInSessionRef = useRef(false)
  const restartCountRef = useRef(0)

  // Verify Web Speech API support
  useEffect(() => {
    if (typeof window === "undefined") return
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      setIsSupported(false)
      setPermissionState("unsupported")
    }
  }, [])

  // Clear silence timer
  const clearSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current !== null) {
      window.clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }
  }, [])

  // Explicitly request microphone permission
  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setPermissionState("unsupported")
      return false
    }

    try {
      setError(null)
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      stream.getTracks().forEach((track) => track.stop())
      setPermissionState("granted")
      return true
    } catch (err: any) {
      console.warn("Microphone access denied or error:", err)
      setPermissionState("denied")
      setError("Microphone permission denied. You can continue by typing your answers.")
      onError?.("Microphone permission denied.")
      return false
    }
  }, [onError])

  // Stop listening
  const stopListening = useCallback(() => {
    shouldListenRef.current = false
    clearSilenceTimer()
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch {
        // non-blocking
      }
      recognitionRef.current = null
    }
    setIsListening(false)
    setInterimTranscript("")
  }, [clearSilenceTimer])

  // Reset transcript buffers
  const resetTranscript = useCallback(() => {
    accumulatedFinalRef.current = ""
    setInterimTranscript("")
    setFinalTranscript("")
    hasSpokenInSessionRef.current = false
    restartCountRef.current = 0
  }, [])

  // Start listening
  const startListening = useCallback(async (): Promise<boolean> => {
    if (typeof window === "undefined") return false

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      setError("Speech recognition is not supported in this browser. Please use Chrome/Edge or type your answers.")
      return false
    }

    // Ensure mic permission
    if (permissionState !== "granted") {
      const granted = await requestPermission()
      if (!granted) return false
    }

    // Mark intent to listen
    shouldListenRef.current = true
    clearSilenceTimer()
    setError(null)

    // Stop existing instance before restarting
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch {}
      recognitionRef.current = null
    }

    try {
      const recognition = new SpeechRecognition()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = lang || navigator.language || "en-US"

      recognition.onresult = (event: SpeechRecognitionEventLike) => {
        let currentInterim = ""

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const res = event.results[i]
          if (res?.[0]) {
            const textPart = res[0].transcript.trim()
            if (res.isFinal) {
              accumulatedFinalRef.current = accumulatedFinalRef.current
                ? `${accumulatedFinalRef.current} ${textPart}`
                : textPart
            } else {
              currentInterim = currentInterim ? `${currentInterim} ${textPart}` : textPart
            }
          }
        }

        const consolidatedFinal = accumulatedFinalRef.current.trim()
        const consolidatedFull = currentInterim
          ? consolidatedFinal
            ? `${consolidatedFinal} ${currentInterim}`
            : currentInterim
          : consolidatedFinal

        if (consolidatedFull.length > 0) {
          hasSpokenInSessionRef.current = true
        }

        setInterimTranscript(currentInterim)
        setFinalTranscript(consolidatedFinal)

        // Broadcast to listeners
        if (onTranscriptUpdate) {
          onTranscriptUpdate(consolidatedFull, currentInterim)
        } else if (onSpeechSegment && consolidatedFinal) {
          onSpeechSegment(consolidatedFinal)
        }

        // Silence detection: only activate if candidate has actually spoken meaningful content
        clearSilenceTimer()
        if (hasSpokenInSessionRef.current && consolidatedFull.length >= 8 && silenceDelayMs > 0 && shouldListenRef.current) {
          silenceTimerRef.current = window.setTimeout(() => {
            if (shouldListenRef.current) {
              onSilence?.()
            }
          }, silenceDelayMs)
        }
      }

      recognition.onend = () => {
        recognitionRef.current = null
        // If candidate is still supposed to be answering and hasn't manually stopped, auto-restart
        if (shouldListenRef.current && restartCountRef.current < 20) {
          restartCountRef.current += 1
          window.setTimeout(() => {
            if (shouldListenRef.current) {
              try {
                recognition.start()
                recognitionRef.current = recognition
                setIsListening(true)
              } catch {
                setIsListening(false)
              }
            }
          }, 150)
        } else {
          setIsListening(false)
        }
      }

      recognition.onerror = (e) => {
        if (e.error !== "no-speech" && e.error !== "aborted") {
          console.warn("Speech recognition notice:", e.error)
          if (e.error === "not-allowed") {
            setPermissionState("denied")
            setError("Microphone permission denied.")
            onError?.("Microphone permission denied.")
          }
        }
        // If aborted or no-speech, onend will handle controlled recovery
      }

      recognition.start()
      recognitionRef.current = recognition
      setIsListening(true)
      return true
    } catch (err: any) {
      console.warn("Failed to initialize speech recognition:", err)
      setError("Speech recognition failed to initialize.")
      setIsListening(false)
      recognitionRef.current = null
      return false
    }
  }, [lang, permissionState, requestPermission, clearSilenceTimer, silenceDelayMs, onTranscriptUpdate, onSpeechSegment, onSilence, onError])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      shouldListenRef.current = false
      clearSilenceTimer()
      stopListening()
    }
  }, [clearSilenceTimer, stopListening])

  return {
    isListening,
    isSupported,
    permissionState,
    interimTranscript,
    finalTranscript,
    error,
    startListening,
    stopListening,
    resetTranscript,
    requestPermission,
  }
}
