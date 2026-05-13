import { useState, useEffect } from 'react'
// RoomSelect removed as per request
import Visualizer from './components/Visualizer'
import CustomUploadVisualizer from './components/CustomUploadVisualizer'
import AdminPanel from './components/AdminPanel'
import AdminLogin from './components/AdminLogin'
import AdminSignup from './components/AdminSignup'
import LandingPage from './components/LandingPage'
import AIInteriorCopilot from './components/AIInteriorCopilot'

function App() {
  const [selectedRoom, setSelectedRoom] = useState<any>(null)
  const [currentRoute, setCurrentRoute] = useState('landing')
  const [isAdminAuthenticated, setIsAdminAuthenticated] = useState(false)
  const [adminAuthMode, setAdminAuthMode] = useState<'login' | 'signup'>('login')
  const [adminUser, setAdminUser] = useState<{ name?: string, id?: string | number } | null>(null)
  const [isReady, setIsReady] = useState(false)
  const [pendingImage, setPendingImage] = useState<File | null>(null)

  useEffect(() => {
    const adminAuth = localStorage.getItem('isAdminAuthenticated')
    const adminName = localStorage.getItem('adminName')
    const adminId = localStorage.getItem('adminId')
    if (adminAuth === 'true') {
      setIsAdminAuthenticated(true)
      if (adminName) setAdminUser({ name: adminName, id: adminId || undefined })
    }

    // Initial route based on UR
    const path = window.location.pathname
    if (path === '/admin') {
      setCurrentRoute('admin')
    } else if (path === '/home') {
      setCurrentRoute('landing') // Redirect home to landing
    } else if (path === '/custom') {
      setCurrentRoute('custom')
    } else if (path === '/copilot') {
      setCurrentRoute('copilot')
    } else {
      setCurrentRoute('landing')
    }

    setIsReady(true)
  }, [])

  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname
      if (path === '/admin') setCurrentRoute('admin')
      else if (path === '/home') setCurrentRoute('landing')
      else if (path === '/custom') setCurrentRoute('custom')
      else if (path === '/copilot') setCurrentRoute('copilot')
      else setCurrentRoute('landing')
    }

    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  // Sync URL with currentRoute
  useEffect(() => {
    if (!isReady) return

    const path = currentRoute === 'landing' ? '/' : `/${currentRoute}`
    if (window.location.pathname !== path) {
      window.history.pushState({}, '', path)
    }
  }, [currentRoute, isReady])

  const handleAdminLogin = (userData: any) => {
    setIsAdminAuthenticated(true)
    const name = userData.name || userData.email || 'Admin'
    const id = userData.id
    setAdminUser({ name, id })
    localStorage.setItem('isAdminAuthenticated', 'true')
    localStorage.setItem('adminName', name)
    if (id) localStorage.setItem('adminId', id.toString())
    setCurrentRoute('admin')
  }

  const handleAdminLogout = () => {
    localStorage.removeItem('isAdminAuthenticated')
    localStorage.removeItem('adminName')
    localStorage.removeItem('adminId')
    setIsAdminAuthenticated(false)
    setAdminUser(null)
    setCurrentRoute('landing')
  }

  const handleNavigate = (route: string, data?: any) => {
    if (route === 'custom' && data instanceof File) {
      setPendingImage(data)
    }
    setCurrentRoute(route)
  }

  if (!isReady) return null

  if (currentRoute === 'landing') {
    return <LandingPage onNavigate={handleNavigate} />
  }

  if (currentRoute === 'custom') {
    return (
      <CustomUploadVisualizer 
        onBack={() => {
          setPendingImage(null)
          setCurrentRoute('landing')
        }} 
        userId={adminUser?.id} 
        userName={adminUser?.name}
        initialImage={pendingImage}
      />
    )
  }

  if (currentRoute === 'copilot') {
    return <AIInteriorCopilot onBack={() => setCurrentRoute('landing')} userId={adminUser?.id} userName={adminUser?.name} />
  }

  // Home route removed as per request, always redirect to landing if somehow hit
  if (currentRoute === 'home') {
    return <LandingPage onNavigate={handleNavigate} />
  }

  if (currentRoute === 'admin') {
    if (!isAdminAuthenticated) {
      if (adminAuthMode === 'signup') {
        return <AdminSignup onSignup={() => setAdminAuthMode('login')} onSwitchToLogin={() => setAdminAuthMode('login')} />
      }
      return <AdminLogin onLogin={handleAdminLogin} onSwitchToSignup={() => setAdminAuthMode('signup')} />
    }
    return <AdminPanel onBack={() => setCurrentRoute('landing')} onLogout={handleAdminLogout} userName={adminUser?.name} userId={adminUser?.id} />
  }

  return null
}

export default App
