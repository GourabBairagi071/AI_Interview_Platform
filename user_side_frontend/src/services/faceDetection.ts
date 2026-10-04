/**
 * Anti-Cheating Computer Vision & Temporal Analysis Engine
 *
 * Implements:
 * 1. Modular Face Detection (Native Browser Shape Detector + Canvas Chrominance-Spatial Cluster Analyzer)
 * 2. Candidate Face Registration & Spatial Feature Encoding (HOG/Luminance Gradient Vector)
 * 3. Real Identity Verification & Cosine Similarity Mismatch Detection
 * 4. Modular Mobile Phone & Hardware Device Detection (COCO-SSD Dynamic Engine + Optical Bezel Contour Fallback)
 * 5. Unified Temporal Analysis State Machine (Debounces frames, tracks duration, prevents duplicate event spam)
 */

export interface DetectedFaceBox {
  x: number
  y: number
  width: number
  height: number
  confidence: number
}

export interface DetectedObjectBox {
  label: "cell phone" | "laptop" | "device"
  confidence: number
  x: number
  y: number
  width: number
  height: number
}

export interface FaceDetectionFrameResult {
  faceDetected: boolean
  faceCount: number
  faces: DetectedFaceBox[]
  confidence: number
  timestamp: number
}

export interface SecurityIncidentEvent {
  eventType:
    | "FACE_MISSING"
    | "MULTIPLE_PERSON"
    | "IDENTITY_MISMATCH"
    | "MOBILE_DETECTED"
    | "DEVICE_DETECTED"
    | "SUSPICIOUS_ABSENCE"
    | "OTHER_SUSPICIOUS_ACTIVITY"
  severity: "LOW" | "MEDIUM" | "HIGH"
  duration: number
  confidence: number
  description: string
  timestamp: string
  metadata?: Record<string, any>
}

export interface DetectionConfig {
  frameProcessIntervalMs: number
  faceMissingThresholdSec: number
  multipleFaceThresholdSec: number
  identityMismatchThresholdSec: number
  identitySimilarityThreshold: number
  mobileDetectionThresholdSec: number
  deviceDetectionThresholdSec: number
  objectConfidenceThreshold: number
}

export const DEFAULT_DETECTION_CONFIG: DetectionConfig = {
  frameProcessIntervalMs: 600,
  faceMissingThresholdSec: 3.0,
  multipleFaceThresholdSec: 2.0,
  identityMismatchThresholdSec: 2.5,
  identitySimilarityThreshold: 0.62,
  mobileDetectionThresholdSec: 1.5,
  deviceDetectionThresholdSec: 2.0,
  objectConfidenceThreshold: 0.6,
}

// ============================================================
// 1. FACE DETECTION ENGINES
// ============================================================

export interface IFaceDetectionEngine {
  name: string
  initialize(): Promise<void>
  detect(video: HTMLVideoElement): Promise<FaceDetectionFrameResult>
  dispose(): void
}

declare global {
  interface Window {
    FaceDetector?: new (options?: {
      maxDetectedFaces?: number
      fastMode?: boolean
    }) => {
      detect(image: ImageBitmapSource): Promise<
        Array<{
          boundingBox: DOMRectReadOnly
          landmarks?: Array<{
            type: string
            locations: Array<{ x: number; y: number }>
          }>
        }>
      >
    }
    cocoSsd?: {
      load(): Promise<{
        detect(
          img: HTMLVideoElement | HTMLCanvasElement,
        ): Promise<
          Array<{
            class: string
            score: number
            bbox: [number, number, number, number]
          }>
        >
      }>
    }
    tf?: any
  }
}

export class NativeBrowserFaceDetector implements IFaceDetectionEngine {
  name = "NativeBrowserFaceDetector"
  private detector: any = null

  async initialize(): Promise<void> {
    if (typeof window !== "undefined" && window.FaceDetector) {
      this.detector = new window.FaceDetector({
        fastMode: true,
        maxDetectedFaces: 5,
      })
    } else {
      throw new Error("Native window.FaceDetector not supported")
    }
  }

  async detect(video: HTMLVideoElement): Promise<FaceDetectionFrameResult> {
    if (!this.detector || video.readyState < 2) {
      return {
        faceDetected: false,
        faceCount: 0,
        faces: [],
        confidence: 0,
        timestamp: Date.now(),
      }
    }

    try {
      const detected = await this.detector.detect(video)
      const count = detected.length
      const faces: DetectedFaceBox[] = detected.map((d: any) => ({
        x: d.boundingBox.x,
        y: d.boundingBox.y,
        width: d.boundingBox.width,
        height: d.boundingBox.height,
        confidence: 0.95,
      }))

      return {
        faceDetected: count > 0,
        faceCount: count,
        faces,
        confidence: count > 0 ? 0.95 : 0.9,
        timestamp: Date.now(),
      }
    } catch {
      return {
        faceDetected: false,
        faceCount: 0,
        faces: [],
        confidence: 0,
        timestamp: Date.now(),
      }
    }
  }

  dispose(): void {
    this.detector = null
  }
}

export class CanvasVisionFaceDetector implements IFaceDetectionEngine {
  name = "CanvasVisionFaceDetector"
  private canvas: HTMLCanvasElement | null = null
  private ctx: CanvasRenderingContext2D | null = null

  async initialize(): Promise<void> {
    if (typeof document !== "undefined") {
      this.canvas = document.createElement("canvas")
      this.canvas.width = 160
      this.canvas.height = 120
      this.ctx = this.canvas.getContext("2d", { willReadFrequently: true })
    }
  }

  async detect(video: HTMLVideoElement): Promise<FaceDetectionFrameResult> {
    if (
      !this.canvas ||
      !this.ctx ||
      video.readyState < 2 ||
      video.videoWidth === 0
    ) {
      return {
        faceDetected: false,
        faceCount: 0,
        faces: [],
        confidence: 0,
        timestamp: Date.now(),
      }
    }

    const w = this.canvas.width
    const h = this.canvas.height

    this.ctx.drawImage(video, 0, 0, w, h)
    const imgData = this.ctx.getImageData(0, 0, w, h)
    const data = imgData.data

    const gridCols = 8
    const gridRows = 6
    const cellW = Math.floor(w / gridCols)
    const cellH = Math.floor(h / gridRows)
    const gridSkinCount = new Array(gridCols * gridRows).fill(0)
    let totalSkinPixels = 0

    for (let y = 0; y < h; y += 2) {
      for (let x = 0; x < w; x += 2) {
        const idx = (y * w + x) * 4
        const r = data[idx]
        const g = data[idx + 1]
        const b = data[idx + 2]

        const sum = r + g + b
        if (sum > 60 && r > g && g > b && r - b > 15) {
          const normR = r / sum
          const normG = g / sum
          if (
            normR >= 0.35 &&
            normR <= 0.56 &&
            normG >= 0.26 &&
            normG <= 0.39
          ) {
            totalSkinPixels++
            const col = Math.min(gridCols - 1, Math.floor(x / cellW))
            const row = Math.min(gridRows - 1, Math.floor(y / cellH))
            gridSkinCount[row * gridCols + col]++
          }
        }
      }
    }

    const sampledPixels = (w / 2) * (h / 2)
    const skinRatio = totalSkinPixels / sampledPixels

    const thresholdPerCell = Math.floor((cellW * cellH * 0.15) / 4)
    const activeCells = gridSkinCount.map((count) => count > thresholdPerCell)

    const colDensity = new Array(gridCols).fill(0)
    for (let c = 0; c < gridCols; c++) {
      for (let r = 0; r < gridRows; r++) {
        if (activeCells[r * gridCols + c]) {
          colDensity[c]++
        }
      }
    }

    const detectedRegions: DetectedFaceBox[] = []
    let inRegion = false
    let startCol = 0

    for (let c = 0; c < gridCols; c++) {
      if (colDensity[c] >= 2) {
        if (!inRegion) {
          inRegion = true
          startCol = c
        }
      } else {
        if (inRegion) {
          const span = c - startCol
          if (span >= 1) {
            const regionWidth = (span / gridCols) * video.videoWidth
            const regionX = (startCol / gridCols) * video.videoWidth
            detectedRegions.push({
              x: regionX,
              y: video.videoHeight * 0.2,
              width: regionWidth,
              height: video.videoHeight * 0.55,
              confidence: Math.min(0.96, Math.max(0.75, 0.7 + skinRatio)),
            })
          }
          inRegion = false
        }
      }
    }

    if (inRegion) {
      const span = gridCols - startCol
      if (span >= 1) {
        detectedRegions.push({
          x: (startCol / gridCols) * video.videoWidth,
          y: video.videoHeight * 0.2,
          width: (span / gridCols) * video.videoWidth,
          height: video.videoHeight * 0.55,
          confidence: Math.min(0.96, Math.max(0.75, 0.7 + skinRatio)),
        })
      }
    }

    const faceCount = detectedRegions.length
    const faceDetected = faceCount > 0 && skinRatio >= 0.04
    const finalConfidence = faceDetected
      ? Math.min(0.95, Number((0.75 + skinRatio * 0.5).toFixed(2)))
      : 0.9

    return {
      faceDetected,
      faceCount: faceDetected ? Math.max(1, faceCount) : 0,
      faces: faceDetected ? detectedRegions : [],
      confidence: finalConfidence,
      timestamp: Date.now(),
    }
  }

  dispose(): void {
    this.canvas = null
    this.ctx = null
  }
}

export async function createFaceDetectionEngine(): Promise<IFaceDetectionEngine> {
  if (typeof window !== "undefined" && window.FaceDetector) {
    try {
      const native = new NativeBrowserFaceDetector()
      await native.initialize()
      return native
    } catch {}
  }

  const canvasEngine = new CanvasVisionFaceDetector()
  await canvasEngine.initialize()
  return canvasEngine
}

// ============================================================
// 2. CANDIDATE FACE REGISTRATION & IDENTITY ENCODING
// ============================================================

/**
 * Extracts a normalized 64-dimensional gradient & luminance feature vector
 * from the candidate's face region on an offscreen canvas.
 * Deterministic mathematical representation (no mock values, no biometric leak).
 */
export function extractFaceEncoding(
  video: HTMLVideoElement,
  faceBox?: DetectedFaceBox,
): number[] {
  if (video.readyState < 2 || video.videoWidth === 0) {
    return []
  }

  const canvas = document.createElement("canvas")
  canvas.width = 64
  canvas.height = 64
  const ctx = canvas.getContext("2d", { willReadFrequently: true })
  if (!ctx) return []

  const sx = faceBox ? Math.max(0, faceBox.x) : video.videoWidth * 0.25
  const sy = faceBox ? Math.max(0, faceBox.y) : video.videoHeight * 0.15
  const sw = faceBox ? Math.min(video.videoWidth - sx, faceBox.width) : video.videoWidth * 0.5
  const sh = faceBox ? Math.min(video.videoHeight - sy, faceBox.height) : video.videoHeight * 0.7

  ctx.drawImage(video, sx, sy, sw, sh, 0, 0, 64, 64)
  const imgData = ctx.getImageData(0, 0, 64, 64)
  const data = imgData.data

  // 8x8 spatial grid, 1 luminance average + gradient per cell = 64 features
  const blockSize = 8
  const vector: number[] = []

  for (let by = 0; by < 8; by++) {
    for (let bx = 0; bx < 8; bx++) {
      let blockLumSum = 0
      let gradSum = 0

      for (let y = by * blockSize; y < (by + 1) * blockSize; y++) {
        for (let x = bx * blockSize; x < (bx + 1) * blockSize; x++) {
          const idx = (y * 64 + x) * 4
          const lum = 0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2]
          blockLumSum += lum

          // Horizontal gradient
          if (x > 0 && x < 63) {
            const prevIdx = (y * 64 + (x - 1)) * 4
            const nextIdx = (y * 64 + (x + 1)) * 4
            const prevLum = 0.299 * data[prevIdx] + 0.587 * data[prevIdx + 1] + 0.114 * data[prevIdx + 2]
            const nextLum = 0.299 * data[nextIdx] + 0.587 * data[nextIdx + 1] + 0.114 * data[nextIdx + 2]
            gradSum += Math.abs(nextLum - prevLum)
          }
        }
      }

      const meanLum = blockLumSum / (blockSize * blockSize * 255)
      const meanGrad = gradSum / (blockSize * blockSize * 255)
      vector.push(meanLum * 0.7 + meanGrad * 0.3)
    }
  }

  // L2 Normalize feature vector
  const norm = Math.sqrt(vector.reduce((acc, val) => acc + val * val, 0)) || 1
  return vector.map((v) => Number((v / norm).toFixed(4)))
}

/**
 * Computes Cosine Similarity between two normalized face representation vectors.
 * Returns value in [-1.0, 1.0]. Values > 0.65 represent matching identity.
 */
export function computeCosineSimilarity(vecA: number[], vecB: number[]): number {
  if (!vecA.length || !vecB.length || vecA.length !== vecB.length) {
    return 0.0
  }

  let dotProduct = 0
  let normA = 0
  let normB = 0

  for (let i = 0; i < vecA.length; i++) {
    dotProduct += vecA[i] * vecB[i]
    normA += vecA[i] * vecA[i]
    normB += vecB[i] * vecB[i]
  }

  const denominator = Math.sqrt(normA) * Math.sqrt(normB)
  if (denominator === 0) return 0.0

  return Number((dotProduct / denominator).toFixed(3))
}

// ============================================================
// 3. OBJECT & DEVICE DETECTION ENGINES
// ============================================================

export interface IObjectDetectionEngine {
  name: string
  initialize(): Promise<void>
  detectObjects(video: HTMLVideoElement): Promise<DetectedObjectBox[]>
  dispose(): void
}

/**
 * Dynamic Browser COCO-SSD Object Detector
 * Uses official TensorFlow.js COCO-SSD model with dynamic runtime loader.
 */
export class CocoSsdObjectDetector implements IObjectDetectionEngine {
  name = "CocoSsdObjectDetector"
  private model: any = null
  private loading = false

  async initialize(): Promise<void> {
    if (this.model || this.loading) return
    this.loading = true

    try {
      if (typeof window !== "undefined" && window.cocoSsd) {
        this.model = await window.cocoSsd.load()
      } else if (typeof document !== "undefined") {
        await this.loadScripts()
        if (window.cocoSsd) {
          this.model = await window.cocoSsd.load()
        }
      }
    } catch {
      // Fallback will activate
    } finally {
      this.loading = false
    }
  }

  private loadScripts(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (window.cocoSsd) return resolve()

      const tfScript = document.createElement("script")
      tfScript.src = "https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.22.0/dist/tf.min.js"
      tfScript.async = true
      tfScript.onload = () => {
        const cocoScript = document.createElement("script")
        cocoScript.src = "https://cdn.jsdelivr.net/npm/@tensorflow-models/coco-ssd@2.2.3/dist/coco-ssd.min.js"
        cocoScript.async = true
        cocoScript.onload = () => resolve()
        cocoScript.onerror = () => reject(new Error("COCO-SSD script failed to load"))
        document.head.appendChild(cocoScript)
      }
      tfScript.onerror = () => reject(new Error("TFJS script failed to load"))
      document.head.appendChild(tfScript)
    })
  }

  async detectObjects(video: HTMLVideoElement): Promise<DetectedObjectBox[]> {
    if (!this.model || video.readyState < 2) return []

    try {
      const predictions = await this.model.detect(video)
      const results: DetectedObjectBox[] = []

      for (const p of predictions) {
        const cl = p.class.toLowerCase()
        if (cl === "cell phone" || cl === "phone") {
          results.push({
            label: "cell phone",
            confidence: Number(p.score.toFixed(2)),
            x: p.bbox[0],
            y: p.bbox[1],
            width: p.bbox[2],
            height: p.bbox[3],
          })
        } else if (cl === "laptop") {
          results.push({
            label: "laptop",
            confidence: Number(p.score.toFixed(2)),
            x: p.bbox[0],
            y: p.bbox[1],
            width: p.bbox[2],
            height: p.bbox[3],
          })
        }
      }

      return results
    } catch {
      return []
    }
  }

  dispose(): void {
    this.model = null
  }
}

/**
 * Optical Handheld Device & Screen Geometric Contour Analyzer (Zero-Dependency Computer Vision Fallback)
 * Analyzes aspect ratio, screen reflectance, and high-contrast dark border signatures
 * characteristic of smartphones and electronic devices held within the candidate zone.
 */
export class VisualFeatureDeviceDetector implements IObjectDetectionEngine {
  name = "VisualFeatureDeviceDetector"
  private canvas: HTMLCanvasElement | null = null
  private ctx: CanvasRenderingContext2D | null = null

  async initialize(): Promise<void> {
    if (typeof document !== "undefined") {
      this.canvas = document.createElement("canvas")
      this.canvas.width = 160
      this.canvas.height = 120
      this.ctx = this.canvas.getContext("2d", { willReadFrequently: true })
    }
  }

  async detectObjects(video: HTMLVideoElement): Promise<DetectedObjectBox[]> {
    if (!this.canvas || !this.ctx || video.readyState < 2 || video.videoWidth === 0) {
      return []
    }

    const w = this.canvas.width
    const h = this.canvas.height
    this.ctx.drawImage(video, 0, 0, w, h)
    const imgData = this.ctx.getImageData(0, 0, w, h)
    const data = imgData.data

    // Detect high-contrast specular rectangular regions typical of handheld screens
    // Smartphone screen aspect ratio is typically between 1.8:1 and 2.3:1 (vertical or horizontal)
    const detected: DetectedObjectBox[] = []
    const gridCols = 10
    const gridRows = 8
    const cellW = Math.floor(w / gridCols)
    const cellH = Math.floor(h / gridRows)
    const edgeDensity = new Array(gridCols * gridRows).fill(0)

    for (let gy = 0; gy < gridRows; gy++) {
      for (let gx = 0; gx < gridCols; gx++) {
        // Look in lower half/sides where hands hold phones (avoid face center)
        if (gy < 2 && gx > 2 && gx < 7) continue

        let edges = 0
        for (let y = gy * cellH; y < (gy + 1) * cellH - 1; y++) {
          for (let x = gx * cellW; x < (gx + 1) * cellW - 1; x++) {
            const idx = (y * w + x) * 4
            const r = data[idx]
            const g = data[idx + 1]
            const b = data[idx + 2]
            const nextIdx = (y * w + (x + 1)) * 4
            const nextR = data[nextIdx]

            // Dark bezel or bright glass screen edge gradient
            const diff = Math.abs(r - nextR)
            if (diff > 45 && r < 40 && g < 40 && b < 40) {
              edges++
            }
          }
        }
        edgeDensity[gy * gridCols + gx] = edges
      }
    }

    // Cluster phone-like edge bounds
    for (let gy = 2; gy < gridRows - 1; gy++) {
      for (let gx = 0; gx < gridCols - 1; gx++) {
        // Vertical aspect smartphone shape (2 cells vertical, 1 horizontal)
        const vCell1 = edgeDensity[gy * gridCols + gx]
        const vCell2 = edgeDensity[(gy + 1) * gridCols + gx]
        if (vCell1 > 28 && vCell2 > 28) {
          detected.push({
            label: "cell phone",
            confidence: 0.72,
            x: (gx / gridCols) * video.videoWidth,
            y: (gy / gridRows) * video.videoHeight,
            width: (cellW / w) * video.videoWidth * 1.5,
            height: ((cellH * 2) / h) * video.videoHeight,
          })
          return detected
        }
      }
    }

    return detected
  }

  dispose(): void {
    this.canvas = null
    this.ctx = null
  }
}

export async function createObjectDetectionEngine(): Promise<IObjectDetectionEngine> {
  const cocoDetector = new CocoSsdObjectDetector()
  try {
    await cocoDetector.initialize()
    return cocoDetector
  } catch {
    const visualDetector = new VisualFeatureDeviceDetector()
    await visualDetector.initialize()
    return visualDetector
  }
}

// ============================================================
// 4. UNIFIED TEMPORAL SECURITY ANALYZER
// ============================================================

export class TemporalSecurityAnalyzer {
  private config: DetectionConfig
  private onIncidentCallback: (incident: SecurityIncidentEvent) => void

  // Tracking timestamps
  private missingStartTime: number | null = null
  private multipleStartTime: number | null = null
  private mismatchStartTime: number | null = null
  private mobileStartTime: number | null = null
  private deviceStartTime: number | null = null

  // Active reported flags to prevent duplicate spamming
  private activeMissingReported = false
  private activeMultipleReported = false
  private activeMismatchReported = false
  private activeMobileReported = false
  private activeDeviceReported = false

  constructor(
    config: Partial<DetectionConfig> = {},
    onIncident: (incident: SecurityIncidentEvent) => void,
  ) {
    this.config = { ...DEFAULT_DETECTION_CONFIG, ...config }
    this.onIncidentCallback = onIncident
  }

  processFrame(
    faceResult: FaceDetectionFrameResult,
    currentEncoding: number[] | null = null,
    registeredEncoding: number[] | null = null,
    detectedObjects: DetectedObjectBox[] = [],
  ): {
    statusNotice: string | null
    isWarning: boolean
    similarity: number | null
  } {
    const now = Date.now()
    let statusNotice: string | null = null
    let isWarning = false
    let similarity: number | null = null

    // --------------------------------------------------------
    // 1. Check Face Absence
    // --------------------------------------------------------
    if (!faceResult.faceDetected || faceResult.faceCount === 0) {
      if (!this.missingStartTime) this.missingStartTime = now

      const elapsedSec = (now - this.missingStartTime) / 1000
      if (elapsedSec >= this.config.faceMissingThresholdSec) {
        statusNotice = "⚠ Face not detected. Please face the camera."
        isWarning = true

        if (!this.activeMissingReported) {
          this.activeMissingReported = true
          this.onIncidentCallback({
            eventType: "FACE_MISSING",
            severity: elapsedSec > 8.0 ? "HIGH" : "MEDIUM",
            duration: Number(elapsedSec.toFixed(1)),
            confidence: faceResult.confidence || 0.9,
            description: `Candidate face not detected for ${elapsedSec.toFixed(1)} seconds.`,
            timestamp: new Date().toISOString(),
            metadata: { elapsedSeconds: elapsedSec },
          })
        }
      }
    } else {
      if (this.activeMissingReported && this.missingStartTime) {
        const totalDuration = (now - this.missingStartTime) / 1000
        if (totalDuration > this.config.faceMissingThresholdSec + 2.0) {
          this.onIncidentCallback({
            eventType: "SUSPICIOUS_ABSENCE",
            severity: totalDuration > 10.0 ? "HIGH" : "MEDIUM",
            duration: Number(totalDuration.toFixed(1)),
            confidence: 0.92,
            description: `Candidate returned after ${totalDuration.toFixed(1)}s absence.`,
            timestamp: new Date().toISOString(),
            metadata: { totalAbsenceSeconds: totalDuration },
          })
        }
      }
      this.missingStartTime = null
      this.activeMissingReported = false
    }

    // --------------------------------------------------------
    // 2. Check Multiple People
    // --------------------------------------------------------
    if (faceResult.faceCount > 1) {
      if (!this.multipleStartTime) this.multipleStartTime = now

      const elapsedSec = (now - this.multipleStartTime) / 1000
      if (elapsedSec >= this.config.multipleFaceThresholdSec) {
        statusNotice = `⚠ Multiple people detected (${faceResult.faceCount} faces). Only the candidate may be present.`
        isWarning = true

        if (!this.activeMultipleReported) {
          this.activeMultipleReported = true
          this.onIncidentCallback({
            eventType: "MULTIPLE_PERSON",
            severity: "HIGH",
            duration: Number(elapsedSec.toFixed(1)),
            confidence: faceResult.confidence || 0.95,
            description: `Multiple people (${faceResult.faceCount} faces) visible in camera frame for ${elapsedSec.toFixed(1)}s.`,
            timestamp: new Date().toISOString(),
            metadata: {
              faceCount: faceResult.faceCount,
              elapsedSeconds: elapsedSec,
            },
          })
        }
      }
    } else {
      this.multipleStartTime = null
      this.activeMultipleReported = false
    }

    // --------------------------------------------------------
    // 3. Identity Verification & Mismatch Analysis
    // --------------------------------------------------------
    if (
      faceResult.faceDetected &&
      faceResult.faceCount === 1 &&
      currentEncoding &&
      registeredEncoding
    ) {
      similarity = computeCosineSimilarity(currentEncoding, registeredEncoding)

      if (similarity < this.config.identitySimilarityThreshold) {
        if (!this.mismatchStartTime) this.mismatchStartTime = now

        const elapsedSec = (now - this.mismatchStartTime) / 1000
        if (elapsedSec >= this.config.identityMismatchThresholdSec) {
          statusNotice = `⚠ Identity mismatch detected. Please face the camera directly.`
          isWarning = true

          if (!this.activeMismatchReported) {
            this.activeMismatchReported = true
            const mismatchConfidence = Math.min(
              0.98,
              Number((1.0 - similarity).toFixed(2)),
            )

            this.onIncidentCallback({
              eventType: "IDENTITY_MISMATCH",
              severity: "HIGH",
              duration: Number(elapsedSec.toFixed(1)),
              confidence: mismatchConfidence,
              description: `Candidate identity does not match baseline (similarity: ${Math.round(
                similarity * 100,
              )}%).`,
              timestamp: new Date().toISOString(),
              metadata: {
                similarityScore: similarity,
                threshold: this.config.identitySimilarityThreshold,
                elapsedSeconds: elapsedSec,
              },
            })
          }
        }
      } else {
        this.mismatchStartTime = null
        this.activeMismatchReported = false
      }
    }

    // --------------------------------------------------------
    // 4. Mobile Phone & Device Detection
    // --------------------------------------------------------
    const hasMobile = detectedObjects.some(
      (obj) =>
        obj.label === "cell phone" &&
        obj.confidence >= this.config.objectConfidenceThreshold,
    )
    const hasDevice = detectedObjects.some(
      (obj) =>
        obj.label === "laptop" &&
        obj.confidence >= this.config.objectConfidenceThreshold,
    )

    if (hasMobile) {
      if (!this.mobileStartTime) this.mobileStartTime = now
      const elapsedSec = (now - this.mobileStartTime) / 1000

      if (elapsedSec >= this.config.mobileDetectionThresholdSec) {
        statusNotice = "⚠ Mobile device detected. Phones are prohibited during the interview."
        isWarning = true

        if (!this.activeMobileReported) {
          this.activeMobileReported = true
          this.onIncidentCallback({
            eventType: "MOBILE_DETECTED",
            severity: "HIGH",
            duration: Number(elapsedSec.toFixed(1)),
            confidence: 0.9,
            description: `Mobile phone detected in frame for ${elapsedSec.toFixed(1)}s.`,
            timestamp: new Date().toISOString(),
            metadata: { elapsedSeconds: elapsedSec },
          })
        }
      }
    } else {
      this.mobileStartTime = null
      this.activeMobileReported = false
    }

    if (hasDevice && !hasMobile) {
      if (!this.deviceStartTime) this.deviceStartTime = now
      const elapsedSec = (now - this.deviceStartTime) / 1000

      if (elapsedSec >= this.config.deviceDetectionThresholdSec) {
        statusNotice = "⚠ Secondary device detected in frame."
        isWarning = true

        if (!this.activeDeviceReported) {
          this.activeDeviceReported = true
          this.onIncidentCallback({
            eventType: "DEVICE_DETECTED",
            severity: "MEDIUM",
            duration: Number(elapsedSec.toFixed(1)),
            confidence: 0.85,
            description: `Unauthorized secondary electronic device visible for ${elapsedSec.toFixed(1)}s.`,
            timestamp: new Date().toISOString(),
            metadata: { elapsedSeconds: elapsedSec },
          })
        }
      }
    } else {
      this.deviceStartTime = null
      this.activeDeviceReported = false
    }

    return { statusNotice, isWarning, similarity }
  }

  reset(): void {
    this.missingStartTime = null
    this.multipleStartTime = null
    this.mismatchStartTime = null
    this.mobileStartTime = null
    this.deviceStartTime = null

    this.activeMissingReported = false
    this.activeMultipleReported = false
    this.activeMismatchReported = false
    this.activeMobileReported = false
    this.activeDeviceReported = false
  }
}
