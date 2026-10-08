export default function AuthLayout({ title, subtitle, children }) {
  return (
    <main className="auth">
      <section className="auth-card">
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
        {children}
      </section>
    </main>
  )
}
