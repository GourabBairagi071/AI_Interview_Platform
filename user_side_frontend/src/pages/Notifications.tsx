import { useCallback, useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  deleteNotification,
  getNotifications,
  getUnreadNotificationCount,
  markAllNotificationsAsRead,
  markNotificationAsRead,
  type NotificationItem,
} from "../services/api"
import "./Notifications.css"

const CATEGORIES = [
  { id: "all", label: "All" },
  { id: "unread", label: "Unread" },
  { id: "achievements", label: "Achievements" },
  { id: "practice", label: "Practice" },
  { id: "progress", label: "Progress" },
  { id: "interviews", label: "Interviews" },
  { id: "system", label: "System" },
]

function formatTimeAgo(isoString: string): string {
  try {
    const date = new Date(isoString)
    const now = new Date()
    const diffSec = Math.floor((now.getTime() - date.getTime()) / 1000)
    if (diffSec < 60) return "Just now"
    const diffMin = Math.floor(diffSec / 60)
    if (diffMin < 60) return `${diffMin}m ago`
    const diffHours = Math.floor(diffMin / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
  } catch {
    return isoString
  }
}

export default function Notifications() {
  const navigate = useNavigate()

  const [mobileMenu, setMobileMenu] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState("all")
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [limit] = useState(20)

  // Loading & error states
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [markingAll, setMarkingAll] = useState(false)

  // ------------------------------------------------------------
  // LOAD NOTIFICATIONS & UNREAD COUNT
  // ------------------------------------------------------------
  const loadNotificationsData = useCallback(
    async (currentPage = page, category = selectedCategory) => {
      setLoading(true)
      setError("")
      try {
        const isUnreadTab = category === "unread"
        const catFilter = isUnreadTab ? undefined : category !== "all" ? category : undefined

        const [listRes, countRes] = await Promise.all([
          getNotifications({
            page: currentPage,
            limit,
            unread_only: isUnreadTab,
            category: catFilter,
          }),
          getUnreadNotificationCount().catch(() => ({ unread_count: 0 })),
        ])

        setNotifications(listRes.notifications)
        setTotal(listRes.total)
        setHasNext(listRes.has_next)
        setUnreadCount(countRes.unread_count)
      } catch (err) {
        console.error("Failed to load notifications:", err)
        setError("Couldn't load notifications. Please check your connection.")
      } finally {
        setLoading(false)
      }
    },
    [page, selectedCategory, limit]
  )

  useEffect(() => {
    void loadNotificationsData(page, selectedCategory)
  }, [page, selectedCategory, loadNotificationsData])

  // ------------------------------------------------------------
  // TAB SWITCHING
  // ------------------------------------------------------------
  const handleCategoryChange = (catId: string) => {
    setSelectedCategory(catId)
    setPage(1)
  }

  // ------------------------------------------------------------
  // MARK SINGLE AS READ
  // ------------------------------------------------------------
  const handleMarkAsRead = async (item: NotificationItem, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    if (item.is_read) return

    // Optimistic UI update
    setNotifications((prev) =>
      prev.map((n) => (n.id === item.id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n))
    )
    setUnreadCount((prev) => Math.max(0, prev - 1))

    try {
      await markNotificationAsRead(item.id)
    } catch (err) {
      console.error("Failed to mark notification as read:", err)
      // Revert if error
      setNotifications((prev) =>
        prev.map((n) => (n.id === item.id ? { ...n, is_read: false } : n))
      )
      setUnreadCount((prev) => prev + 1)
    }
  }

  // ------------------------------------------------------------
  // MARK ALL AS READ
  // ------------------------------------------------------------
  const handleMarkAllAsRead = async () => {
    if (unreadCount === 0 || markingAll) return
    setMarkingAll(true)

    // Optimistic update
    const prevNotifications = [...notifications]
    const prevCount = unreadCount

    setNotifications((prev) =>
      prev.map((n) => ({ ...n, is_read: true, read_at: new Date().toISOString() }))
    )
    setUnreadCount(0)

    try {
      await markAllNotificationsAsRead()
    } catch (err) {
      console.error("Failed to mark all notifications as read:", err)
      // Revert
      setNotifications(prevNotifications)
      setUnreadCount(prevCount)
    } finally {
      setMarkingAll(false)
    }
  }

  // ------------------------------------------------------------
  // DELETE NOTIFICATION
  // ------------------------------------------------------------
  const handleDeleteNotification = async (item: NotificationItem, e: React.MouseEvent) => {
    e.stopPropagation()
    const wasUnread = !item.is_read

    // Optimistic remove
    setNotifications((prev) => prev.filter((n) => n.id !== item.id))
    setTotal((prev) => Math.max(0, prev - 1))
    if (wasUnread) {
      setUnreadCount((prev) => Math.max(0, prev - 1))
    }

    try {
      await deleteNotification(item.id)
    } catch (err) {
      console.error("Failed to delete notification:", err)
      // Refresh to restore accurate state
      void loadNotificationsData(page, selectedCategory)
    }
  }

  // ------------------------------------------------------------
  // CARD CLICK & ACTION
  // ------------------------------------------------------------
  const handleCardClick = (item: NotificationItem) => {
    if (!item.is_read) {
      void handleMarkAsRead(item)
    }
    if (item.action_url) {
      navigate(item.action_url)
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / limit))

  return (
    <div className="notif-shell">
      {/* ======================================================
          SIDEBAR NAVIGATION
      ====================================================== */}
      <aside className={`notif-sidebar ${mobileMenu ? "mobile-open" : ""}`}>
        <div className="sidebar-brand">
          <div className="brand-logo">
            <span>AI</span>
          </div>
          <div className="brand-name">
            <strong>AI Interview</strong>
            <span>Platform</span>
          </div>
          <button
            type="button"
            className="collapse-button"
            onClick={() => setMobileMenu(false)}
            aria-label="Close sidebar"
          >
            ‹
          </button>
        </div>

        <nav className="sidebar-menu">
          <button
            type="button"
            className="notif-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/dashboard")
            }}
          >
            <span className="nav-icon">▦</span>
            <span>Dashboard</span>
          </button>

          <button
            type="button"
            className="notif-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/resume")
            }}
          >
            <span className="nav-icon">▤</span>
            <span>Resume Analyzer</span>
          </button>

          <button
            type="button"
            className="notif-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/interview-setup")
            }}
          >
            <span className="nav-icon">♙</span>
            <span>AI Interview</span>
          </button>

          <button
            type="button"
            className="notif-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/performance")
            }}
          >
            <span className="nav-icon">▥</span>
            <span>Performance</span>
          </button>

          <button
            type="button"
            className="notif-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/practice")
            }}
          >
            <span className="nav-icon">✎</span>
            <span>Question Practice</span>
          </button>

          <button
            type="button"
            className="notif-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/achievements")
            }}
          >
            <span className="nav-icon">🏆</span>
            <span>Achievements</span>
          </button>

          <button
            type="button"
            className="notif-nav-link active"
            onClick={() => setMobileMenu(false)}
          >
            <span className="nav-icon">🔔</span>
            <span>Notifications</span>
            {unreadCount > 0 && (
              <span className="sidebar-unread-pill">{unreadCount > 99 ? "99+" : unreadCount}</span>
            )}
          </button>

          <button
            type="button"
            className="notif-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/profile")
            }}
          >
            <span className="nav-icon">👤</span>
            <span>Profile</span>
          </button>

          <button
            type="button"
            className="notif-nav-link"
            onClick={() => {
              setMobileMenu(false)
              navigate("/settings")
            }}
          >
            <span className="nav-icon">⚙</span>
            <span>Settings</span>
          </button>
        </nav>

        {/* QUICK PRACTICE CARD */}
        <div className="notif-quick-card">
          <div className="quick-icon">🎯</div>
          <h3>Practice &amp; Learn</h3>
          <p>Solve questions in Practice 2.0 to unlock achievements and level milestones.</p>
          <button
            type="button"
            onClick={() => {
              setMobileMenu(false)
              navigate("/practice")
            }}
          >
            Go to Practice <span>→</span>
          </button>
        </div>
      </aside>

      {/* ======================================================
          MAIN NOTIFICATIONS CONTENT
      ====================================================== */}
      <main className="notif-main">
        {/* TOP BAR */}
        <div className="notif-topbar">
          <button
            type="button"
            className="mobile-toggle"
            onClick={() => setMobileMenu((prev) => !prev)}
            aria-label="Open mobile menu"
          >
            ☰
          </button>

          <div className="breadcrumb">
            <span onClick={() => navigate("/dashboard")}>Dashboard</span>
            <span className="separator">/</span>
            <span className="current">Notifications</span>
          </div>

          <div className="topbar-actions">
            <button
              type="button"
              className="action-btn back-btn"
              onClick={() => navigate("/dashboard")}
            >
              ← Back to Dashboard
            </button>
          </div>
        </div>

        {/* NOTIFICATIONS HEADER BANNER */}
        <header className="notif-header">
          <div className="notif-header-content">
            <div className="title-row">
              <h1>Notifications</h1>
              {unreadCount > 0 ? (
                <span className="unread-badge-pill" id="unread-count-badge">
                  {unreadCount} unread
                </span>
              ) : (
                <span className="all-read-badge-pill">All caught up</span>
              )}
            </div>
            <p className="notif-subtitle">
              Stay updated with your progress, achievements, interviews and activity.
            </p>
          </div>

          <div className="notif-header-actions">
            <button
              type="button"
              id="mark-all-read-btn"
              className={`mark-all-btn ${unreadCount === 0 ? "disabled" : ""}`}
              onClick={handleMarkAllAsRead}
              disabled={unreadCount === 0 || markingAll}
            >
              ✓ Mark all as read
            </button>
          </div>
        </header>

        {/* CATEGORY TABS */}
        <section className="notif-tabs-bar" aria-label="Notification Categories">
          <div className="tabs-container">
            {CATEGORIES.map((cat) => {
              const isActive = selectedCategory === cat.id
              return (
                <button
                  key={cat.id}
                  type="button"
                  id={`tab-${cat.id}`}
                  className={`tab-btn ${isActive ? "active" : ""}`}
                  onClick={() => handleCategoryChange(cat.id)}
                >
                  {cat.label}
                  {cat.id === "unread" && unreadCount > 0 && (
                    <span className="tab-count">{unreadCount}</span>
                  )}
                </button>
              )
            })}
          </div>
        </section>

        {/* NOTIFICATION LIST SECTION */}
        <section className="notif-list-section">
          {/* LOADING STATE */}
          {loading && (
            <div className="notif-loading-list">
              {[1, 2, 3, 4, 5].map((idx) => (
                <div key={idx} className="notif-skeleton-card">
                  <div className="skeleton-icon" />
                  <div className="skeleton-content">
                    <div className="skeleton-line-title" />
                    <div className="skeleton-line-body" />
                  </div>
                  <div className="skeleton-meta" />
                </div>
              ))}
            </div>
          )}

          {/* ERROR STATE */}
          {!loading && error && (
            <div className="notif-error-state">
              <div className="error-icon">⚠️</div>
              <h3>Couldn't load notifications</h3>
              <p>{error}</p>
              <button
                type="button"
                className="retry-btn"
                onClick={() => void loadNotificationsData(page, selectedCategory)}
              >
                ↻ Retry
              </button>
            </div>
          )}

          {/* EMPTY STATE */}
          {!loading && !error && notifications.length === 0 && (
            <div className="notif-empty-state">
              <div className="empty-bell-icon">🔔</div>
              <h3>You&apos;re all caught up.</h3>
              <p>Your achievements, practice milestones and interview updates will appear here.</p>
              <button
                type="button"
                className="empty-action-btn"
                onClick={() => navigate("/practice")}
              >
                Go to Question Practice →
              </button>
            </div>
          )}

          {/* NOTIFICATION CARDS */}
          {!loading && !error && notifications.length > 0 && (
            <div className="notif-cards-list">
              {notifications.map((item) => {
                const categoryClass = item.category?.toLowerCase() || "system"
                return (
                  <article
                    key={item.id}
                    id={`notif-${item.id}`}
                    className={`notif-card ${!item.is_read ? "unread" : "read"} cat-${categoryClass}`}
                    onClick={() => handleCardClick(item)}
                  >
                    {/* ICON CONTAINER */}
                    <div className="notif-icon-col">
                      <div className={`notif-icon-badge ${categoryClass}`}>
                        {item.icon || "🔔"}
                      </div>
                    </div>

                    {/* CONTENT CONTAINER */}
                    <div className="notif-body-col">
                      <div className="notif-meta-row">
                        <span className={`notif-category-tag ${categoryClass}`}>
                          {item.category || "System"}
                        </span>
                        <span className="notif-time">{formatTimeAgo(item.created_at)}</span>
                        {!item.is_read && <span className="unread-dot" title="Unread notification" />}
                      </div>

                      <h3 className="notif-title">{item.title}</h3>
                      <p className="notif-message">{item.message}</p>

                      {/* ACTION BUTTON (IF URL ATTACHED) */}
                      {item.action_url && (
                        <div className="notif-card-actions">
                          <button
                            type="button"
                            className="notif-action-link"
                            onClick={(e) => {
                              e.stopPropagation()
                              if (!item.is_read) void handleMarkAsRead(item)
                              navigate(item.action_url!)
                            }}
                          >
                            {item.category === "Achievements"
                              ? "View Achievements →"
                              : item.category === "Interviews"
                              ? "View Results →"
                              : "Continue Practice →"}
                          </button>
                        </div>
                      )}
                    </div>

                    {/* CONTROLS (MARK READ / DISMISS) */}
                    <div className="notif-controls-col">
                      {!item.is_read ? (
                        <button
                          type="button"
                          className="mark-read-icon-btn"
                          title="Mark as read"
                          onClick={(e) => handleMarkAsRead(item, e)}
                          aria-label="Mark as read"
                        >
                          ✓
                        </button>
                      ) : (
                        <span className="read-status-icon" title="Read">✓</span>
                      )}

                      <button
                        type="button"
                        className="delete-icon-btn"
                        title="Delete notification"
                        onClick={(e) => handleDeleteNotification(item, e)}
                        aria-label="Delete notification"
                      >
                        ×
                      </button>
                    </div>
                  </article>
                )
              })}
            </div>
          )}

          {/* SERVER-SIDE PAGINATION CONTROLS */}
          {!loading && !error && total > 0 && (
            <div className="notif-pagination">
              <span className="pagination-info">
                Showing {Math.min((page - 1) * limit + 1, total)}–{Math.min(page * limit, total)} of {total}
              </span>

              <div className="pagination-buttons">
                <button
                  type="button"
                  className="page-btn prev-btn"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                >
                  ‹ Previous
                </button>

                <span className="page-current">
                  Page {page} of {totalPages}
                </span>

                <button
                  type="button"
                  className="page-btn next-btn"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={!hasNext || page >= totalPages}
                >
                  Next ›
                </button>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}
