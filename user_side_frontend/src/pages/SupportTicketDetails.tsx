import React, { useState, useEffect, useRef, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  getSupportTicket,
  sendTicketMessage,
  closeSupportTicket,
  reopenSupportTicket,
} from "../services/api"
import type {
  SupportTicket,
  SupportTicketMessage,
} from "../services/api"
import { useWebSocketEvent } from "../hooks/useWebSocket"
import RealtimeStatusBadge from "../components/RealtimeStatusBadge"
import "./SupportTicketDetails.css"

export default function SupportTicketDetails() {
  const { ticketId } = useParams<{ ticketId: string }>()
  const navigate = useNavigate()

  const [ticket, setTicket] = useState<SupportTicket | null>(null)
  const [messages, setMessages] = useState<SupportTicketMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  // Reply state
  const [replyText, setReplyText] = useState("")
  const [sending, setSending] = useState(false)
  const [replyError, setReplyError] = useState("")

  // Action states
  const [actionLoading, setActionLoading] = useState(false)
  const [toastMsg, setToastMsg] = useState("")

  const messagesEndRef = useRef<HTMLDivElement | null>(null)

  const showToast = (msg: string) => {
    setToastMsg(msg)
    setTimeout(() => setToastMsg(""), 4000)
  }

  const loadTicketData = useCallback(async () => {
    if (!ticketId) return
    setLoading(true)
    setError("")
    try {
      const data = await getSupportTicket(ticketId)
      setTicket(data)
      setMessages(data.messages || [])
    } catch (err: any) {
      console.error("Failed to load ticket details:", err)
      setError(err.message || "Failed to load ticket details. The ticket may not exist or you lack permission.")
    } finally {
      setLoading(false)
    }
  }, [ticketId])

  useEffect(() => {
    loadTicketData()
  }, [loadTicketData])

  useEffect(() => {
    // Scroll to bottom of message list on update
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  // Real-time incoming message on this ticket
  useWebSocketEvent("support.ticket.message", (data: any) => {
    if (!data || data.ticket_id !== ticketId) return
    setMessages((prev) => {
      if (prev.some((m) => m.id === data.id)) return prev
      const incoming: SupportTicketMessage = {
        id: data.id,
        ticket_id: data.ticket_id,
        sender_id: data.sender_id,
        sender_name: data.sender_name,
        sender_type: data.sender_type,
        message: data.message,
        is_internal: data.is_internal || false,
        created_at: data.created_at || new Date().toISOString(),
        updated_at: data.created_at || new Date().toISOString(),
      }
      return [...prev, incoming]
    })
    if (data.ticket_status) {
      setTicket((prev) =>
        prev
          ? {
              ...prev,
              status: data.ticket_status,
              updated_at: data.created_at || prev.updated_at,
            }
          : prev
      )
    }
  })

  // Real-time status update on this ticket
  useWebSocketEvent("support.ticket.status", (data: any) => {
    if (!data || data.ticket_id !== ticketId) return
    setTicket((prev) =>
      prev
        ? {
            ...prev,
            status: data.status,
            updated_at: data.updated_at || prev.updated_at,
          }
        : prev
    )
    showToast(`Ticket status updated: ${(data.status ?? "").replace(/_/g, " ")}`)
  })

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!ticketId || !replyText.trim() || sending) return

    setSending(true)
    setReplyError("")
    try {
      const newMsg = await sendTicketMessage(ticketId, replyText.trim())
      setMessages((prev) => [...prev, newMsg])
      setReplyText("")
      // Update ticket updated_at
      if (ticket) {
        setTicket({
          ...ticket,
          updated_at: new Date().toISOString(),
          status: ticket.status === "closed" ? "open" : ticket.status,
        })
      }
    } catch (err: any) {
      setReplyError(err.message || "Failed to send message.")
    } finally {
      setSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleCloseTicket = async () => {
    if (!ticketId || actionLoading) return
    if (!window.confirm("Are you sure you want to mark this ticket as closed?")) return

    setActionLoading(true)
    try {
      const updated = await closeSupportTicket(ticketId)
      setTicket(updated)
      showToast("Ticket marked as closed.")
    } catch (err: any) {
      showToast(err.message || "Could not close ticket.")
    } finally {
      setActionLoading(false)
    }
  }

  const handleReopenTicket = async () => {
    if (!ticketId || actionLoading) return

    setActionLoading(true)
    try {
      const updated = await reopenSupportTicket(ticketId)
      setTicket(updated)
      showToast("Ticket reopened.")
    } catch (err: any) {
      showToast(err.message || "Could not reopen ticket.")
    } finally {
      setActionLoading(false)
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

  const formatStatus = (s?: string | null) => {
    return (s ?? "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) || "Open"
  }

  if (loading) {
    return (
      <div className="ticket-detail-page">
        <div className="ticket-detail-loading">
          <div className="ticket-detail-spinner"></div>
          <p>Loading ticket conversation...</p>
        </div>
      </div>
    )
  }

  if (error || !ticket) {
    return (
      <div className="ticket-detail-page">
        <div className="ticket-detail-error">
          <div className="ticket-detail-error-icon">⚠️</div>
          <h2>Ticket Not Accessible</h2>
          <p>{error || "We could not find the requested support ticket."}</p>
          <button
            className="ticket-detail-back-btn primary"
            onClick={() => navigate("/support/tickets")}
          >
            Return to My Tickets
          </button>
        </div>
      </div>
    )
  }

  const isClosed = ticket.status === "closed"

  return (
    <div className="ticket-detail-page">
      {/* Toast */}
      {toastMsg && <div className="ticket-detail-toast">{toastMsg}</div>}

      {/* Top Header */}
      <div className="ticket-detail-top-nav">
        <button
          className="ticket-detail-back-link"
          onClick={() => navigate("/support/tickets")}
        >
          ← Back to All Tickets
        </button>

        <div className="ticket-detail-top-actions">
          <RealtimeStatusBadge />
          {isClosed ? (
            <button
              className="ticket-action-btn reopen"
              onClick={handleReopenTicket}
              disabled={actionLoading}
            >
              🔄 Reopen Ticket
            </button>
          ) : (
            <button
              className="ticket-action-btn close"
              onClick={handleCloseTicket}
              disabled={actionLoading}
            >
              ✓ Mark as Closed
            </button>
          )}
        </div>
      </div>

      {/* Ticket Overview Banner */}
      <div className="ticket-banner-card">
        <div className="ticket-banner-left">
          <div className="ticket-banner-number-row">
            <span className="ticket-banner-number">{ticket.ticket_number}</span>
            <span className={`ticket-badge status ${getStatusBadgeClass(ticket.status)}`}>
              {formatStatus(ticket.status)}
            </span>
            <span className="ticket-badge priority">
              {(ticket.priority ?? "medium").toUpperCase()} PRIORITY
            </span>
            <span className="ticket-category-tag">{ticket.category || "General"}</span>
          </div>
          <h1 className="ticket-banner-title">{ticket.subject}</h1>
        </div>

        <div className="ticket-banner-meta">
          <div>
            <span className="meta-label">Created</span>
            <span className="meta-value">
              {new Date(ticket.created_at || Date.now()).toLocaleString()}
            </span>
          </div>
          <div>
            <span className="meta-label">Last Updated</span>
            <span className="meta-value">
              {new Date(ticket.updated_at || Date.now()).toLocaleString()}
            </span>
          </div>
          {ticket.resolved_at && (
            <div>
              <span className="meta-label">Resolved</span>
              <span className="meta-value">
                {new Date(ticket.resolved_at).toLocaleString()}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Conversation Thread */}
      <div className="ticket-thread-section">
        <div className="ticket-thread-header">
          <h3>Conversation History ({messages.length})</h3>
          <span className="ticket-thread-sub">
            All messages are securely stored and encrypted.
          </span>
        </div>

        <div className="ticket-messages-list">
          {messages.map((msg, index) => {
            const isCandidate = msg.sender_type === "candidate"
            const isSupport = msg.sender_type === "support" || msg.sender_type === "admin"

            return (
              <div
                key={msg.id || index}
                className={`ticket-message-wrapper ${isCandidate ? "candidate" : "support"}`}
              >
                <div className="ticket-message-avatar">
                  {isCandidate ? "👤" : "🛡️"}
                </div>

                <div className="ticket-message-bubble">
                  <div className="ticket-message-meta">
                    <span className="ticket-message-author">
                      {isCandidate ? "You (Candidate)" : msg.sender_name || "Support Engineer"}
                    </span>
                    {isSupport && (
                      <span className="ticket-support-verified-tag">Support Team</span>
                    )}
                    <span className="ticket-message-time">
                      {new Date(msg.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                        month: "short",
                        day: "numeric",
                      })}
                    </span>
                  </div>

                  <div className="ticket-message-body">
                    <p>{msg.message}</p>
                  </div>
                </div>
              </div>
            )
          })}
          <div ref={messagesEndRef} />
        </div>

        {/* Reply Composer */}
        <div className="ticket-reply-composer">
          {isClosed ? (
            <div className="ticket-closed-notice">
              <p>This ticket is currently marked as closed.</p>
              <button className="ticket-reopen-inline-btn" onClick={handleReopenTicket}>
                Reopen Ticket to reply
              </button>
            </div>
          ) : (
            <form onSubmit={handleSendMessage} className="ticket-reply-form">
              {replyError && <div className="ticket-reply-error">{replyError}</div>}

              <div className="ticket-reply-textarea-wrap">
                <textarea
                  className="ticket-reply-input"
                  placeholder="Type your reply here... (Ctrl + Enter to send)"
                  rows={3}
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={sending}
                />
              </div>

              <div className="ticket-reply-actions-row">
                <span className="ticket-reply-hint">Press Ctrl + Enter to submit</span>
                <button
                  type="submit"
                  className="ticket-send-btn"
                  disabled={sending || !replyText.trim()}
                >
                  {sending ? "Sending..." : "Send Reply →"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
