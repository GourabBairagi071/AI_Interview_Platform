const API_BASE_URL = "http://127.0.0.1:8000/api/v1"

// ============================================================
// TYPES
// ============================================================

export type Interview = {
  id: string
  user_id: string
  job_role: string
  difficulty: string
  status: string
  questions: string | null
  answers: string | null
  transcript: string | null
  score: number | null
  feedback: string | null
  strengths: string | null
  weaknesses: string | null
  question_evaluations: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export type User = {
  id: string
  email: string
  full_name: string
  is_active?: boolean
  is_verified?: boolean
}

export type Resume = {
  id: string
  user_id: string
  filename: string
  file_url: string
  uploaded_at: string
  updated_at: string
}

// ============================================================
// GENERIC API REQUEST
// ============================================================

export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem("access_token")

  const headers = new Headers(options.headers)

  headers.set("Accept", "application/json")

  // Do NOT manually set Content-Type for FormData.
  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set(
      "Content-Type",
      "application/json",
    )
  }

  if (token) {
    headers.set(
      "Authorization",
      `Bearer ${token}`,
    )
  }

  const response = await fetch(
    `${API_BASE_URL}${endpoint}`,
    {
      ...options,
      headers,
    },
  )

  const data = await response
    .json()
    .catch(() => null)

  // ----------------------------------------------------------
  // UNAUTHORIZED
  // ----------------------------------------------------------

  if (response.status === 401) {
    localStorage.removeItem("access_token")

    window.location.href = "/login"

    throw new Error(
      "Session expired. Please login again.",
    )
  }

  // ----------------------------------------------------------
  // OTHER ERRORS
  // ----------------------------------------------------------

  if (!response.ok) {
    throw new Error(
      data?.detail ||
        data?.message ||
        `Request failed with status ${response.status}`,
    )
  }

  return data as T
}

// ============================================================
// AUTH
// ============================================================

export async function getCurrentUser(): Promise<User> {
  return apiRequest<User>(
    "/auth/me",
  )
}

// ============================================================
// INTERVIEW
// ============================================================

export async function getInterviews(): Promise<{
  interviews: Interview[]
}> {
  return apiRequest<{
    interviews: Interview[]
  }>("/interview")
}

// ------------------------------------------------------------
// CREATE INTERVIEW
// ------------------------------------------------------------

export async function createInterview(
  jobRole: string,
  difficulty: string,
): Promise<{
  message: string
  interview: Interview
}> {
  return apiRequest<{
    message: string
    interview: Interview
  }>(
    "/interview",
    {
      method: "POST",
      body: JSON.stringify({
        job_role: jobRole,
        difficulty,
      }),
    },
  )
}

// ------------------------------------------------------------
// GET SINGLE INTERVIEW
// ------------------------------------------------------------

export async function getInterview(
  interviewId: string,
): Promise<Interview> {
  return apiRequest<Interview>(
    `/interview/${interviewId}`,
  )
}

// ------------------------------------------------------------
// START INTERVIEW
// ------------------------------------------------------------

export async function startInterview(
  interviewId: string,
): Promise<{
  message: string
  interview: Interview
}> {
  return apiRequest<{
    message: string
    interview: Interview
  }>(
    `/interview/${interviewId}/start`,
    {
      method: "POST",
    },
  )
}

// ------------------------------------------------------------
// SUBMIT ANSWERS
// ------------------------------------------------------------

export async function submitAnswers(
  interviewId: string,
  answers: string,
): Promise<{
  message: string
  interview: Interview
}> {
  return apiRequest<{
    message: string
    interview: Interview
  }>(
    `/interview/${interviewId}/answers`,
    {
      method: "POST",
      body: JSON.stringify({
        answers,
      }),
    },
  )
}

// ------------------------------------------------------------
// COMPLETE INTERVIEW
// ------------------------------------------------------------

export async function completeInterview(
  interviewId: string,
): Promise<{
  message: string
  interview: Interview
}> {
  return apiRequest<{
    message: string
    interview: Interview
  }>(
    `/interview/${interviewId}/complete`,
    {
      method: "POST",
    },
  )
}

// ============================================================
// RESUME
// ============================================================

// ------------------------------------------------------------
// GET RESUME
// ------------------------------------------------------------

export async function getResume(): Promise<{
  id: string
  user_id: string
  filename: string
  file_url: string
  uploaded_at: string
  updated_at: string
}> {
  return apiRequest(
    "/resume",
  )
}

// ------------------------------------------------------------
// UPLOAD RESUME
// ------------------------------------------------------------

export async function uploadResume(
  file: File,
) {
  const formData = new FormData()

  formData.append(
    "file",
    file,
  )

  return apiRequest(
    "/resume",
    {
      method: "POST",
      body: formData,
    },
  )
}

// ------------------------------------------------------------
// ANALYZE RESUME
// ------------------------------------------------------------

export async function analyzeResume() {
  return apiRequest(
    "/resume/analyze",
    {
      method: "POST",
    },
  )
}

// ------------------------------------------------------------
// GENERATE ATS RESUME
// ------------------------------------------------------------

export async function generateATSResume(
  targetRole: string,
) {
  return apiRequest(
    "/resume/optimize",
    {
      method: "POST",
      body: JSON.stringify({
        target_role: targetRole.trim(),
      }),
    },
  )
}

// ------------------------------------------------------------
// DELETE RESUME
// ------------------------------------------------------------

export async function deleteResume() {
  return apiRequest(
    "/resume",
    {
      method: "DELETE",
    },
  )
}

// ============================================================
// HELPERS
// ============================================================

export function getInterviewStatus(
  interview: Interview,
): string {
  return (
    interview.status?.toLowerCase() ||
    "unknown"
  )
}

export function isInterviewCompleted(
  interview: Interview,
): boolean {
  return (
    getInterviewStatus(interview) ===
    "completed"
  )
}

export function isInterviewStarted(
  interview: Interview,
): boolean {
  return (
    getInterviewStatus(interview) ===
    "started"
  )
}

export function isInterviewCreated(
  interview: Interview,
): boolean {
  return (
    getInterviewStatus(interview) ===
    "created"
  )
}

// ============================================================
// FIND ACTIVE INTERVIEW
// ============================================================

export function findActiveInterview(
  interviews: Interview[],
): Interview | null {
  return (
    interviews.find(
      (interview) =>
        getInterviewStatus(interview) ===
          "started",
    ) ||
    interviews.find(
      (interview) =>
        getInterviewStatus(interview) ===
          "created",
    ) ||
    null
  )
}

// ============================================================
// FIND LATEST INTERVIEW
// ============================================================

export function findLatestInterview(
  interviews: Interview[],
): Interview | null {
  if (!interviews.length) {
    return null
  }

  return [...interviews].sort(
    (a, b) =>
      new Date(b.created_at).getTime() -
      new Date(a.created_at).getTime(),
  )[0]
}

// ============================================================
// FIND UPCOMING / ACTIVE INTERVIEW
// ============================================================

export function findUpcomingInterview(
  interviews: Interview[],
): Interview | null {
  const active = findActiveInterview(
    interviews,
  )

  if (active) {
    return active
  }

  return findLatestInterview(
    interviews.filter(
      (interview) =>
        !isInterviewCompleted(interview),
    ),
  )
}