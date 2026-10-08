import AuthLayout from '../components/AuthLayout.jsx'
import { Link } from 'react-router-dom'

// Day 2: name, email, username, phone, role, password -> POST /auth/register
export default function Register() {
  return (
    <AuthLayout title="Create account" subtitle="Registration form comes on Day 2.">
      <p className="links"><Link to="/login">Back to sign in</Link></p>
    </AuthLayout>
  )
}
