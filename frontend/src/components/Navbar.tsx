import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Activity, LogOut } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  // When logged in there's no need for a Home tab — the app is fully
  // navigated from the dashboard-style links below.
  const links = user
    ? [
        { to: '/predict', label: 'Predict' },
        { to: '/history', label: 'History' },
      ]
    : [{ to: '/', label: 'Home' }]

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link to="/" className="flex items-center gap-2 focus-ring rounded-md">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-vibrant-cta text-white shadow-glow-pink">
            <Activity size={18} strokeWidth={2.5} />
          </div>
          <span className="font-display text-lg font-semibold tracking-tight">
            <span className="text-vibrant">PostPulse</span>
          </span>
        </Link>
        <nav className="flex items-center gap-1">
          {links.map((link) => {
            const active = location.pathname === link.to
            return (
              <Link
                key={link.to}
                to={link.to}
                className={`focus-ring rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                  active ? 'bg-surface-raised text-text-primary' : 'text-text-secondary hover:text-text-primary'
                }`}
              >
                {link.label}
              </Link>
            )
          })}

          {user ? (
            <div className="ml-2 flex items-center gap-2">
              <span className="hidden text-xs text-text-muted sm:inline">{user.email}</span>
              <button
                onClick={handleLogout}
                className="focus-ring flex items-center gap-1.5 rounded-md border border-border px-3 py-2 text-sm font-medium text-text-secondary hover:text-text-primary"
              >
                <LogOut size={14} /> Log out
              </button>
            </div>
          ) : (
            <div className="ml-2 flex items-center gap-2">
              <Link
                to="/login"
                className="focus-ring rounded-md px-4 py-2 text-sm font-medium text-text-secondary hover:text-text-primary"
              >
                Log in
              </Link>
              <Link
                to="/register"
                className="focus-ring rounded-md bg-vibrant-cta px-4 py-2 text-sm font-semibold text-white shadow-glow-pink transition-transform hover:scale-[1.03]"
              >
                Sign up
              </Link>
            </div>
          )}
        </nav>
      </div>
    </header>
  )
}
