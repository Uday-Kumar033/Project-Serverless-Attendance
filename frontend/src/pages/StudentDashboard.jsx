import { useAuth } from '../context/AuthContext.jsx'

// Day 3: GET /attendance/me
export default function StudentDashboard() {
  const { user, logout } = useAuth()
  return (
    <div className="shell">
      <header><h1>My attendance</h1><button className="ghost" onClick={logout}>Sign out</button></header>
      <p className="muted">Signed in as {user.name}. Your attendance records will appear here.</p>
    </div>
  )
}
