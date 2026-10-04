import { useEffect, useState, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import {
  getSubscriptionPlans,
  getMySubscription,
  getSubscriptionUsage,
  getPaymentHistory,
  getInvoices,
  createPaymentOrder,
  verifyPayment,
  validateCoupon,
  cancelSubscription,
  type SubscriptionPlan,
  type UserSubscription,
  type UsageResponse,
  type PaymentTransaction,
  type Invoice,
  type CouponValidationResponse,
} from "../services/api"
import "./Subscription.css"

// Helper to dynamically load Razorpay script
const loadRazorpayScript = (): Promise<boolean> => {
  return new Promise((resolve) => {
    if ((window as any).Razorpay) {
      resolve(true)
      return
    }
    const script = document.createElement("script")
    script.src = "https://checkout.razorpay.com/v1/checkout.js"
    script.async = true
    script.onload = () => resolve(true)
    script.onerror = () => resolve(false)
    document.body.appendChild(script)
  })
}

export default function Subscription() {
  const navigate = useNavigate()

  // Data states
  const [plans, setPlans] = useState<SubscriptionPlan[]>([])
  const [subscription, setSubscription] = useState<UserSubscription | null>(null)
  const [usage, setUsage] = useState<UsageResponse | null>(null)
  const [history, setHistory] = useState<PaymentTransaction[]>([])
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<"plans" | "usage" | "invoices">("plans")

  // Checkout modal states
  const [selectedPlan, setSelectedPlan] = useState<SubscriptionPlan | null>(null)
  const [couponCode, setCouponCode] = useState("")
  const [validatingCoupon, setValidatingCoupon] = useState(false)
  const [couponResult, setCouponResult] = useState<CouponValidationResponse | null>(null)
  const [checkoutLoading, setCheckoutLoading] = useState(false)
  const [checkoutError, setCheckoutError] = useState("")
  const [successModal, setSuccessModal] = useState<{
    planName: string
    invoiceNumber?: string
    amount: number
  } | null>(null)

  // Invoice view modal
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null)

  // Cancellation modal
  const [cancellingSub, setCancellingSub] = useState(false)
  const [cancelConfirmOpen, setCancelConfirmOpen] = useState(false)

  // Toast / notification
  const [toastMessage, setToastMessage] = useState("")

  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(""), 4000)
  }

  // Load all initial subscription data
  const fetchData = async () => {
    try {
      setLoading(true)
      const [plansData, subData, usageData, historyData, invoicesData] = await Promise.all([
        getSubscriptionPlans().catch(() => []),
        getMySubscription().catch(() => null),
        getSubscriptionUsage().catch(() => null),
        getPaymentHistory().catch(() => ({ payments: [], total: 0 })),
        getInvoices().catch(() => ({ invoices: [], total: 0 })),
      ])

      setPlans(plansData)
      setSubscription(subData)
      setUsage(usageData)
      setHistory(historyData.payments || [])
      setInvoices(invoicesData.invoices || [])
    } catch (err: any) {
      console.error("Error loading subscription details:", err)
      showToast("Failed to load subscription details. Please refresh.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  // Current active plan slug
  const currentPlanSlug = useMemo(() => {
    if (!subscription || subscription.status !== "active") return "free"
    return subscription.plan?.slug || usage?.plan_slug || "free"
  }, [subscription, usage])

  // Open checkout modal for a plan
  const handleSelectPlan = (plan: SubscriptionPlan) => {
    if (plan.slug === currentPlanSlug) return
    setSelectedPlan(plan)
    setCouponCode("")
    setCouponResult(null)
    setCheckoutError("")
  }

  // Validate coupon
  const handleApplyCoupon = async () => {
    if (!selectedPlan || !couponCode.trim()) return
    setValidatingCoupon(true)
    setCheckoutError("")
    try {
      const res = await validateCoupon(couponCode.trim().toUpperCase(), selectedPlan.id)
      setCouponResult(res)
      if (!res.valid) {
        setCheckoutError(res.message || "Invalid coupon code")
      }
    } catch (err: any) {
      setCouponResult(null)
      setCheckoutError(err.message || "Failed to validate coupon")
    } finally {
      setValidatingCoupon(false)
    }
  }

  // Calculate pricing breakdown in Checkout Modal
  const checkoutCalculation = useMemo(() => {
    if (!selectedPlan) return { original: 0, discount: 0, final: 0 }
    const original = selectedPlan.price
    const discount = couponResult?.valid ? couponResult.discount_amount : 0
    const final = Math.max(0, original - discount)
    return { original, discount, final }
  }, [selectedPlan, couponResult])

  // Process Razorpay Checkout
  const handleProceedToPayment = async () => {
    if (!selectedPlan) return
    setCheckoutLoading(true)
    setCheckoutError("")

    try {
      // 1. Create order on backend
      const orderData = await createPaymentOrder(
        selectedPlan.id,
        couponResult?.valid ? couponCode : undefined
      )

      // 2. Load Razorpay script
      const scriptLoaded = await loadRazorpayScript()
      if (!scriptLoaded) {
        throw new Error("Unable to load Razorpay payment gateway. Please check internet connection.")
      }

      // 3. Configure Razorpay checkout
      const options = {
        key: import.meta.env.VITE_RAZORPAY_KEY_ID || orderData.razorpay_key_id,
        amount: orderData.amount,
        currency: orderData.currency,
        name: "AI Interview Platform",
        description: `Subscription: ${orderData.plan_name} Plan`,
        order_id: orderData.order_id,
        handler: async function (response: any) {
          try {
            setCheckoutLoading(true)
            const verifyRes = await verifyPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            })

            if (verifyRes.status === "success") {
              setSelectedPlan(null)
              setSuccessModal({
                planName: selectedPlan.name,
                invoiceNumber: verifyRes.invoice?.invoice_number,
                amount: orderData.amount,
              })
              await fetchData()
            } else {
              setCheckoutError(verifyRes.message || "Verification failed")
            }
          } catch (vErr: any) {
            setCheckoutError(vErr.message || "Payment verification failed")
          } finally {
            setCheckoutLoading(false)
          }
        },
        prefill: {
          name: "User",
          email: "user@example.com",
        },
        theme: {
          color: "#6366f1",
        },
        modal: {
          ondismiss: function () {
            setCheckoutLoading(false)
          },
        },
      }

      const rzp = new (window as any).Razorpay(options)
      rzp.on("payment.failed", function (response: any) {
        setCheckoutError(response.error?.description || "Payment failed. Please try again.")
        setCheckoutLoading(false)
      })
      rzp.open()
    } catch (err: any) {
      console.error("Payment initiation error:", err)
      setCheckoutError(
        err.message || "Could not initiate payment. Ensure Razorpay keys are configured."
      )
      setCheckoutLoading(false)
    }
  }

  // Handle Cancel Subscription
  const handleCancelSubscription = async () => {
    try {
      setCancellingSub(true)
      await cancelSubscription()
      setCancelConfirmOpen(false)
      showToast("Your subscription has been cancelled.")
      await fetchData()
    } catch (err: any) {
      showToast(err.message || "Failed to cancel subscription")
    } finally {
      setCancellingSub(false)
    }
  }

  return (
    <div className="sub-container">
      {/* Toast Alert */}
      {toastMessage && <div className="sub-toast">{toastMessage}</div>}

      {/* TOP HEADER */}
      <header className="sub-header">
        <div className="sub-header-left">
          <button className="sub-back-btn" onClick={() => navigate("/dashboard")}>
            ← Back to Dashboard
          </button>
          <div className="sub-title-wrapper">
            <h1 className="sub-title">Subscription & Billing</h1>
            <span className="sub-badge-plan">
              Current Plan: <strong>{currentPlanSlug.toUpperCase()}</strong>
            </span>
          </div>
          <p className="sub-subtitle">
            Unlock advanced AI interviews, limitless coding environments, detailed resume telemetry, and career accelerators.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="sub-tabs">
          <button
            className={`sub-tab ${activeTab === "plans" ? "active" : ""}`}
            onClick={() => setActiveTab("plans")}
          >
            Upgrade Plans
          </button>
          <button
            className={`sub-tab ${activeTab === "usage" ? "active" : ""}`}
            onClick={() => setActiveTab("usage")}
          >
            Usage & Quotas
          </button>
          <button
            className={`sub-tab ${activeTab === "invoices" ? "active" : ""}`}
            onClick={() => setActiveTab("invoices")}
          >
            Billing & Invoices ({invoices.length})
          </button>
        </div>
      </header>

      {/* ACTIVE SUBSCRIPTION SUMMARY BANNER (if on paid plan) */}
      {subscription && subscription.status === "active" && (
        <div className="sub-active-banner">
          <div className="sub-banner-content">
            <span className="sub-banner-icon">💎</span>
            <div>
              <h3>
                Active {subscription.plan?.name || "Premium"} Subscription
              </h3>
              <p>
                Valid until:{" "}
                <strong>
                  {subscription.expires_at
                    ? new Date(subscription.expires_at).toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "long",
                        day: "numeric",
                      })
                    : "Lifetime"}
                </strong>
              </p>
            </div>
          </div>
          <button
            className="sub-cancel-btn"
            onClick={() => setCancelConfirmOpen(true)}
          >
            Cancel Subscription
          </button>
        </div>
      )}

      {/* TAB 1: PLANS GRID */}
      {activeTab === "plans" && (
        <section className="sub-plans-section">
          {loading ? (
            <div className="sub-loading-spinner">Loading membership plans...</div>
          ) : (
            <div className="sub-plans-grid">
              {plans.map((p) => {
                const isCurrent = p.slug === currentPlanSlug
                const isPopular = p.slug === "pro"
                const priceFormatted = (p.price / 100).toLocaleString("en-IN")

                return (
                  <div
                    key={p.id}
                    className={`sub-plan-card ${isPopular ? "popular" : ""} ${
                      isCurrent ? "current" : ""
                    }`}
                  >
                    {isPopular && <div className="sub-popular-tag">MOST POPULAR</div>}
                    {isCurrent && <div className="sub-current-tag">ACTIVE PLAN</div>}

                    <div className="sub-card-header">
                      <h2 className="sub-plan-name">{p.name}</h2>
                      <p className="sub-plan-desc">{p.description}</p>
                      <div className="sub-price-row">
                        <span className="sub-currency">₹</span>
                        <span className="sub-amount">{priceFormatted}</span>
                        <span className="sub-period">/ month</span>
                      </div>
                    </div>

                    <div className="sub-features-list">
                      <h4>What's included:</h4>
                      <ul>
                        {p.features?.items?.map((feat, idx) => (
                          <li key={idx}>
                            <span className="sub-check-icon">✓</span>
                            <span>{feat}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="sub-card-footer">
                      {isCurrent ? (
                        <button className="sub-plan-cta current-btn" disabled>
                          Current Active Plan
                        </button>
                      ) : p.price === 0 ? (
                        <button className="sub-plan-cta free-btn" disabled>
                          Free Forever
                        </button>
                      ) : (
                        <button
                          className="sub-plan-cta upgrade-btn"
                          onClick={() => handleSelectPlan(p)}
                        >
                          Upgrade to {p.name} →
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Money Back / Security Guarantee */}
          <div className="sub-guarantee-bar">
            <div className="sub-guarantee-item">
              <span className="sub-g-icon">🔒</span>
              <div>
                <strong>Bank-Grade 256-Bit Security</strong>
                <p>Protected by Razorpay PCI-DSS certified gateway</p>
              </div>
            </div>
            <div className="sub-guarantee-item">
              <span className="sub-g-icon">⚡</span>
              <div>
                <strong>Instant Plan Activation</strong>
                <p>All interview quotas & features unlocked immediately</p>
              </div>
            </div>
            <div className="sub-guarantee-item">
              <span className="sub-g-icon">🏷️</span>
              <div>
                <strong>Flexible & Transparent</strong>
                <p>No hidden recurring charges. Cancel anytime easily</p>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* TAB 2: USAGE & QUOTAS */}
      {activeTab === "usage" && (
        <section className="sub-usage-section">
          <div className="sub-usage-grid">
            {/* AI Mock Interviews Quota */}
            <div className="sub-usage-card">
              <div className="sub-usage-top">
                <span className="sub-usage-icon">🎙️</span>
                <h3>AI Mock Interviews</h3>
              </div>
              <p className="sub-usage-caption">Monthly interview allocation</p>
              <div className="sub-metric-val">
                <span>{usage?.current_usage?.ai_interviews_this_month || 0}</span>
                <span className="sub-metric-denom">
                  / {usage?.limits?.ai_interviews_per_month >= 9999 ? "Unlimited" : usage?.limits?.ai_interviews_per_month || 3}
                </span>
              </div>
              <div className="sub-progress-bar">
                <div
                  className="sub-progress-fill"
                  style={{
                    width: `${Math.min(
                      100,
                      ((usage?.current_usage?.ai_interviews_this_month || 0) /
                        (usage?.limits?.ai_interviews_per_month >= 9999 ? 100 : usage?.limits?.ai_interviews_per_month || 3)) *
                        100
                    )}%`,
                  }}
                />
              </div>
              <span className="sub-metric-hint">Resets at the 1st of each calendar month</span>
            </div>

            {/* Daily Coding Problems */}
            <div className="sub-usage-card">
              <div className="sub-usage-top">
                <span className="sub-usage-icon">⌨️</span>
                <h3>Coding Problems</h3>
              </div>
              <p className="sub-usage-caption">Daily solved quota</p>
              <div className="sub-metric-val">
                <span>{usage?.current_usage?.coding_problems_today || 0}</span>
                <span className="sub-metric-denom">
                  / {usage?.limits?.coding_problems_per_day >= 9999 ? "Unlimited" : usage?.limits?.coding_problems_per_day || 5}
                </span>
              </div>
              <div className="sub-progress-bar">
                <div
                  className="sub-progress-fill"
                  style={{
                    width: `${Math.min(
                      100,
                      ((usage?.current_usage?.coding_problems_today || 0) /
                        (usage?.limits?.coding_problems_per_day >= 9999 ? 100 : usage?.limits?.coding_problems_per_day || 5)) *
                        100
                    )}%`,
                  }}
                />
              </div>
              <span className="sub-metric-hint">Resets every 24 hours at midnight</span>
            </div>

            {/* Resume Telemetry Analyses */}
            <div className="sub-usage-card">
              <div className="sub-usage-top">
                <span className="sub-usage-icon">📄</span>
                <h3>Resume ATS Analyses</h3>
              </div>
              <p className="sub-usage-caption">Monthly resume audit quota</p>
              <div className="sub-metric-val">
                <span>{usage?.current_usage?.resume_analyses_this_month || 0}</span>
                <span className="sub-metric-denom">
                  / {usage?.limits?.resume_analyses_per_month >= 9999 ? "Unlimited" : usage?.limits?.resume_analyses_per_month || 2}
                </span>
              </div>
              <div className="sub-progress-bar">
                <div
                  className="sub-progress-fill"
                  style={{
                    width: `${Math.min(
                      100,
                      ((usage?.current_usage?.resume_analyses_this_month || 0) /
                        (usage?.limits?.resume_analyses_per_month >= 9999 ? 100 : usage?.limits?.resume_analyses_per_month || 2)) *
                        100
                    )}%`,
                  }}
                />
              </div>
              <span className="sub-metric-hint">Resets at the 1st of each calendar month</span>
            </div>
          </div>

          {/* Feature Access Matrix */}
          <div className="sub-access-matrix">
            <h3>Feature Privileges & Entitlements</h3>
            <div className="sub-matrix-table-wrap">
              <table className="sub-matrix-table">
                <thead>
                  <tr>
                    <th>Capability</th>
                    <th>Status</th>
                    <th>Required Plan</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Advanced Analytics & Trend Reports</td>
                    <td>
                      {usage?.limits?.advanced_analytics ? (
                        <span className="sub-badge-active">Enabled</span>
                      ) : (
                        <span className="sub-badge-locked">Locked (Pro+)</span>
                      )}
                    </td>
                    <td>Pro / Premium</td>
                  </tr>
                  <tr>
                    <td>Contest & Competitive Arena</td>
                    <td>
                      {usage?.limits?.contest_participation ? (
                        <span className="sub-badge-active">Enabled</span>
                      ) : (
                        <span className="sub-badge-locked">Locked</span>
                      )}
                    </td>
                    <td>Free, Pro, Premium</td>
                  </tr>
                  <tr>
                    <td>Question Bank & Curated Practice</td>
                    <td>
                      {usage?.limits?.question_practice ? (
                        <span className="sub-badge-active">Enabled</span>
                      ) : (
                        <span className="sub-badge-locked">Locked</span>
                      )}
                    </td>
                    <td>Free, Pro, Premium</td>
                  </tr>
                  <tr>
                    <td>Priority Career Coaching & Support</td>
                    <td>
                      {usage?.limits?.priority_support ? (
                        <span className="sub-badge-active">Enabled</span>
                      ) : (
                        <span className="sub-badge-locked">Locked (Premium)</span>
                      )}
                    </td>
                    <td>Premium</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {/* TAB 3: BILLING & INVOICES */}
      {activeTab === "invoices" && (
        <section className="sub-invoices-section">
          {invoices.length === 0 ? (
            <div className="sub-empty-state">
              <span className="sub-empty-icon">🧾</span>
              <h3>No Invoices Yet</h3>
              <p>When you upgrade or renew a subscription, your official GST invoices will be generated here.</p>
              <button className="sub-empty-btn" onClick={() => setActiveTab("plans")}>
                View Plans
              </button>
            </div>
          ) : (
            <div className="sub-invoices-table-card">
              <table className="sub-invoices-table">
                <thead>
                  <tr>
                    <th>Invoice No.</th>
                    <th>Issue Date</th>
                    <th>Amount Paid</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((inv) => (
                    <tr key={inv.id}>
                      <td className="sub-inv-number">{inv.invoice_number}</td>
                      <td>{new Date(inv.issued_at).toLocaleDateString()}</td>
                      <td>₹{(inv.total_amount / 100).toLocaleString("en-IN")}</td>
                      <td>
                        <span className="sub-status-pill paid">{inv.status.toUpperCase()}</span>
                      </td>
                      <td>
                        <button
                          className="sub-inv-view-btn"
                          onClick={() => setSelectedInvoice(inv)}
                        >
                          View Invoice
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Payment History List */}
          {history.length > 0 && (
            <div className="sub-history-card">
              <h3>Transaction History</h3>
              <table className="sub-invoices-table">
                <thead>
                  <tr>
                    <th>Payment ID / Order</th>
                    <th>Date</th>
                    <th>Amount</th>
                    <th>Method</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((tx) => (
                    <tr key={tx.id}>
                      <td className="sub-tx-id">
                        {tx.provider_payment_id || tx.provider_order_id || tx.id.substring(0, 8)}
                      </td>
                      <td>{new Date(tx.created_at).toLocaleString()}</td>
                      <td>₹{(tx.amount / 100).toLocaleString("en-IN")}</td>
                      <td>{tx.payment_method || "Razorpay Online"}</td>
                      <td>
                        <span
                          className={`sub-status-pill ${
                            tx.status === "paid" ? "paid" : tx.status === "failed" ? "failed" : "pending"
                          }`}
                        >
                          {tx.status.toUpperCase()}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* CHECKOUT MODAL */}
      {selectedPlan && (
        <div className="sub-modal-backdrop" onClick={() => setSelectedPlan(null)}>
          <div className="sub-modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="sub-modal-header">
              <h2>Confirm Upgrade to {selectedPlan.name}</h2>
              <button className="sub-modal-close" onClick={() => setSelectedPlan(null)}>
                ✕
              </button>
            </div>

            <div className="sub-modal-body">
              {/* Coupon Section */}
              <div className="sub-coupon-group">
                <label>Have a Discount Coupon?</label>
                <div className="sub-coupon-input-wrap">
                  <input
                    type="text"
                    placeholder="Enter code (e.g. WELCOME50)"
                    value={couponCode}
                    onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                    disabled={validatingCoupon || checkoutLoading}
                  />
                  <button
                    className="sub-coupon-btn"
                    onClick={handleApplyCoupon}
                    disabled={!couponCode.trim() || validatingCoupon}
                  >
                    {validatingCoupon ? "Checking..." : "Apply"}
                  </button>
                </div>

                {couponResult && couponResult.valid && (
                  <div className="sub-coupon-success">
                    ✓ Coupon applied: {couponResult.message || "Discount applied!"}
                  </div>
                )}
                {checkoutError && <div className="sub-coupon-error">{checkoutError}</div>}
              </div>

              {/* Price Breakdown */}
              <div className="sub-order-summary">
                <h4>Order Summary</h4>
                <div className="sub-summary-row">
                  <span>{selectedPlan.name} Plan (Monthly)</span>
                  <span>₹{(checkoutCalculation.original / 100).toLocaleString("en-IN")}</span>
                </div>
                {checkoutCalculation.discount > 0 && (
                  <div className="sub-summary-row discount">
                    <span>Coupon Discount</span>
                    <span>-₹{(checkoutCalculation.discount / 100).toLocaleString("en-IN")}</span>
                  </div>
                )}
                <div className="sub-summary-row tax">
                  <span>GST Included (18%)</span>
                  <span>Calculated</span>
                </div>
                <div className="sub-summary-row total">
                  <span>Total Payable:</span>
                  <span>₹{(checkoutCalculation.final / 100).toLocaleString("en-IN")}</span>
                </div>
              </div>
            </div>

            <div className="sub-modal-footer">
              <button
                className="sub-modal-cancel"
                onClick={() => setSelectedPlan(null)}
                disabled={checkoutLoading}
              >
                Cancel
              </button>
              <button
                className="sub-modal-pay-btn"
                onClick={handleProceedToPayment}
                disabled={checkoutLoading}
              >
                {checkoutLoading
                  ? "Connecting Gateway..."
                  : `Pay ₹${(checkoutCalculation.final / 100).toLocaleString("en-IN")} with Razorpay`}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* PAYMENT SUCCESS MODAL */}
      {successModal && (
        <div className="sub-modal-backdrop" onClick={() => setSuccessModal(null)}>
          <div className="sub-modal-box success-box" onClick={(e) => e.stopPropagation()}>
            <div className="sub-success-icon">🎉</div>
            <h2>Subscription Activated!</h2>
            <p>
              Congratulations! You are now subscribed to the <strong>{successModal.planName}</strong> plan.
            </p>
            {successModal.invoiceNumber && (
              <p className="sub-invoice-callout">
                Invoice generated: <strong>{successModal.invoiceNumber}</strong>
              </p>
            )}
            <button
              className="sub-success-done-btn"
              onClick={() => {
                setSuccessModal(null)
                setActiveTab("usage")
              }}
            >
              Explore Your Unlocked Features →
            </button>
          </div>
        </div>
      )}

      {/* VIEW INVOICE MODAL */}
      {selectedInvoice && (
        <div className="sub-modal-backdrop" onClick={() => setSelectedInvoice(null)}>
          <div className="sub-modal-box invoice-box" onClick={(e) => e.stopPropagation()}>
            <div className="sub-invoice-sheet">
              <div className="sub-inv-brand-row">
                <div>
                  <h2 className="sub-inv-title">TAX INVOICE</h2>
                  <p className="sub-inv-meta">
                    Invoice No: <strong>{selectedInvoice.invoice_number}</strong>
                  </p>
                  <p className="sub-inv-meta">
                    Date: {new Date(selectedInvoice.issued_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="sub-inv-seller">
                  <h3>AI Interview Platform Inc.</h3>
                  <p>Bangalore, Karnataka, India</p>
                  <p>GSTIN: 29ABCDE1234F1Z5</p>
                </div>
              </div>

              <hr className="sub-inv-divider" />

              <table className="sub-inv-item-table">
                <thead>
                  <tr>
                    <th>Description</th>
                    <th>Base Price</th>
                    <th>Discount</th>
                    <th>Tax (18%)</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Platform Membership Subscription</td>
                    <td>₹{(selectedInvoice.amount / 100).toLocaleString("en-IN")}</td>
                    <td>₹{(selectedInvoice.discount / 100).toLocaleString("en-IN")}</td>
                    <td>₹{(selectedInvoice.tax / 100).toLocaleString("en-IN")}</td>
                    <td>
                      <strong>
                        ₹{(selectedInvoice.total_amount / 100).toLocaleString("en-IN")}
                      </strong>
                    </td>
                  </tr>
                </tbody>
              </table>

              <div className="sub-inv-status-tag paid">
                STATUS: {selectedInvoice.status.toUpperCase()}
              </div>

              <div className="sub-inv-actions">
                <button
                  className="sub-inv-print-btn"
                  onClick={() => window.print()}
                >
                  🖨️ Print / Save as PDF
                </button>
                <button
                  className="sub-modal-cancel"
                  onClick={() => setSelectedInvoice(null)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* CANCEL CONFIRMATION DIALOG */}
      {cancelConfirmOpen && (
        <div className="sub-modal-backdrop" onClick={() => setCancelConfirmOpen(false)}>
          <div className="sub-modal-box cancel-box" onClick={(e) => e.stopPropagation()}>
            <h3>Cancel Active Subscription?</h3>
            <p>
              Are you sure you want to cancel your plan? You will retain access until the end of your billing cycle, after which your account will revert to the Free tier.
            </p>
            <div className="sub-modal-footer">
              <button
                className="sub-modal-cancel"
                onClick={() => setCancelConfirmOpen(false)}
                disabled={cancellingSub}
              >
                Keep My Plan
              </button>
              <button
                className="sub-danger-btn"
                onClick={handleCancelSubscription}
                disabled={cancellingSub}
              >
                {cancellingSub ? "Cancelling..." : "Confirm Cancellation"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
