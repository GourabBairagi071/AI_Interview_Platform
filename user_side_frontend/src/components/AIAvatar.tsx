import React from "react"
import "./AIAvatar.css"

export type AvatarState = "idle" | "thinking" | "speaking" | "listening" | "processing"

export interface AIAvatarProps {
  state: AvatarState
  interviewerName?: string
  jobRole?: string
  isMuted?: boolean
  isSpeaking?: boolean
  isPaused?: boolean
  onReplay?: () => void
  onToggleMute?: () => void
  onPauseResume?: () => void
  className?: string
}

export const AIAvatar: React.FC<AIAvatarProps> = ({
  state,
  interviewerName = "AI Lead Interviewer",
  jobRole = "Technical Assessment",
  isMuted = false,
  isSpeaking = false,
  isPaused = false,
  onReplay,
  onToggleMute,
  onPauseResume,
  className = "",
}) => {
  const effectiveState = state
  const getStatusText = () => {
    switch (state) {
      case "speaking":
        return isPaused ? "AI voice paused" : "AI Interviewer is speaking..."
      case "listening":
        return "Listening to your answer... Speak naturally"
      case "processing":
        return "Processing & evaluating your answer..."
      case "thinking":
        return "AI formulating next question..."
      case "idle":
      default:
        return "AI Interviewer ready"
    }
  }

  const getStatusIcon = () => {
    switch (state) {
      case "speaking":
        return "🔊"
      case "listening":
        return "🎙️"
      case "processing":
        return "⚙️"
      case "thinking":
        return "⚡"
      case "idle":
      default:
        return "🤖"
    }
  }

  return (
    <div className={`ai-avatar-card ${state} ${className}`}>
      {/* Ambient Radial Aura */}
      <div className={`avatar-ambient-glow ${state}`} />

      {/* Main Avatar Visualizer */}
      <div className="avatar-visualizer-container">
        {/* Outer Orbit Rings */}
        <div className={`avatar-orbit-ring ring-1 ${effectiveState}`} />
        <div className={`avatar-orbit-ring ring-2 ${effectiveState}`} />

        {/* Central Neural Sphere / Hologram Face */}
        <div className={`avatar-sphere ${effectiveState}`}>
          {/* Subtle Cyber Grid Lines inside Orb */}
          <div className="avatar-grid-overlay" />

          {/* Hologram Icon / Face Indicator */}
          <div className="avatar-core-icon">
            <span className="icon-symbol">{getStatusIcon()}</span>
          </div>

          {/* Reactive Soundwave Aura */}
          {effectiveState === "speaking" && !isPaused && (
            <div className="avatar-sound-ripples">
              <span className="sound-ripple r-1" />
              <span className="sound-ripple r-2" />
              <span className="sound-ripple r-3" />
            </div>
          )}

          {effectiveState === "listening" && (
            <div className="avatar-listening-rings">
              <span className="listen-ring l-1" />
              <span className="listen-ring l-2" />
            </div>
          )}
        </div>
      </div>

      {/* Dynamic Sound Equalizer Waveform Bars */}
      <div className={`avatar-equalizer-bars ${effectiveState}`}>
        <span className="eq-bar bar-1" />
        <span className="eq-bar bar-2" />
        <span className="eq-bar bar-3" />
        <span className="eq-bar bar-4" />
        <span className="eq-bar bar-5" />
        <span className="eq-bar bar-6" />
        <span className="eq-bar bar-7" />
        <span className="eq-bar bar-8" />
      </div>

      {/* Interviewer Identity & Status */}
      <div className="avatar-info-block">
        <h3 className="avatar-name">{interviewerName}</h3>
        <span className="avatar-role">{jobRole}</span>
      </div>

      {/* Status Badge */}
      <div className={`avatar-status-badge ${effectiveState}`}>
        <span className="status-indicator-dot" />
        <span className="status-label">{getStatusText()}</span>
      </div>

      {/* Integrated Audio & Replay Controls */}
      <div className="avatar-controls-row">
        {onReplay && (
          <button
            type="button"
            className="avatar-control-btn"
            onClick={onReplay}
            disabled={effectiveState === "thinking"}
            title="Replay question audio"
          >
            🔄 Replay Question
          </button>
        )}

        {isSpeaking && onPauseResume && (
          <button
            type="button"
            className="avatar-control-btn"
            onClick={onPauseResume}
            title={isPaused ? "Resume speech" : "Pause speech"}
          >
            {isPaused ? "▶ Resume Voice" : "⏸ Pause Voice"}
          </button>
        )}

        {onToggleMute && (
          <button
            type="button"
            className={`avatar-control-btn ${isMuted ? "muted" : ""}`}
            onClick={onToggleMute}
            title={isMuted ? "Unmute AI voice" : "Mute AI voice"}
          >
            {isMuted ? "🔇 Unmute" : "🔊 Mute"}
          </button>
        )}
      </div>
    </div>
  )
}

export default AIAvatar
