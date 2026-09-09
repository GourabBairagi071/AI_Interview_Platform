import {
  useEffect,
  useRef,
  useState,
} from "react"

import * as sdk from "@d-id/client-sdk"

import "./DIDAvatar.css"

interface DIDAvatarProps {
  text: string
  onSpeakingChange?: (speaking: boolean) => void
}

function DIDAvatar({
  text,
  onSpeakingChange,
}: DIDAvatarProps) {
  const videoRef =
    useRef<HTMLVideoElement | null>(null)

  const managerRef =
    useRef<
      Awaited<
        ReturnType<
          typeof sdk.createAgentManager
        >
      > | null
    >(null)

  const streamRef =
    useRef<MediaStream | null>(null)

  const [connected, setConnected] =
    useState(false)

  const [error, setError] =
    useState("")

  const agentId =
    import.meta.env.VITE_DID_AGENT_ID

  const clientKey =
    import.meta.env.VITE_DID_CLIENT_KEY

  /*
   * =====================================================
   * CONNECT TO D-ID AGENT
   * =====================================================
   */

  useEffect(() => {
    let mounted = true

    async function initialize() {
      if (!agentId || !clientKey) {
        setError(
          "D-ID configuration is missing. Check your .env file.",
        )

        return
      }

      try {
        const callbacks = {
          /*
           * D-ID WebRTC stream
           */

          onSrcObjectReady(
            value: MediaStream,
          ) {
            console.log(
              "D-ID MediaStream received",
            )

            streamRef.current =
              value

            if (videoRef.current) {
              videoRef.current.srcObject =
                value

              videoRef.current
                .play()
                .catch((err) => {
                  console.warn(
                    "Video autoplay warning:",
                    err,
                  )
                })
            }

            return value
          },

          /*
           * Avatar speaking state
           */

          onVideoStateChange(
            state: string,
          ) {
            console.log(
              "D-ID video state:",
              state,
            )

            if (state === "START") {
              onSpeakingChange?.(
                true,
              )
            }

            if (state === "STOP") {
              onSpeakingChange?.(
                false,
              )
            }
          },

          /*
           * WebRTC connection state
           */

          onConnectionStateChange(
            state: string,
          ) {
            console.log(
              "D-ID connection state:",
              state,
            )

            if (!mounted) {
              return
            }

            if (
              state === "connected"
            ) {
              setConnected(true)
              setError("")
            }

            if (
              state ===
                "disconnected" ||
              state === "closed" ||
              state === "failed"
            ) {
              setConnected(false)
            }
          },

          /*
           * D-ID messages
           */

          onNewMessage(
            messages: unknown,
            type: string,
          ) {
            console.log(
              "D-ID message:",
              type,
              messages,
            )
          },

          /*
           * D-ID errors
           */

          onError(
            error: unknown,
            errorData: unknown,
          ) {
            console.error(
              "D-ID error:",
              error,
              errorData,
            )

            if (!mounted) {
              return
            }

            setConnected(false)

            setError(
              "D-ID avatar connection failed.",
            )

            onSpeakingChange?.(
              false,
            )
          },
        }

        /*
         * Create Agent Manager
         */

        const manager =
          await sdk.createAgentManager(
            agentId,
            {
              auth: {
                type: "key",
                clientKey:
                  clientKey,
              },

              callbacks,

              streamOptions: {
                compatibilityMode:
                  "auto",

                streamWarmup: true,
              },
            },
          )

        if (!mounted) {
          manager.disconnect()
          return
        }

        managerRef.current =
          manager

        /*
         * Connect WebRTC
         */

        await manager.connect()

        console.log(
          "D-ID Agent connected successfully",
        )
      } catch (err) {
        console.error(
          "D-ID initialization error:",
          err,
        )

        if (!mounted) {
          return
        }

        setConnected(false)

        setError(
          err instanceof Error
            ? err.message
            : "Unable to connect to D-ID.",
        )
      }
    }

    void initialize()

    /*
     * Cleanup
     */

    return () => {
      mounted = false

      onSpeakingChange?.(
        false,
      )

      if (managerRef.current) {
        try {
          managerRef.current.disconnect()
        } catch (err) {
          console.warn(
            "D-ID disconnect warning:",
            err,
          )
        }

        managerRef.current =
          null
      }

      streamRef.current = null

      if (videoRef.current) {
        videoRef.current.srcObject =
          null
      }
    }
  }, [
    agentId,
    clientKey,
    onSpeakingChange,
  ])

  /*
   * =====================================================
   * SPEAK CURRENT QUESTION
   * =====================================================
   */

  useEffect(() => {
    if (
      !connected ||
      !managerRef.current ||
      !text.trim()
    ) {
      return
    }

    let cancelled = false

    async function speakQuestion() {
      try {
        if (cancelled) {
          return
        }

        console.log(
          "AI interviewer speaking:",
          text,
        )

        onSpeakingChange?.(
          true,
        )

        await managerRef.current?.speak(
          {
            type: "text",
            input: text,
          },
        )
      } catch (err) {
        console.error(
          "D-ID speak error:",
          err,
        )

        if (!cancelled) {
          onSpeakingChange?.(
            false,
          )

          setError(
            "Unable to make the AI interviewer speak.",
          )
        }
      }
    }

    void speakQuestion()

    return () => {
      cancelled = true
    }
  }, [
    text,
    connected,
    onSpeakingChange,
  ])

  /*
   * =====================================================
   * REPLAY QUESTION
   * =====================================================
   */

  async function replayQuestion() {
    if (
      !managerRef.current ||
      !connected ||
      !text.trim()
    ) {
      return
    }

    try {
      setError("")

      onSpeakingChange?.(
        true,
      )

      console.log(
        "Replaying question:",
        text,
      )

      await managerRef.current.speak(
        {
          type: "text",
          input: text,
        },
      )
    } catch (err) {
      console.error(
        "D-ID replay error:",
        err,
      )

      onSpeakingChange?.(
        false,
      )

      setError(
        "Unable to replay the question.",
      )
    }
  }

  /*
   * =====================================================
   * UI
   * =====================================================
   */

  return (
    <div className="did-avatar-wrapper">

      <div className="did-avatar-video-container">

        <video
          ref={videoRef}
          className="did-avatar-video"
          autoPlay
          playsInline
        />

        {!connected && (
          <div className="did-avatar-loading">

            <div className="did-loading-spinner" />

            <span>
              Connecting to AI interviewer...
            </span>

          </div>
        )}

        {error && (
          <div className="did-avatar-error">
            {error}
          </div>
        )}

      </div>

      <div className="did-avatar-controls">

        <div className="did-avatar-status">

          <span
            className={
              connected
                ? "did-status-dot online"
                : "did-status-dot"
            }
          />

          <span>
            {connected
              ? "AI Interviewer Online"
              : "Connecting..."}
          </span>

        </div>

        <button
          type="button"
          className="did-replay-button"
          onClick={() => {
            void replayQuestion()
          }}
          disabled={
            !connected ||
            !text.trim()
          }
        >
          🔊 Replay Question
        </button>

      </div>

    </div>
  )
}

export default DIDAvatar