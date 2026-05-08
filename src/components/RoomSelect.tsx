export default function RoomSelect({ 
  onSelect, 
  onCustomAI, 
  onCopilot,
  onAdmin, 
  onLogout, 
  userName, 
  showAuth = false 
}: { 
  onSelect: (room: any) => void, 
  onCustomAI?: () => void, 
  onCopilot?: () => void,
  onAdmin?: () => void, 
  onLogout?: () => void, 
  userName?: string,
  showAuth?: boolean
}) {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
              </div>
              <span className="text-lg font-semibold text-gray-900 tracking-tight">
                Studio Editor
              </span>
            </div>
            {showAuth && (
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-3 pl-4 border-l border-gray-200">
                  {userName ? (
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-sm shadow-inner uppercase">
                        {userName.charAt(0)}
                      </div>
                      <span className="text-sm font-semibold text-gray-700 hidden sm:block">{userName}</span>
                    </div>
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-sm shadow-inner">
                      U
                    </div>
                  )}
                  {onLogout && (
                    <button onClick={onLogout} className="text-sm text-gray-500 hover:text-red-600 transition-colors font-medium ml-2">
                      Logout
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 overflow-hidden">
        <div className="text-center mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-3 sm:mb-4">
            AI-Powered Room Visualization
          </h1>
          <p className="text-gray-500 text-sm sm:text-base max-w-xl mx-auto leading-relaxed">
            Experience the future of interior design. Our advanced AI automatically detects walls and floors in your photos, allowing for instant, realistic material application.
          </p>
        </div>

        <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-6">
          <button
            onClick={onCustomAI}
            className="group relative bg-white p-6 sm:p-8 rounded-2xl border-2 border-dashed border-blue-200 hover:border-blue-500 transition-all duration-300 shadow-sm hover:shadow-xl flex flex-col items-center text-center overflow-hidden active:scale-[0.98]"
          >
            <div className="absolute inset-0 bg-blue-50/50 opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="relative z-10 w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center text-white mb-4 shadow-lg group-hover:rotate-6 transition-transform">
              <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
            </div>
            <div className="relative z-10">
              <h2 className="text-xl font-bold text-gray-900 mb-2">Launch Studio Visualizer</h2>
              <p className="text-gray-500 text-sm">
                Upload your room photo and use our precision manual editing tools.
              </p>
            </div>
            <div className="mt-4 flex items-center gap-2 text-blue-600 font-bold text-sm">
              <span>Start Designing Now</span>
              <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
            </div>
          </button>

          <button
            onClick={onCopilot}
            className="group relative bg-slate-900 p-6 sm:p-8 rounded-2xl border-2 border-transparent hover:border-blue-500/50 transition-all duration-300 shadow-2xl hover:shadow-blue-500/20 flex flex-col items-center text-center overflow-hidden active:scale-[0.98]"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-blue-600/20 to-purple-600/20 opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="relative z-10 w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center text-white mb-4 shadow-[0_10px_20px_rgba(37,99,235,0.4)] group-hover:scale-110 transition-transform">
              <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
              </svg>
            </div>
            <div className="relative z-10">
              <h2 className="text-xl font-bold text-white mb-2">Try AI Interior Copilot</h2>
              <p className="text-slate-400 text-sm">
                Redesign your space using conversational AI and generative magic.
              </p>
            </div>
            <div className="mt-4 flex items-center gap-2 text-blue-400 font-bold text-sm">
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                Instant AI Generation
              </span>
              <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
            </div>
          </button>
        </div>

        <div className="mt-8 sm:mt-10 grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 w-full max-w-4xl">
           <Feature icon="⚡" title="Real-time" desc="Instant feedback as you change materials." />
           <Feature icon="🎯" title="Precise" desc="AI-driven edge detection for sharp results." />
           <Feature icon="✨" title="Simple" desc="No technical skills required. Just upload and click." />
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-gray-200 bg-white shrink-0">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 sm:py-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-2 sm:gap-4">
            <p className="text-[10px] sm:text-xs text-gray-400">
              Powered by Studio Editor AI
            </p>
            <div className="flex items-center gap-4 sm:gap-6">
              {showAuth && onAdmin && <button onClick={onAdmin} className="text-[10px] sm:text-xs text-gray-300 hover:text-gray-500 transition-colors">Admin Login</button>}
              <a href="#" className="text-[10px] sm:text-xs text-gray-400 hover:text-gray-600 transition-colors">Privacy</a>
              <a href="#" className="text-[10px] sm:text-xs text-gray-400 hover:text-gray-600 transition-colors">Terms</a>
              <a href="#" className="text-[10px] sm:text-xs text-gray-400 hover:text-gray-600 transition-colors">Support</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

function Feature({ icon, title, desc }: { icon: string, title: string, desc: string }) {
  return (
    <div className="text-center p-6 bg-white rounded-2xl shadow-sm border border-gray-100">
      <div className="text-3xl mb-3">{icon}</div>
      <h3 className="font-bold text-gray-900 mb-1">{title}</h3>
      <p className="text-xs text-gray-500">{desc}</p>
    </div>
  )
}
