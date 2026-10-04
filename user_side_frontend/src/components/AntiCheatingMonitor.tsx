import { useEffect, useRef, useState } from "react"
import {
  createFaceDetectionEngine,
  createObjectDetectionEngine,
  extractFaceEncoding,
  TemporalSecurityAnalyzer,
  type IFaceDetectionEngine,
  type IObjectDetectionEngine,
  type SecurityIncidentEvent,
} from "../services/faceDetection"
import {
  recordAntiCheatingEvent,
  registerCandidateFace,
} from "../services/api"
import "./AntiCheatingMonitor.css"

export type MonitoringState =
  | "CAMERA_INITIALIZING"
  | "CAMERA_ACTIVE"
  | "CAMERA_DENIED"
  | "CAMERA_ERROR"
  | "MONITORING_ACTIVE"
  | "MONITORING_STOPPED"

interface AntiCheatingMonitorProps {
  interviewId: string
  isActive?: boolean
  onStatusChange?: (status: MonitoringState) => void
  onIncidentDetected?: (incident: SecurityIncidentEvent) => void
  className?: string
}

export function AntiCheatingMonitor({
  interviewId,
  isActive = true,
  onStatusChange,
  onIncidentDetected,
  className = "",
}: AntiCheatingMonitorProps) {
  const [monitoringState, setMonitoringState] =
    useState<MonitoringState>("CAMERA_INITIALIZING")
  const [warningMessage, setWarningMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [faceCount, setFaceCount] = useState<number>(0)
  const [identityVerified, setIdentityVerified] = useState<boolean>(false)

  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const faceEngineRef = useRef<IFaceDetectionEngine | null>(null)
  const objectEngineRef = useRef<IObjectDetectionEngine | null>(null)
  const analyzerRef = useRef<TemporalSecurityAnalyzer | null>(null)
  const registeredEncodingRef = useRef<number[] | null>(null)
  const isRegisteringFaceRef = useRef(false)
  const intervalRef = useRef<number | null>(null)
  const isMountedRef = useRef(true)

  // Report status updates to parent
  const updateState = (nextState: MonitoringState) => {
    setMonitoringState(nextState)
    onStatusChange?.(nextState)
  }

  // Handle recorded incident & send to backend API
  const handleSecurityIncident = async (incident: SecurityIncidentEvent) => {
    if (!interviewId) return

    onIncidentDetected?.(incident)

    try {
      await recordAntiCheatingEvent(interviewId, {
        event_type: incident.eventType,
        severity: incident.severity,
        timestamp: incident.timestamp,
        duration: incident.duration,
        confidence: incident.confidence,
        description: incident.description,
        metadata: incident.metadata,
      })
    } catch (err) {
      console.warn("Could not record anti-cheating event to backend:", err)
    }
  }

  // Initialize camera, face engine, and object detector
  const startCamera = async () => {
    updateState("CAMERA_INITIALIZING")
    setErrorMessage(null)

    if (
      typeof navigator === "undefined" ||
      !navigator.mediaDevices ||
      !navigator.mediaDevices.getUserMedia
    ) {
      setErrorMessage("Camera access is not supported in this browser.")
      updateState("CAMERA_ERROR")
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 480 },
          height: { ideal: 360 },
          facingMode: "user",
        },
        audio: false,
      })

      if (!isMountedRef.current) {
        stream.getTracks().forEach((track) => track.stop())
        return
      }

      streamRef.current = stream

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        try {
          await videoRef.current.play()
        } catch {}
      }

      // Initialize Face Detection Engine
      const faceEngine = await createFaceDetectionEngine()
      faceEngineRef.current = faceEngine

      // Initialize Object & Device Detection Engine
      try {
        const objectEngine = await createObjectDetectionEngine()
        objectEngineRef.current = objectEngine
      } catch (err) {
        console.warn("Object engine initialisation warning:", err)
      }

      // Initialize Unified Temporal Security Analyzer
      analyzerRef.current = new TemporalSecurityAnalyzer(
        {
          frameProcessIntervalMs: 600,
          faceMissingThresholdSec: 3.0,
          multipleFaceThresholdSec: 2.0,
          identityMismatchThresholdSec: 2.5,
          identitySimilarityThreshold: 0.62,
          mobileDetectionThresholdSec: 1.5,
          deviceDetectionThresholdSec: 2.0,
          objectConfidenceThreshold: 0.6,
        },
        handleSecurityIncident,
      )

      updateState(isActive ? "MONITORING_ACTIVE" : "CAMERA_ACTIVE")

      // Start Frame Analysis Loop
      startAnalysisLoop()
    } catch (err: any) {
      if (!isMountedRef.current) return

      if (
        err.name === "NotAllowedError" ||
        err.name === "PermissionDeniedError"
      ) {
        setErrorMessage("Camera permission denied. Please allow camera access.")
        updateState("CAMERA_DENIED")
      } else if (
        err.name === "NotFoundError" ||
        err.name === "DevicesNotFoundError"
      ) {
        setErrorMessage("No webcam device detected on your system.")
        updateState("CAMERA_ERROR")
      } else {
        setErrorMessage(
          err.message || "Unable to activate camera for proctoring.",
        )
        updateState("CAMERA_ERROR")
      }
    }
  }

  // Periodic frame evaluation: Face + Identity + Object Analysis
  const startAnalysisLoop = () => {
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current)
    }

    intervalRef.current = window.setInterval(async () => {
      if (
        !isActive ||
        !videoRef.current ||
        !faceEngineRef.current ||
        !analyzerRef.current
      ) {
        return
      }

      try {
        // 1. Detect faces
        const faceResult = await faceEngineRef.current.detect(videoRef.current)
        setFaceCount(faceResult.faceCount)

        // 2. Extract current face encoding (if single face is detected)
        let currentEncoding: number[] | null = null
        if (faceResult.faceDetected && faceResult.faceCount === 1) {
          currentEncoding = extractFaceEncoding(
            videoRef.current,
            faceResult.faces[0],
          )

          // Auto-register session face baseline if not yet registered
          if (
            !registeredEncodingRef.current &&
            !isRegisteringFaceRef.current &&
            currentEncoding.length > 0 &&
            faceResult.confidence >= 0.8
          ) {
            isRegisteringFaceRef.current = true
            registeredEncodingRef.current = currentEncoding
            setIdentityVerified(true)

            // Register with backend session endpoint
            registerCandidateFace(interviewId, currentEncoding, {
              faceBox: faceResult.faces[0],
            }).catch((err) => {
              console.warn("Backend session face registration notice:", err)
            })
          }
        }

        // 3. Detect mobile devices & laptops
        let detectedObjects: any[] = []
        if (objectEngineRef.current) {
          try {
            detectedObjects = await objectEngineRef.current.detectObjects(
              videoRef.current,
            )
          } catch {}
        }

        // 4. Run temporal analysis across all signals
        const analysis = analyzerRef.current.processFrame(
          faceResult,
          currentEncoding,
          registeredEncodingRef.current,
          detectedObjects,
        )

        setWarningMessage(analysis.statusNotice)
      } catch (err) {
        // Silently tolerate single frame glitch
      }
    }, 600)
  }

  // Stop camera tracks cleanly
  const stopCamera = () => {
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current)
      intervalRef.current = null
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }

    if (videoRef.current) {
      videoRef.current.srcObject = null
    }

    if (faceEngineRef.current) {
      faceEngineRef.current.dispose()
      faceEngineRef.current = null
    }

    if (objectEngineRef.current) {
      objectEngineRef.current.dispose()
      objectEngineRef.current = null
    }

    analyzerRef.current?.reset()
    registeredEncodingRef.current = null
    isRegisteringFaceRef.current = false
    setIdentityVerified(false)
    updateState("MONITORING_STOPPED")
  }

  useEffect(() => {
    isMountedRef.current = true
    void startCamera()

    return () => {
      isMountedRef.current = false
      stopCamera()
    }
  }, [])

  // React to isActive prop changes
  useEffect(() => {
    if (streamRef.current) {
      if (isActive) {
        updateState("MONITORING_ACTIVE")
        if (!intervalRef.current) startAnalysisLoop()
      } else {
        updateState("CAMERA_ACTIVE")
        if (intervalRef.current) {
          window.clearInterval(intervalRef.current)
          intervalRef.current = null
        }
      }
    }
  }, [isActive])

  return (
    <div
      className={`anti-cheating-monitor-wrapper ${
        warningMessage ? "is-warning" : ""
      } ${className}`}
    >
      {/* MONITOR HEADER */}
      <div className="ac-monitor-header">
        <div className="ac-header-left">
          <span className="ac-badge-title">Proctoring AI</span>
        </div>

        {monitoringState === "MONITORING_ACTIVE" && (
          <span
            className={`ac-status-badge ${
              warningMessage ? "status-warning" : ""
            }`}
          >
            <span className="ac-status-dot" />
            {warningMessage
              ? "Warning"
              : identityVerified
                ? "Identity Verified ✓"
                : faceCount > 1
                  ? `${faceCount} Faces`
                  : "Active"}
          </span>
        )}

        {monitoringState === "CAMERA_INITIALIZING" && (
          <span className="ac-status-badge status-init">
            <span className="ac-status-dot" />
            Starting...
          </span>
        )}

        {(monitoringState === "CAMERA_DENIED" ||
          monitoringState === "CAMERA_ERROR") && (
          <span className="ac-status-badge status-warning">
            <span className="ac-status-dot" />
            Offline
          </span>
        )}
      </div>

      {/* VIDEO PREVIEW OR ERROR STATE */}
      <div className="ac-video-container">
        {monitoringState === "CAMERA_DENIED" ? (
          <div className="ac-message-card">
            <span className="ac-message-icon">📷</span>
            <div className="ac-message-title">Camera Permission Required</div>
            <p className="ac-message-desc">
              Please grant camera access in your browser to enable proctoring.
            </p>
            <button
              type="button"
              className="ac-retry-btn"
              onClick={() => void startCamera()}
            >
              Grant Permission
            </button>
          </div>
        ) : monitoringState === "CAMERA_ERROR" ? (
          <div className="ac-message-card">
            <span className="ac-message-icon">⚠️</span>
            <div className="ac-message-title">Camera Unavailable</div>
            <p className="ac-message-desc">
              {errorMessage || "Unable to access your camera device."}
            </p>
            <button
              type="button"
              className="ac-retry-btn"
              onClick={() => void startCamera()}
            >
              Retry Camera
            </button>
          </div>
        ) : (
          <>
            <video
              ref={videoRef}
              playsInline
              muted
              autoPlay
              className="ac-webcam-video"
            />

            {/* Target face guide overlay */}
            <div className="ac-face-guide" />

            {/* Real-time warning alert overlay */}
            {warningMessage && (
              <div className="ac-warning-overlay">
                <span>⚠️</span>
                <span>{warningMessage}</span>
              </div>
            )}
          </>
        )}
      </div>

      {/* PRIVACY FOOTER */}
      <div className="ac-privacy-footer">
        <div className="ac-privacy-lock">
          <span>🔒</span>
          <span>Zero video recording • Client-side AI</span>
        </div>
        <span>v1.0</span>
      </div>
    </div>
  )
}

export default AntiCheatingMonitor
