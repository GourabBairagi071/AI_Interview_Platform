import { useEffect, useState } from "react"
import type { ChangeEvent } from "react"


import {
  analyzeResume,
  deleteResume,
  generateATSResume,
  getResume,
  uploadResume,
} from "../services/api"


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
  ats_score: number
  skills: string[]
  strengths: string[]
  weaknesses: string[]
  improvement_suggestions: string[]
  role_matching: RoleMatch[]
  summary: string
}

interface OptimizedResume {
  estimated_ats_score: number
  target_role: string
  professional_summary: string

  skills: string[]

  experience: {
    company: string
    role: string
    duration: string
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
  }[]

  certifications: string[]
  keywords: string[]
  improvements: string[]
  missing_keywords: string[]
}


// ============================================================
// HELPERS
// ============================================================

function safeString(value: unknown): string {
  if (
    value === null ||
    value === undefined
  ) {
    return ""
  }

  return String(value)
}


function safeStringArray(
  value: unknown,
): string[] {
  if (!Array.isArray(value)) {
    return []
  }

  return value
    .filter(
      (item) =>
        item !== null &&
        item !== undefined,
    )
    .map(String)
    .filter(
      (item) =>
        item.trim().length > 0,
    )
}


function safeNumber(
  value: unknown,
): number {
  const number = Number(value)

  if (!Number.isFinite(number)) {
    return 0
  }

  return number
}


function clampScore(
  value: unknown,
): number {
  return Math.max(
    0,
    Math.min(
      100,
      safeNumber(value),
    ),
  )
}


// ============================================================
// NORMALIZE AI ANALYSIS
// ============================================================

function normalizeAnalysis(
  raw: any,
): ResumeAnalysis {

  if (
    !raw ||
    typeof raw !== "object"
  ) {
    throw new Error(
      "AI returned an invalid analysis response.",
    )
  }

  const rawRoles =
    Array.isArray(
      raw.role_matching,
    )
      ? raw.role_matching
      : []

  const roleMatching: RoleMatch[] =
    rawRoles
      .filter(
        (item: any) =>
          item &&
          typeof item === "object",
      )
      .map(
        (item: any) => ({
          role: safeString(
            item.role ??
            item.job_role ??
            "Unknown Role",
          ),

          match_percentage:
            clampScore(
              item.match_percentage ??
              item.match ??
              item.score ??
              0,
            ),

          reason: safeString(
            item.reason ??
            item.explanation ??
            "",
          ),
        }),
      )

  return {
    ats_score: clampScore(
      raw.ats_score ??
      raw.estimated_ats_score ??
      raw.score ??
      0,
    ),

    skills: safeStringArray(
      raw.skills,
    ),

    strengths: safeStringArray(
      raw.strengths,
    ),

    weaknesses: safeStringArray(
      raw.weaknesses,
    ),

    improvement_suggestions:
      safeStringArray(
        raw.improvement_suggestions ??
        raw.suggestions ??
        raw.improvements,
      ),

    role_matching:
      roleMatching,

    summary: safeString(
      raw.summary ??
      raw.professional_summary ??
      raw.overview ??
      "",
    ),
  }
}


// ============================================================
// NORMALIZE OPTIMIZED RESUME
// ============================================================

function normalizeOptimizedResume(
  raw: any,
): OptimizedResume {

  if (
    !raw ||
    typeof raw !== "object"
  ) {
    throw new Error(
      "AI returned an invalid optimized resume.",
    )
  }

  const experience =
    Array.isArray(
      raw.experience,
    )
      ? raw.experience
          .filter(
            (item: any) =>
              item &&
              typeof item === "object",
          )
          .map(
            (item: any) => ({
              company:
                safeString(
                  item.company,
                ),

              role:
                safeString(
                  item.role,
                ),

              duration:
                safeString(
                  item.duration,
                ),

              bullets:
                safeStringArray(
                  item.bullets,
                ),
            }),
          )
      : []

  const projects =
    Array.isArray(
      raw.projects,
    )
      ? raw.projects
          .filter(
            (item: any) =>
              item &&
              typeof item === "object",
          )
          .map(
            (item: any) => ({
              name:
                safeString(
                  item.name,
                ),

              technologies:
                safeStringArray(
                  item.technologies,
                ),

              bullets:
                safeStringArray(
                  item.bullets,
                ),
            }),
          )
      : []

  const education =
    Array.isArray(
      raw.education,
    )
      ? raw.education
          .filter(
            (item: any) =>
              item &&
              typeof item === "object",
          )
          .map(
            (item: any) => ({
              degree:
                safeString(
                  item.degree,
                ),

              institution:
                safeString(
                  item.institution,
                ),

              duration:
                safeString(
                  item.duration,
                ),
            }),
          )
      : []

  return {
    estimated_ats_score:
      clampScore(
        raw.estimated_ats_score ??
        raw.ats_score ??
        0,
      ),

    target_role:
      safeString(
        raw.target_role,
      ),

    professional_summary:
      safeString(
        raw.professional_summary ??
        raw.summary,
      ),

    skills:
      safeStringArray(
        raw.skills,
      ),

    experience,

    projects,

    education,

    certifications:
      safeStringArray(
        raw.certifications,
      ),

    keywords:
      safeStringArray(
        raw.keywords,
      ),

    improvements:
      safeStringArray(
        raw.improvements,
      ),

    missing_keywords:
      safeStringArray(
        raw.missing_keywords,
      ),
  }
}


// ============================================================
// COMPONENT
// ============================================================

function Resume() {

  // ----------------------------------------------------------
  // Resume
  // ----------------------------------------------------------

  const [resume, setResume] =
    useState<ResumeData | null>(
      null,
    )


  // ----------------------------------------------------------
  // Analysis
  // ----------------------------------------------------------

  const [analysis, setAnalysis] =
    useState<ResumeAnalysis | null>(
      null,
    )


  // ----------------------------------------------------------
  // Optimized Resume
  // ----------------------------------------------------------

  const [
    optimizedResume,
    setOptimizedResume,
  ] =
    useState<OptimizedResume | null>(
      null,
    )


  // ----------------------------------------------------------
  // Target role
  // ----------------------------------------------------------

  const [
    targetRole,
    setTargetRole,
  ] =
    useState(
      "Machine Learning Engineer",
    )


  // ----------------------------------------------------------
  // Loading
  // ----------------------------------------------------------

  const [
    loading,
    setLoading,
  ] =
    useState(false)

  const [
    analyzing,
    setAnalyzing,
  ] =
    useState(false)

  const [
    generating,
    setGenerating,
  ] =
    useState(false)

  const [
    deleting,
    setDeleting,
  ] =
    useState(false)


  // ----------------------------------------------------------
  // Error / Success
  // ----------------------------------------------------------

  const [
    error,
    setError,
  ] =
    useState("")

  const [
    success,
    setSuccess,
  ] =
    useState("")


  // ==========================================================
  // LOAD RESUME
  // ==========================================================

  useEffect(() => {
    loadResume()
  }, [])


  async function loadResume() {

    try {

      setLoading(true)
      setError("")

      const data =
        await getResume()

      setResume(data)

    } catch (err) {

      const message =
        err instanceof Error
          ? err.message
          : "Failed to load resume"

      if (
        !message
          .toLowerCase()
          .includes(
            "resume not found",
          )
      ) {
        setError(message)
      }

    } finally {

      setLoading(false)

    }
  }


  // ==========================================================
  // UPLOAD
  // ==========================================================

  async function handleUpload(
    event: ChangeEvent<HTMLInputElement>,
  ) {

    const file =
      event.target.files?.[0]

    if (!file) {
      return
    }

    const extension =
      file.name
        .split(".")
        .pop()
        ?.toLowerCase()

    if (
      extension !== "pdf" &&
      extension !== "docx"
    ) {

      setError(
        "Only PDF and DOCX files are allowed.",
      )

      event.target.value = ""

      return
    }

    try {

      setLoading(true)
      setError("")
      setSuccess("")

      const data =
        await uploadResume(
          file,
        )

      setResume(
        data.resume,
      )

      setAnalysis(null)

      setOptimizedResume(null)

      setSuccess(
        "Resume uploaded successfully.",
      )

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Resume upload failed",
      )

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

      setError(
        "Please upload a resume first.",
      )

      return
    }

    try {

      setAnalyzing(true)
      setError("")
      setSuccess("")

      const data =
        await analyzeResume()

      console.log(
        "ANALYSIS API RESPONSE:",
        data,
      )

      if (
        !data ||
        typeof data !== "object"
      ) {
        throw new Error(
          "Backend returned an invalid response.",
        )
      }

      if (
        !data.analysis ||
        typeof data.analysis !== "object"
      ) {
        throw new Error(
          "AI returned an empty or invalid analysis.",
        )
      }

      const normalizedAnalysis =
        normalizeAnalysis(
          data.analysis,
        )

      setAnalysis(
        normalizedAnalysis,
      )

      setSuccess(
        "Resume analysis completed successfully.",
      )

    } catch (err) {

      console.error(
        "Resume analysis error:",
        err,
      )

      setError(
        err instanceof Error
          ? err.message
          : "Resume analysis failed",
      )

    } finally {

      setAnalyzing(false)

    }
  }


  // ==========================================================
  // GENERATE ATS RESUME
  // ==========================================================

  async function handleGenerateATSResume() {

    if (!resume) {

      setError(
        "Please upload a resume first.",
      )

      return
    }

    if (!targetRole.trim()) {

      setError(
        "Please enter a target job role.",
      )

      return
    }

    try {

      setGenerating(true)
      setError("")
      setSuccess("")

      const data =
        await generateATSResume(
          targetRole.trim(),
        )

      console.log(
        "ATS RESUME API RESPONSE:",
        data,
      )

      if (
        !data ||
        typeof data !== "object"
      ) {
        throw new Error(
          "Backend returned an invalid response.",
        )
      }

      if (
        !data.optimized_resume ||
        typeof data.optimized_resume !==
          "object"
      ) {
        throw new Error(
          "AI returned an invalid optimized resume.",
        )
      }

      const normalizedResume =
        normalizeOptimizedResume(
          data.optimized_resume,
        )

      setOptimizedResume(
        normalizedResume,
      )

      setSuccess(
        "ATS-optimized resume generated successfully.",
      )

    } catch (err) {

      console.error(
        "ATS resume generation error:",
        err,
      )

      setError(
        err instanceof Error
          ? err.message
          : "Failed to generate ATS resume",
      )

    } finally {

      setGenerating(false)

    }
  }


  // ==========================================================
  // DELETE
  // ==========================================================

  async function handleDelete() {

    if (!resume) {
      return
    }

    const confirmed =
      window.confirm(
        "Are you sure you want to delete your resume?",
      )

    if (!confirmed) {
      return
    }

    try {

      setDeleting(true)
      setError("")
      setSuccess("")

      await deleteResume()

      setResume(null)
      setAnalysis(null)
      setOptimizedResume(null)

      setSuccess(
        "Resume deleted successfully.",
      )

    } catch (err) {

      setError(
        err instanceof Error
          ? err.message
          : "Failed to delete resume",
      )

    } finally {

      setDeleting(false)

    }
  }


  // ==========================================================
  // LOADING
  // ==========================================================

  if (loading) {

    return (
      <div style={styles.page}>
        <div style={styles.loading}>
          Loading resume...
        </div>
      </div>
    )
  }


  // ==========================================================
  // UI
  // ==========================================================

  return (

    <div style={styles.page}>

      <div style={styles.container}>

        {/* ================================================= */}
        {/* HEADER */}
        {/* ================================================= */}

        <div style={styles.header}>

          <div>

            <h1 style={styles.title}>
              Resume Analyzer
            </h1>

            <p style={styles.subtitle}>
              Analyze your resume and create
              an ATS-optimized version.
            </p>

          </div>

        </div>


        {/* ================================================= */}
        {/* MESSAGES */}
        {/* ================================================= */}

        {error && (

          <div style={styles.error}>
            ⚠ {error}
          </div>

        )}

        {success && (

          <div style={styles.success}>
            ✓ {success}
          </div>

        )}


        {/* ================================================= */}
        {/* UPLOAD */}
        {/* ================================================= */}

        <section style={styles.card}>

          <h2 style={styles.sectionTitle}>
            Resume
          </h2>

          {!resume ? (

            <div style={styles.uploadBox}>

              <div style={styles.uploadIcon}>
                ↑
              </div>

              <h3>
                Upload your resume
              </h3>

              <p style={styles.muted}>
                PDF or DOCX
              </p>

              <label
                htmlFor="resume-upload"
                style={styles.primaryButton}
              >
                Choose Resume
              </label>

              <input
                id="resume-upload"
                type="file"
                accept=".pdf,.docx"
                onChange={
                  handleUpload
                }
                style={{
                  display: "none",
                }}
              />

            </div>

          ) : (

            <div style={styles.resumeRow}>

              <div>

                <div
                  style={
                    styles.filename
                  }
                >
                  {resume.filename}
                </div>

                <div
                  style={
                    styles.muted
                  }
                >
                  Uploaded{" "}
                  {new Date(
                    resume.uploaded_at,
                  ).toLocaleDateString()}
                </div>

              </div>

              <div
                style={
                  styles.buttonGroup
                }
              >

                <label
                  htmlFor="replace-resume"
                  style={
                    styles.secondaryButton
                  }
                >
                  Replace
                </label>

                <input
                  id="replace-resume"
                  type="file"
                  accept=".pdf,.docx"
                  onChange={
                    handleUpload
                  }
                  style={{
                    display: "none",
                  }}
                />

                <button
                  onClick={
                    handleDelete
                  }
                  disabled={deleting}
                  style={
                    styles.dangerButton
                  }
                >
                  {deleting
                    ? "Deleting..."
                    : "Delete"}
                </button>

              </div>

            </div>

          )}

        </section>


        {/* ================================================= */}
        {/* ACTIONS */}
        {/* ================================================= */}

        {resume && (

          <section style={styles.card}>

            <h2 style={styles.sectionTitle}>
              AI Resume Tools
            </h2>


            {/* ANALYZE */}

            <div style={styles.tool}>

              <div>

                <h3>
                  Resume Analysis
                </h3>

                <p style={styles.muted}>
                  Check ATS score, skills,
                  strengths, weaknesses and
                  suitable roles.
                </p>

              </div>

              <button
                onClick={
                  handleAnalyze
                }
                disabled={analyzing}
                style={
                  styles.primaryButton
                }
              >
                {analyzing
                  ? "Analyzing..."
                  : "Analyze Resume"}
              </button>

            </div>


            {/* ATS GENERATOR */}

            <div style={styles.tool}>

              <div
                style={
                  styles.toolContent
                }
              >

                <h3>
                  AI ATS Resume Builder
                </h3>

                <p style={styles.muted}>
                  Rebuild your existing resume
                  for your target role using
                  ATS-friendly structure and
                  keywords.
                </p>

                <input
                  type="text"
                  value={targetRole}
                  onChange={(event) =>
                    setTargetRole(
                      event.target.value,
                    )
                  }
                  placeholder="Target job role"
                  style={
                    styles.input
                  }
                />

              </div>

              <button
                onClick={
                  handleGenerateATSResume
                }
                disabled={generating}
                style={
                  styles.primaryButton
                }
              >
                {generating
                  ? "Generating..."
                  : "Create ATS Resume"}
              </button>

            </div>

          </section>

        )}


        {/* ================================================= */}
        {/* ANALYSIS RESULT */}
        {/* ================================================= */}

        {analysis && (

          <section style={styles.card}>

            <h2 style={styles.sectionTitle}>
              Analysis Complete
            </h2>


            {/* ATS SCORE */}

            <div style={styles.scoreBox}>

              <div>

                <div style={styles.scoreLabel}>
                  ATS SCORE
                </div>

                <div style={styles.score}>
                  {Math.round(
                    analysis.ats_score,
                  )}

                  <span
                    style={
                      styles.scoreMax
                    }
                  >
                    /100
                  </span>

                </div>

              </div>

              <div
                style={
                  styles.scoreMessage
                }
              >

                {analysis.ats_score >= 90
                  ? "Excellent ATS compatibility"
                  : analysis.ats_score >= 75
                    ? "Good ATS compatibility"
                    : "Needs improvement"}

              </div>

            </div>


            {/* SUMMARY */}

            {analysis.summary && (

              <div
                style={
                  styles.resultBlock
                }
              >

                <h3>
                  Professional Summary
                </h3>

                <p>
                  {analysis.summary}
                </p>

              </div>

            )}


            {/* SKILLS */}

            <div
              style={
                styles.resultBlock
              }
            >

              <h3>
                Skills Detected
              </h3>

              {analysis.skills.length >
              0 ? (

                <div style={styles.tags}>

                  {analysis.skills.map(
                    (skill, index) => (

                      <span
                        key={index}
                        style={styles.tag}
                      >
                        {skill}
                      </span>

                    ),
                  )}

                </div>

              ) : (

                <p style={styles.muted}>
                  No skills detected.
                </p>

              )}

            </div>


            {/* STRENGTHS */}

            <div
              style={
                styles.resultBlock
              }
            >

              <h3>
                Strengths
              </h3>

              {analysis.strengths.length >
              0 ? (

                <ul>

                  {analysis.strengths.map(
                    (item, index) => (

                      <li key={index}>
                        {item}
                      </li>

                    ),
                  )}

                </ul>

              ) : (

                <p style={styles.muted}>
                  No strengths returned.
                </p>

              )}

            </div>


            {/* WEAKNESSES */}

            <div
              style={
                styles.resultBlock
              }
            >

              <h3>
                Weaknesses
              </h3>

              {analysis.weaknesses.length >
              0 ? (

                <ul>

                  {analysis.weaknesses.map(
                    (item, index) => (

                      <li key={index}>
                        {item}
                      </li>

                    ),
                  )}

                </ul>

              ) : (

                <p style={styles.muted}>
                  No weaknesses returned.
                </p>

              )}

            </div>


            {/* SUGGESTIONS */}

            <div
              style={
                styles.resultBlock
              }
            >

              <h3>
                AI Improvement Suggestions
              </h3>

              {analysis
                .improvement_suggestions
                .length > 0 ? (

                <ol>

                  {analysis
                    .improvement_suggestions
                    .map(
                      (item, index) => (

                        <li key={index}>
                          {item}
                        </li>

                      ),
                    )}

                </ol>

              ) : (

                <p style={styles.muted}>
                  No improvement suggestions returned.
                </p>

              )}

            </div>


            {/* ROLE MATCHING */}

            <div
              style={
                styles.resultBlock
              }
            >

              <h3>
                Role Matching
              </h3>

              {analysis.role_matching
                .length > 0 ? (

                <div
                  style={
                    styles.roleGrid
                  }
                >

                  {analysis.role_matching.map(
                    (role, index) => (

                      <div
                        key={index}
                        style={
                          styles.roleCard
                        }
                      >

                        <div
                          style={
                            styles.roleHeader
                          }
                        >

                          <strong>
                            {role.role}
                          </strong>

                          <strong>
                            {Math.round(
                              role.match_percentage,
                            )}
                            %
                          </strong>

                        </div>

                        {role.reason && (

                          <p
                            style={
                              styles.muted
                            }
                          >
                            {role.reason}
                          </p>

                        )}

                      </div>

                    ),
                  )}

                </div>

              ) : (

                <p style={styles.muted}>
                  No role matching data returned.
                </p>

              )}

            </div>

          </section>

        )}


        {/* ================================================= */}
        {/* OPTIMIZED RESUME */}
        {/* ================================================= */}

        {optimizedResume && (

          <section style={styles.card}>

            <div
              style={
                styles.optimizedHeader
              }
            >

              <div>

                <h2
                  style={
                    styles.sectionTitle
                  }
                >
                  ATS Resume Generated
                </h2>

                <p style={styles.muted}>
                  Target Role:{" "}
                  <strong>
                    {
                      optimizedResume.target_role
                    }
                  </strong>
                </p>

              </div>

              <div
                style={
                  styles.optimizedScore
                }
              >

                <span>
                  Estimated ATS
                </span>

                <strong>
                  {Math.round(
                    optimizedResume.estimated_ats_score,
                  )}
                  /100
                </strong>

              </div>

            </div>


            {/* SUMMARY */}

            {optimizedResume
              .professional_summary && (

              <div
                style={
                  styles.resultBlock
                }
              >

                <h3>
                  Professional Summary
                </h3>

                <p>
                  {
                    optimizedResume.professional_summary
                  }
                </p>

              </div>

            )}


            {/* SKILLS */}

            <div
              style={
                styles.resultBlock
              }
            >

              <h3>
                Technical Skills
              </h3>

              {optimizedResume.skills
                .length > 0 ? (

                <div style={styles.tags}>

                  {optimizedResume.skills.map(
                    (skill, index) => (

                      <span
                        key={index}
                        style={styles.tag}
                      >
                        {skill}
                      </span>

                    ),
                  )}

                </div>

              ) : (

                <p style={styles.muted}>
                  No skills returned.
                </p>

              )}

            </div>


            {/* EXPERIENCE */}

            {optimizedResume.experience.length >
              0 && (

              <div
                style={
                  styles.resultBlock
                }
              >

                <h3>
                  Experience
                </h3>

                {optimizedResume.experience.map(
                  (item, index) => (

                    <div
                      key={index}
                      style={
                        styles.experienceItem
                      }
                    >

                      <div
                        style={
                          styles.roleHeader
                        }
                      >

                        <strong>
                          {item.role}
                        </strong>

                        <span>
                          {item.duration}
                        </span>

                      </div>

                      {item.company && (

                        <div
                          style={
                            styles.muted
                          }
                        >
                          {item.company}
                        </div>

                      )}

                      {item.bullets.length >
                        0 && (

                        <ul>

                          {item.bullets.map(
                            (
                              bullet,
                              bulletIndex,
                            ) => (

                              <li
                                key={
                                  bulletIndex
                                }
                              >
                                {bullet}
                              </li>

                            ),
                          )}

                        </ul>

                      )}

                    </div>

                  ),
                )}

              </div>

            )}


            {/* PROJECTS */}

            {optimizedResume.projects.length >
              0 && (

              <div
                style={
                  styles.resultBlock
                }
              >

                <h3>
                  Projects
                </h3>

                {optimizedResume.projects.map(
                  (project, index) => (

                    <div
                      key={index}
                      style={
                        styles.experienceItem
                      }
                    >

                      <strong>
                        {project.name}
                      </strong>

                      {project.technologies.length >
                        0 && (

                        <div
                          style={
                            styles.tags
                          }
                        >

                          {project.technologies.map(
                            (
                              technology,
                              technologyIndex,
                            ) => (

                              <span
                                key={
                                  technologyIndex
                                }
                                style={
                                  styles.tag
                                }
                              >
                                {technology}
                              </span>

                            ),
                          )}

                        </div>

                      )}

                      {project.bullets.length >
                        0 && (

                        <ul>

                          {project.bullets.map(
                            (
                              bullet,
                              bulletIndex,
                            ) => (

                              <li
                                key={
                                  bulletIndex
                                }
                              >
                                {bullet}
                              </li>

                            ),
                          )}

                        </ul>

                      )}

                    </div>

                  ),
                )}

              </div>

            )}


            {/* EDUCATION */}

            {optimizedResume.education.length >
              0 && (

              <div
                style={
                  styles.resultBlock
                }
              >

                <h3>
                  Education
                </h3>

                {optimizedResume.education.map(
                  (
                    education,
                    index,
                  ) => (

                    <div
                      key={index}
                      style={
                        styles.experienceItem
                      }
                    >

                      <strong>
                        {education.degree}
                      </strong>

                      {education.institution && (

                        <div>
                          {
                            education.institution
                          }
                        </div>

                      )}

                      {education.duration && (

                        <div
                          style={
                            styles.muted
                          }
                        >
                          {
                            education.duration
                          }
                        </div>

                      )}

                    </div>

                  ),
                )}

              </div>

            )}


            {/* CERTIFICATIONS */}

            {optimizedResume.certifications.length >
              0 && (

              <div
                style={
                  styles.resultBlock
                }
              >

                <h3>
                  Certifications
                </h3>

                <ul>

                  {optimizedResume.certifications.map(
                    (
                      certification,
                      index,
                    ) => (

                      <li key={index}>
                        {certification}
                      </li>

                    ),
                  )}

                </ul>

              </div>

            )}


            {/* KEYWORDS */}

            {optimizedResume.keywords.length >
              0 && (

              <div
                style={
                  styles.resultBlock
                }
              >

                <h3>
                  ATS Keywords
                </h3>

                <div
                  style={
                    styles.tags
                  }
                >

                  {optimizedResume.keywords.map(
                    (
                      keyword,
                      index,
                    ) => (

                      <span
                        key={index}
                        style={styles.tag}
                      >
                        {keyword}
                      </span>

                    ),
                  )}

                </div>

              </div>

            )}


            {/* IMPROVEMENTS */}

            {optimizedResume.improvements.length >
              0 && (

              <div
                style={
                  styles.resultBlock
                }
              >

                <h3>
                  Improvements Made
                </h3>

                <ul>

                  {optimizedResume.improvements.map(
                    (
                      item,
                      index,
                    ) => (

                      <li key={index}>
                        {item}
                      </li>

                    ),
                  )}

                </ul>

              </div>

            )}


            {/* MISSING KEYWORDS */}

            {optimizedResume.missing_keywords.length >
              0 && (

              <div
                style={
                  styles.resultBlock
                }
              >

                <h3>
                  Missing Keywords
                </h3>

                <div
                  style={
                    styles.tags
                  }
                >

                  {optimizedResume.missing_keywords.map(
                    (
                      keyword,
                      index,
                    ) => (

                      <span
                        key={index}
                        style={
                          styles.warningTag
                        }
                      >
                        {keyword}
                      </span>

                    ),
                  )}

                </div>

              </div>

            )}

          </section>

        )}

      </div>

    </div>
  )
}


export default Resume


// ============================================================
// STYLES
// ============================================================

const styles: Record<
  string,
  React.CSSProperties
> = {

  page: {
    minHeight: "100vh",
    background: "#030712",
    color: "#f9fafb",
    padding: "40px 20px",
  },

  container: {
    maxWidth: "1100px",
    margin: "0 auto",
  },

  header: {
    marginBottom: "30px",
  },

  title: {
    fontSize: "36px",
    marginBottom: "8px",
  },

  subtitle: {
    color: "#9ca3af",
    fontSize: "16px",
  },

  card: {
    background: "#111827",
    border: "1px solid #1f2937",
    borderRadius: "16px",
    padding: "28px",
    marginBottom: "24px",
  },

  sectionTitle: {
    fontSize: "24px",
    marginTop: 0,
    marginBottom: "20px",
  },

  uploadBox: {
    border: "1px dashed #374151",
    borderRadius: "14px",
    padding: "50px 20px",
    textAlign: "center",
  },

  uploadIcon: {
    fontSize: "40px",
    marginBottom: "10px",
  },

  resumeRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "20px",
    flexWrap: "wrap",
  },

  filename: {
    fontSize: "18px",
    fontWeight: 600,
    marginBottom: "6px",
  },

  muted: {
    color: "#9ca3af",
    lineHeight: 1.6,
  },

  buttonGroup: {
    display: "flex",
    gap: "10px",
    alignItems: "center",
  },

  primaryButton: {
    display: "inline-block",
    border: "none",
    borderRadius: "9px",
    padding: "12px 20px",
    background: "#6366f1",
    color: "#ffffff",
    fontWeight: 600,
    cursor: "pointer",
    textDecoration: "none",
  },

  secondaryButton: {
    display: "inline-block",
    border: "1px solid #374151",
    borderRadius: "9px",
    padding: "11px 18px",
    background: "#1f2937",
    color: "#ffffff",
    fontWeight: 600,
    cursor: "pointer",
  },

  dangerButton: {
    border: "1px solid #7f1d1d",
    borderRadius: "9px",
    padding: "11px 18px",
    background: "#450a0a",
    color: "#fecaca",
    fontWeight: 600,
    cursor: "pointer",
  },

  tool: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "30px",
    padding: "22px 0",
    borderBottom: "1px solid #1f2937",
  },

  toolContent: {
    flex: 1,
  },

  input: {
    width: "100%",
    maxWidth: "500px",
    boxSizing: "border-box",
    marginTop: "12px",
    padding: "12px 14px",
    borderRadius: "9px",
    border: "1px solid #374151",
    background: "#030712",
    color: "#ffffff",
    fontSize: "15px",
    outline: "none",
  },

  error: {
    background: "#450a0a",
    border: "1px solid #7f1d1d",
    color: "#fecaca",
    padding: "14px 18px",
    borderRadius: "10px",
    marginBottom: "20px",
  },

  success: {
    background: "#052e16",
    border: "1px solid #166534",
    color: "#bbf7d0",
    padding: "14px 18px",
    borderRadius: "10px",
    marginBottom: "20px",
  },

  loading: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "#030712",
    color: "#ffffff",
    fontSize: "18px",
  },

  scoreBox: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "20px",
    padding: "24px",
    background: "#030712",
    borderRadius: "14px",
    marginBottom: "25px",
  },

  scoreLabel: {
    color: "#9ca3af",
    fontSize: "13px",
    fontWeight: 700,
    letterSpacing: "1px",
  },

  score: {
    fontSize: "52px",
    fontWeight: 800,
    marginTop: "5px",
  },

  scoreMax: {
    fontSize: "20px",
    color: "#9ca3af",
    marginLeft: "5px",
  },

  scoreMessage: {
    color: "#a5b4fc",
    fontWeight: 600,
  },

  resultBlock: {
    marginTop: "28px",
  },

  tags: {
    display: "flex",
    flexWrap: "wrap",
    gap: "8px",
    marginTop: "12px",
  },

  tag: {
    background: "#1e293b",
    border: "1px solid #334155",
    color: "#cbd5e1",
    padding: "6px 10px",
    borderRadius: "999px",
    fontSize: "13px",
  },

  warningTag: {
    background: "#422006",
    border: "1px solid #92400e",
    color: "#fde68a",
    padding: "6px 10px",
    borderRadius: "999px",
    fontSize: "13px",
  },

  roleGrid: {
    display: "grid",
    gridTemplateColumns:
      "repeat(auto-fit, minmax(250px, 1fr))",
    gap: "15px",
    marginTop: "15px",
  },

  roleCard: {
    background: "#030712",
    border: "1px solid #1f2937",
    borderRadius: "12px",
    padding: "18px",
  },

  roleHeader: {
    display: "flex",
    justifyContent: "space-between",
    gap: "15px",
    marginBottom: "8px",
  },

  optimizedHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "20px",
    flexWrap: "wrap",
  },

  optimizedScore: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    background: "#030712",
    padding: "15px 22px",
    borderRadius: "12px",
  },

  experienceItem: {
    padding: "18px 0",
    borderBottom: "1px solid #1f2937",
  },
}