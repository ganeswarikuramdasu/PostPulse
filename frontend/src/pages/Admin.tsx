import { useEffect, useState } from 'react'
import { fetchAdminUsers, updateAdminUser, fetchAdminStats } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { LoadingState, ErrorState } from '../components/States'
import { ShieldCheck, Users, Zap, CheckCircle } from 'lucide-react'

interface AdminUser {
  id: number
  email: string
  is_verified: boolean
  is_admin: boolean
  plan: string
  created_at: string
}

export default function Admin() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [stats, setStats] = useState<Record<string, number> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    setError(null)
    Promise.all([fetchAdminUsers(), fetchAdminStats()])
      .then(([u, s]) => {
        setUsers(u)
        setStats(s)
      })
      .catch(() => setError('Could not load admin data. Make sure your account has admin access.'))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const togglePlan = async (u: AdminUser) => {
    const newPlan = u.plan === 'pro' ? 'free' : 'pro'
    const updated = await updateAdminUser(u.id, { plan: newPlan })
    setUsers((prev) => prev.map((x) => (x.id === u.id ? updated : x)))
  }

  const toggleAdmin = async (u: AdminUser) => {
    const updated = await updateAdminUser(u.id, { is_admin: !u.is_admin })
    setUsers((prev) => prev.map((x) => (x.id === u.id ? updated : x)))
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-14">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Admin</h1>
      <p className="mt-2 text-text-secondary">Manage users, plans, and admin access.</p>

      {loading && <LoadingState label="Loading admin data…" />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && (
        <>
          {stats && (
            <div className="mt-8 grid gap-4 sm:grid-cols-4">
              <div className="rounded-xl border border-border bg-surface p-5">
                <Users size={16} className="text-teal" />
                <p className="mt-2 font-mono text-2xl font-semibold text-text-primary">{stats.total_users}</p>
                <p className="text-xs text-text-muted">Total users</p>
              </div>
              <div className="rounded-xl border border-border bg-surface p-5">
                <CheckCircle size={16} className="text-score-high" />
                <p className="mt-2 font-mono text-2xl font-semibold text-text-primary">{stats.verified_users}</p>
                <p className="text-xs text-text-muted">Verified</p>
              </div>
              <div className="rounded-xl border border-border bg-surface p-5">
                <Zap size={16} className="text-accent" />
                <p className="mt-2 font-mono text-2xl font-semibold text-text-primary">{stats.pro_users}</p>
                <p className="text-xs text-text-muted">Pro plan</p>
              </div>
              <div className="rounded-xl border border-border bg-surface p-5">
                <ShieldCheck size={16} className="text-score-medium" />
                <p className="mt-2 font-mono text-2xl font-semibold text-text-primary">{stats.total_predictions}</p>
                <p className="text-xs text-text-muted">Predictions run</p>
              </div>
            </div>
          )}

          <div className="mt-8 overflow-hidden rounded-xl border border-border">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface text-xs uppercase tracking-wider text-text-muted">
                <tr>
                  <th className="px-4 py-3 font-medium">Email</th>
                  <th className="px-4 py-3 font-medium">Joined</th>
                  <th className="px-4 py-3 font-medium">Verified</th>
                  <th className="px-4 py-3 font-medium">Plan</th>
                  <th className="px-4 py-3 font-medium">Admin</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-t border-border bg-bg">
                    <td className="px-4 py-3 text-text-primary">{u.email}</td>
                    <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${u.is_verified ? 'bg-score-high/10 text-score-high' : 'bg-score-medium/10 text-score-medium'}`}>
                        {u.is_verified ? 'Verified' : 'Pending'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => togglePlan(u)}
                        className={`focus-ring rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${u.plan === 'pro' ? 'bg-accent/10 text-accent' : 'bg-surface-raised text-text-secondary'}`}
                      >
                        {u.plan}
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => toggleAdmin(u)}
                        disabled={u.id === currentUser?.id}
                        className={`focus-ring rounded-full px-2.5 py-1 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${u.is_admin ? 'bg-teal/10 text-teal' : 'bg-surface-raised text-text-secondary'}`}
                      >
                        {u.is_admin ? 'Admin' : 'User'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
