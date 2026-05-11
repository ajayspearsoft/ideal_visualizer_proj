import React from 'react'
import { Home, Upload, ArrowRight, Shield, Zap, Sparkles } from 'lucide-react'

export default function RoomSelect({ 
  onSelect, 
  onCustomAI, 
  onAdmin, 
  onLogout, 
  userName, 
  showAuth = false 
}: { 
  onSelect: (room: any) => void, 
  onCustomAI?: () => void, 
  onAdmin?: () => void, 
  onLogout?: () => void, 
  userName?: string,
  showAuth?: boolean
}) {
  return (
    <div className="min-h-screen bg-[#fdfdfb] text-[#1a1a1a] font-sans flex flex-col">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-stone-100 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 lg:px-12">
          <div className="flex items-center justify-between h-20">
            <div className="flex items-center gap-4">
              <div className="w-8 h-8 bg-[#1a1a1a] rounded-sm flex items-center justify-center">
                <Home className="text-white" size={16} />
              </div>
              <span className="text-lg font-bold tracking-tight text-[#1a1a1a] font-serif">
                Studio Editor
              </span>
            </div>
            {showAuth && (
              <div className="flex items-center gap-6 pl-6 border-l border-stone-100">
                {userName ? (
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-sm bg-stone-100 flex items-center justify-center text-stone-600 font-bold text-xs shadow-sm uppercase">
                      {userName.charAt(0)}
                    </div>
                    <span className="text-[10px] font-bold uppercase tracking-widest text-stone-500 hidden sm:block">{userName}</span>
                  </div>
                ) : (
                  <div className="w-8 h-8 rounded-sm bg-stone-100 flex items-center justify-center text-stone-600 font-bold text-xs">
                    U
                  </div>
                )}
                {onLogout && (
                  <button onClick={onLogout} className="text-[10px] font-bold uppercase tracking-widest text-stone-400 hover:text-red-500 transition-colors">
                    Logout
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center max-w-7xl mx-auto px-6 lg:px-12 py-20 w-full">
        <div className="text-center mb-20">
          <div className="inline-flex items-center gap-3 text-stone-300 text-[10px] font-bold uppercase tracking-[0.3em] mb-6 justify-center">
            <div className="w-8 h-px bg-stone-200"></div>
            <span>Material Workspace</span>
            <div className="w-8 h-px bg-stone-200"></div>
          </div>
          <h1 className="text-4xl lg:text-6xl font-medium text-[#1a1a1a] mb-6 font-serif">
            Welcome to the Studio.
          </h1>
          <p className="text-stone-400 text-lg max-w-xl mx-auto leading-relaxed font-light italic">
            Begin your visualization journey by selecting a workspace or uploading your own architectural photography.
          </p>
        </div>

        <div className="w-full max-w-2xl">
          <button
            onClick={onCustomAI}
            className="group relative w-full bg-white p-12 lg:p-16 border border-stone-100 hover:border-stone-300 transition-all duration-500 shadow-sm hover:shadow-2xl flex flex-col items-center text-center overflow-hidden active:scale-[0.99]"
          >
            <div className="absolute top-0 left-0 w-1 h-0 bg-[#1a1a1a] group-hover:h-full transition-all duration-500"></div>
            <div className="w-20 h-20 bg-stone-50 border border-stone-100 rounded-sm flex items-center justify-center text-[#1a1a1a] mb-10 transition-transform duration-700 group-hover:rotate-90">
              <Upload size={32} strokeWidth={1} />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-[#1a1a1a] mb-4 font-serif">Launch Studio Visualizer</h2>
              <p className="text-stone-400 text-sm leading-relaxed max-w-xs mx-auto font-light">
                Upload custom photography for professional-grade material application and precision wall mapping.
              </p>
            </div>
            <div className="mt-10 flex items-center gap-4 text-[#1a1a1a] font-bold text-xs uppercase tracking-widest group">
              <span>Enter Workspace</span>
              <div className="w-6 h-[1px] bg-[#1a1a1a] group-hover:w-12 transition-all"></div>
            </div>
          </button>
        </div>

        <div className="mt-24 grid grid-cols-1 sm:grid-cols-3 gap-12 w-full max-w-4xl">
           <Feature icon={<Zap size={16} />} title="Real-time" desc="Instant feedback on every material selection." />
           <Feature icon={<Shield size={16} />} title="Precise" desc="Architectural accuracy in every render." />
           <Feature icon={<Sparkles size={16} />} title="Atelier" desc="Professional tools for high-end design." />
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-stone-100 bg-white">
        <div className="max-w-7xl mx-auto px-12 py-10 flex flex-col sm:flex-row items-center justify-between gap-6">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-stone-300">
            Powered by Ideal Studio AI
          </p>
          <div className="flex items-center gap-10">
            {onAdmin && <button onClick={onAdmin} className="text-[10px] font-bold uppercase tracking-widest text-stone-300 hover:text-stone-500 transition-colors">Admin Portal</button>}
            <div className="flex gap-6">
              <a href="#" className="text-[10px] font-bold uppercase tracking-widest text-stone-300 hover:text-[#1a1a1a] transition-colors">Privacy</a>
              <a href="#" className="text-[10px] font-bold uppercase tracking-widest text-stone-300 hover:text-[#1a1a1a] transition-colors">Terms</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

function Feature({ icon, title, desc }: { icon: React.ReactNode, title: string, desc: string }) {
  return (
    <div className="flex flex-col items-center text-center group">
      <div className="w-10 h-10 border border-stone-100 rounded-full flex items-center justify-center text-stone-300 mb-6 group-hover:bg-stone-50 group-hover:text-[#1a1a1a] transition-all">
        {icon}
      </div>
      <h3 className="text-xs font-bold text-[#1a1a1a] uppercase tracking-widest mb-3">{title}</h3>
      <p className="text-[11px] text-stone-400 leading-relaxed font-light max-w-[160px]">{desc}</p>
    </div>
  )
}
