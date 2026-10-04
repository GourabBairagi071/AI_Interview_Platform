import { useEffect, useState, useMemo } from "react"
import type { ChangeEvent } from "react"

import {
  analyzeResume,
  deleteResume,
  downloadOptimizedResumePDFBlob,
  generateATSResume,
  getResume,
  uploadResume,
} from "../services/api"

import "./Resume.css"

// ============================================================
// TYPES
// ============================================================

interface ResumeData {
  id: string
  user_id: string
  filename: string
  file_url: string
  uploaded_at: string
  updated_at: string
}

interface RoleMatch {
  role: string
  match_percentage: number
  reason: string
}

interface ResumeAnalysis {
  ats_score: number | null
  skills: string[]
  strengths: string[]
  weaknesses: string[]
  improvement_suggestions: string[]
  role_matching: RoleMatch[]
  summary: string
}

interface ContactInfo {
  email?: string
  phone?: string
  location?: string
  linkedin?: string
  github?: string
  website?: string
}

interface OptimizedResume {
  name?: string
  contact_info?: ContactInfo
  estimated_ats_score: number | null
  target_role: string
  professional_summary: string
  skills: string[]
  experience: {
    company: string
    role: string
    duration: string
    location?: string
    bullets: string[]
  }[]
  projects: {
    name: string
    technologies: string[]
    bullets: string[]
  }[]
  education: {
    degree: string
    institution: string
    duration: string
    grade?: string
  }[]
  certifications: string[]
  achievements: string[]
  keywords: string[]
  improvements: string[]
  missing_keywords: string[]
}

const COMMON_ROLES = [
  "Software Engineer",
  "Full Stack Developer",
  "Frontend Developer",
  "Backend Developer",
  "Data Scientist",
  "DevOps Engineer",
  "Machine Learning Engineer",
]

// ============================================================
// HELPERS
// ============================================================

function safeString(value: unknown): string {
  if (value === null || value === undefined) {
    return ""
  }
  return String(value).trim()
}

function safeStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return []
  }
  return value
    .filter((item) => item !== null && item !== undefined)
    .map(String)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
}

function parseSafeScore(value: unknown): number | null {
  if (value === null || value === undefined || value === "") {
    return null
  }
  if (typeof value === "number") {
    return Number.isFinite(value) ? Math.max(0, Math.min(100, Math.round(value))) : null
  }
  if (typeof value === "string") {
    const trimmed = value.trim()
    if (!trimmed) return null
    // Extract first numeric group (handles "78", "78%", "78/100", "78 out of 100")
    const match = trimmed.match(/(\d+(?:\.\d+)?)/)
    if (match) {
      const num = parseFloat(match[1])
      if (Number.isFinite(num)) {
        return Math.max(0, Math.min(100, Math.round(num)))
      }
    }
  }
  return null
}

function clampScore(value: unknown): number {
  const score = parseSafeScore(value)
  return score !== null ? score : 0
}

function base64ToBlob(base64: string, mimeType = "application/pdf"): Blob {
  const cleanBase64 = base64.replace(/\s/g, "")
  const byteCharacters = atob(cleanBase64)
  const byteNumbers = new Array(byteCharacters.length)
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i)
  }
  const byteArray = new Uint8Array(byteNumbers)
  return new Blob([byteArray], { type: mimeType })
}

// ============================================================
// NORMALIZE AI ANALYSIS
// ============================================================

function normalizeAnalysis(raw: Record<string, unknown>): ResumeAnalysis {
  if (!raw || typeof raw !== "object") {
    throw new Error("AI returned an invalid analysis response.")
  }

  // Handle nested analysis wrapper if raw is the root response object
  const target: Record<string, unknown> =
    raw.analysis && typeof raw.analysis === "object"
      ? (raw.analysis as Record<string, unknown>)
      : raw

  // Extract raw score across possible backend/AI property keys
  const rawScore =
    target.ats_score !== undefined
      ? target.ats_score
      : (target as any).atsScore !== undefined
      ? (target as any).atsScore
      : target.estimated_ats_score !== undefined
      ? target.estimated_ats_score
      : (target as any).estimatedAtsScore !== undefined
      ? (target as any).estimatedAtsScore
      : target.score

  const atsScore = parseSafeScore(rawScore)

  const rawRoles = Array.isArray(target.role_matching) ? target.role_matching : []

  const roleMatching: RoleMatch[] = rawRoles
    .filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object"))
    .map((item) => ({
      role: safeString(item.role ?? item.job_role ?? "Unknown Role"),
      match_percentage: clampScore(item.match_percentage ?? item.match ?? item.score ?? 0),
      reason: safeString(item.reason ?? item.explanation ?? ""),
    }))

  return {
    ats_score: atsScore,
    skills: safeStringArray(target.skills),
    strengths: safeStringArray(target.strengths),
    weaknesses: safeStringArray(target.weaknesses),
    improvement_suggestions: safeStringArray(
      target.improvement_suggestions ?? target.suggestions ?? target.improvements,
    ),
    role_matching: roleMatching,
    summary: safeString(target.summary ?? target.professional_summary ?? target.overview ?? ""),
  }
}

// ============================================================
// NORMALIZE OPTIMIZED RESUME
// ============================================================

function normalizeOptimizedResume(raw: Record<string, unknown>): OptimizedResume {
  if (!raw || typeof raw !== "object") {
    throw new Error("AI returned an invalid optimized resume.")
  }

  const rawExperience = Array.isArray(raw.experience) ? raw.experience : []
  const experience = rawExperience
    .filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object"))
    .map((item) => ({
      company: safeString(item.company),
      role: safeString(item.role),
      duration: safeString(item.duration),
      location: safeString(item.location),
      bullets: safeStringArray(item.bullets),
    }))

  const rawProjects = Array.isArray(raw.projects) ? raw.projects : []
  const projects = rawProjects
    .filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object"))
    .map((item) => ({
      name: safeString(item.name),
      technologies: safeStringArray(item.technologies),
      bullets: safeStringArray(item.bullets),
    }))

  const rawEducation = Array.isArray(raw.education) ? raw.education : []
  const education = rawEducation
    .filter((item): item is Record<string, unknown> => Boolean(item && typeof item === "object"))
    .map((item) => ({
      degree: safeString(item.degree),
      institution: safeString(item.institution),
      duration: safeString(item.duration),
      grade: safeString(item.grade),
    }))

  const rawContact =
    raw.contact_info && typeof raw.contact_info === "object"
      ? (raw.contact_info as Record<string, unknown>)
      : {}

  const rawScore =
    raw.estimated_ats_score !== undefined
      ? raw.estimated_ats_score
      : (raw as any).estimatedAtsScore !== undefined
      ? (raw as any).estimatedAtsScore
      : raw.ats_score !== undefined
      ? raw.ats_score
      : raw.score
  const estimatedAtsScore = parseSafeScore(rawScore)

  return {
    name: safeString(raw.name),
    contact_info: {
      email: safeString(rawContact.email),
      phone: safeString(rawContact.phone),
      location: safeString(rawContact.location),
      linkedin: safeString(rawContact.linkedin),
      github: safeString(rawContact.github),
      website: safeString(rawContact.website),
    },
    estimated_ats_score: estimatedAtsScore,
    target_role: safeString(raw.target_role),
    professional_summary: safeString(raw.professional_summary ?? raw.summary),
    skills: safeStringArray(raw.skills),
    experience,
    projects,
    education,
    certifications: safeStringArray(raw.certifications),
    achievements: safeStringArray(raw.achievements),
    keywords: safeStringArray(raw.keywords),
    improvements: safeStringArray(raw.improvements),
    missing_keywords: safeStringArray(raw.missing_keywords),
  }
}

// ============================================================
// COMPONENT
// ============================================================

export default function Resume() {
  const [resume, setResume] = useState<ResumeData | null>(null)
  const [analysis, setAnalysis] = useState<ResumeAnalysis | null>(null)
  const [optimizedResume, setOptimizedResume] = useState<OptimizedResume | null>(null)

  const [targetRole, setTargetRole] = useState("Software Engineer")

  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null)
  const [showPdfPreview, setShowPdfPreview] = useState(false)
  const [downloadingPdf, setDownloadingPdf] = useState(false)

  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")

  // Clean up object URL on unmount
  useEffect(() => {
    return () => {
      if (pdfBlobUrl) {
        URL.revokeObjectURL(pdfBlobUrl)
      }
    }
  }, [pdfBlobUrl])

  async function loadResume() {
    try {
      setLoading(true)
      setError("")
      const data = await getResume()
      setResume(data)

      // Hydrate existing analysis from backend if available
      if (data && (data as any).analysis) {
        try {
          const normalized = normalizeAnalysis((data as any).analysis as Record<string, unknown>)
          setAnalysis(normalized)
          if (normalized.role_matching.length > 0 && targetRole === "Software Engineer") {
            setTargetRole(normalized.role_matching[0].role)
          }
        } catch (normErr) {
          console.warn("Could not parse existing analysis:", normErr)
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load resume"
      if (!message.toLowerCase().includes("resume not found")) {
        setError(message)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadResume()
  }, [])

  // ==========================================================
  // UPLOAD
  // ==========================================================

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return

    const extension = file.name.split(".").pop()?.toLowerCase()
    if (extension !== "pdf" && extension !== "docx") {
      setError("Only PDF and DOCX files are allowed.")
      event.target.value = ""
      return
    }

    try {
      setLoading(true)
      setError("")
      setSuccess("")

      const data = await uploadResume(file)
      setResume(data.resume)
      setAnalysis(null)
      setOptimizedResume(null)
      if (pdfBlobUrl) {
        URL.revokeObjectURL(pdfBlobUrl)
        setPdfBlobUrl(null)
      }
      setShowPdfPreview(false)
      setSuccess("Resume uploaded successfully.")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resume upload failed")
    } finally {
      setLoading(false)
      event.target.value = ""
    }
  }

  // ==========================================================
  // ANALYZE
  // ==========================================================

  async function handleAnalyze() {
    if (!resume) {
      setError("Please upload a resume first.")
      return
    }

    try {
      setAnalyzing(true)
      setError("")
      setSuccess("")

      const data = await analyzeResume()

      if (!data || typeof data !== "object") {
        throw new Error("AI returned an invalid analysis response.")
      }

      const analysisPayload =
        data.analysis && typeof data.analysis === "object"
          ? (data.analysis as unknown as Record<string, unknown>)
          : (data as unknown as Record<string, unknown>)

      const normalized = normalizeAnalysis(analysisPayload)
      setAnalysis(normalized)

      // Automatically set target role to top match if available and not custom
      if (normalized.role_matching.length > 0 && targetRole === "Software Engineer") {
        setTargetRole(normalized.role_matching[0].role)
      }

      setSuccess("Resume analysis completed successfully.")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resume analysis failed")
    } finally {
      setAnalyzing(false)
    }
  }

  // ==========================================================
  // GENERATE ATS RESUME
  // ==========================================================

  async function handleGenerateATSResume() {
    if (!resume) {
      setError("Please upload a resume first.")
      return
    }

    const cleanRole = targetRole.trim()
    if (!cleanRole || cleanRole.length < 2) {
      setError("Please enter a valid target job role (at least 2 characters).")
      return
    }

    try {
      setGenerating(true)
      setError("")
      setSuccess("")

      const data = await generateATSResume(cleanRole)

      if (!data || typeof data !== "object" || !data.optimized_resume) {
        throw new Error("AI returned an invalid optimized resume.")
      }

      const normalized = normalizeOptimizedResume(
        data.optimized_resume as Record<string, unknown>,
      )
      setOptimizedResume(normalized)

      // Handle PDF blob
      if (data.pdf_base64) {
        try {
          const blob = base64ToBlob(data.pdf_base64, "application/pdf")
          if (pdfBlobUrl) {
            URL.revokeObjectURL(pdfBlobUrl)
          }
          const url = URL.createObjectURL(blob)
          setPdfBlobUrl(url)
        } catch (pdfErr) {
          console.error("Failed to parse PDF base64:", pdfErr)
        }
      }

      setSuccess("✓ ATS Resume Generated")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate ATS-friendly resume")
    } finally {
      setGenerating(false)
    }
  }

  // ==========================================================
  // PREVIEW RESUME
  // ==========================================================

  async function handlePreviewResume() {
    setError("")
    if (pdfBlobUrl) {
      setShowPdfPreview(true)
      return
    }

    // Fallback: fetch blob from backend
    try {
      setDownloadingPdf(true)
      const blob = await downloadOptimizedResumePDFBlob()
      const url = URL.createObjectURL(blob)
      setPdfBlobUrl(url)
      setShowPdfPreview(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load resume PDF for preview.")
    } finally {
      setDownloadingPdf(false)
    }
  }

  // ==========================================================
  // DOWNLOAD PDF
  // ==========================================================

  async function handleDownloadPDF() {
    setError("")
    const safeRoleName = (targetRole || "Job").trim().replace(/[^a-zA-Z0-9_-]/g, "_")
    const fileName = `ATS_Resume_${safeRoleName}.pdf`

    if (pdfBlobUrl) {
      const link = document.createElement("a")
      link.href = pdfBlobUrl
      link.download = fileName
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      return
    }

    try {
      setDownloadingPdf(true)
      const blob = await downloadOptimizedResumePDFBlob()
      const url = URL.createObjectURL(blob)
      setPdfBlobUrl(url)

      const link = document.createElement("a")
      link.href = url
      link.download = fileName
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download PDF resume.")
    } finally {
      setDownloadingPdf(false)
    }
  }

  // ==========================================================
  // DELETE
  // ==========================================================

  async function handleDelete() {
    if (!resume) return

    const confirmed = window.confirm("Are you sure you want to delete your resume?")
    if (!confirmed) return

    try {
      setDeleting(true)
      setError("")
      setSuccess("")

      await deleteResume()

      setResume(null)
      setAnalysis(null)
      setOptimizedResume(null)
      if (pdfBlobUrl) {
        URL.revokeObjectURL(pdfBlobUrl)
        setPdfBlobUrl(null)
      }
      setShowPdfPreview(false)
      setSuccess("Resume deleted successfully.")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete resume")
    } finally {
      setDeleting(false)
    }
  }

  // Available suggestions: roles from analysis or common roles
  const suggestedRoles = useMemo(() => {
    if (analysis && analysis.role_matching.length > 0) {
      return analysis.role_matching.map((r) => r.role)
    }
    return COMMON_ROLES
  }, [analysis])

  // ==========================================================
  // LOADING STATE
  // ==========================================================

  if (loading) {
    return (
      <div className="resume-page">
        <div style={{ textAlign: "center", padding: "100px 20px", color: "#94a3b8" }}>
          <div className="generation-spinner" style={{ margin: "0 auto 16px" }} />
          Loading resume...
        </div>
      </div>
    )
  }

  // ==========================================================
  // RENDER
  // ==========================================================

  return (
    <div className="resume-page">
      {/* Background aesthetics */}
      <div className="resume-background">
        <div className="resume-glow glow-one" />
        <div className="resume-glow glow-two" />
        <div className="resume-grid" />
      </div>

      {/* HEADER */}
      <header className="resume-header">
        <div className="resume-eyebrow">AI RESUME OPTIMIZER</div>
        <h1>Resume Analyzer & ATS Builder</h1>
        <p className="resume-subtitle">
          Upload your resume, analyze ATS readiness, and generate an ATS-optimized, single-column PDF resume targeted to your dream job.
        </p>
      </header>

      <main className="resume-container">
        {/* NOTIFICATIONS */}
        {error && <div className="resume-error">⚠ {error}</div>}
        {success && (
          <div
            style={{
              padding: "14px 18px",
              borderRadius: "12px",
              background: "rgba(16, 185, 129, 0.12)",
              border: "1px solid rgba(16, 185, 129, 0.25)",
              color: "#34d399",
              marginBottom: "20px",
              fontWeight: 600,
            }}
          >
            {success}
          </div>
        )}

        {/* =====================================================
            1. UPLOAD RESUME CARD
        ===================================================== */}
        <section className="upload-card">
          <div className="upload-icon">📄</div>
          <h2>{resume ? "Your Active Resume" : "Upload Your Resume"}</h2>
          <p>
            {resume
              ? "Your resume is active and ready for AI analysis and ATS generation."
              : "Upload your existing resume in PDF or DOCX format to get started."}
          </p>

          {!resume ? (
            <label htmlFor="resume-upload" className="drop-zone">
              <div className="drop-icon">⬆</div>
              <strong>Choose a resume file</strong>
              <span>Supports PDF and DOCX up to 10MB</span>
              <small>Click to browse from your device</small>
              <input
                id="resume-upload"
                type="file"
                accept=".pdf,.docx"
                onChange={handleUpload}
                style={{ display: "none" }}
              />
            </label>
          ) : (
            <div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "18px 24px",
                  borderRadius: "16px",
                  background: "rgba(15, 23, 42, 0.9)",
                  border: "1px solid #334155",
                  marginBottom: "20px",
                  flexWrap: "wrap",
                  gap: "12px",
                }}
              >
                <div style={{ textAlign: "left" }}>
                  <div style={{ fontSize: "17px", fontWeight: 700, color: "#f8fafc" }}>
                    {resume.filename}
                  </div>
                  <div style={{ fontSize: "13px", color: "#94a3b8", marginTop: "4px" }}>
                    Uploaded {new Date(resume.uploaded_at).toLocaleDateString()}
                  </div>
                </div>

                <div style={{ display: "flex", gap: "10px" }}>
                  <label
                    htmlFor="replace-resume"
                    style={{
                      padding: "10px 18px",
                      borderRadius: "10px",
                      background: "#1e293b",
                      border: "1px solid #475569",
                      color: "#f8fafc",
                      fontSize: "13px",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    Replace File
                  </label>
                  <input
                    id="replace-resume"
                    type="file"
                    accept=".pdf,.docx"
                    onChange={handleUpload}
                    style={{ display: "none" }}
                  />

                  <button
                    type="button"
                    onClick={handleDelete}
                    disabled={deleting}
                    style={{
                      padding: "10px 18px",
                      borderRadius: "10px",
                      background: "rgba(239, 68, 68, 0.15)",
                      border: "1px solid rgba(239, 68, 68, 0.3)",
                      color: "#fca5a5",
                      fontSize: "13px",
                      fontWeight: 700,
                      cursor: "pointer",
                    }}
                  >
                    {deleting ? "Deleting..." : "Delete"}
                  </button>
                </div>
              </div>

              <button
                type="button"
                className="analyze-button"
                onClick={handleAnalyze}
                disabled={analyzing}
              >
                {analyzing ? "Analyzing Resume..." : "Analyze Resume with AI →"}
              </button>
            </div>
          )}
        </section>

        {/* =====================================================
            2. RESUME ANALYSIS RESULTS
        ===================================================== */}
        {analysis && (
          <section className="analysis-results">
            <div className="results-top">
              <div>
                <span className="resume-eyebrow">AUDIT SUMMARY</span>
                <h2>Resume Analysis</h2>
                <p>
                  {analysis.summary ||
                    "Comprehensive ATS compatibility evaluation based on your resume content."}
                </p>
              </div>

              <div className="ats-card">
                <span>ESTIMATED ATS SCORE</span>
                <strong>
                  {analysis.ats_score !== null && analysis.ats_score !== undefined
                    ? analysis.ats_score
                    : "--"}
                </strong>
                <small>/100 Match</small>
              </div>
            </div>

            {/* SKILLS */}
            {analysis.skills.length > 0 && (
              <div className="result-card">
                <div className="section-heading">
                  <span>CORE SKILLS</span>
                  <h3>Detected Technical Skills ({analysis.skills.length})</h3>
                </div>
                <div className="skills-list">
                  {analysis.skills.map((skill, idx) => (
                    <span key={idx} className="skill-pill">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* STRENGTHS & WEAKNESSES */}
            <div className="two-column">
              <div className="result-card">
                <div className="section-heading">
                  <span>KEY STRENGTHS</span>
                  <h3>Profile Strengths</h3>
                </div>
                <ul className="insight-list">
                  {analysis.strengths.map((item, idx) => (
                    <li key={idx}>
                      <span>✓</span>
                      <div>{item}</div>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="result-card">
                <div className="section-heading">
                  <span style={{ color: "#fca5a5" }}>AREAS TO IMPROVE</span>
                  <h3>Identified Gaps</h3>
                </div>
                <ul className="insight-list">
                  {analysis.weaknesses.map((item, idx) => (
                    <li key={idx}>
                      <span style={{ color: "#f87171" }}>✕</span>
                      <div>{item}</div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* AI SUGGESTIONS */}
            {analysis.improvement_suggestions.length > 0 && (
              <div className="result-card">
                <div className="section-heading">
                  <span>RECOMMENDATIONS</span>
                  <h3>Actionable ATS Improvements</h3>
                </div>
                <div className="suggestion-list">
                  {analysis.improvement_suggestions.map((sug, idx) => (
                    <div key={idx} className="suggestion">
                      <span>{String(idx + 1).padStart(2, "0")}</span>
                      <p>{sug}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ROLE MATCHES */}
            {analysis.role_matching.length > 0 && (
              <div className="result-card">
                <div className="section-heading">
                  <span>CAREER ALIGNMENT</span>
                  <h3>Role Match Breakdown</h3>
                </div>
                <div className="role-list">
                  {analysis.role_matching.map((roleItem, idx) => (
                    <div key={idx} className="role-item">
                      <div className="role-info">
                        <strong>{roleItem.role}</strong>
                        {roleItem.reason && <p>{roleItem.reason}</p>}
                      </div>
                      <div className="role-score">
                        <strong>{Math.round(roleItem.match_percentage)}% Match</strong>
                        <div className="score-bar">
                          <div
                            style={{
                              width: `${Math.min(100, Math.max(0, roleItem.match_percentage))}%`,
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {/* =====================================================
            3. AI ATS RESUME BUILDER (TARGET ROLE + GENERATE)
        ===================================================== */}
        {resume && (
          <section className="rebuilder-card" style={{ marginTop: "40px" }}>
            <div className="rebuilder-header">
              <div>
                <span className="resume-eyebrow">ATS OPTIMIZATION</span>
                <h2>Generate ATS-Friendly Resume</h2>
                <p>
                  Target your resume for a specific job title. Our AI restructures your truthful source experience, enhances action verbs, optimizes keyword density, and generates an ATS-compliant single-column PDF.
                </p>
              </div>
              <div className="rebuilder-icon">⚡</div>
            </div>

            {/* TARGET ROLE CONTROLS */}
            <div className="rebuilder-controls">
              <label htmlFor="target-role-input">Target Job Role</label>
              <div className="role-input-row">
                <input
                  id="target-role-input"
                  type="text"
                  value={targetRole}
                  onChange={(e) => setTargetRole(e.target.value)}
                  placeholder="e.g. Software Engineer, Full Stack Developer, Data Scientist"
                  disabled={generating}
                />
                <button
                  type="button"
                  id="generate-ats-resume-btn"
                  className="generate-resume-button"
                  onClick={handleGenerateATSResume}
                  disabled={generating || !targetRole.trim()}
                >
                  {generating ? "Generating..." : "Generate ATS-Friendly Resume"}
                </button>
              </div>

              {/* ROLE SUGGESTIONS CHIPS */}
              <div className="role-suggestions">
                <span className="role-suggestions-label">Suggestions:</span>
                {suggestedRoles.map((roleName, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className={`role-chip ${targetRole.toLowerCase() === roleName.toLowerCase() ? "active" : ""}`}
                    onClick={() => setTargetRole(roleName)}
                    disabled={generating}
                  >
                    {roleName}
                  </button>
                ))}
              </div>
            </div>

            {/* GENERATING STATE */}
            {generating && (
              <div className="generation-status-box">
                <div className="generation-spinner" />
                <div className="generation-status-text">
                  Generating your ATS-friendly resume...
                </div>
              </div>
            )}

            {/* SUCCESS BANNER & ACTION BUTTONS */}
            {optimizedResume && !generating && (
              <div className="ats-success-banner">
                <div className="ats-success-info">
                  <div className="ats-success-badge">✓ ATS Resume Generated</div>
                  <span style={{ color: "#94a3b8" }}>
                    Optimized for <strong>{optimizedResume.target_role}</strong>
                  </span>
                </div>

                <div className="ats-action-buttons">
                  <button
                    type="button"
                    id="preview-resume-btn"
                    className="preview-resume-btn"
                    onClick={handlePreviewResume}
                    disabled={downloadingPdf}
                  >
                    👁 Preview Resume
                  </button>
                  <button
                    type="button"
                    id="download-pdf-btn"
                    className="download-pdf-btn"
                    onClick={handleDownloadPDF}
                    disabled={downloadingPdf}
                  >
                    ⬇ Download PDF
                  </button>
                </div>
              </div>
            )}

            {/* =====================================================
                OPTIMIZED RESUME CONTENT OVERVIEW
            ===================================================== */}
            {optimizedResume && (
              <div className="optimized-result">
                <div className="optimized-score">
                  <div>
                    <span>ESTIMATED ATS SCORE</span>
                    <strong>
                      {optimizedResume.estimated_ats_score !== null &&
                      optimizedResume.estimated_ats_score !== undefined
                        ? optimizedResume.estimated_ats_score
                        : "--"}
                    </strong>
                    <small>/100 Match</small>
                  </div>
                  <div className="target-badge">{optimizedResume.target_role}</div>
                </div>

                {/* Candidate Name & Contact Info */}
                {(optimizedResume.name || optimizedResume.contact_info) && (
                  <div className="optimized-section" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", paddingBottom: "16px" }}>
                    <h3 style={{ fontSize: "20px", color: "#f8fafc", margin: "0 0 6px" }}>
                      {optimizedResume.name || "Candidate"}
                    </h3>
                    {optimizedResume.contact_info && (
                      <p style={{ color: "#94a3b8", fontSize: "14px", margin: 0 }}>
                        {[
                          optimizedResume.contact_info.email,
                          optimizedResume.contact_info.phone,
                          optimizedResume.contact_info.location,
                          optimizedResume.contact_info.linkedin,
                          optimizedResume.contact_info.github,
                        ]
                          .filter(Boolean)
                          .join(" • ")}
                      </p>
                    )}
                  </div>
                )}

                {/* Summary */}
                {optimizedResume.professional_summary && (
                  <div className="optimized-section">
                    <h3>Professional Summary</h3>
                    <p>{optimizedResume.professional_summary}</p>
                  </div>
                )}

                {/* Skills */}
                {optimizedResume.skills.length > 0 && (
                  <div className="optimized-section">
                    <h3>Targeted Skills</h3>
                    <div className="project-tech">
                      {optimizedResume.skills.map((skill, idx) => (
                        <span key={idx} className="keyword-pill">
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Experience */}
                {optimizedResume.experience.length > 0 && (
                  <div className="optimized-section">
                    <h3>Work Experience</h3>
                    {optimizedResume.experience.map((exp, idx) => (
                      <div key={idx} className="optimized-item">
                        <div className="optimized-item-header">
                          <strong>{exp.role}</strong>
                          <span>{exp.duration}</span>
                        </div>
                        {exp.company && (
                          <div className="company-name">
                            {exp.company}
                            {exp.location ? ` • ${exp.location}` : ""}
                          </div>
                        )}
                        {exp.bullets.length > 0 && (
                          <ul>
                            {exp.bullets.map((bullet, bIdx) => (
                              <li key={bIdx}>{bullet}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Projects */}
                {optimizedResume.projects.length > 0 && (
                  <div className="optimized-section">
                    <h3>Projects</h3>
                    {optimizedResume.projects.map((proj, idx) => (
                      <div key={idx} className="optimized-item">
                        <strong>{proj.name}</strong>
                        {proj.technologies.length > 0 && (
                          <div className="project-tech">
                            {proj.technologies.map((tech, tIdx) => (
                              <span key={tIdx}>{tech}</span>
                            ))}
                          </div>
                        )}
                        {proj.bullets.length > 0 && (
                          <ul>
                            {proj.bullets.map((bullet, bIdx) => (
                              <li key={bIdx}>{bullet}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Education */}
                {optimizedResume.education.length > 0 && (
                  <div className="optimized-section">
                    <h3>Education</h3>
                    {optimizedResume.education.map((edu, idx) => (
                      <div key={idx} className="education-item">
                        <strong>{edu.degree}</strong>
                        <span>{edu.institution}</span>
                        {edu.duration && <small>{edu.duration}</small>}
                      </div>
                    ))}
                  </div>
                )}

                {/* Certifications */}
                {optimizedResume.certifications.length > 0 && (
                  <div className="optimized-section">
                    <h3>Certifications</h3>
                    <ul>
                      {optimizedResume.certifications.map((cert, idx) => (
                        <li key={idx} style={{ color: "#cbd5e1" }}>
                          {cert}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Achievements */}
                {optimizedResume.achievements.length > 0 && (
                  <div className="optimized-section">
                    <h3>Achievements</h3>
                    <ul>
                      {optimizedResume.achievements.map((ach, idx) => (
                        <li key={idx} style={{ color: "#cbd5e1" }}>
                          {ach}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* ATS Keywords */}
                {optimizedResume.keywords.length > 0 && (
                  <div className="optimized-section">
                    <h3>ATS Keywords Incorporated</h3>
                    <div className="project-tech">
                      {optimizedResume.keywords.map((kw, idx) => (
                        <span key={idx} className="keyword-pill">
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Improvements */}
                {optimizedResume.improvements.length > 0 && (
                  <div className="optimized-section">
                    <h3>Optimizations Applied</h3>
                    <ul className="improvement-list">
                      {optimizedResume.improvements.map((imp, idx) => (
                        <li key={idx} style={{ color: "#86efac", marginBottom: "6px" }}>
                          ✓ {imp}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Missing Keywords */}
                {optimizedResume.missing_keywords.length > 0 && (
                  <div className="missing-keywords">
                    <h3>Recommended Missing Keywords to Consider</h3>
                    <div className="project-tech">
                      {optimizedResume.missing_keywords.map((mkw, idx) => (
                        <span key={idx} style={{ background: "rgba(245,158,11,0.15)", color: "#fde68a", borderColor: "rgba(245,158,11,0.3)" }}>
                          + {mkw}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </section>
        )}
      </main>

      {/* =====================================================
          4. PDF PREVIEW MODAL
      ===================================================== */}
      {showPdfPreview && (
        <div
          className="pdf-preview-overlay"
          role="dialog"
          aria-modal="true"
          onClick={() => setShowPdfPreview(false)}
        >
          <div
            className="pdf-preview-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="pdf-modal-header">
              <div className="pdf-modal-title-group">
                <h3>ATS Resume Preview</h3>
                <p>Generated PDF for target role: {targetRole}</p>
              </div>

              <div className="pdf-modal-controls">
                <button
                  type="button"
                  className="download-pdf-btn"
                  onClick={handleDownloadPDF}
                  style={{ padding: "8px 16px", fontSize: "13px" }}
                >
                  ⬇ Download PDF
                </button>
                <button
                  type="button"
                  className="pdf-modal-close-btn"
                  onClick={() => setShowPdfPreview(false)}
                  aria-label="Close preview"
                >
                  ✕
                </button>
              </div>
            </div>

            <div className="pdf-modal-body">
              {pdfBlobUrl ? (
                <iframe
                  src={pdfBlobUrl}
                  title="ATS Resume PDF Viewer"
                  className="pdf-preview-iframe"
                />
              ) : (
                <div style={{ textAlign: "center", padding: "80px 20px", color: "#94a3b8" }}>
                  Loading PDF preview...
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}