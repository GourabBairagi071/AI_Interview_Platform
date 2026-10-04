import React, { useState, useEffect, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import {
  getFAQs,
  getHelpArticles,
  getHelpArticle,
  createSupportTicket,
  submitFeedback,
} from "../services/api"
import type {
  FAQItem,
  HelpArticleItem,
  TicketCreateRequest,
  FeedbackCreateRequest,
} from "../services/api"
import "./SupportCenter.css"

export default function SupportCenter() {
  const navigate = useNavigate()

  // Data states
  const [faqs, setFaqs] = useState<FAQItem[]>([])
  const [articles, setArticles] = useState<HelpArticleItem[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedCategory, setSelectedCategory] = useState("all")
  const [expandedFaqId, setExpandedFaqId] = useState<string | null>(null)
  const [selectedArticle, setSelectedArticle] = useState<HelpArticleItem | null>(null)

  // Modals
  const [isTicketModalOpen, setIsTicketModalOpen] = useState(false)
  const [isFeedbackModalOpen, setIsFeedbackModalOpen] = useState(false)
  const [feedbackType, setFeedbackType] = useState<"feedback" | "bug_report">("feedback")

  // Ticket Form state
  const [ticketForm, setTicketForm] = useState<TicketCreateRequest>({
    subject: "",
    category: "Interview",
    priority: "medium",
    description: "",
  })
  const [ticketSubmitting, setTicketSubmitting] = useState(false)
  const [ticketError, setTicketError] = useState("")

  // Feedback Form state
  const [feedbackForm, setFeedbackForm] = useState<FeedbackCreateRequest>({
    category: "platform",
    rating: 5,
    message: "",
    page_context: window.location.pathname,
  })
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false)
  const [feedbackSuccess, setFeedbackSuccess] = useState(false)
  const [feedbackError, setFeedbackError] = useState("")

  // Toast
  const [toastMessage, setToastMessage] = useState("")

  const categories = [
    "all",
    "Account",
    "Interview",
    "Resume",
    "Coding",
    "Learning",
    "Payment",
    "Subscription",
    "Technical",
  ]

  useEffect(() => {
    loadContent()
  }, [])

  const loadContent = async () => {
    setLoading(true)
    try {
      const [faqData, articleData] = await Promise.all([
        getFAQs(),
        getHelpArticles(),
      ])
      setFaqs(Array.isArray(faqData) ? faqData : [])
      setArticles(Array.isArray(articleData) ? articleData : [])
    } catch (err) {
      console.error("Failed to load help center content:", err)
    } finally {
      setLoading(false)
    }
  }

  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(""), 4000)
  }

  // Filter FAQs based on category & search query
  const filteredFaqs = useMemo(() => {
    const q = (searchQuery ?? "").trim().toLowerCase()
    const selCat = (selectedCategory ?? "all").toLowerCase()

    return (faqs ?? []).filter((faq) => {
      if (!faq) return false
      const cat = (faq.category ?? "").toLowerCase()
      const matchesCategory = selCat === "all" || cat === selCat

      if (!matchesCategory) return false
      if (!q) return true

      const questionText = (faq.question ?? "").toLowerCase()
      const answerText = (faq.answer ?? "").toLowerCase()
      return questionText.includes(q) || answerText.includes(q)
    })
  }, [faqs, selectedCategory, searchQuery])

  // Filter Articles based on search query
  const filteredArticles = useMemo(() => {
    const q = (searchQuery ?? "").trim().toLowerCase()
    const selCat = (selectedCategory ?? "all").toLowerCase()

    return (articles ?? []).filter((art) => {
      if (!art) return false
      const cat = (art.category ?? "").toLowerCase()
      const matchesCategory = selCat === "all" || cat === selCat

      if (!matchesCategory) return false
      if (!q) return true

      const titleText = (art.title ?? "").toLowerCase()
      const contentText = (art.content ?? "").toLowerCase()
      return titleText.includes(q) || contentText.includes(q)
    })
  }, [articles, selectedCategory, searchQuery])

  const toggleFaq = (id: string) => {
    setExpandedFaqId((prev) => (prev === id ? null : id))
  }

  const handleOpenArticle = async (art: HelpArticleItem) => {
    setSelectedArticle(art)
    if (!art.content && art.slug) {
      try {
        const fullArticle = await getHelpArticle(art.slug)
        if (fullArticle) {
          setSelectedArticle(fullArticle)
        }
      } catch (err) {
        console.error("Failed to load article detail:", err)
      }
    }
  }

  // Handle Ticket Submission
  const handleTicketSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!(ticketForm.subject ?? "").trim() || !(ticketForm.description ?? "").trim()) {
      setTicketError("Please fill out both subject and description.")
      return
    }

    setTicketSubmitting(true)
    setTicketError("")
    try {
      const created = await createSupportTicket(ticketForm)
      setIsTicketModalOpen(false)
      setTicketForm({
        subject: "",
        category: "Interview",
        priority: "medium",
        description: "",
      })
      showToast(`Support Ticket ${created.ticket_number} created successfully!`)
      // Redirect to newly created ticket
      setTimeout(() => {
        navigate(`/support/tickets/${created.id}`)
      }, 800)
    } catch (err: any) {
      setTicketError(err.message || "Failed to create support ticket. Please try again.")
    } finally {
      setTicketSubmitting(false)
    }
  }

  // Handle Feedback / Bug Report Submission
  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!(feedbackForm.message ?? "").trim()) {
      setFeedbackError("Please provide a message or description.")
      return
    }

    setFeedbackSubmitting(true)
    setFeedbackError("")
    try {
      const payload: FeedbackCreateRequest = {
        ...feedbackForm,
        category: feedbackType === "bug_report" ? "bug_report" : feedbackForm.category,
      }
      await submitFeedback(payload)
      setFeedbackSuccess(true)
      setTimeout(() => {
        setIsFeedbackModalOpen(false)
        setFeedbackSuccess(false)
        setFeedbackForm({
          category: "platform",
          rating: 5,
          message: "",
          page_context: window.location.pathname,
        })
        showToast(
          feedbackType === "bug_report"
            ? "Bug report submitted. Thank you for helping us improve!"
            : "Feedback submitted. Thank you for your review!",
        )
      }, 1000)
    } catch (err: any) {
      setFeedbackError(err.message || "Failed to submit feedback. Please try again.")
    } finally {
      setFeedbackSubmitting(false)
    }
  }

  const openBugReportModal = () => {
    setFeedbackType("bug_report")
    setFeedbackForm((prev) => ({
      ...prev,
      category: "bug_report",
      rating: 3,
      page_context: window.location.pathname,
    }))
    setIsFeedbackModalOpen(true)
  }

  const openFeedbackModal = () => {
    setFeedbackType("feedback")
    setFeedbackForm((prev) => ({
      ...prev,
      category: "platform",
      rating: 5,
      page_context: window.location.pathname,
    }))
    setIsFeedbackModalOpen(true)
  }

  return (
    <div className="support-page-container">
      {/* Toast Notification */}
      {toastMessage && <div className="support-toast">{toastMessage}</div>}

      {/* Top Navigation Bar */}
      <div className="support-top-nav">
        <button className="support-back-btn" onClick={() => navigate("/dashboard")}>
          ← Back to Dashboard
        </button>
        <div className="support-nav-actions">
          <button
            className="support-nav-btn secondary"
            onClick={() => navigate("/notifications")}
          >
            🔔 Notifications
          </button>
          <button
            className="support-nav-btn primary"
            onClick={() => navigate("/support/tickets")}
          >
            🎫 My Tickets
          </button>
        </div>
      </div>

      {/* Hero Section */}
      <div className="support-hero">
        <div className="support-hero-badge">HELP CENTER & SUPPORT</div>
        <h1 className="support-hero-title">How can we help you today?</h1>
        <p className="support-hero-subtitle">
          Search our knowledge base, explore frequently asked questions, or connect with our support team.
        </p>

        {/* Global Search Bar */}
        <div className="support-search-wrapper">
          <span className="support-search-icon">🔍</span>
          <input
            type="text"
            className="support-search-input"
            placeholder="Search questions, interview guides, billing, or technical issues..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button className="support-search-clear" onClick={() => setSearchQuery("")}>
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Quick Action Cards */}
      <div className="support-actions-grid">
        <div className="support-action-card" onClick={() => setIsTicketModalOpen(true)}>
          <div className="support-action-icon blue">🎫</div>
          <div className="support-action-content">
            <h3>Create Support Ticket</h3>
            <p>Open a new inquiry for personalized help from our engineering and support specialists.</p>
          </div>
          <span className="support-action-arrow">→</span>
        </div>

        <div className="support-action-card" onClick={() => navigate("/support/tickets")}>
          <div className="support-action-icon purple">💬</div>
          <div className="support-action-content">
            <h3>My Support Tickets</h3>
            <p>Track the progress of your active tickets, review responses, and reply to support agents.</p>
          </div>
          <span className="support-action-arrow">→</span>
        </div>

        <div className="support-action-card" onClick={openFeedbackModal}>
          <div className="support-action-icon green">⭐</div>
          <div className="support-action-content">
            <h3>Candidate Feedback</h3>
            <p>Rate your experience with AI interviews, coding challenges, or learning roadmaps.</p>
          </div>
          <span className="support-action-arrow">→</span>
        </div>

        <div className="support-action-card" onClick={openBugReportModal}>
          <div className="support-action-icon amber">🐞</div>
          <div className="support-action-content">
            <h3>Report a Bug</h3>
            <p>Discovered an issue? Let us know with context and we will investigate immediately.</p>
          </div>
          <span className="support-action-arrow">→</span>
        </div>
      </div>

      {/* Category Filter Pills */}
      <div className="support-categories-section">
        <div className="support-category-pills">
          {categories.map((cat) => (
            <button
              key={cat}
              className={`support-category-pill ${selectedCategory.toLowerCase() === cat.toLowerCase() ? "active" : ""}`}
              onClick={() => setSelectedCategory(cat.toLowerCase())}
            >
              {cat === "all" ? "All Categories" : cat}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Layout: FAQs and Guides */}
      <div className="support-main-layout">
        {/* Left Column: FAQs Accordion */}
        <div className="support-section faqs-section">
          <div className="support-section-header">
            <h2>Frequently Asked Questions</h2>
            <span className="support-section-count">{filteredFaqs.length} questions</span>
          </div>

          {loading ? (
            <div className="support-loading-state">
              <div className="support-spinner"></div>
              <p>Loading help content...</p>
            </div>
          ) : filteredFaqs.length === 0 ? (
            <div className="support-empty-state">
              <div className="support-empty-icon">❓</div>
              <h3>No matching questions found</h3>
              <p>Try searching for a different keyword or create a support ticket directly.</p>
              <button
                className="support-create-ticket-cta"
                onClick={() => setIsTicketModalOpen(true)}
              >
                Create Support Ticket
              </button>
            </div>
          ) : (
            <div className="support-faq-list">
              {filteredFaqs.map((faq) => {
                const isExpanded = expandedFaqId === faq.id
                return (
                  <div
                    key={faq.id}
                    className={`support-faq-item ${isExpanded ? "expanded" : ""}`}
                    onClick={() => toggleFaq(faq.id)}
                  >
                    <div className="support-faq-question-row">
                      <div className="support-faq-q-left">
                        <span className="support-faq-category-tag">{faq.category}</span>
                        <h4 className="support-faq-question">{faq.question}</h4>
                      </div>
                      <span className="support-faq-chevron">{isExpanded ? "▲" : "▼"}</span>
                    </div>
                    {isExpanded && (
                      <div className="support-faq-answer">
                        <p>{faq.answer}</p>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Right Column: Knowledge Base & Guides */}
        <div className="support-section guides-section">
          <div className="support-section-header">
            <h2>Guides & Knowledge Base</h2>
            <span className="support-section-count">{filteredArticles.length} guides</span>
          </div>

          {filteredArticles.length === 0 ? (
            <div className="support-empty-state mini">
              <p>No guides match current filters.</p>
            </div>
          ) : (
            <div className="support-articles-list">
              {filteredArticles.map((art) => {
                const rawContent = art.content ?? ""
                const cleanContent = rawContent.replace(/#|\*|`/g, "").trim()
                const snippet =
                  cleanContent.length > 0
                    ? cleanContent.slice(0, 110) + (cleanContent.length > 110 ? "..." : "")
                    : "Click to read the complete guide..."

                return (
                  <div
                    key={art.id || art.slug}
                    className="support-article-card"
                    onClick={() => handleOpenArticle(art)}
                  >
                    <div className="support-article-meta">
                      <span className="support-article-tag">{art.category || "Guide"}</span>
                      <span className="support-article-date">
                        {new Date(art.created_at || Date.now()).toLocaleDateString()}
                      </span>
                    </div>
                    <h4 className="support-article-title">{art.title || "Help Guide"}</h4>
                    <p className="support-article-snippet">{snippet}</p>
                    <span className="support-article-readmore">Read full guide →</span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* CREATE TICKET MODAL */}
      {isTicketModalOpen && (
        <div className="support-modal-backdrop" onClick={() => setIsTicketModalOpen(false)}>
          <div className="support-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="support-modal-header">
              <div className="support-modal-title-row">
                <span className="support-modal-icon">🎫</span>
                <h3>Create Support Ticket</h3>
              </div>
              <button
                className="support-modal-close"
                onClick={() => setIsTicketModalOpen(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleTicketSubmit} className="support-ticket-form">
              {ticketError && <div className="support-form-error">{ticketError}</div>}

              <div className="support-form-group">
                <label>Subject *</label>
                <input
                  type="text"
                  placeholder="Summary of the issue or question"
                  value={ticketForm.subject}
                  onChange={(e) => setTicketForm({ ...ticketForm, subject: e.target.value })}
                  required
                />
              </div>

              <div className="support-form-row">
                <div className="support-form-group half">
                  <label>Category *</label>
                  <select
                    value={ticketForm.category}
                    onChange={(e) => setTicketForm({ ...ticketForm, category: e.target.value })}
                  >
                    <option value="Account">Account</option>
                    <option value="Interview">Interview</option>
                    <option value="Resume">Resume</option>
                    <option value="Coding">Coding</option>
                    <option value="Learning">Learning</option>
                    <option value="Payment">Payment</option>
                    <option value="Subscription">Subscription</option>
                    <option value="Technical Issue">Technical Issue</option>
                    <option value="Bug Report">Bug Report</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                <div className="support-form-group half">
                  <label>Priority</label>
                  <select
                    value={ticketForm.priority}
                    onChange={(e) => setTicketForm({ ...ticketForm, priority: e.target.value })}
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
              </div>

              <div className="support-form-group">
                <label>Detailed Description *</label>
                <textarea
                  rows={5}
                  placeholder="Provide details, steps to reproduce, or relevant background so we can resolve this quickly."
                  value={ticketForm.description}
                  onChange={(e) =>
                    setTicketForm({ ...ticketForm, description: e.target.value })
                  }
                  required
                />
              </div>

              <div className="support-form-actions">
                <button
                  type="button"
                  className="support-btn-cancel"
                  onClick={() => setIsTicketModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="support-btn-submit"
                  disabled={ticketSubmitting}
                >
                  {ticketSubmitting ? "Submitting..." : "Submit Ticket"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* FEEDBACK / BUG REPORT MODAL */}
      {isFeedbackModalOpen && (
        <div className="support-modal-backdrop" onClick={() => setIsFeedbackModalOpen(false)}>
          <div className="support-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="support-modal-header">
              <div className="support-modal-title-row">
                <span className="support-modal-icon">
                  {feedbackType === "bug_report" ? "🐞" : "⭐"}
                </span>
                <h3>{feedbackType === "bug_report" ? "Report a Bug" : "Platform Feedback"}</h3>
              </div>
              <button
                className="support-modal-close"
                onClick={() => setIsFeedbackModalOpen(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleFeedbackSubmit} className="support-ticket-form">
              {feedbackError && <div className="support-form-error">{feedbackError}</div>}
              {feedbackSuccess && (
                <div className="support-form-success">
                  ✓ Submitted successfully! Thank you for your feedback.
                </div>
              )}

              {feedbackType === "feedback" && (
                <div className="support-form-group">
                  <label>Overall Experience Rating</label>
                  <div className="support-rating-stars">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        type="button"
                        key={star}
                        className={`support-star-btn ${feedbackForm.rating >= star ? "active" : ""}`}
                        onClick={() => setFeedbackForm({ ...feedbackForm, rating: star })}
                      >
                        ★
                      </button>
                    ))}
                    <span className="support-rating-label">
                      {feedbackForm.rating} / 5
                    </span>
                  </div>
                </div>
              )}

              <div className="support-form-row">
                <div className="support-form-group half">
                  <label>Area / Module</label>
                  <select
                    value={feedbackForm.category}
                    onChange={(e) =>
                      setFeedbackForm({ ...feedbackForm, category: e.target.value })
                    }
                  >
                    <option value="platform">General Platform</option>
                    <option value="interview">AI Mock Interview</option>
                    <option value="coding">Coding Arena</option>
                    <option value="learning">Personalized Learning</option>
                    <option value="resume">Resume Intelligence</option>
                    <option value="payment">Payment & Billing</option>
                    <option value="support">Help & Support</option>
                    {feedbackType === "bug_report" && (
                      <option value="bug_report">Bug Report</option>
                    )}
                  </select>
                </div>

                <div className="support-form-group half">
                  <label>Page Context</label>
                  <input
                    type="text"
                    placeholder="/interview/setup"
                    value={feedbackForm.page_context || ""}
                    onChange={(e) =>
                      setFeedbackForm({ ...feedbackForm, page_context: e.target.value })
                    }
                  />
                </div>
              </div>

              <div className="support-form-group">
                <label>
                  {feedbackType === "bug_report"
                    ? "Bug Description & Expected Behavior *"
                    : "Feedback & Suggestions *"}
                </label>
                <textarea
                  rows={4}
                  placeholder={
                    feedbackType === "bug_report"
                      ? "Describe what happened, error message, or steps to reproduce..."
                      : "Tell us what you loved or how we can make your preparation more impactful..."
                  }
                  value={feedbackForm.message}
                  onChange={(e) =>
                    setFeedbackForm({ ...feedbackForm, message: e.target.value })
                  }
                  required
                />
              </div>

              <div className="support-form-actions">
                <button
                  type="button"
                  className="support-btn-cancel"
                  onClick={() => setIsFeedbackModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="support-btn-submit"
                  disabled={feedbackSubmitting}
                >
                  {feedbackSubmitting ? "Submitting..." : "Send Feedback"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ARTICLE READER MODAL */}
      {selectedArticle && (
        <div className="support-modal-backdrop" onClick={() => setSelectedArticle(null)}>
          <div
            className="support-modal-card article-reader"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="support-modal-header">
              <div>
                <span className="support-article-tag">{selectedArticle.category || "Guide"}</span>
                <h3 className="support-reader-title">{selectedArticle.title || "Help Guide"}</h3>
              </div>
              <button
                className="support-modal-close"
                onClick={() => setSelectedArticle(null)}
              >
                ✕
              </button>
            </div>
            <div className="support-reader-content">
              <pre className="support-article-body">
                {selectedArticle.content || "Loading complete guide content..."}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
