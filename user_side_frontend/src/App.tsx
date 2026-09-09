import { Navigate, Route, Routes } from "react-router-dom"

import Login from "./pages/Login"
import Signup from "./pages/Signup"
import Dashboard from "./pages/Dashboard"
import Resume from "./pages/Resume"
import InterviewSetup from "./pages/InterviewSetup"
import Interview from "./pages/Interview"
import Results from "./pages/Results"

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


      {/* Main application */}
      <Route
        path="/dashboard"
        element={<Dashboard />}
      />

      <Route
        path="/resume"
        element={<Resume />}
      />

      <Route
        path="/interview-setup"
        element={<InterviewSetup />}
      />

      <Route
        path="/interview/:interviewId"
        element={<Interview />}
      />


      {/* Results */}
      <Route
        path="/results/:id"
        element={<Results />}
      />


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