import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import client from '../services/api'

export interface User {
  id: number
  email: string
  is_verified: boolean
  plan: string
  created_at: string
}

interface AuthContextValue {
  user: User | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<string>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

const TOKEN_KEY = 'postpulse_token'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [loading, setLoading] = useState(true)

  const applyToken = (t: string | null) => {
    setToken(t)
    if (t) {
      localStorage.setItem(TOKEN_KEY, t)
      client.defaults.headers.common['Authorization'] = `Bearer ${t}`
    } else {
      localStorage.removeItem(TOKEN_KEY)
      delete client.defaults.headers.common['Authorization']
    }
  }

  const refreshUser = async () => {
    try {
      const { data } = await client.get('/auth/me')
      setUser(data)
    } catch {
      applyToken(null)
      setUser(null)
    }
  }

  useEffect(() => {
    if (token) {
      client.defaults.headers.common['Authorization'] = `Bearer ${token}`
      refreshUser().finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const login = async (email: string, password: string) => {
    const { data } = await client.post('/auth/login', { email, password })
    applyToken(data.access_token)
    setUser(data.user)
  }

  const register = async (email: string, password: string): Promise<string> => {
    const { data } = await client.post('/auth/register', { email, password })
    return data.message as string
  }

  const logout = () => {
    applyToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
