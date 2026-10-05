import { Routes, Route } from "react-router-dom";
import { ProtectedRoute } from "./components/ProtectedRoute";
import Login from "./pages/Login";
import DashboardOverview from "./pages/DashboardOverview";
import StudentsDirectory from "./pages/StudentsDirectory";
import StudentProfile from "./pages/StudentProfile";
import UploadStudentData from "./pages/UploadStudentData";
import JobRoles from "./pages/JobRoles";
import SkillBayAI from "./pages/SkillBayAI";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<ProtectedRoute><DashboardOverview /></ProtectedRoute>} />
      <Route path="/upload" element={<ProtectedRoute><UploadStudentData /></ProtectedRoute>} />
      <Route path="/students" element={<ProtectedRoute><StudentsDirectory /></ProtectedRoute>} />
      <Route path="/students/:id" element={<ProtectedRoute><StudentProfile /></ProtectedRoute>} />
      <Route path="/jobs" element={<ProtectedRoute><JobRoles /></ProtectedRoute>} />
      <Route path="/ai-assistant" element={<ProtectedRoute><SkillBayAI /></ProtectedRoute>} />
      <Route path="/ai" element={<ProtectedRoute><SkillBayAI /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />

    </Routes>
  );
}
