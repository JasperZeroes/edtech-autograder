import { Navigate, Route, Routes } from "react-router-dom";

import AppLayout from "./components/AppLayout";
import GuestRoute from "./auth/GuestRoute";
import ProtectedRoute from "./auth/ProtectedRoute";
import CreateAssignment from "./pages/CreateAssignment";
import Dashboard from "./pages/Dashboard";
import Home from "./pages/Home";
import InstructorDashboard from "./pages/InstructorDashboard";
import InstructorResult from "./pages/InstructorResult";
import InstructorSubmissions from "./pages/InstructorSubmissions";
import Login from "./pages/Login";
import NotFound from "./pages/NotFound";
import Register from "./pages/Register";
import StudentAssignment from "./pages/StudentAssignment";
import StudentDashboard from "./pages/StudentDashboard";
import StudentResult from "./pages/StudentResult";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />

      <Route
        path="/login"
        element={
          <GuestRoute>
            <Login />
          </GuestRoute>
        }
      />

      <Route
        path="/register"
        element={
          <GuestRoute>
            <Register />
          </GuestRoute>
        }
      />

      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />

        <Route
          path="/instructor"
          element={
            <ProtectedRoute role="instructor">
              <InstructorDashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/instructor/assignments/new"
          element={
            <ProtectedRoute role="instructor">
              <CreateAssignment />
            </ProtectedRoute>
          }
        />

        <Route
          path="/instructor/assignments/:assignmentId/submissions"
          element={
            <ProtectedRoute role="instructor">
              <InstructorSubmissions />
            </ProtectedRoute>
          }
        />

        <Route
          path="/instructor/assignments/:assignmentId/submissions/:submissionId"
          element={
            <ProtectedRoute role="instructor">
              <InstructorResult />
            </ProtectedRoute>
          }
        />

        <Route
          path="/student"
          element={
            <ProtectedRoute role="student">
              <StudentDashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/student/assignments/:assignmentId"
          element={
            <ProtectedRoute role="student">
              <StudentAssignment />
            </ProtectedRoute>
          }
        />

        <Route
          path="/student/submissions/:submissionId/result"
          element={
            <ProtectedRoute role="student">
              <StudentResult />
            </ProtectedRoute>
          }
        />
      </Route>

      <Route path="/home" element={<Navigate to="/" replace />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
