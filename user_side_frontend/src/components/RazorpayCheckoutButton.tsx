import { useState } from "react"
import {
  createPaymentOrder,
  verifyPayment,
  type VerifyPaymentResponse,
} from "../services/api"
import "./RazorpayCheckoutButton.css"

export interface RazorpayCheckoutButtonProps {
  amount?: number // in paise (e.g. 49900 = ₹499)
  currency?: string
  planId?: string
  planName?: string
  couponCode?: string
  buttonText?: string
  className?: string
  disabled?: boolean
  customerEmail?: string
  customerName?: string
  customerContact?: string
  onSuccess?: (response: VerifyPaymentResponse) => void
  onError?: (errorMessage: string) => void
  onDismiss?: () => void
}

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

export default function RazorpayCheckoutButton({
  amount = 49900,
  currency = "INR",
  planId,
  planName,
  couponCode,
  buttonText = "Pay with Razorpay",
  className = "",
  disabled = false,
  customerEmail = "candidate@example.com",
  customerName = "Candidate",
  customerContact = "",
  onSuccess,
  onError,
  onDismiss,
}: RazorpayCheckoutButtonProps) {
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const handleCheckout = async () => {
    setLoading(true)
    setErrorMessage(null)

    try {
      // 1. Ensure Razorpay checkout.js script is loaded
      const isLoaded = await loadRazorpayScript()
      if (!isLoaded) {
        throw new Error(
          "Failed to load Razorpay checkout script. Please check your internet connection."
        )
      }

      // 2. Create Order on backend
      const order = await createPaymentOrder({
        planId,
        amount: planId ? undefined : amount,
        currency,
        couponCode,
      })

      if (!order || !order.order_id) {
        throw new Error("Failed to initialize payment order.")
      }

      // Fallback key: environment key or key from backend
      const razorpayKey =
        import.meta.env.VITE_RAZORPAY_KEY_ID || order.razorpay_key_id

      if (!razorpayKey) {
        throw new Error("Razorpay Key ID is not configured.")
      }

      // 3. Configure Razorpay Standard Modal options
      const options = {
        key: razorpayKey,
        amount: order.amount,
        currency: order.currency,
        name: "AI Interview Platform",
        description: planName
          ? `Subscription: ${planName}`
          : `Platform Payment - ₹${(order.amount / 100).toFixed(2)}`,
        order_id: order.order_id,
        prefill: {
          name: customerName,
          email: customerEmail,
          contact: customerContact,
        },
        theme: {
          color: "#6366f1",
        },
        handler: async function (response: {
          razorpay_payment_id: string
          razorpay_order_id: string
          razorpay_signature: string
        }) {
          try {
            setLoading(true)
            // 4. Verify Payment on backend
            const verification = await verifyPayment({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            })

            if (verification.status === "success") {
              onSuccess?.(verification)
            } else {
              const msg = verification.message || "Payment verification failed."
              setErrorMessage(msg)
              onError?.(msg)
            }
          } catch (vErr: any) {
            const msg = vErr.message || "Payment signature verification failed."
            setErrorMessage(msg)
            onError?.(msg)
          } finally {
            setLoading(false)
          }
        },
        modal: {
          ondismiss: function () {
            setLoading(false)
            onDismiss?.()
          },
        },
      }

      // 4. Open Razorpay Modal
      const razorpayInstance = new (window as any).Razorpay(options)

      razorpayInstance.on("payment.failed", function (response: any) {
        const errorDesc =
          response.error?.description ||
          response.error?.reason ||
          "Payment processing failed."
        setErrorMessage(errorDesc)
        onError?.(errorDesc)
        setLoading(false)
      })

      razorpayInstance.open()
    } catch (err: any) {
      console.error("Razorpay checkout error:", err)
      const msg = err.message || "Failed to start checkout. Please try again."
      setErrorMessage(msg)
      onError?.(msg)
      setLoading(false)
    }
  }

  return (
    <div className="rzp-btn-container">
      <button
        type="button"
        className={`rzp-checkout-btn ${className}`}
        onClick={handleCheckout}
        disabled={disabled || loading}
      >
        {loading ? (
          <span className="rzp-btn-loading">
            <span className="rzp-spinner"></span> Processing...
          </span>
        ) : (
          buttonText
        )}
      </button>

      {errorMessage && (
        <div className="rzp-error-text" role="alert">
          ⚠ {errorMessage}
        </div>
      )}
    </div>
  )
}
