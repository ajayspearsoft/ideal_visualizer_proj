import { useState } from 'react'
import { API_BASE_URL } from '../config'
import { Shield } from 'lucide-react'

export default function AdminLogin({ onLogin, onSwitchToSignup }: { onLogin: (user: any) => void, onSwitchToSignup: () => void }) {
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!identifier || !password) {
      setError('Please enter your email/mobile and password.')
      return
    }

    setError('')
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE_URL}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier, password })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.message || 'Login failed')
      
      localStorage.setItem('isAdminAuthenticated', 'true')
      localStorage.setItem('adminName', data.user.name)
      onLogin(data.user)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#fcfcfb] flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans selection:bg-stone-200">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="mx-auto h-16 w-16 bg-[#1a1a1a] rounded-sm flex items-center justify-center shadow-lg mb-8 transition-transform hover:rotate-12">
          <Shield className="text-white" size={28} />
        </div>
        <h2 className="text-4xl font-medium text-[#1a1a1a] tracking-tight font-serif mb-2">Studio Portal</h2>
        <p className="text-[10px] font-bold uppercase tracking-[0.3em] text-stone-400">Secure Catalog Management</p>
      </div>

      <div className="mt-12 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-12 px-8 shadow-sm border border-stone-100 sm:px-12">
          <form className="space-y-8" onSubmit={handleSubmit}>
            {error && (
              <div className="p-4 bg-stone-50 text-red-800 text-[11px] font-bold uppercase tracking-widest border-l-4 border-red-500 animate-in fade-in slide-in-from-left-2">
                {error}
              </div>
            )}
            
            <div className="space-y-2">
              <label className="block text-[10px] font-bold uppercase tracking-widest text-stone-500">Identity</label>
              <input 
                type="text" 
                required 
                value={identifier} 
                onChange={(e) => setIdentifier(e.target.value)} 
                className="block w-full px-4 py-4 border-b border-stone-200 text-sm focus:border-[#1a1a1a] outline-none transition-all placeholder:text-stone-300" 
                placeholder="Email or Mobile" 
              />
            </div>

            <div className="space-y-2">
              <label className="block text-[10px] font-bold uppercase tracking-widest text-stone-500">Security</label>
              <input 
                type="password" 
                required 
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                className="block w-full px-4 py-4 border-b border-stone-200 text-sm focus:border-[#1a1a1a] outline-none transition-all placeholder:text-stone-300" 
                placeholder="Enter Password" 
              />
            </div>

            <button 
              type="submit" 
              disabled={loading} 
              className="w-full py-5 border border-transparent text-xs font-bold uppercase tracking-[0.2em] text-white bg-[#1a1a1a] hover:bg-stone-800 transition-all active:scale-[0.98] shadow-lg disabled:bg-stone-300"
            >
              {loading ? 'Authenticating...' : 'Sign In to Studio'}
            </button>
          </form>

          <div className="mt-12 pt-8 border-t border-stone-100 text-center">
             <p className="text-[10px] font-bold uppercase tracking-widest text-stone-400">
               New associate? <button onClick={onSwitchToSignup} className="text-[#1a1a1a] hover:underline ml-2">Request Access</button>
             </p>
          </div>
        </div>
      </div>
    </div>
  )
}
