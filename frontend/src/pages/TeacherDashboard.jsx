import { useAuth } from '../context/AuthContext.jsx'

// Day 3: mark attendance (POST /attendance) and view by class/date (GET /attendance)
export default function TeacherDashboard() {
  const { user, logout } = useAuth()
  return (
    <div className="shell">
      <header><h1>Class register</h1><button className="ghost" onClick={logout}>Sign out</button></header>
      <p className="muted">Signed in as {user.name}. Mark and review attendance here.</p>
    </div>
  )
}
