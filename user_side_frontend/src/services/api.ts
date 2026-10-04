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

export type Profile = {
  id?: string
  user_id?: string
  phone?: string | null
  bio?: string | null
  skills?: string | null
  experience_years?: number | null
  education?: string | null
  resume_url?: string | null
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

export async function getUserProfile(): Promise<Profile> {
  return apiRequest<Profile>("/auth/profile")
}

export async function updateUserProfile(
  data: Partial<Profile>,
): Promise<Profile> {
  return apiRequest<Profile>("/auth/profile", {
    method: "PUT",
    body: JSON.stringify(data),
  })
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

export interface CreateInterviewOptions {
  experienceLevel?: string
  interviewType?: string
  numberOfQuestions?: number
}

export async function createInterview(
  jobRole: string,
  difficulty: string,
  options?: CreateInterviewOptions,
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
        experience_level: options?.experienceLevel || "Mid-Level",
        interview_type: options?.interviewType || "Technical",
        number_of_questions: options?.numberOfQuestions || 5,
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

// ------------------------------------------------------------
// GENERATE FOLLOW-UP QUESTION
// ------------------------------------------------------------

export interface FollowupResponse {
  should_follow_up: boolean
  question: string
  reason: string
  difficulty: string
}

export async function generateFollowup(
  interviewId: string,
  question: string,
  answer: string,
  conversationHistory: Array<{ role: string; content: string }> = [],
): Promise<FollowupResponse> {
  return apiRequest<FollowupResponse>(
    `/interview/${interviewId}/followup`,
    {
      method: "POST",
      body: JSON.stringify({
        question,
        answer,
        conversation_history: conversationHistory,
      }),
    },
  )
}

// ------------------------------------------------------------
// INTERVIEW TRANSCRIPT (PHASE 5)
// ------------------------------------------------------------

export interface TranscriptEntry {
  question: string
  candidate_answer: string
  timestamp?: string | null
  question_index: number
  question_type?: string
  is_followup?: boolean
  evaluation?: Record<string, any> | null
}

export interface TranscriptResponse {
  interview_id: string
  entries: TranscriptEntry[]
  total_entries: number
}

export async function getInterviewTranscript(
  interviewId: string,
): Promise<TranscriptResponse> {
  return apiRequest<TranscriptResponse>(`/interview/${interviewId}/transcript`)
}

export async function syncInterviewTranscript(
  interviewId: string,
  entries: TranscriptEntry[],
): Promise<TranscriptResponse> {
  return apiRequest<TranscriptResponse>(
    `/interview/${interviewId}/transcript`,
    {
      method: "POST",
      body: JSON.stringify({
        entries,
      }),
    },
  )
}

// ============================================================
// RESUME
// ============================================================

// ------------------------------------------------------------
// GET RESUME
// ------------------------------------------------------------

export interface AnalysisData {
  ats_score: number | string
  skills: string[]
  strengths: string[]
  weaknesses: string[]
  improvement_suggestions: string[]
  role_matching: Array<{
    role: string
    match_percentage?: number
    match?: number
    reason: string
  }>
  summary?: string
}

export interface ResumeAnalysisResponse {
  message: string
  resume: Resume
  analysis: AnalysisData
}

export interface ResumeWithAnalysis extends Resume {
  analysis?: AnalysisData | null
}

export async function getResume(): Promise<ResumeWithAnalysis> {
  return apiRequest<ResumeWithAnalysis>("/resume")
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

export async function analyzeResume(): Promise<ResumeAnalysisResponse> {
  return apiRequest<ResumeAnalysisResponse>(
    "/resume/analyze",
    {
      method: "POST",
    },
  )
}

// ------------------------------------------------------------
// GENERATE ATS RESUME
// ------------------------------------------------------------

export interface OptimizeResumeResponse {
  message: string
  resume: Resume
  optimized_resume: any
  pdf_url?: string
  pdf_base64?: string
}

export async function generateATSResume(
  targetRole: string,
): Promise<OptimizeResumeResponse> {
  return apiRequest<OptimizeResumeResponse>(
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
// DOWNLOAD OPTIMIZED RESUME PDF
// ------------------------------------------------------------

export async function downloadOptimizedResumePDFBlob(): Promise<Blob> {
  const token = localStorage.getItem("access_token")
  const headers = new Headers()

  if (token) {
    headers.set("Authorization", `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE_URL}/resume/optimized-pdf`, {
    headers,
  })

  if (!response.ok) {
    const data = await response.json().catch(() => null)
    throw new Error(
      data?.detail ||
        data?.message ||
        `Failed to download PDF (status ${response.status})`,
    )
  }

  return response.blob()
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

// ============================================================
// ANALYTICS TYPES & API
// ============================================================

export interface OverallPerformance {
  overall_score: number | null
  best_score: number | null
  recent_score: number | null
  total_interviews: number
  completed_interviews: number
  total_questions_answered: number
  score_change: number | null
  score_change_direction: "up" | "down" | "neutral" | null
}

export interface ScoreHistoryItem {
  interview_id: string
  date: string
  role: string
  score: number
  difficulty: string
}

export interface TopicPerformance {
  topic: string
  average_score: number
  question_count: number
  trend: "improving" | "declining" | "stable" | "insufficient_data"
}

export interface DifficultyPerformance {
  difficulty: string
  average_score: number | null
  question_count: number
}

export interface InterviewHistoryItem {
  interview_id: string
  date: string
  role: string
  score: number | null
  difficulty: string
  status: string
  total_questions: number
  result_route: string
}

export interface AnalyticsOverviewResponse {
  overall: OverallPerformance
  score_history: ScoreHistoryItem[]
  topic_performance: TopicPerformance[]
  difficulty_performance: DifficultyPerformance[]
  strengths: string[]
  weaknesses: string[]
  recommendations: string[]
  interview_history: InterviewHistoryItem[]
}

export async function getAnalyticsOverview(): Promise<AnalyticsOverviewResponse> {
  return apiRequest<AnalyticsOverviewResponse>("/analytics/overview")
}

// ============================================================
// PRACTICE TYPES & API
// ============================================================

export interface TechnologySummary {
  technology: string
  slug: string
  total_questions: number
  solved: number
  remaining: number
  mastery_percentage: number
  xp_earned: number
  topics_count: number
}

export interface TechnologyListResponse {
  technologies: TechnologySummary[]
  total_technologies: number
  total_questions: number
  total_solved: number
}

export interface TopicSummary {
  technology: string
  technology_slug: string
  topic: string
  slug: string
  total_questions: number
  solved: number
  remaining: number
  mastery_percentage: number
}

export interface TopicListResponse {
  technology: string
  technology_slug: string
  topics: TopicSummary[]
  total_topics: number
  total_questions: number
  total_solved: number
}

export interface PracticeQuestionSummary {
  id: string
  question: string
  topic: string
  difficulty: string
  role: string | null
  question_type: string
  technology?: string
  technology_slug?: string
  subtopic?: string
  explanation?: string | null
  solved: boolean
  bookmarked: boolean
  attempts: number
  xp_reward?: number
}

export interface PracticeQuestionListResponse {
  questions: PracticeQuestionSummary[]
  total: number
  page: number
  page_size: number
  topics: string[]
  difficulties: string[]
  question_types: string[]
}

export interface PracticeQuestionDetailResponse {
  id: string
  question: string
  topic: string
  difficulty: string
  role: string | null
  question_type: string
  technology?: string
  technology_slug?: string
  subtopic?: string
  explanation: string
  solved: boolean
  bookmarked: boolean
  attempts: number
  xp_reward?: number
  last_answer: string | null
  last_attempted_at: string | null
  previous_id: string | null
  next_id: string | null
}

export interface SolveQuestionResponse {
  success: boolean
  solved: boolean
  attempts: number
  message: string
  xp_earned?: number
  bonus_xp?: number
  total_xp?: number
  current_level?: number
  level_title?: string
  leveled_up?: boolean
  streak_days?: number
  completed_missions?: string[]
}

export interface BookmarkResponse {
  success: boolean
  bookmarked: boolean
  message: string
}

export interface TopicProgressItem {
  topic: string
  total: number
  solved: number
  percentage: number
}

export interface DifficultyProgressItem {
  difficulty: string
  total: number
  solved: number
  percentage: number
}

export interface PracticeProgressResponse {
  total_questions: number
  solved_count: number
  unsolved_count: number
  bookmarked_count: number
  completion_percentage: number
  topic_progress: TopicProgressItem[]
  difficulty_progress: DifficultyProgressItem[]
}

export interface PracticeHistoryItem {
  question_id: string
  question: string
  topic: string
  difficulty: string
  solved: boolean
  attempts: number
  last_answer: string | null
  last_attempted_at: string | null
}

export interface PracticeHistoryResponse {
  history: PracticeHistoryItem[]
  total: number
}

// ============================================================
// STATS: XP, MASTERY, STREAK, MISSIONS, ACHIEVEMENTS, NOTIFICATIONS
// ============================================================

export interface XpStats {
  total_xp: number
  level: number
  level_title: string
  current_level_xp: number
  next_level_xp: number
  progress_pct: number
}

export interface TopicMasteryItem {
  topic: string
  total: number
  solved: number
  percentage: number
  status: string
}

export interface MasteryStats {
  overall_percentage: number
  mastered_topics: number
  proficient_topics: number
  total_topics: number
  top_topics: TopicMasteryItem[]
}

export interface StreakStats {
  current_streak: number
  longest_streak: number
  is_active_today: boolean
  last_practiced_date: string | null
}

export interface PracticeMission {
  id: string
  title: string
  description: string
  icon: string
  progress: number
  target: number
  completed: boolean
  xp_reward: number
}

export interface PracticeAchievement {
  id: string
  title: string
  description: string
  icon: string
  unlocked: boolean
  progress: string
  category: string
}

export interface PracticeNotification {
  id: string
  type: string
  title: string
  message: string
  timestamp: string
  icon: string
}

export interface PracticeStatsResponse {
  xp: XpStats
  mastery: MasteryStats
  streak: StreakStats
  missions: PracticeMission[]
  achievements: PracticeAchievement[]
  notifications: PracticeNotification[]
}

export async function getPracticeTechnologies(search?: string): Promise<TechnologyListResponse> {
  const query = search ? `?search=${encodeURIComponent(search)}` : ""
  return apiRequest<TechnologyListResponse>(`/practice/technologies${query}`)
}

export async function getPracticeTechnologyTopics(
  techSlug: string,
): Promise<TopicListResponse> {
  return apiRequest<TopicListResponse>(`/practice/technologies/${techSlug}/topics`)
}

export async function getPracticeQuestions(params?: {
  technology?: string
  topic?: string
  search?: string
  difficulty?: string
  question_type?: string
  status?: string
  page?: number
  page_size?: number
}): Promise<PracticeQuestionListResponse> {
  const query = new URLSearchParams()
  if (params?.technology && params.technology !== "all") query.set("technology", params.technology)
  if (params?.topic && params.topic !== "all") query.set("topic", params.topic)
  if (params?.search) query.set("search", params.search)
  if (params?.difficulty && params.difficulty !== "all") query.set("difficulty", params.difficulty)
  if (params?.question_type && params.question_type !== "all") query.set("question_type", params.question_type)
  if (params?.status && params.status !== "all") query.set("status", params.status)
  if (params?.page) query.set("page", String(params.page))
  if (params?.page_size) query.set("page_size", String(params.page_size))

  const qs = query.toString()
  return apiRequest<PracticeQuestionListResponse>(`/practice/questions${qs ? `?${qs}` : ""}`)
}

export async function getPracticeQuestionDetail(
  questionId: string,
): Promise<PracticeQuestionDetailResponse> {
  return apiRequest<PracticeQuestionDetailResponse>(`/practice/questions/${questionId}`)
}

export async function solvePracticeQuestion(
  questionId: string,
  answer?: string,
  solved: boolean = true,
): Promise<SolveQuestionResponse> {
  return apiRequest<SolveQuestionResponse>(`/practice/questions/${questionId}/solve`, {
    method: "POST",
    body: JSON.stringify({ answer, solved }),
  })
}

export async function bookmarkPracticeQuestion(
  questionId: string,
): Promise<BookmarkResponse> {
  return apiRequest<BookmarkResponse>(`/practice/questions/${questionId}/bookmark`, {
    method: "POST",
  })
}

export async function unbookmarkPracticeQuestion(
  questionId: string,
): Promise<BookmarkResponse> {
  return apiRequest<BookmarkResponse>(`/practice/questions/${questionId}/bookmark`, {
    method: "DELETE",
  })
}

export async function getPracticeProgress(): Promise<PracticeProgressResponse> {
  return apiRequest<PracticeProgressResponse>("/practice/progress")
}

export async function getPracticeHistory(): Promise<PracticeHistoryResponse> {
  return apiRequest<PracticeHistoryResponse>("/practice/history")
}

export async function getPracticeStats(): Promise<PracticeStatsResponse> {
  return apiRequest<PracticeStatsResponse>("/practice/stats")
}

// ============================================================
// ACHIEVEMENTS TYPES & API
// ============================================================

export interface AchievementItem {
  id: string
  name: string
  description: string
  category: string
  icon: string
  rarity: "Common" | "Rare" | "Epic" | "Legendary" | string
  xp_reward: number
  current_progress: number
  target_progress: number
  progress_percentage: number
  unlocked: boolean
  unlocked_at: string | null
  requirement_description?: string | null
}

export interface CategoryProgress {
  category: string
  total: number
  unlocked: number
  percentage: number
}

export interface AchievementSummaryResponse {
  total_achievements: number
  unlocked_count: number
  locked_count: number
  total_xp_earned: number
  completion_percentage: number
  recent_unlocks: AchievementItem[]
  categories: CategoryProgress[]
}

export interface AchievementListResponse {
  achievements: AchievementItem[]
  total: number
  unlocked_count: number
}

export interface AchievementDetailResponse {
  achievement: AchievementItem
  related_metrics?: Record<string, unknown> | null
}

export async function getAchievements(category?: string): Promise<AchievementListResponse> {
  const query = category && category.toLowerCase() !== "all" ? `?category=${encodeURIComponent(category)}` : ""
  return apiRequest<AchievementListResponse>(`/achievements${query}`)
}

export async function getAchievementsSummary(): Promise<AchievementSummaryResponse> {
  return apiRequest<AchievementSummaryResponse>("/achievements/summary")
}

export async function getAchievementDetail(id: string): Promise<AchievementDetailResponse> {
  return apiRequest<AchievementDetailResponse>(`/achievements/${id}`)
}

// ============================================================
// NOTIFICATIONS API (TASK 12)
// ============================================================

export interface NotificationItem {
  id: string
  type: string
  title: string
  message: string
  icon: string
  category: string
  is_read: boolean
  created_at: string
  read_at?: string | null
  action_url?: string | null
  priority: string
  metadata?: Record<string, any>
}

export interface NotificationListResponse {
  notifications: NotificationItem[]
  total: number
  page: number
  limit: number
  unread_count: number
  has_next: boolean
}

export interface UnreadCountResponse {
  unread_count: number
}

export interface GetNotificationsParams {
  page?: number
  limit?: number
  unread_only?: boolean
  category?: string
  type?: string
}

export async function getNotifications(params?: GetNotificationsParams): Promise<NotificationListResponse> {
  const queryParams = new URLSearchParams()
  if (params?.page) queryParams.set("page", String(params.page))
  if (params?.limit) queryParams.set("limit", String(params.limit))
  if (params?.unread_only) queryParams.set("unread_only", "true")
  if (params?.category && params.category.toLowerCase() !== "all") {
    queryParams.set("category", params.category)
  }
  if (params?.type) queryParams.set("type", params.type)

  const qs = queryParams.toString()
  return apiRequest<NotificationListResponse>(`/notifications${qs ? `?${qs}` : ""}`)
}

export async function getUnreadNotificationCount(): Promise<UnreadCountResponse> {
  return apiRequest<UnreadCountResponse>("/notifications/unread-count")
}

export async function markNotificationAsRead(id: string): Promise<{ message: string; id: string; is_read: boolean }> {
  return apiRequest<{ message: string; id: string; is_read: boolean }>(`/notifications/${id}/read`, {
    method: "PATCH",
  })
}

export async function markAllNotificationsAsRead(): Promise<{ message: string; updated_count: number }> {
  return apiRequest<{ message: string; updated_count: number }>("/notifications/read-all", {
    method: "PATCH",
  })
}

export async function deleteNotification(id: string): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/notifications/${id}`, {
    method: "DELETE",
  })
}

// ============================================================
// PROFILE API (TASK 13)
// ============================================================

export interface ProfileDetails {
  id: string
  user_id: string
  full_name: string
  email: string
  headline: string | null
  bio: string | null
  phone: string | null
  location: string | null
  college: string | null
  degree: string | null
  graduation_year: number | null
  target_role: string | null
  experience_level: string | null
  skills: string | null
  github_url: string | null
  linkedin_url: string | null
  portfolio_url: string | null
  avatar_url: string | null
  created_at: string
  updated_at: string
}

export interface AccountDetails {
  id: string
  email: string
  is_verified: boolean
  created_at: string
}

export interface PracticeTechItem {
  technology: string
  slug: string
  solved: number
  total: number
  mastery_percentage: number
}

export interface PracticeSummary {
  questions_solved: number
  total_questions: number
  completion_percentage: number
  current_streak: number
  longest_streak: number
  total_xp: number
  current_level: number
  level_title: string
  progress_pct: number
  topics_mastered: number
  technologies_practiced: PracticeTechItem[]
}

export interface AchievementSummaryItem {
  id: string
  name: string
  description: string
  icon: string
  rarity: string
  xp_reward: number
  unlocked_at?: string | null
}

export interface AchievementSummary {
  unlocked_count: number
  total_achievements: number
  completion_percentage: number
  recent_unlocks: AchievementSummaryItem[]
}

export interface RecentInterview {
  id: string
  job_role: string
  difficulty: string
  score: number | null
  completed_at: string | null
}

export interface InterviewSummary {
  completed_interviews: number
  average_score: number
  best_score: number
  recent_interview: RecentInterview | null
}

export interface ResumeStatus {
  has_resume: boolean
  filename: string | null
  uploaded_at: string | null
}

export interface ComprehensiveProfileResponse {
  profile: ProfileDetails
  account: AccountDetails
  practice_summary: PracticeSummary
  achievement_summary: AchievementSummary
  interview_summary: InterviewSummary
  resume_status: ResumeStatus
}

export interface ProfileUpdateRequest {
  full_name?: string
  headline?: string | null
  bio?: string | null
  phone?: string | null
  location?: string | null
  college?: string | null
  degree?: string | null
  graduation_year?: number | null
  target_role?: string | null
  experience_level?: string | null
  skills?: string | null
  github_url?: string | null
  linkedin_url?: string | null
  portfolio_url?: string | null
  avatar_url?: string | null
}

export async function getComprehensiveProfile(): Promise<ComprehensiveProfileResponse> {
  return apiRequest<ComprehensiveProfileResponse>("/profile")
}

export async function updateComprehensiveProfile(
  data: ProfileUpdateRequest,
): Promise<ComprehensiveProfileResponse> {
  return apiRequest<ComprehensiveProfileResponse>("/profile", {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

// ============================================================
// ANTI-CHEATING (PHASE 7)
// ============================================================

export interface AntiCheatingEvent {
  id: string
  interview_id: string
  event_type: string
  severity: "LOW" | "MEDIUM" | "HIGH"
  timestamp: string
  duration: number
  confidence: number
  description: string
  evidence_reference?: string | null
  metadata?: Record<string, any> | null
  created_at: string
}

export interface AntiCheatingSummary {
  overall_status: "CLEAR" | "REVIEW" | "SUSPICIOUS"
  total_events: number
  face_missing_events: number
  multiple_person_events: number
  identity_mismatch_events: number
  device_events: number
  total_suspicious_duration: number
  risk_score: number
}

export interface RecordAntiCheatingEventPayload {
  event_type:
    | "FACE_MISSING"
    | "MULTIPLE_PERSON"
    | "IDENTITY_MISMATCH"
    | "MOBILE_DETECTED"
    | "DEVICE_DETECTED"
    | "SUSPICIOUS_ABSENCE"
    | "OTHER_SUSPICIOUS_ACTIVITY"
  severity?: "LOW" | "MEDIUM" | "HIGH"
  timestamp?: string
  duration?: number
  confidence?: number
  description: string
  evidence_reference?: string | null
  metadata?: Record<string, any>
}

export async function recordAntiCheatingEvent(
  interviewId: string,
  data: RecordAntiCheatingEventPayload,
): Promise<AntiCheatingEvent> {
  return apiRequest<AntiCheatingEvent>(
    `/interview/${interviewId}/anti-cheating/events`,
    {
      method: "POST",
      body: JSON.stringify(data),
    },
  )
}

export async function getAntiCheatingEvents(
  interviewId: string,
): Promise<{ events: AntiCheatingEvent[]; total: number }> {
  return apiRequest<{ events: AntiCheatingEvent[]; total: number }>(
    `/interview/${interviewId}/anti-cheating/events`,
  )
}

export async function getAntiCheatingSummary(
  interviewId: string,
): Promise<AntiCheatingSummary> {
  return apiRequest<AntiCheatingSummary>(
    `/interview/${interviewId}/anti-cheating/summary`,
  )
}

export interface RegisterFaceResponse {
  registered: boolean
  interview_id: string
  vector_dimension: number
  registered_at: string
}

export async function registerCandidateFace(
  interviewId: string,
  encoding: number[],
  metadata?: Record<string, any>,
): Promise<RegisterFaceResponse> {
  return apiRequest<RegisterFaceResponse>(
    `/interview/${interviewId}/anti-cheating/register-face`,
    {
      method: "POST",
      body: JSON.stringify({
        encoding,
        metadata,
      }),
    },
  )
}

// ============================================================
// PHASE 8: CODING INTERVIEW SYSTEM
// ============================================================

export interface CodingProblemListItem {
  id: string
  title: string
  slug: string
  difficulty: "Easy" | "Medium" | "Hard" | string
  topic: string
  tags?: string[]
  company_tags?: string[]
  role_tags?: string[]
  supported_languages: string[]
  is_solved?: boolean | null
  is_attempted?: boolean | null
  acceptance_rate?: number | null
  created_at: string
}

export interface CodingProblemListResponse {
  problems: CodingProblemListItem[]
  items?: CodingProblemListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface CodingProblemExample {
  input: string
  output: string
  explanation?: string
}

export interface CodingProblemDetail {
  id: string
  title: string
  slug: string
  description: string
  difficulty: "Easy" | "Medium" | "Hard" | string
  topic: string
  tags?: string[]
  company_tags?: string[]
  role_tags?: string[]
  constraints?: string[] | string | null
  input_format?: string | null
  output_format?: string | null
  examples: CodingProblemExample[]
  starter_code: Record<string, string>
  supported_languages: string[]
  sample_test_cases: { input: string; output: string }[]
  expected_time_complexity?: string | null
  expected_space_complexity?: string | null
  hints?: string[]
  created_at: string
}

export interface TestCaseExecutionResult {
  test_index: number
  input: string
  expected_output: string
  actual_output: string
  passed: boolean
  execution_time: number
  error?: string | null
}

export interface RunCodeResponse {
  status: string
  results: TestCaseExecutionResult[]
  total_passed: number
  total_tests: number
  compile_error?: string | null
  runtime_error?: string | null
}

export interface RunCustomCodeResponse {
  stdout: string
  stderr: string
  runtime: number
  status: string
}

export interface AIAssistResponse {
  action: string
  content: string
  hint_level?: number | null
  max_hints: number
}

export interface LeaderboardItem {
  rank: number
  user_id: string
  user_name: string
  problems_solved: number
  total_accepted: number
  coding_xp: number
  average_score: number
  current_streak: number
}

export interface LeaderboardResponse {
  leaderboard: LeaderboardItem[]
  total_candidates: number
  user_rank?: number | null
}

export interface PersonalizedRecommendationsResponse {
  weak_topics: string[]
  strong_topics: string[]
  recommended_problems: CodingProblemListItem[]
  recommendation_reasons: string[]
}

export interface AIReviewStructure {
  summary: string
  strengths: string[]
  issues: string[]
  complexity: {
    time: string
    space: string
  }
  optimization_suggestions: string[]
}

export interface CodingSubmission {
  id: string
  user_id: string
  problem_id: string
  problem_title?: string | null
  interview_id?: string | null
  language: string
  source_code: string
  status: string
  score: number
  passed_tests: number
  total_tests: number
  execution_time: number
  compile_error?: string | null
  runtime_error?: string | null
  test_results: TestCaseExecutionResult[]
  complexity_time?: string | null
  complexity_space?: string | null
  ai_review?: AIReviewStructure | null
  optimization_suggestions: string[]
  created_at: string
}

export interface CodingSubmissionListResponse {
  submissions: CodingSubmission[]
  total: number
}

export interface CodingStats {
  total_attempted: number
  total_solved: number
  success_rate: number
  average_score: number
  easy_solved?: number
  medium_solved?: number
  hard_solved?: number
  current_streak?: number
  longest_streak?: number
  recent_submissions: CodingSubmission[]
  topic_breakdown: Record<string, any>
}

export type UserCodingStats = CodingStats
export type CustomCodeResponse = RunCustomCodeResponse
export type AIAssistanceResponse = AIAssistResponse

export async function getCodingProblems(params?: {
  difficulty?: string
  topic?: string
  tag?: string
  company?: string
  role?: string
  search?: string
  solved?: boolean
  attempted?: boolean
  sort?: string
  page?: number
  page_size?: number
}): Promise<CodingProblemListResponse> {
  const query = new URLSearchParams()
  if (params?.difficulty && params.difficulty !== "All") query.append("difficulty", params.difficulty)
  if (params?.topic && params.topic !== "All") query.append("topic", params.topic)
  if (params?.tag && params.tag !== "All") query.append("tag", params.tag)
  if (params?.company && params.company !== "All") query.append("company", params.company)
  if (params?.role && params.role !== "All") query.append("role", params.role)
  if (params?.search) query.append("search", params.search)
  if (params?.solved !== undefined) query.append("solved", String(params.solved))
  if (params?.attempted !== undefined) query.append("attempted", String(params.attempted))
  if (params?.sort) query.append("sort", params.sort)
  if (params?.page) query.append("page", String(params.page))
  if (params?.page_size) query.append("page_size", String(params.page_size))

  const queryString = query.toString() ? `?${query.toString()}` : ""
  return apiRequest<CodingProblemListResponse>(`/coding/problems${queryString}`)
}

export async function getCodingProblem(idOrSlug: string): Promise<CodingProblemDetail> {
  return apiRequest<CodingProblemDetail>(`/coding/problems/${idOrSlug}`)
}

export async function runCodingProblem(
  problemId: string,
  language: string,
  sourceCode: string,
): Promise<RunCodeResponse> {
  return apiRequest<RunCodeResponse>("/coding/run", {
    method: "POST",
    body: JSON.stringify({
      problem_id: problemId,
      language,
      source_code: sourceCode,
    }),
  })
}

export async function runCustomCode(
  problemId: string,
  language: string,
  sourceCode: string,
  customInput: string,
): Promise<RunCustomCodeResponse> {
  return apiRequest<RunCustomCodeResponse>("/coding/run-custom", {
    method: "POST",
    body: JSON.stringify({
      problem_id: problemId,
      language,
      source_code: sourceCode,
      custom_input: customInput,
    }),
  })
}

export async function submitCodingProblem(
  problemId: string,
  language: string,
  sourceCode: string,
  interviewId?: string,
): Promise<CodingSubmission> {
  return apiRequest<CodingSubmission>("/coding/submit", {
    method: "POST",
    body: JSON.stringify({
      problem_id: problemId,
      language,
      source_code: sourceCode,
      interview_id: interviewId || null,
    }),
  })
}

export interface AIAssistParams {
  problem_id: string
  language: string
  source_code?: string
  code?: string
  action: string
  hint_level?: number
  error_message?: string | null
}

export async function getAIAssistance(
  paramsOrProblemId: string | AIAssistParams,
  language?: string,
  sourceCode?: string,
  action?: string,
  hintLevel: number = 1,
  errorMessage?: string,
): Promise<AIAssistResponse> {
  let pid: string
  let lang: string
  let code: string
  let act: string
  let hl: number = 1
  let err: string | null = null

  if (typeof paramsOrProblemId === "object") {
    pid = paramsOrProblemId.problem_id
    lang = paramsOrProblemId.language
    code = paramsOrProblemId.source_code || paramsOrProblemId.code || ""
    act = paramsOrProblemId.action
    hl = paramsOrProblemId.hint_level ?? 1
    err = paramsOrProblemId.error_message || null
  } else {
    pid = paramsOrProblemId
    lang = language || "python"
    code = sourceCode || ""
    act = action || "give_hint"
    hl = hintLevel
    err = errorMessage || null
  }

  // Normalize action names
  if (act === "hint") act = "give_hint"
  if (act === "explain_problem") act = "explain_problem"
  if (act === "complexity") act = "analyze_complexity"
  if (act === "edge_cases") act = "explain_edge_cases"

  return apiRequest<AIAssistResponse>("/coding/assist", {
    method: "POST",
    body: JSON.stringify({
      problem_id: pid,
      language: lang,
      source_code: code,
      action: act,
      hint_level: hl,
      error_message: err,
    }),
  })
}

export async function getCodingSubmissions(params?: {
  problem_id?: string
  page?: number
  page_size?: number
}): Promise<CodingSubmissionListResponse> {
  const query = new URLSearchParams()
  if (params?.problem_id) query.append("problem_id", params.problem_id)
  if (params?.page) query.append("page", String(params.page))
  if (params?.page_size) query.append("page_size", String(params.page_size))

  const queryString = query.toString() ? `?${query.toString()}` : ""
  return apiRequest<CodingSubmissionListResponse>(`/coding/submissions${queryString}`)
}

export async function getCodingSubmission(submissionId: string): Promise<CodingSubmission> {
  return apiRequest<CodingSubmission>(`/coding/submissions/${submissionId}`)
}

export async function getCodingStats(): Promise<CodingStats> {
  return apiRequest<CodingStats>("/coding/stats")
}

export const getUserCodingStats = getCodingStats

export async function getArenaLeaderboard(limit: number = 50): Promise<LeaderboardResponse> {
  return apiRequest<LeaderboardResponse>(`/coding/leaderboard?limit=${limit}`)
}

export async function getPersonalizedRecommendations(): Promise<PersonalizedRecommendationsResponse> {
  return apiRequest<PersonalizedRecommendationsResponse>("/coding/recommendations")
}

// ============================================================
// PHASE 8D: COMPETITIVE CODING & LIVE CONTEST ARENA
// ============================================================

export interface ContestListItem {
  id: string
  title: string
  slug: string
  description: string
  start_time: string
  end_time: string
  duration_minutes: number
  status: "UPCOMING" | "LIVE" | "ENDED" | "CANCELLED" | string
  max_participants?: number | null
  is_proctored: boolean
  scoring_type: string
  problems_count: number
  registered_count: number
  is_registered: boolean
}

export interface ContestListResponse {
  contests: ContestListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  server_time: string
}

export interface ContestDetail {
  id: string
  title: string
  slug: string
  description: string
  start_time: string
  end_time: string
  duration_minutes: number
  status: "UPCOMING" | "LIVE" | "ENDED" | "CANCELLED" | string
  max_participants?: number | null
  is_proctored: boolean
  scoring_type: string
  penalty_per_wrong_attempt_mins: number
  rules?: string | null
  allowed_languages: string[]
  problems_count: number
  registered_count: number
  is_registered: boolean
  server_time: string
  time_to_start_seconds: number
  time_remaining_seconds: number
}

export interface ContestProblemItem {
  id: string
  problem_id: string
  order_index: number
  label: string
  title: string
  slug: string
  difficulty: string
  topic: string
  points: number
  penalty_mins: number
  time_limit_seconds: number
  is_solved: boolean
  attempts_count: number
}

export interface ContestProblemListResponse {
  contest_id: string
  contest_title: string
  status: string
  server_time: string
  time_remaining_seconds: number
  problems: ContestProblemItem[]
}

export interface ContestProblemDetail {
  id: string
  problem_id: string
  order_index: number
  label: string
  points: number
  penalty_mins: number
  time_limit_seconds: number
  title: string
  slug: string
  description: string
  difficulty: string
  topic: string
  tags: string[]
  constraints?: string[] | string | null
  input_format?: string | null
  output_format?: string | null
  examples: { input: string; output: string; explanation?: string }[]
  starter_code: Record<string, string>
  supported_languages: string[]
  test_cases: { input: string; output: string }[]
}

export interface ContestSubmitResponse {
  submission_id: string
  status: string
  score: number
  points_awarded: number
  execution_time: number
  passed_tests: number
  total_tests: number
  penalty_minutes: number
  current_rank?: number | null
  total_solved: number
  total_score: number
  compile_error?: string | null
  runtime_error?: string | null
}

export interface ContestLeaderboardEntry {
  rank: number
  user_id: string
  username: string
  full_name: string
  solved_count: number
  total_score: number
  penalty_minutes: number
  last_submission_at?: string | null
  problem_results: Record<string, any>
}

export interface LeaderboardProblemMeta {
  problem_id: string
  label: string
  points: number
}

export interface ContestLeaderboardResponse {
  contest_id: string
  contest_title: string
  status: string
  server_time: string
  total_participants: number
  problems: LeaderboardProblemMeta[]
  leaderboard: ContestLeaderboardEntry[]
  user_entry?: ContestLeaderboardEntry | null
}

export interface ProblemPerformance {
  label: string
  title: string
  points: number
  solved: boolean
  attempts: number
  time_taken_mins?: number | null
  status: string
}

export interface ContestMyStatusResponse {
  contest_id: string
  registered: boolean
  attended: boolean
  solved_count: number
  total_score: number
  penalty_minutes: number
  rank?: number | null
  problems: ProblemPerformance[]
  submissions: any[]
}

export interface ContestResultsResponse {
  contest_id: string
  contest_title: string
  status: string
  total_participants: number
  final_rank?: number | null
  percentile?: number | null
  total_score: number
  solved_count: number
  penalty_minutes: number
  problems: ProblemPerformance[]
  submissions: any[]
}

export interface UserContestHistoryItem {
  contest_id: string
  contest_title: string
  contest_slug: string
  start_time: string
  end_time: string
  status: string
  rank?: number | null
  total_participants: number
  solved_count: number
  total_score: number
  penalty_minutes: number
  percentile?: number | null
}

export interface UserContestHistoryResponse {
  contests: UserContestHistoryItem[]
  total_contests: number
  best_rank?: number | null
  average_rank?: number | null
  total_problems_solved: number
}

export async function getContests(params?: {
  status?: string
  search?: string
  page?: number
  page_size?: number
}): Promise<ContestListResponse> {
  const query = new URLSearchParams()
  if (params?.status) query.append("status", params.status)
  if (params?.search) query.append("search", params.search)
  if (params?.page) query.append("page", String(params.page))
  if (params?.page_size) query.append("page_size", String(params.page_size))

  const qs = query.toString() ? `?${query.toString()}` : ""
  return apiRequest<ContestListResponse>(`/contests${qs}`)
}

export async function getContestDetail(idOrSlug: string): Promise<ContestDetail> {
  return apiRequest<ContestDetail>(`/contests/${idOrSlug}`)
}

export async function registerForContest(contestId: string): Promise<{ registered: boolean; message: string }> {
  return apiRequest<{ registered: boolean; message: string }>(`/contests/${contestId}/register`, {
    method: "POST",
  })
}

export async function getContestProblems(contestId: string): Promise<ContestProblemListResponse> {
  return apiRequest<ContestProblemListResponse>(`/contests/${contestId}/problems`)
}

export async function getContestProblemDetail(contestId: string, problemId: string): Promise<ContestProblemDetail> {
  return apiRequest<ContestProblemDetail>(`/contests/${contestId}/problems/${problemId}`)
}

export async function submitContestProblem(
  contestId: string,
  problemId: string,
  language: string,
  sourceCode: string,
): Promise<ContestSubmitResponse> {
  return apiRequest<ContestSubmitResponse>(`/contests/${contestId}/submit`, {
    method: "POST",
    body: JSON.stringify({
      problem_id: problemId,
      language,
      source_code: sourceCode,
    }),
  })
}

export async function runContestProblem(
  contestId: string,
  problemId: string,
  language: string,
  sourceCode: string,
): Promise<RunCodeResponse> {
  return apiRequest<RunCodeResponse>(`/contests/${contestId}/run`, {
    method: "POST",
    body: JSON.stringify({
      problem_id: problemId,
      language,
      source_code: sourceCode,
    }),
  })
}

export async function runContestCustom(
  contestId: string,
  problemId: string,
  language: string,
  sourceCode: string,
  customInput: string,
): Promise<RunCustomCodeResponse> {
  return apiRequest<RunCustomCodeResponse>(`/contests/${contestId}/run-custom`, {
    method: "POST",
    body: JSON.stringify({
      problem_id: problemId,
      language,
      source_code: sourceCode,
      custom_input: customInput,
    }),
  })
}

export async function getContestLeaderboard(contestId: string): Promise<ContestLeaderboardResponse> {
  return apiRequest<ContestLeaderboardResponse>(`/contests/${contestId}/leaderboard`)
}

export async function getContestMyStatus(contestId: string): Promise<ContestMyStatusResponse> {
  return apiRequest<ContestMyStatusResponse>(`/contests/${contestId}/my-status`)
}

export async function getContestResults(contestId: string): Promise<ContestResultsResponse> {
  return apiRequest<ContestResultsResponse>(`/contests/${contestId}/results`)
}

export async function getUserContestHistory(): Promise<UserContestHistoryResponse> {
  return apiRequest<UserContestHistoryResponse>("/contests/my-history")
}

// ============================================================
// PHASE 10: RAG VECTOR & RETRIEVAL APIS
// ============================================================

export interface RagStatusResponse {
  status: string
  provider: string
  model_name: string
  embedding_dimension: number
  total_indexed: number
  pgvector_available: boolean
}

export interface RetrievedQuestion {
  question_id: string
  question_text: string
  question_type: string
  role: string | null
  difficulty: string
  topic: string
  skills: string[]
  company: string | null
  source: string
  similarity: number
  relevance_score: number
  role_match: boolean
  skill_match: boolean
  difficulty_match: boolean
}

export interface RagSearchResponse {
  query: string
  total_retrieved: number
  results: RetrievedQuestion[]
}

export interface RagIndexResponse {
  status: string
  indexed_count: number
  skipped_count: number
  total_vectors: number
}

export async function getRagStatus(): Promise<RagStatusResponse> {
  return apiRequest<RagStatusResponse>("/rag/status")
}

export async function searchRagQuestions(params: {
  query: string
  role?: string
  difficulty?: string
  topic?: string
  skills?: string[]
  question_type?: string
  company?: string
  limit?: number
  exclude_questions?: string[]
}): Promise<RagSearchResponse> {
  return apiRequest<RagSearchResponse>("/rag/search", {
    method: "POST",
    body: JSON.stringify(params),
  })
}

export async function indexRagQuestions(options?: {
  batch_size?: number
  limit?: number
  force_reindex?: boolean
}): Promise<RagIndexResponse> {
  return apiRequest<RagIndexResponse>("/rag/index", {
    method: "POST",
    body: JSON.stringify(options || {}),
  })
}

export async function reindexRagQuestions(options?: {
  batch_size?: number
  limit?: number
}): Promise<RagIndexResponse> {
  return apiRequest<RagIndexResponse>("/rag/reindex", {
    method: "POST",
    body: JSON.stringify(options || {}),
  })
}

// ============================================================
// PHASE 11: PERSONALIZED LEARNING & RECOMMENDATIONS
// ============================================================

export interface LearningProfile {
  id: string
  user_id: string
  target_role: string
  target_level: string
  overall_readiness_score: number | null
  hours_per_week: number
  created_at: string
  updated_at: string
}

export interface SkillPerformanceItem {
  id?: string
  canonical_skill: string
  category: string
  interview_score: number | null
  interview_attempts: number
  coding_score: number | null
  coding_attempts: number
  combined_score: number | null
  total_attempts: number
  status: "strong" | "needs_practice" | "weak" | "unassessed"
  confidence: "high" | "medium" | "low" | "insufficient"
  last_assessed_at: string | null
  reason?: string | null
}

export interface WeakTopicItem {
  topic: string
  category: string
  combined_score: number | null
  status: string
  confidence: string
  attempts: number
  priority: "high" | "medium" | "low"
  reason: string
  recommended_action: string
}

export interface RoadmapItem {
  id: string
  title: string
  type: "study" | "practice" | "interview" | "coding"
  topic: string
  is_completed: boolean
  estimated_mins: number
  ref_link?: string | null
}

export interface RoadmapWeek {
  week_number: number
  title: string
  focus_topic: string
  priority: string
  reason: string
  items: RoadmapItem[]
}

export interface LearningRoadmap {
  id: string
  user_id: string
  target_role: string
  title: string
  status: string
  progress_percentage: number
  weeks: RoadmapWeek[]
  created_at: string
  updated_at: string
}

export interface LearningResource {
  id: string
  title: string
  description: string
  topic: string
  canonical_skill: string
  difficulty: string
  resource_type: string
  url?: string | null
  estimated_duration_mins: number
  source: string
  quality_rating: number
}

export interface ConsolidatedRecommendationsResponse {
  weak_topics: WeakTopicItem[]
  resources: LearningResource[]
  interview_practice: Array<{
    question_id?: string
    question: string
    topic: string
    difficulty: string
    role?: string
    reason: string
    action_url: string
  }>
  coding_challenges: Array<{
    problem_id: string
    title: string
    slug: string
    difficulty: string
    topic: string
    reason: string
    action_url: string
  }>
  generated_at: string
}

export interface DailyPlanTask {
  id: string
  title: string
  type: "study" | "interview" | "coding" | "revision"
  topic: string
  duration_mins: number
  is_completed: boolean
  ref_type?: string | null
  ref_id?: string | null
  action_url?: string | null
}

export interface DailyPracticePlan {
  id: string
  user_id: string
  plan_date: string
  items: DailyPlanTask[]
  is_completed: boolean
  completed_at?: string | null
  progress_percentage: number
}

export interface WeeklyGoal {
  id: string
  user_id: string
  week_start_date: string
  title: string
  goal_type: string
  target_count: number
  completed_count: number
  deadline?: string | null
  status: "in_progress" | "completed" | "expired"
  progress_percentage: number
}

export interface SkillProgressTrend {
  canonical_skill: string
  current_score: number | null
  initial_score: number | null
  delta: number | null
  status: string
  attempts: number
}

export interface LearningProgressResponse {
  overall_readiness: number
  total_skills_assessed: number
  strong_skills_count: number
  needs_practice_count: number
  weak_skills_count: number
  roadmap_progress_pct: number
  daily_plan_completed: boolean
  weekly_goals_completed_pct: number
  skills_trend: SkillProgressTrend[]
  summary_message: string
}

export async function getLearningProfile(): Promise<LearningProfile> {
  return apiRequest<LearningProfile>("/learning/profile")
}

export async function updateLearningProfile(data: {
  target_role?: string
  target_level?: string
  hours_per_week?: number
}): Promise<LearningProfile> {
  return apiRequest<LearningProfile>("/learning/profile", {
    method: "PUT",
    body: JSON.stringify(data),
  })
}

export async function getSkillsPerformance(forceSync: boolean = false): Promise<SkillPerformanceItem[]> {
  return apiRequest<SkillPerformanceItem[]>(`/learning/skills?force_sync=${forceSync}`)
}

export async function getWeakTopics(): Promise<WeakTopicItem[]> {
  return apiRequest<WeakTopicItem[]>("/learning/weak-topics")
}

export async function getLearningRoadmap(): Promise<LearningRoadmap> {
  return apiRequest<LearningRoadmap>("/learning/roadmap")
}

export async function generateLearningRoadmap(data: {
  target_role?: string
  target_level?: string
}): Promise<LearningRoadmap> {
  return apiRequest<LearningRoadmap>("/learning/roadmap/generate", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function getLearningResources(params?: {
  topic?: string
  limit?: number
}): Promise<LearningResource[]> {
  const query = new URLSearchParams()
  if (params?.topic) query.append("topic", params.topic)
  if (params?.limit) query.append("limit", params.limit.toString())
  const qs = query.toString() ? `?${query.toString()}` : ""
  return apiRequest<LearningResource[]>(`/learning/resources${qs}`)
}

export async function getConsolidatedRecommendations(): Promise<ConsolidatedRecommendationsResponse> {
  return apiRequest<ConsolidatedRecommendationsResponse>("/learning/recommendations")
}

export async function getDailyPracticePlan(): Promise<DailyPracticePlan> {
  return apiRequest<DailyPracticePlan>("/learning/daily-plan")
}

export async function toggleDailyPracticeTask(taskId: string): Promise<DailyPracticePlan> {
  return apiRequest<DailyPracticePlan>(`/learning/daily-plan/${taskId}/toggle`, {
    method: "POST",
  })
}

export async function getWeeklyGoals(): Promise<WeeklyGoal[]> {
  return apiRequest<WeeklyGoal[]>("/learning/weekly-goals")
}

export async function incrementWeeklyGoal(goalId: string): Promise<WeeklyGoal> {
  return apiRequest<WeeklyGoal>(`/learning/weekly-goals/${goalId}/increment`, {
    method: "POST",
  })
}

export async function getLearningProgress(): Promise<LearningProgressResponse> {
  return apiRequest<LearningProgressResponse>("/learning/progress")
}

// ============================================================
// PAYMENTS & SUBSCRIPTIONS (Phase 14)
// ============================================================

export type SubscriptionPlan = {
  id: string
  name: string
  slug: string
  description?: string | null
  price: number // in paise
  currency: string
  billing_interval: string
  duration_days: number
  is_active: boolean
  features?: { items?: string[] } | null
  limits?: Record<string, any> | null
  sort_order: number
}

export type UserSubscription = {
  id: string
  user_id: string
  plan_id: string
  status: string
  starts_at?: string | null
  expires_at?: string | null
  auto_renew: boolean
  cancelled_at?: string | null
  plan?: SubscriptionPlan | null
}

export type PaymentTransaction = {
  id: string
  user_id: string
  subscription_id?: string | null
  plan_id: string
  provider: string
  provider_order_id?: string | null
  provider_payment_id?: string | null
  amount: number
  currency: string
  status: string
  payment_method?: string | null
  failure_reason?: string | null
  created_at: string
}

export type Invoice = {
  id: string
  user_id: string
  subscription_id?: string | null
  payment_id: string
  invoice_number: string
  amount: number
  discount: number
  tax: number
  total_amount: number
  currency: string
  status: string
  issued_at: string
}

export type CreateOrderResponse = {
  order_id: string
  amount: number
  currency: string
  razorpay_key_id: string
  plan_name: string
  plan_slug: string
  original_amount: number
  discount: number
  transaction_id: string
}

export type VerifyPaymentResponse = {
  status: string
  message: string
  payment?: PaymentTransaction | null
  subscription?: UserSubscription | null
  invoice?: Invoice | null
}

export type CouponValidationResponse = {
  valid: boolean
  message: string
  discount_amount: number
  discount_type?: string | null
  discount_value?: number | null
  final_amount: number
}

export type UsageResponse = {
  plan_name: string
  plan_slug: string
  limits: Record<string, any>
  current_usage: Record<string, any>
}

export async function getSubscriptionPlans(): Promise<SubscriptionPlan[]> {
  return apiRequest<SubscriptionPlan[]>("/payments/plans")
}

export async function getMySubscription(): Promise<UserSubscription | null> {
  return apiRequest<UserSubscription | null>("/payments/subscription")
}

export async function createPaymentOrder(
  planOrOptions: string | {
    planId?: string
    couponCode?: string
    amount?: number
    currency?: string
    receipt?: string
  },
  legacyCouponCode?: string,
): Promise<CreateOrderResponse> {
  const payload: Record<string, any> = {}

  if (typeof planOrOptions === "string") {
    payload.plan_id = planOrOptions
    if (legacyCouponCode) payload.coupon_code = legacyCouponCode.trim()
  } else {
    if (planOrOptions.planId) payload.plan_id = planOrOptions.planId
    if (planOrOptions.couponCode) payload.coupon_code = planOrOptions.couponCode.trim()
    if (planOrOptions.amount !== undefined) payload.amount = planOrOptions.amount
    if (planOrOptions.currency) payload.currency = planOrOptions.currency
    if (planOrOptions.receipt) payload.receipt = planOrOptions.receipt
  }

  return apiRequest<CreateOrderResponse>("/payments/create-order", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export async function verifyPayment(data: {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
}): Promise<VerifyPaymentResponse> {
  return apiRequest<VerifyPaymentResponse>("/payments/verify", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function validateCoupon(
  couponCode: string,
  planId: string,
): Promise<CouponValidationResponse> {
  return apiRequest<CouponValidationResponse>("/payments/validate-coupon", {
    method: "POST",
    body: JSON.stringify({
      coupon_code: couponCode,
      plan_id: planId,
    }),
  })
}

export async function cancelSubscription(): Promise<UserSubscription> {
  return apiRequest<UserSubscription>("/payments/cancel-subscription", {
    method: "POST",
  })
}

export async function getSubscriptionUsage(): Promise<UsageResponse> {
  return apiRequest<UsageResponse>("/payments/usage")
}

export async function getPaymentHistory(
  limit: number = 50,
  offset: number = 0,
): Promise<{ payments: PaymentTransaction[]; total: number }> {
  return apiRequest<{ payments: PaymentTransaction[]; total: number }>(
    `/payments/history?limit=${limit}&offset=${offset}`,
  )
}

export async function getInvoices(
  limit: number = 50,
  offset: number = 0,
): Promise<{ invoices: Invoice[]; total: number }> {
  return apiRequest<{ invoices: Invoice[]; total: number }>(
    `/payments/invoices?limit=${limit}&offset=${offset}`,
  )
}

export async function getSingleInvoice(invoiceId: string): Promise<Invoice> {
  return apiRequest<Invoice>(`/payments/invoices/${invoiceId}`)
}

// ============================================================
// SUPPORT & COMMUNICATION API (PHASE 15)
// ============================================================

export interface SupportTicketMessage {
  id: string
  ticket_id: string
  sender_id: string
  sender_name?: string
  sender_type: "candidate" | "support" | "admin"
  message: string
  is_internal: boolean
  created_at: string
  updated_at?: string
}

export interface SupportTicket {
  id: string
  user_id: string
  ticket_number: string
  subject: string
  description?: string
  category: string
  priority: string
  status: string
  assigned_to?: string | null
  created_at: string
  updated_at: string
  resolved_at?: string | null
  closed_at?: string | null
  message_count?: number
  messages?: SupportTicketMessage[]
}

export interface TicketListResponse {
  tickets: SupportTicket[]
  total: number
}

export interface TicketCreateRequest {
  subject: string
  description: string
  category: string
  priority?: string
}

export interface FeedbackItem {
  id: string
  user_id: string
  category: string
  rating: number
  message: string
  page_context?: string | null
  status: string
  created_at: string
}

export interface FeedbackCreateRequest {
  category: string
  rating: number
  message: string
  page_context?: string
  metadata?: Record<string, any>
}

export interface FAQItem {
  id: string
  question: string
  answer: string
  category: string
  display_order: number
  is_active: boolean
  created_at?: string
  updated_at?: string
}

export interface HelpArticleItem {
  id: string
  title: string
  slug: string
  category: string
  content?: string
  display_order: number
  is_published: boolean
  created_at: string
  updated_at?: string
}

export async function createSupportTicket(data: TicketCreateRequest): Promise<SupportTicket> {
  return apiRequest<SupportTicket>("/support/tickets", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function getSupportTickets(
  status?: string,
  category?: string,
  limit: number = 50,
  offset: number = 0,
): Promise<TicketListResponse> {
  const params = new URLSearchParams()
  if (status && status !== "all") params.set("status", status)
  if (category && category !== "all") params.set("category", category)
  params.set("limit", String(limit))
  params.set("offset", String(offset))
  const qs = params.toString()
  return apiRequest<TicketListResponse>(`/support/tickets${qs ? `?${qs}` : ""}`)
}

export async function getSupportTicket(ticketId: string): Promise<SupportTicket> {
  return apiRequest<SupportTicket>(`/support/tickets/${ticketId}`)
}

export async function sendTicketMessage(
  ticketId: string,
  message: string,
): Promise<SupportTicketMessage> {
  return apiRequest<SupportTicketMessage>(`/support/tickets/${ticketId}/messages`, {
    method: "POST",
    body: JSON.stringify({ message }),
  })
}

export async function closeSupportTicket(ticketId: string): Promise<SupportTicket> {
  return apiRequest<SupportTicket>(`/support/tickets/${ticketId}/close`, {
    method: "POST",
  })
}

export async function reopenSupportTicket(ticketId: string): Promise<SupportTicket> {
  return apiRequest<SupportTicket>(`/support/tickets/${ticketId}/reopen`, {
    method: "POST",
  })
}

export async function submitFeedback(data: FeedbackCreateRequest): Promise<FeedbackItem> {
  return apiRequest<FeedbackItem>("/support/feedback", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function getMyFeedback(
  limit: number = 20,
  offset: number = 0,
): Promise<{ items: FeedbackItem[]; total: number }> {
  return apiRequest<{ items: FeedbackItem[]; total: number }>(
    `/support/feedback/mine?limit=${limit}&offset=${offset}`,
  )
}

export async function getFAQs(category?: string): Promise<FAQItem[]> {
  const qs = category && category !== "all" ? `?category=${encodeURIComponent(category)}` : ""
  return apiRequest<FAQItem[]>(`/support/faqs${qs}`)
}

export async function getHelpArticles(category?: string): Promise<HelpArticleItem[]> {
  const qs = category && category !== "all" ? `?category=${encodeURIComponent(category)}` : ""
  return apiRequest<HelpArticleItem[]>(`/support/articles${qs}`)
}

export async function getHelpArticle(slug: string): Promise<HelpArticleItem> {
  return apiRequest<HelpArticleItem>(`/support/articles/${encodeURIComponent(slug)}`)
}

// Notification aliases to strictly meet Phase 15 method naming specs
export const markNotificationRead = markNotificationAsRead
export const markAllNotificationsRead = markAllNotificationsAsRead
