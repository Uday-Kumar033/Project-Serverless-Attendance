import AuthLayout from '../components/AuthLayout.jsx'
import { Link } from 'react-router-dom'

// Day 4: phone -> OTP -> new password (POST /auth/forgot, /auth/reset)
export default function ForgotPassword() {
  return (
    <AuthLayout title="Reset password" subtitle="OTP reset comes on Day 4.">
      <p className="links"><Link to="/login">Back to sign in</Link></p>
    </AuthLayout>
  )
}
