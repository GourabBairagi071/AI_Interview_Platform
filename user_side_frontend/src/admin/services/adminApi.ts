// ============================================================
// ADMIN DASHBOARD API CLIENT
// ============================================================

const API_BASE_URL = "http://127.0.0.1:8000/api/v1"

export async function adminRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem("access_token")

  const headers = new Headers(options.headers)
  headers.set("Accept", "application/json")

  if (
    options.body &&
    !(options.body instanceof FormData) &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json")
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const errorMsg =
      data?.detail ||
      data?.message ||
      `Request failed with status ${response.status}`
    throw new Error(errorMsg)
  }

  return data as T
}

export const adminApi = {
  // Current user info
  getCurrentUser: async () => {
    try {
      return await adminRequest<any>("/admin/me")
    } catch {
      return await adminRequest<any>("/auth/me")
    }
  },

  // Dashboard Overview & KPIs
  getDashboardKPIs: (timeRange = "30d") =>
    adminRequest<any>(`/admin/dashboard?time_range=${timeRange}`),

  // User Management
  getUsers: (params: {
    page?: number
    page_size?: number
    search?: string
    role?: string
    is_active?: boolean
  } = {}) => {
    const q = new URLSearchParams()
    if (params.page) q.set("page", params.page.toString())
    if (params.page_size) q.set("page_size", params.page_size.toString())
    if (params.search) q.set("search", params.search)
    if (params.role) q.set("role", params.role)
    if (params.is_active !== undefined)
      q.set("is_active", String(params.is_active))
    return adminRequest<any>(`/admin/users?${q.toString()}`)
  },

  getUserDetail: (userId: string) =>
    adminRequest<any>(`/admin/users/${userId}`),

  updateUserStatus: (userId: string, isActive: boolean) =>
    adminRequest<any>(`/admin/users/${userId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    }),

  updateUserRole: (userId: string, role: string) =>
    adminRequest<any>(`/admin/users/${userId}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    }),

  // Interviews
  getInterviews: (params: {
    page?: number
    page_size?: number
    status?: string
    job_role?: string
    difficulty?: string
    search?: string
  } = {}) => {
    const q = new URLSearchParams()
    if (params.page) q.set("page", params.page.toString())
    if (params.page_size) q.set("page_size", params.page_size.toString())
    if (params.status) q.set("status", params.status)
    if (params.job_role) q.set("job_role", params.job_role)
    if (params.difficulty) q.set("difficulty", params.difficulty)
    if (params.search) q.set("search", params.search)
    return adminRequest<any>(`/admin/interviews?${q.toString()}`)
  },

  getInterviewDetail: (interviewId: string) =>
    adminRequest<any>(`/admin/interviews/${interviewId}`),

  // Practice Questions
  getQuestions: (params: {
    page?: number
    page_size?: number
    technology?: string
    difficulty?: string
    search?: string
  } = {}) => {
    const q = new URLSearchParams()
    if (params.page) q.set("page", params.page.toString())
    if (params.page_size) q.set("page_size", params.page_size.toString())
    if (params.technology) q.set("technology", params.technology)
    if (params.difficulty) q.set("difficulty", params.difficulty)
    if (params.search) q.set("search", params.search)
    return adminRequest<any>(`/admin/questions?${q.toString()}`)
  },

  createQuestion: (data: any) =>
    adminRequest<any>("/admin/questions", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateQuestion: (questionId: string, data: any) =>
    adminRequest<any>(`/admin/questions/${questionId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteQuestion: (questionId: string) =>
    adminRequest<any>(`/admin/questions/${questionId}`, {
      method: "DELETE",
    }),

  // Coding Problems (1,000 problem bank)
  getCodingProblems: (params: {
    page?: number
    page_size?: number
    difficulty?: string
    topic?: string
    search?: string
  } = {}) => {
    const q = new URLSearchParams()
    if (params.page) q.set("page", params.page.toString())
    if (params.page_size) q.set("page_size", params.page_size.toString())
    if (params.difficulty) q.set("difficulty", params.difficulty)
    if (params.topic) q.set("topic", params.topic)
    if (params.search) q.set("search", params.search)
    return adminRequest<any>(`/admin/coding/problems?${q.toString()}`)
  },

  getCodingProblemDetail: (problemId: string) =>
    adminRequest<any>(`/admin/coding/problems/${problemId}`),

  // Companies
  getCompanies: (params: {
    page?: number
    page_size?: number
    industry?: string
    search?: string
  } = {}) => {
    const q = new URLSearchParams()
    if (params.page) q.set("page", params.page.toString())
    if (params.page_size) q.set("page_size", params.page_size.toString())
    if (params.industry) q.set("industry", params.industry)
    if (params.search) q.set("search", params.search)
    return adminRequest<any>(`/admin/companies?${q.toString()}`)
  },

  createCompany: (data: any) =>
    adminRequest<any>("/admin/companies", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateCompany: (companyId: string, data: any) =>
    adminRequest<any>(`/admin/companies/${companyId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteCompany: (companyId: string) =>
    adminRequest<any>(`/admin/companies/${companyId}`, {
      method: "DELETE",
    }),

  // Learning Resources
  getResources: (params: {
    page?: number
    page_size?: number
    topic?: string
    search?: string
  } = {}) => {
    const q = new URLSearchParams()
    if (params.page) q.set("page", params.page.toString())
    if (params.page_size) q.set("page_size", params.page_size.toString())
    if (params.topic) q.set("topic", params.topic)
    if (params.search) q.set("search", params.search)
    return adminRequest<any>(`/admin/resources?${q.toString()}`)
  },

  createResource: (data: any) =>
    adminRequest<any>("/admin/resources", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateResource: (resourceId: string, data: any) =>
    adminRequest<any>(`/admin/resources/${resourceId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteResource: (resourceId: string) =>
    adminRequest<any>(`/admin/resources/${resourceId}`, {
      method: "DELETE",
    }),

  // AI Agent Configurations
  getAIAgents: () => adminRequest<any[]>("/admin/ai-agents"),

  updateAIAgent: (agentId: string, data: any) =>
    adminRequest<any>(`/admin/ai-agents/${agentId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  // Resume ATS
  getResumes: (params: { page?: number; page_size?: number; search?: string } = {}) => {
    const q = new URLSearchParams()
    if (params.page) q.set("page", params.page.toString())
    if (params.page_size) q.set("page_size", params.page_size.toString())
    if (params.search) q.set("search", params.search)
    return adminRequest<any>(`/admin/resume-ats?${q.toString()}`)
  },

  // Subscriptions & Payments
  getSubscriptionPlans: () =>
    adminRequest<any[]>("/admin/subscriptions/plans"),

  createSubscriptionPlan: (data: any) =>
    adminRequest<any>("/admin/subscriptions/plans", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getPayments: (params: {
    page?: number
    page_size?: number
    status?: string
    search?: string
  } = {}) => {
    const q = new URLSearchParams()
    if (params.page) q.set("page", params.page.toString())
    if (params.page_size) q.set("page_size", params.page_size.toString())
    if (params.status) q.set("status", params.status)
    if (params.search) q.set("search", params.search)
    return adminRequest<any>(`/admin/payments?${q.toString()}`)
  },

  getCoupons: (params: { page?: number; page_size?: number } = {}) => {
    const q = new URLSearchParams()
    if (params.page) q.set("page", params.page.toString())
    if (params.page_size) q.set("page_size", params.page_size.toString())
    return adminRequest<any>(`/admin/coupons?${q.toString()}`)
  },

  createCoupon: (data: any) =>
    adminRequest<any>("/admin/coupons", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  toggleCoupon: (couponId: string) =>
    adminRequest<any>(`/admin/coupons/${couponId}/status`, {
      method: "PATCH",
    }),

  getInvoices: (params: { page?: number; page_size?: number } = {}) => {
    const q = new URLSearchParams()
    if (params.page) q.set("page", params.page.toString())
    if (params.page_size) q.set("page_size", params.page_size.toString())
    return adminRequest<any>(`/admin/invoices?${q.toString()}`)
  },

  // Support & Feedback
  getSupportTickets: (params: {
    page?: number
    page_size?: number
    status?: string
    priority?: string
    category?: string
  } = {}) => {
    const q = new URLSearchParams()
    if (params.page) q.set("page", params.page.toString())
    if (params.page_size) q.set("page_size", params.page_size.toString())
    if (params.status) q.set("status", params.status)
    if (params.priority) q.set("priority", params.priority)
    if (params.category) q.set("category", params.category)
    return adminRequest<any>(`/admin/support/tickets?${q.toString()}`)
  },

  getSupportTicketDetail: (ticketId: string) =>
    adminRequest<any>(`/admin/support/tickets/${ticketId}`),

  replySupportTicket: (ticketId: string, message: string, isInternal = false) => {
    const q = new URLSearchParams({
      message,
      is_internal: String(isInternal),
    })
    return adminRequest<any>(`/admin/support/tickets/${ticketId}/reply?${q.toString()}`, {
      method: "POST",
    })
  },

  updateSupportTicketStatus: (ticketId: string, status: string) => {
    const q = new URLSearchParams({ status })
    return adminRequest<any>(`/admin/support/tickets/${ticketId}/status?${q.toString()}`, {
      method: "PATCH",
    })
  },

  getFeedback: (params: {
    page?: number
    page_size?: number
    category?: string
    status?: string
  } = {}) => {
    const q = new URLSearchParams()
    if (params.page) q.set("page", params.page.toString())
    if (params.page_size) q.set("page_size", params.page_size.toString())
    if (params.category) q.set("category", params.category)
    if (params.status) q.set("status", params.status)
    return adminRequest<any>(`/admin/feedback?${q.toString()}`)
  },

  updateFeedbackStatus: (feedbackId: string, status: string, notes?: string) =>
    adminRequest<any>(`/admin/feedback/${feedbackId}`, {
      method: "PATCH",
      body: JSON.stringify({ status, resolution_notes: notes }),
    }),

  // Announcements / Broadcast Notifications
  broadcastNotification: (data: {
    title: string
    message: string
    target_role?: string
    priority?: string
  }) =>
    adminRequest<any>("/admin/notifications/broadcast", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Achievements
  getAchievements: () => adminRequest<any[]>("/admin/achievements"),

  createAchievement: (data: any) =>
    adminRequest<any>("/admin/achievements", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Audit Logs
  getAuditLogs: (params: {
    page?: number
    page_size?: number
    action?: string
    resource?: string
    actor_email?: string
  } = {}) => {
    const q = new URLSearchParams()
    if (params.page) q.set("page", params.page.toString())
    if (params.page_size) q.set("page_size", params.page_size.toString())
    if (params.action) q.set("action", params.action)
    if (params.resource) q.set("resource", params.resource)
    if (params.actor_email) q.set("actor_email", params.actor_email)
    return adminRequest<any>(`/admin/audit-logs?${q.toString()}`)
  },

  // Settings
  getSettings: () => adminRequest<any[]>("/admin/settings"),

  updateSetting: (key: string, value: any) =>
    adminRequest<any>(`/admin/settings/${key}`, {
      method: "PUT",
      body: JSON.stringify({ value }),
    }),

  // RBAC
  getRBACRoles: () => adminRequest<any[]>("/admin/rbac/roles"),

  updateRBACRole: (roleName: string, permissions: string[]) =>
    adminRequest<any>(`/admin/rbac/roles/${roleName}`, {
      method: "PUT",
      body: JSON.stringify({ permissions }),
    }),

  assignUserRole: (userId: string, role: string) =>
    adminRequest<any>("/admin/rbac/assign", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, role }),
    }),

  // Intelligence & Contests
  getRAGStatus: () => adminRequest<any>("/admin/rag/status"),

  getLearningStats: () => adminRequest<any>("/admin/learning/stats"),

  getContests: (params: { page?: number; page_size?: number } = {}) => {
    const q = new URLSearchParams()
    if (params.page) q.set("page", params.page.toString())
    if (params.page_size) q.set("page_size", params.page_size.toString())
    return adminRequest<any>(`/admin/contests?${q.toString()}`)
  },
}
