import React, { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import {
  getSupportTickets,
  createSupportTicket,
} from "../services/api"
import type {
  SupportTicket,
  TicketCreateRequest,
} from "../services/api"
import "./SupportTickets.css"

export default function SupportTickets() {
  const navigate = useNavigate()

  const [tickets, setTickets] = useState<SupportTicket[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  // Filters
  const [statusFilter, setStatusFilter] = useState("all")
  const [categoryFilter, setCategoryFilter] = useState("all")

  // Create Ticket Modal
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [ticketForm, setTicketForm] = useState<TicketCreateRequest>({
    subject: "",
    category: "Technical Issue",
    priority: "medium",
    description: "",
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState("")
  const [toastMsg, setToastMsg] = useState("")

  const loadTickets = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      const res = await getSupportTickets(statusFilter, categoryFilter)
      setTickets(res.tickets)
      setTotal(res.total)
    } catch (err: any) {
      console.error("Failed to load tickets:", err)
      setError(err.message || "Failed to load support tickets.")
    } finally {
      setLoading(false)
    }
  }, [statusFilter, categoryFilter])

  useEffect(() => {
    loadTickets()
  }, [loadTickets])

  const showToast = (msg: string) => {
    setToastMsg(msg)
    setTimeout(() => setToastMsg(""), 4000)
  }

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!ticketForm.subject.trim() || !ticketForm.description.trim()) {
      setFormError("Please fill out both subject and description.")
      return
    }

    setIsSubmitting(true)
    setFormError("")
    try {
      const created = await createSupportTicket(ticketForm)
      setIsModalOpen(false)
      setTicketForm({
        subject: "",
        category: "Technical Issue",
        priority: "medium",
        description: "",
      })
      showToast(`Ticket ${created.ticket_number} created successfully!`)
      // Refresh tickets
      loadTickets()
      // Navigate to details
      navigate(`/support/tickets/${created.id}`)
    } catch (err: any) {
      setFormError(err.message || "Failed to create ticket. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  const getStatusBadgeClass = (status?: string | null) => {
    switch ((status ?? "").toLowerCase()) {
      case "open":
        return "badge-status-open"
      case "in_progress":
        return "badge-status-progress"
      case "waiting_for_user":
        return "badge-status-waiting"
      case "resolved":
        return "badge-status-resolved"
      case "closed":
        return "badge-status-closed"
      default:
        return "badge-status-default"
    }
  }

  const getPriorityBadgeClass = (priority?: string | null) => {
    switch ((priority ?? "").toLowerCase()) {
      case "urgent":
        return "badge-priority-urgent"
      case "high":
        return "badge-priority-high"
      case "medium":
        return "badge-priority-medium"
      case "low":
        return "badge-priority-low"
      default:
        return ""
    }
  }

  const formatStatus = (s?: string | null) => {
    return (s ?? "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) || "Open"
  }

  return (
    <div className="tickets-page-container">
      {/* Toast */}
      {toastMsg && <div className="tickets-toast">{toastMsg}</div>}

      {/* Navigation Header */}
      <div className="tickets-top-bar">
        <button className="tickets-back-btn" onClick={() => navigate("/support")}>
          ← Back to Help Center
        </button>
        <button
          className="tickets-create-btn"
          onClick={() => setIsModalOpen(true)}
        >
          + Open New Ticket
        </button>
      </div>

      {/* Page Title & Stats */}
      <div className="tickets-header-section">
        <div>
          <h1 className="tickets-header-title">My Support Tickets</h1>
          <p className="tickets-header-subtitle">
            Track communication with support engineers, review replies, and resolve queries.
          </p>
        </div>
        <div className="tickets-stats-counter">
          <span className="tickets-count-number">{total}</span>
          <span className="tickets-count-label">Total Tickets</span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="tickets-filter-bar">
        <div className="tickets-filter-group">
          <label>Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="tickets-filter-select"
          >
            <option value="all">All Statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="waiting_for_user">Waiting for Candidate</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
        </div>

        <div className="tickets-filter-group">
          <label>Category:</label>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="tickets-filter-select"
          >
            <option value="all">All Categories</option>
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
      </div>

      {/* Tickets List Area */}
      {loading ? (
        <div className="tickets-loading-card">
          <div className="tickets-spinner"></div>
          <p>Loading your support tickets...</p>
        </div>
      ) : error ? (
        <div className="tickets-error-card">
          <p>{error}</p>
          <button className="tickets-retry-btn" onClick={loadTickets}>
            Retry
          </button>
        </div>
      ) : tickets.length === 0 ? (
        <div className="tickets-empty-card">
          <div className="tickets-empty-icon">📂</div>
          <h3>No support tickets found</h3>
          <p>
            {statusFilter !== "all" || categoryFilter !== "all"
              ? "No tickets match your selected filters. Try clearing filters or open a new ticket."
              : "You have not opened any support inquiries yet. Need help with an interview or subscription?"}
          </p>
          <button
            className="tickets-create-btn"
            onClick={() => setIsModalOpen(true)}
          >
            + Create Support Ticket
          </button>
        </div>
      ) : (
        <div className="tickets-grid">
          {tickets.map((t) => (
            <div
              key={t.id}
              className="ticket-card"
              onClick={() => navigate(`/support/tickets/${t.id}`)}
            >
              <div className="ticket-card-header">
                <span className="ticket-number-badge">{t.ticket_number}</span>
                <div className="ticket-badges-group">
                  <span className={`ticket-badge priority ${getPriorityBadgeClass(t.priority)}`}>
                    {(t.priority ?? "medium").toUpperCase()}
                  </span>
                  <span className={`ticket-badge status ${getStatusBadgeClass(t.status)}`}>
                    {formatStatus(t.status)}
                  </span>
                </div>
              </div>

              <h3 className="ticket-subject">{t.subject}</h3>
              {t.description && (
                <p className="ticket-description-preview">
                  {(t.description ?? "").slice(0, 140)}
                  {(t.description ?? "").length > 140 ? "..." : ""}
                </p>
              )}

              <div className="ticket-footer">
                <div className="ticket-meta-info">
                  <span className="ticket-category-tag">{t.category}</span>
                  <span className="ticket-timestamp">
                    Created {new Date(t.created_at || Date.now()).toLocaleDateString()}
                  </span>
                </div>
                <div className="ticket-replies-count">
                  💬 {t.message_count ?? 1} {(t.message_count ?? 1) === 1 ? "message" : "messages"}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* CREATE TICKET MODAL */}
      {isModalOpen && (
        <div className="tickets-modal-backdrop" onClick={() => setIsModalOpen(false)}>
          <div className="tickets-modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="tickets-modal-header">
              <div className="tickets-modal-title">
                <span className="tickets-modal-icon">🎫</span>
                <h3>Open Support Ticket</h3>
              </div>
              <button
                className="tickets-modal-close"
                onClick={() => setIsModalOpen(false)}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="tickets-modal-form">
              {formError && <div className="tickets-form-error">{formError}</div>}

              <div className="tickets-form-group">
                <label>Subject *</label>
                <input
                  type="text"
                  placeholder="Concise summary of your inquiry"
                  value={ticketForm.subject}
                  onChange={(e) =>
                    setTicketForm({ ...ticketForm, subject: e.target.value })
                  }
                  required
                />
              </div>

              <div className="tickets-form-row">
                <div className="tickets-form-group half">
                  <label>Category</label>
                  <select
                    value={ticketForm.category}
                    onChange={(e) =>
                      setTicketForm({ ...ticketForm, category: e.target.value })
                    }
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

                <div className="tickets-form-group half">
                  <label>Priority</label>
                  <select
                    value={ticketForm.priority}
                    onChange={(e) =>
                      setTicketForm({ ...ticketForm, priority: e.target.value })
                    }
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
              </div>

              <div className="tickets-form-group">
                <label>Detailed Description *</label>
                <textarea
                  rows={5}
                  placeholder="Provide context, what you were doing, error text, or questions..."
                  value={ticketForm.description}
                  onChange={(e) =>
                    setTicketForm({ ...ticketForm, description: e.target.value })
                  }
                  required
                />
              </div>

              <div className="tickets-modal-actions">
                <button
                  type="button"
                  className="tickets-cancel-btn"
                  onClick={() => setIsModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="tickets-submit-btn"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? "Submitting..." : "Submit Ticket"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
