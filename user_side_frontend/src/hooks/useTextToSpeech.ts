import { useState, useEffect, useRef, useCallback } from "react"

export interface UseTextToSpeechOptions {
  rate?: number
  pitch?: number
  volume?: number
  lang?: string
  onStart?: () => void
  onEnd?: () => void
  onError?: (error: string) => void
}

export interface UseTextToSpeechReturn {
  isSpeaking: boolean
  isPaused: boolean
  isLoading: boolean
  isSupported: boolean
  isMuted: boolean
  speak: (text: string) => void
  pause: () => void
  resume: () => void
  replay: () => void
  stop: () => void
  toggleMute: () => void
  setMuted: (muted: boolean) => void
}

export function useTextToSpeech(options: UseTextToSpeechOptions = {}): UseTextToSpeechReturn {
  const {
    rate = 1.0,
    pitch = 1.0,
    volume = 1.0,
    lang = "en-US",
    onStart,
    onEnd,
    onError,
  } = options

  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isSupported, setIsSupported] = useState(true)
  const [isMuted, setIsMuted] = useState(false)

  const lastTextRef = useRef<string>("")
  const isMutedRef = useRef(false)
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)

  // Keep mute ref in sync
  useEffect(() => {
    isMutedRef.current = isMuted
  }, [isMuted])

  // Check browser support
  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      setIsSupported(false)
    }
  }, [])

  // Safely stop any ongoing speech
  const stop = useCallback(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel()
      } catch {
        // non-blocking
      }
    }
    setIsSpeaking(false)
    setIsPaused(false)
    setIsLoading(false)
    utteranceRef.current = null
  }, [])

  // Pause speech
  const pause = useCallback(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window && isSpeaking && !isPaused) {
      try {
        window.speechSynthesis.pause()
        setIsPaused(true)
      } catch {
        // non-blocking
      }
    }
  }, [isSpeaking, isPaused])

  // Resume paused speech
  const resume = useCallback(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window && isPaused) {
      try {
        window.speechSynthesis.resume()
        setIsPaused(false)
      } catch {
        // non-blocking
      }
    }
  }, [isPaused])

  // Speak text
  const speak = useCallback(
    (text: string) => {
      if (!text || typeof window === "undefined" || !("speechSynthesis" in window)) {
        return
      }

      if (isMutedRef.current) {
        return
      }

      // Stop previous utterance to prevent overlapping speech
      stop()
      lastTextRef.current = text

      // Clean markdown, symbols, and formatting
      const cleanText = text
        .replace(/[*_#`[\]()]/g, "")
        .replace(/\s+/g, " ")
        .trim()

      if (!cleanText) return

      try {
        setIsLoading(true)
        const utterance = new SpeechSynthesisUtterance(cleanText)
        utterance.rate = rate
        utterance.pitch = pitch
        utterance.volume = volume
        utterance.lang = lang

        // Select optimal natural voice
        const voices = window.speechSynthesis.getVoices()
        const preferredVoice =
          voices.find(
            (v) =>
              v.lang.startsWith("en-") &&
              (v.name.includes("Natural") ||
                v.name.includes("Google") ||
                v.name.includes("Online") ||
                v.name.includes("Jenny") ||
                v.name.includes("Guy") ||
                v.name.includes("Samantha")),
          ) ||
          voices.find((v) => v.lang.startsWith("en-") || v.lang === "en") ||
          voices[0]

        if (preferredVoice) {
          utterance.voice = preferredVoice
        }

        utterance.onstart = () => {
          setIsLoading(false)
          setIsSpeaking(true)
          setIsPaused(false)
          onStart?.()
        }

        utterance.onend = () => {
          setIsSpeaking(false)
          setIsPaused(false)
          setIsLoading(false)
          utteranceRef.current = null
          onEnd?.()
        }

        utterance.onerror = (e) => {
          setIsSpeaking(false)
          setIsPaused(false)
          setIsLoading(false)
          utteranceRef.current = null
          // cancellation is expected on question switch / stop
          if (e.error !== "canceled" && e.error !== "interrupted") {
            console.warn("Speech synthesis notice:", e.error)
            onError?.(e.error)
          }
        }

        utteranceRef.current = utterance
        window.speechSynthesis.speak(utterance)
      } catch (err: any) {
        console.warn("TTS speak failed:", err)
        setIsSpeaking(false)
        setIsPaused(false)
        setIsLoading(false)
        onError?.(err?.message || "Speech synthesis failed")
      }
    },
    [rate, pitch, volume, lang, stop, onStart, onEnd, onError],
  )

  // Replay last spoken text
  const replay = useCallback(() => {
    if (lastTextRef.current) {
      speak(lastTextRef.current)
    }
  }, [speak])

  // Toggle mute state
  const toggleMute = useCallback(() => {
    setIsMuted((prev) => {
      const next = !prev
      if (next) {
        stop()
      } else if (lastTextRef.current) {
        speak(lastTextRef.current)
      }
      return next
    })
  }, [stop, speak])

  // Set explicit mute state
  const setMutedExplicit = useCallback(
    (muted: boolean) => {
      setIsMuted(muted)
      if (muted) {
        stop()
      }
    },
    [stop],
  )

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stop()
    }
  }, [stop])

  return {
    isSpeaking,
    isPaused,
    isLoading,
    isSupported,
    isMuted,
    speak,
    pause,
    resume,
    replay,
    stop,
    toggleMute,
    setMuted: setMutedExplicit,
  }
}
