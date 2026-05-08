import React from 'react'
import { Sparkles, Home, Upload, Palette, Wand2, ArrowRight, Zap, CheckCircle2 } from 'lucide-react'

interface LandingPageProps {
  onNavigate: (route: string) => void;
}

export default function LandingPage({ onNavigate }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-[#020617] text-white font-sans flex flex-col selection:bg-blue-500/30">
      {/* Decorative Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-600/10 blur-[120px] rounded-full"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/10 blur-[120px] rounded-full"></div>
        <div className="absolute top-[20%] right-[10%] w-[30%] h-[30%] bg-emerald-600/5 blur-[120px] rounded-full"></div>
      </div>

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-[#020617]/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-violet-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-900/20">
                <Home className="text-white" size={20} />
              </div>
              <div className="flex flex-col">
                <span className="text-xl font-black tracking-tight text-white">Ideal Visualizer</span>
                <span className="text-[10px] uppercase tracking-widest text-blue-400 font-bold leading-none">AI Driven Studio</span>
              </div>
            </div>
            
            <nav className="hidden md:flex items-center gap-8">
              <a href="#" className="text-sm font-semibold text-slate-400 hover:text-white transition-colors">How it works</a>
              <a href="#" className="text-sm font-semibold text-slate-400 hover:text-white transition-colors">Pricing</a>
              <a href="#" className="text-sm font-semibold text-slate-400 hover:text-white transition-colors">Showcase</a>
            </nav>

            <div className="flex items-center gap-4">
               <button 
                onClick={() => onNavigate('home')}
                className="text-sm font-bold text-slate-300 hover:text-white px-4 py-2"
               >
                 Login
               </button>
               <button 
                onClick={() => onNavigate('copilot')}
                className="bg-white text-black px-6 py-2.5 rounded-full font-bold text-sm hover:bg-slate-100 transition-all active:scale-95 shadow-xl"
               >
                 Launch App
               </button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="relative pt-32 lg:pt-48 pb-20 px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-bold uppercase tracking-widest mb-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <Sparkles size={14} />
            <span>The Future of Interior Design is Here</span>
          </div>
          
          <h1 className="text-5xl lg:text-8xl font-black tracking-tighter text-white mb-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
            Design Your Dream Space <br />
            <span className="bg-gradient-to-r from-blue-400 via-violet-400 to-emerald-400 bg-clip-text text-transparent">With Conversational AI</span>
          </h1>
          
          <p className="max-w-2xl mx-auto text-lg lg:text-xl text-slate-400 leading-relaxed mb-12 animate-in fade-in slide-in-from-bottom-12 duration-1000">
            Upload a photo and chat with our AI to redesign your room. From luxury kitchen makeovers to minimalistic bedroom transformations—all in seconds.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-6 animate-in fade-in slide-in-from-bottom-16 duration-1000">
            <button 
              onClick={() => onNavigate('copilot')}
              className="w-full sm:w-auto px-10 py-5 bg-gradient-to-r from-blue-600 to-violet-600 rounded-2xl font-black text-xl flex items-center justify-center gap-3 shadow-[0_20px_50px_rgba(37,99,235,0.3)] hover:shadow-[0_20px_60px_rgba(37,99,235,0.5)] transition-all active:scale-[0.98] group"
            >
              <Wand2 size={24} />
              Try AI Copilot
              <ArrowRight className="group-hover:translate-x-1 transition-transform" />
            </button>
            
            <button 
              onClick={() => onNavigate('home')}
              className="w-full sm:w-auto px-10 py-5 bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl font-black text-xl hover:bg-white/10 transition-all flex items-center justify-center gap-3 shadow-2xl active:scale-[0.98]"
            >
              <Palette size={24} />
              Material Studio
            </button>
          </div>

          {/* Trust Badge / Stats */}
          <div className="mt-24 grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto">
             <StatItem value="10k+" label="Rooms Redesigned" />
             <StatItem value="500+" label="AI Textures" />
             <StatItem value="99.9%" label="Accuracy" />
             <StatItem value="24/7" label="AI Assistant" />
          </div>
        </div>
      </main>

      {/* Feature Showcase */}
      <section className="py-32 px-6 lg:px-8 border-t border-white/5 relative bg-[#020617]/50">
         <div className="max-w-7xl mx-auto">
            <div className="flex flex-col lg:flex-row gap-16 items-center">
               <div className="lg:w-1/2">
                  <h2 className="text-4xl lg:text-6xl font-black tracking-tight mb-8">
                     Room Understanding <br />
                     <span className="text-blue-500">Meets Generative Art</span>
                  </h2>
                  <div className="space-y-6">
                     <FeatureItem 
                      icon={<Upload className="text-blue-400" />} 
                      title="Upload & Analyze" 
                      description="Our YOLO-SAM pipeline identifies walls, cabinets, and furniture with pixel-perfect precision." 
                     />
                     <FeatureItem 
                      icon={<Zap className="text-emerald-400" />} 
                      title="Instant Preview" 
                      description="See architectural-grade renders in real-time with our depth-aware texture engine." 
                     />
                     <FeatureItem 
                      icon={<Wand2 className="text-purple-400" />} 
                      title="Generative Overhaul" 
                      description="Use natural language to trigger complete room redesigns via DALL-E 3 and SDXL." 
                     />
                  </div>
               </div>
               <div className="lg:w-1/2 relative group">
                  <div className="absolute -inset-4 bg-gradient-to-r from-blue-600 to-violet-600 rounded-[2.5rem] blur-2xl opacity-20 group-hover:opacity-40 transition-opacity"></div>
                  <div className="relative aspect-[4/3] rounded-[2rem] overflow-hidden border border-white/10 shadow-2xl">
                     <img 
                      src="https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?w=1200" 
                      className="w-full h-full object-cover transition-transform duration-1000 group-hover:scale-105"
                      alt="AI Interior Showcase"
                     />
                     <div className="absolute inset-0 bg-gradient-to-t from-[#020617] via-transparent to-transparent"></div>
                     <div className="absolute bottom-8 left-8 right-8 p-6 bg-black/40 backdrop-blur-xl border border-white/10 rounded-2xl">
                        <div className="flex items-center gap-4 mb-3">
                           <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-[10px] font-bold">AI</div>
                           <span className="text-xs font-bold uppercase tracking-widest text-slate-400">Prompt Applied</span>
                        </div>
                        <p className="text-lg font-bold text-white italic">"Convert this to a luxury modern kitchen with white marble and gold accents"</p>
                     </div>
                  </div>
               </div>
            </div>
         </div>
      </section>

      {/* CTA Footer */}
      <footer className="py-20 border-t border-white/5 bg-[#020617]">
         <div className="max-w-7xl mx-auto px-6 lg:px-8 text-center">
            <h2 className="text-3xl font-bold mb-8">Ready to transform your home?</h2>
            <button 
              onClick={() => onNavigate('copilot')}
              className="px-12 py-5 bg-white text-black rounded-2xl font-black text-xl hover:bg-slate-100 transition-all active:scale-95 shadow-2xl"
            >
              Get Started for Free
            </button>
            <p className="mt-12 text-slate-500 text-sm">© 2026 Ideal Visualizer AI. All rights reserved.</p>
         </div>
      </footer>
    </div>
  )
}

function StatItem({ value, label }: { value: string, label: string }) {
  return (
    <div className="flex flex-col items-center">
      <span className="text-3xl lg:text-4xl font-black text-white mb-1">{value}</span>
      <span className="text-xs font-bold text-slate-500 uppercase tracking-widest text-center">{label}</span>
    </div>
  )
}

function FeatureItem({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) {
  return (
    <div className="flex gap-6 items-start">
      <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center shrink-0 border border-white/10">
        {icon}
      </div>
      <div>
        <h4 className="text-xl font-bold text-white mb-2">{title}</h4>
        <p className="text-slate-400 leading-relaxed">{description}</p>
      </div>
    </div>
  )
}
