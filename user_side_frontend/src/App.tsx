import { Navigate, Route, Routes } from "react-router-dom"

import Login from "./pages/Login"
import Signup from "./pages/Signup"
import Dashboard from "./pages/Dashboard"
import Settings from "./pages/Settings"
import Resume from "./pages/Resume"
import InterviewSetup from "./pages/InterviewSetup"
import Interview from "./pages/Interview"
import Results from "./pages/Results"
import Performance from "./pages/Performance"
import QuestionPractice from "./pages/QuestionPractice"
import Achievements from "./pages/Achievements"
import Notifications from "./pages/Notifications"
import Profile from "./pages/Profile"
import CodingProblems from "./pages/CodingProblems"
import CodingWorkspace from "./pages/CodingWorkspace"
import ContestList from "./pages/ContestList"
import ContestDetails from "./pages/ContestDetails"
import ContestWorkspace from "./pages/ContestWorkspace"
import ContestLeaderboard from "./pages/ContestLeaderboard"
import ContestResults from "./pages/ContestResults"
import Subscription from "./pages/Subscription"
import SupportCenter from "./pages/SupportCenter"
import SupportTickets from "./pages/SupportTickets"
import SupportTicketDetails from "./pages/SupportTicketDetails"
import ProtectedRoute from "./components/ProtectedRoute"

// Phase 13 — Complete Admin Dashboard Components
import AdminProtectedRoute from "./admin/components/AdminProtectedRoute"
import AdminLayout from "./admin/layouts/AdminLayout"
import AdminLogin from "./admin/pages/AdminLogin"
import AdminDashboard from "./admin/pages/AdminDashboard"
import AdminUsers from "./admin/pages/AdminUsers"
import AdminUserDetails from "./admin/pages/AdminUserDetails"
import AdminInterviews from "./admin/pages/AdminInterviews"
import AdminQuestions from "./admin/pages/AdminQuestions"
import AdminCodingProblems from "./admin/pages/AdminCodingProblems"
import AdminCompanies from "./admin/pages/AdminCompanies"
import AdminResources from "./admin/pages/AdminResources"
import AdminAIAgents from "./admin/pages/AdminAIAgents"
import AdminResumeATS from "./admin/pages/AdminResumeATS"
import AdminAnalytics from "./admin/pages/AdminAnalytics"
import AdminSubscriptions from "./admin/pages/AdminSubscriptions"
import AdminPayments from "./admin/pages/AdminPayments"
import AdminCoupons from "./admin/pages/AdminCoupons"
import AdminInvoices from "./admin/pages/AdminInvoices"
import AdminSupport from "./admin/pages/AdminSupport"
import AdminFeedback from "./admin/pages/AdminFeedback"
import AdminNotifications from "./admin/pages/AdminNotifications"
import AdminAchievements from "./admin/pages/AdminAchievements"
import AdminAuditLogs from "./admin/pages/AdminAuditLogs"
import AdminSettings from "./admin/pages/AdminSettings"
import AdminRBAC from "./admin/pages/AdminRBAC"
import AdminRAG from "./admin/pages/AdminRAG"
import AdminLearning from "./admin/pages/AdminLearning"
import AdminContests from "./admin/pages/AdminContests"

function App() {
  return (
    <Routes>

      {/* Authentication */}
      <Route
        path="/"
        element={
          <Navigate
            to="/login"
            replace
          />
        }
      />

      <Route
        path="/login"
        element={<Login />}
      />

      <Route
        path="/signup"
        element={<Signup />}
      />


      {/* Main application (Protected) */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />

      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <Settings />
          </ProtectedRoute>
        }
      />

      <Route
        path="/subscription"
        element={
          <ProtectedRoute>
            <Subscription />
          </ProtectedRoute>
        }
      />

      <Route
        path="/resume"
        element={
          <ProtectedRoute>
            <Resume />
          </ProtectedRoute>
        }
      />

      <Route
        path="/interview-setup"
        element={
          <ProtectedRoute>
            <InterviewSetup />
          </ProtectedRoute>
        }
      />

      <Route
        path="/interview/:interviewId"
        element={
          <ProtectedRoute>
            <Interview />
          </ProtectedRoute>
        }
      />


      {/* Results */}
      <Route
        path="/results/:id"
        element={
          <ProtectedRoute>
            <Results />
          </ProtectedRoute>
        }
      />

      {/* Performance & Analytics */}
      <Route
        path="/performance"
        element={
          <ProtectedRoute>
            <Performance />
          </ProtectedRoute>
        }
      />

      <Route
        path="/analytics"
        element={
          <Navigate
            to="/performance"
            replace
          />
        }
      />

      {/* Question Practice */}
      <Route
        path="/practice"
        element={
          <ProtectedRoute>
            <QuestionPractice />
          </ProtectedRoute>
        }
      />
      <Route
        path="/practice/:techSlug"
        element={
          <ProtectedRoute>
            <QuestionPractice />
          </ProtectedRoute>
        }
      />
      <Route
        path="/practice/:techSlug/:topicSlug"
        element={
          <ProtectedRoute>
            <QuestionPractice />
          </ProtectedRoute>
        }
      />

      {/* Achievements */}
      <Route
        path="/achievements"
        element={
          <ProtectedRoute>
            <Achievements />
          </ProtectedRoute>
        }
      />

      {/* Notifications (Task 12) */}
      <Route
        path="/notifications"
        element={
          <ProtectedRoute>
            <Notifications />
          </ProtectedRoute>
        }
      />

      {/* Profile (Task 13) */}
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        }
      />

      {/* Coding Interview Arena (Phase 8) */}
      <Route
        path="/coding"
        element={
          <ProtectedRoute>
            <CodingProblems />
          </ProtectedRoute>
        }
      />
      <Route
        path="/coding/:problemId"
        element={
          <ProtectedRoute>
            <CodingWorkspace />
          </ProtectedRoute>
        }
      />

      {/* Competitive Coding & Live Contests (Phase 8D) */}
      <Route
        path="/contests"
        element={
          <ProtectedRoute>
            <ContestList />
          </ProtectedRoute>
        }
      />
      <Route
        path="/contests/:contestId"
        element={
          <ProtectedRoute>
            <ContestDetails />
          </ProtectedRoute>
        }
      />
      <Route
        path="/contests/:contestId/arena"
        element={
          <ProtectedRoute>
            <ContestWorkspace />
          </ProtectedRoute>
        }
      />
      <Route
        path="/contests/:contestId/leaderboard"
        element={
          <ProtectedRoute>
            <ContestLeaderboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/contests/:contestId/results"
        element={
          <ProtectedRoute>
            <ContestResults />
          </ProtectedRoute>
        }
      />

      {/* Support & Help Center (Phase 15) */}
      <Route
        path="/support"
        element={
          <ProtectedRoute>
            <SupportCenter />
          </ProtectedRoute>
        }
      />
      <Route
        path="/support/tickets"
        element={
          <ProtectedRoute>
            <SupportTickets />
          </ProtectedRoute>
        }
      />
      <Route
        path="/support/tickets/:ticketId"
        element={
          <ProtectedRoute>
            <SupportTicketDetails />
          </ProtectedRoute>
        }
      />

      {/* Pricing alias to Subscription */}
      <Route
        path="/pricing"
        element={
          <Navigate
            to="/subscription"
            replace
          />
        }
      />

      {/* Admin Authentication (Phase 13) */}
      <Route path="/admin/login" element={<AdminLogin />} />

      {/* Admin Dashboard & Management Console (Phase 13) */}
      <Route
        path="/admin"
        element={
          <AdminProtectedRoute>
            <AdminLayout />
          </AdminProtectedRoute>
        }
      >
        <Route index element={<AdminDashboard />} />
        <Route path="dashboard" element={<AdminDashboard />} />
        <Route path="users" element={<AdminUsers />} />
        <Route path="users/:userId" element={<AdminUserDetails />} />
        <Route path="users/:id" element={<AdminUserDetails />} />
        <Route path="interviews" element={<AdminInterviews />} />
        <Route path="interviews/:interviewId" element={<AdminInterviews />} />
        <Route path="interviews/:id" element={<AdminInterviews />} />
        <Route path="questions" element={<AdminQuestions />} />
        <Route path="questions/new" element={<AdminQuestions />} />
        <Route path="questions/:id/edit" element={<AdminQuestions />} />
        <Route path="coding" element={<AdminCodingProblems />} />
        <Route path="coding-problems" element={<AdminCodingProblems />} />
        <Route path="companies" element={<AdminCompanies />} />
        <Route path="resources" element={<AdminResources />} />
        <Route path="ai-agents" element={<AdminAIAgents />} />
        <Route path="resume-ats" element={<AdminResumeATS />} />
        <Route path="analytics" element={<AdminAnalytics />} />
        <Route path="subscriptions" element={<AdminSubscriptions />} />
        <Route path="payments" element={<AdminPayments />} />
        <Route path="coupons" element={<AdminCoupons />} />
        <Route path="invoices" element={<AdminInvoices />} />
        <Route path="support" element={<AdminSupport />} />
        <Route path="support/:ticketId" element={<AdminSupport />} />
        <Route path="feedback" element={<AdminFeedback />} />
        <Route path="notifications" element={<AdminNotifications />} />
        <Route path="achievements" element={<AdminAchievements />} />
        <Route path="audit-logs" element={<AdminAuditLogs />} />
        <Route path="settings" element={<AdminSettings />} />
        <Route path="rbac" element={<AdminRBAC />} />
        <Route path="rag" element={<AdminRAG />} />
        <Route path="learning" element={<AdminLearning />} />
        <Route path="contests" element={<AdminContests />} />
      </Route>

      {/* Fallback */}
      <Route
        path="*"
        element={
          <Navigate
            to="/login"
            replace
          />
        }
      />

    </Routes>
  )
}

export default App