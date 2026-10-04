// ============================================================
// ADMIN DASHBOARD TYPES & INTERFACES
// ============================================================

export type AdminRoleType =
  | "SUPER_ADMIN"
  | "ADMIN"
  | "CONTENT_MANAGER"
  | "SUPPORT_AGENT"
  | "FINANCE_ADMIN"
  | "INTERVIEW_COACH"
  | "AI_ENGINEER"
  | "CANDIDATE"

export interface AdminUser {
  id: string
  email: string
  full_name: string
  role: string
  is_admin: boolean
  is_active: boolean
  is_verified: boolean
  created_at?: string
  last_login?: string
}

export interface AdminKPISummary {
  total_users: number
  active_users: number
  new_users_last_7_days: number
  total_interviews: number
  completed_interviews: number
  average_interview_score: number
  active_subscriptions: number
  total_revenue_inr: number
  open_support_tickets: number
  total_coding_submissions: number
  active_contests: number
  total_contest_participants: number
  rag_indexed_questions: number
}

export interface TrendDataPoint {
  date: string
  value: number
  label?: string
}

export interface DistributionItem {
  name: string
  count: number
  percentage?: number
}

export interface RecentActivityItem {
  id: string
  actor_email: string
  action: string
  resource_type: string
  resource_id?: string
  timestamp: string
  details?: Record<string, any>
}

export interface AdminDashboardData {
  kpis: AdminKPISummary
  trends: {
    interviews_daily: TrendDataPoint[]
    revenue_daily: TrendDataPoint[]
    user_signups_daily: TrendDataPoint[]
  }
  distributions: {
    subscription_plans: DistributionItem[]
    interview_scores: DistributionItem[]
    support_by_priority: DistributionItem[]
  }
  recent_activities: RecentActivityItem[]
}

// User Management
export interface AdminUserListItem {
  id: string
  email: string
  full_name: string
  role: string
  is_admin: boolean
  is_active: boolean
  is_verified: boolean
  created_at: string
  interview_count: number
  subscription_status?: string
}

export interface AdminUserDetail extends AdminUserListItem {
  interviews: Array<{
    id: string
    job_role: string
    difficulty: string
    status: string
    score: number | null
    created_at: string
  }>
  subscriptions: Array<{
    id: string
    plan_name: string
    status: string
    current_period_end: string
  }>
  payments: Array<{
    id: string
    amount_inr: number
    status: string
    provider_order_id: string
    created_at: string
  }>
  tickets: Array<{
    id: string
    subject: string
    status: string
    priority: string
    created_at: string
  }>
  coding_stats?: {
    total_submissions: number
    accepted_submissions: number
    easy_solved: number
    medium_solved: number
    hard_solved: number
  }
}

// Interviews
export interface AdminInterviewItem {
  id: string
  user_id: string
  user_email?: string
  user_name?: string
  job_role: string
  difficulty: string
  status: string
  score: number | null
  questions_count?: number
  created_at: string
  completed_at?: string | null
  feedback?: string | null
}

// Questions
export interface AdminQuestionItem {
  id: string
  technology: string
  category: string
  difficulty: string
  question_text: string
  expected_answer?: string
  sample_answer?: string
  evaluation_criteria?: string
  tags?: string[]
  is_active: boolean
  created_at?: string
}

// Coding Problems
export interface AdminCodingProblemItem {
  id: string
  title: string
  slug: string
  difficulty: "Easy" | "Medium" | "Hard"
  category: string
  tags: string[]
  acceptance_rate?: number
  total_submissions?: number
  is_active: boolean
  created_at?: string
}

// Companies
export interface AdminCompanyItem {
  id: string
  name: string
  slug: string
  logo_url?: string
  description?: string
  difficulty: string
  hiring_roles: string[]
  is_active: boolean
  interview_count?: number
}

// Resources
export interface AdminResourceItem {
  id: string
  title: string
  category: string
  type: string
  url: string
  summary?: string
  tags: string[]
  is_featured: boolean
  created_at?: string
}

// AI Agent Configs
export interface AdminAIAgentConfig {
  id: string
  agent_name: string
  model_provider: string
  model_name: string
  system_prompt: string
  temperature: number
  max_tokens: number
  is_active: boolean
  updated_at?: string
}

// Subscriptions & Payments
export interface AdminSubscriptionPlan {
  id: string
  name: string
  slug: string
  price_inr: number
  interval: string
  features: string[]
  is_active: boolean
  subscribers_count?: number
}

export interface AdminPaymentItem {
  id: string
  user_id: string
  user_email?: string
  provider_order_id: string
  provider_payment_id?: string
  amount_inr: number
  currency: string
  status: string
  created_at: string
}

export interface AdminCouponItem {
  id: string
  code: string
  discount_percent: number
  usage_limit?: number
  times_used: number
  expires_at?: string
  is_active: boolean
}

export interface AdminInvoiceItem {
  id: string
  invoice_number: string
  user_id: string
  user_email?: string
  amount_inr: number
  issued_at: string
  download_url?: string
}

// Support & Feedback
export interface AdminSupportTicketItem {
  id: string
  ticket_number: string
  user_id: string
  user_email?: string
  subject: string
  category: string
  priority: string
  status: string
  created_at: string
  updated_at?: string
  messages_count?: number
}

export interface AdminFeedbackItem {
  id: string
  user_id: string
  user_email?: string
  category: string
  rating: number
  feedback_text: string
  sentiment?: string
  status: string
  created_at: string
}

// Notifications
export interface AdminAnnouncementPayload {
  title: string
  message: string
  target_role?: string
  priority: "low" | "medium" | "high" | "urgent"
  channels?: string[]
}

// Achievements
export interface AdminAchievementItem {
  id: string
  title: string
  description: string
  icon_name: string
  points: number
  category: string
  total_unlocked?: number
}

// Audit Logs
export interface AdminAuditLogItem {
  id: string
  actor_id?: string
  actor_email: string
  action: string
  resource_type: string
  resource_id?: string
  changes?: Record<string, any>
  ip_address?: string
  timestamp: string
}

// System Settings
export interface AdminSystemSettingItem {
  key: string
  value: any
  category: string
  description?: string
  is_public: boolean
  updated_at?: string
}

// RBAC
export interface AdminRoleItem {
  id: string
  name: string
  description?: string
  permissions: string[]
  is_system: boolean
  users_count?: number
}

// RAG Monitor
export interface AdminRAGStatus {
  total_vectors: number
  collections: Array<{
    name: string
    count: number
    status: string
  }>
  last_indexed_at?: string
  top_queries?: Array<{
    query: string
    count: number
    avg_relevance: number
  }>
}

// Contests
export interface AdminContestItem {
  id: string
  title: string
  slug: string
  start_time: string
  end_time: string
  status: string
  participant_count: number
  problem_count: number
  is_public: boolean
}
