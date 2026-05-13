import React, { useRef } from 'react'
import { Sparkles, Home, Upload, Palette, ArrowRight, Camera, Image as ImageIcon, CheckCircle2, Shield, Layers, MousePointer2, Wand2 } from 'lucide-react'

interface LandingPageProps {
  onNavigate: (route: string, data?: any) => void;
}

export default function LandingPage({ onNavigate }: LandingPageProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>, isCamera: boolean) => {
    const file = e.target.files?.[0];
    if (file) {
      onNavigate('custom', file);
    }
  };

  return (
    <div className="min-h-screen bg-[#fcfcfc] text-[#1a1a1a] font-sans flex flex-col selection:bg-stone-200">
      {/* Subtle Texture Overlay */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.03]" style={{ backgroundImage: 'url("https://www.transparenttextures.com/patterns/natural-paper.png")' }}></div>

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-xl border-b border-stone-100">
        <div className="max-w-7xl mx-auto px-6 lg:px-12">
          <div className="flex items-center justify-between h-20">
            <div className="flex items-center gap-4">
              <div className="w-8 h-8 bg-[#1a1a1a] rounded flex items-center justify-center">
                <Home className="text-white" size={16} />
              </div>
              <div className="flex flex-col">
                <span className="text-lg font-bold tracking-tight text-[#1a1a1a] font-serif">Ideal Visualizer</span>
                <span className="text-[9px] uppercase tracking-[0.2em] text-stone-400 font-medium leading-none">Interior Intelligence</span>
              </div>
            </div>

            <nav className="hidden lg:flex items-center gap-12">
              <a href="#" className="text-xs font-bold uppercase tracking-widest text-stone-400 hover:text-[#1a1a1a] transition-colors">Studio</a>
              <a href="#" className="text-xs font-bold uppercase tracking-widest text-stone-400 hover:text-[#1a1a1a] transition-colors">Materials</a>
              <a href="#" className="text-xs font-bold uppercase tracking-widest text-stone-400 hover:text-[#1a1a1a] transition-colors">Portfolio</a>
            </nav>

            <div className="flex items-center gap-6">
              <button
                onClick={() => onNavigate('home')}
                className="hidden sm:block text-xs font-bold uppercase tracking-widest text-stone-400 hover:text-[#1a1a1a] transition-colors"
              >
                Sign In
              </button>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="bg-[#1a1a1a] text-white px-8 py-3 rounded-none font-bold text-xs uppercase tracking-widest hover:bg-stone-800 transition-all active:scale-95 shadow-sm"
              >
                Launch Editor
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="relative pt-28 lg:pt-36 pb-20 px-6 lg:px-12">
        <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-20 items-center">
          <div className="flex flex-col items-start text-left">
            <div className="inline-flex items-center gap-3 px-0 py-2 text-stone-400 text-[10px] font-bold uppercase tracking-[0.3em] mb-6">
              <div className="w-8 h-px bg-stone-200"></div>
              <span>Atelier of Vision</span>
            </div>

            <h1 className="text-6xl lg:text-8xl font-medium tracking-tight text-[#1a1a1a] mb-10 leading-[0.95] font-serif">
              Design with <br />
              <span className="italic text-stone-400">Pure Precision.</span>
            </h1>

            <p className="max-w-md text-lg text-stone-600 leading-relaxed mb-12 font-light">
              Transform architectural spaces with our high-fidelity material visualizer. Professional-grade rendering for modern interiors.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
              <button
                onClick={() => cameraInputRef.current?.click()}
                className="flex items-center justify-center gap-3 px-10 py-5 bg-[#1a1a1a] text-white text-xs font-bold uppercase tracking-widest hover:bg-stone-800 transition-all shadow-lg animate-pulse-subtle"
              >
                <Camera size={18} />
                Capture Room
                <input
                  type="file"
                  ref={cameraInputRef}
                  className="hidden"
                  accept="image/*"
                  capture="environment"
                  onChange={(e) => handleFileChange(e, true)}
                />
              </button>

              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center justify-center gap-3 px-10 py-5 bg-white border border-stone-200 text-[#1a1a1a] text-xs font-bold uppercase tracking-widest hover:bg-stone-50 transition-all"
              >
                <Upload size={18} />
                Upload Image
                <input
                  type="file"
                  ref={fileInputRef}
                  className="hidden"
                  accept="image/*"
                  onChange={(e) => handleFileChange(e, false)}
                />
              </button>
            </div>

            {/* AI Copilot Button */}
            <button
              onClick={() => onNavigate('copilot')}
              className="mt-4 flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white text-xs font-bold uppercase tracking-widest rounded-sm shadow-lg shadow-violet-500/20 transition-all active:scale-95 group"
            >
              <Wand2 size={18} className="group-hover:rotate-12 transition-transform" />
              AI Copilot Designer
              <ArrowRight size={16} className="opacity-50 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
            </button>
          </div>

          <div className="relative group">
            <div className="absolute -inset-4 bg-stone-100 rounded-sm scale-95 group-hover:scale-100 transition-transform duration-1000 -z-10"></div>
            <div className="aspect-[4/5] bg-stone-50 overflow-hidden shadow-2xl relative">
              <img
                src="https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?w=1200"
                className="w-full h-full object-cover grayscale-[0.3] group-hover:grayscale-0 transition-all duration-[2s]"
                alt="Minimalist Interior"
              />
              <div className="absolute inset-0 border-[24px] border-white/10 pointer-events-none"></div>
              <div className="absolute bottom-12 right-0 bg-white p-8 shadow-2xl max-w-xs translate-x-12 hidden lg:block">
                <p className="text-[10px] font-bold uppercase tracking-widest text-stone-300 mb-4">Current Palette</p>
                <div className="flex gap-2 mb-6">
                  <div className="w-8 h-8 bg-stone-800"></div>
                  <div className="w-8 h-8 bg-stone-400"></div>
                  <div className="w-8 h-8 bg-stone-200"></div>
                  <div className="w-8 h-8 bg-[#fdfdfb] border border-stone-100"></div>
                </div>
                <p className="text-sm font-medium text-stone-600 leading-relaxed italic">
                  "Simplicity is the ultimate sophistication."
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Feature Section - Atelier Style */}
      <section className="py-20 px-6 lg:px-12 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-16 lg:gap-24">
            <FeatureCard
              number="01"
              title="Neural Texture Mapping"
              description="Our AI understands the geometry of your room, wrapping textures naturally around corners and perspectives."
            />
            <FeatureCard
              number="02"
              title="Material Fidelity"
              description="Library of physically-based materials that react to lighting and shadows with photorealistic accuracy."
            />
            <FeatureCard
              number="03"
              title="Design Continuity"
              description="Seamlessly save and export your visualizations to share with clients, architects, or showrooms."
            />
          </div>
        </div>
      </section>

      {/* The Process - NEW CONTENT */}
      <section className="py-20 px-6 lg:px-12 bg-stone-50 border-y border-stone-100">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col items-center text-center mb-16">
            <h2 className="text-sm font-bold text-stone-400 uppercase tracking-[0.4em] mb-4">The Process</h2>
            <p className="text-2xl font-serif italic text-stone-600">Simplicity in every step.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-12">
            <div className="flex flex-col items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-white border border-stone-200 flex items-center justify-center text-stone-300">
                <Camera size={20} />
              </div>
              <h4 className="text-[10px] font-bold uppercase tracking-widest">Photograph</h4>
            </div>
            <div className="flex flex-col items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-white border border-stone-200 flex items-center justify-center text-stone-300">
                <MousePointer2 size={20} />
              </div>
              <h4 className="text-[10px] font-bold uppercase tracking-widest">Select Area</h4>
            </div>
            <div className="flex flex-col items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-white border border-stone-200 flex items-center justify-center text-stone-300">
                <Palette size={20} />
              </div>
              <h4 className="text-[10px] font-bold uppercase tracking-widest">Apply Design</h4>
            </div>
            <div className="flex flex-col items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-white border border-stone-200 flex items-center justify-center text-stone-300">
                <CheckCircle2 size={20} />
              </div>
              <h4 className="text-[10px] font-bold uppercase tracking-widest">Export Vision</h4>
            </div>
          </div>
        </div>
      </section>

      {/* Second Hero / Showcase */}
      <section className="py-20 px-6 lg:px-12 border-t border-stone-100">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col lg:flex-row-reverse gap-24 items-center">
            <div className="lg:w-1/2 flex flex-col items-start">
              <h2 className="text-4xl lg:text-5xl font-medium tracking-tight mb-10 font-serif leading-tight">
                Beyond Simple Overlays. <br />
                <span className="text-stone-400 italic">True Materiality.</span>
              </h2>
              <p className="text-stone-600 text-lg leading-relaxed mb-12 font-light">
                We don't just change colors. We change the soul of the space. Every stone grain, every paint matte, and every tile reflection is calculated to match the original environment.
              </p>
              <button
                onClick={() => onNavigate('home')}
                className="flex items-center gap-4 text-[#1a1a1a] font-bold text-xs uppercase tracking-[0.2em] group"
              >
                Explore Studio Showcase
                <div className="w-10 h-[1px] bg-[#1a1a1a] group-hover:w-16 transition-all"></div>
              </button>
            </div>
            <div className="lg:w-1/2">
              <div className="aspect-[16/10] bg-stone-100 overflow-hidden shadow-sm group">
                <img
                  src="https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?w=1200"
                  className="w-full h-full object-cover transition-transform duration-[3s] group-hover:scale-105"
                  alt="Interior Detail"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer - Minimalist */}
      <footer className="py-24 border-t border-stone-100 bg-[#fcfcfc]">
        <div className="max-w-7xl mx-auto px-6 lg:px-12">
          <div className="flex flex-col md:flex-row justify-between items-start gap-16">
            <div className="flex flex-col gap-6">
              <div className="flex items-center gap-3">
                <div className="w-6 h-6 bg-[#1a1a1a] rounded-sm"></div>
                <span className="text-lg font-bold text-[#1a1a1a] font-serif">Ideal Visualizer</span>
              </div>
              <p className="text-xs text-stone-400 uppercase tracking-widest max-w-xs leading-loose">
                The essential tool for modern interior visualization. Precision. Clarity. Vision.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-20">
              <div className="flex flex-col gap-6">
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-stone-300">Navigation</h4>
                <ul className="flex flex-col gap-4 text-xs font-bold text-stone-500">
                  <li><a href="#" className="hover:text-[#1a1a1a] transition-colors">Studio</a></li>
                  <li><a href="#" className="hover:text-[#1a1a1a] transition-colors">Materials</a></li>
                  <li><a href="#" className="hover:text-[#1a1a1a] transition-colors">Contact</a></li>
                </ul>
              </div>
              <div className="flex flex-col gap-6">
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-stone-300">Social</h4>
                <ul className="flex flex-col gap-4 text-xs font-bold text-stone-500">
                  <li><a href="#" className="hover:text-[#1a1a1a] transition-colors">Instagram</a></li>
                  <li><a href="#" className="hover:text-[#1a1a1a] transition-colors">LinkedIn</a></li>
                  <li><a href="#" className="hover:text-[#1a1a1a] transition-colors">Behance</a></li>
                </ul>
              </div>
            </div>
          </div>
          <div className="mt-24 pt-12 border-t border-stone-100 flex justify-between items-center">
            <span className="text-[10px] font-bold text-stone-300 uppercase tracking-widest">© 2026 Ideal Visualizer AI</span>
            <div className="flex gap-8">
              <a href="#" className="text-[10px] font-bold text-stone-300 uppercase tracking-widest hover:text-[#1a1a1a]">Privacy</a>
              <a href="#" className="text-[10px] font-bold text-stone-300 uppercase tracking-widest hover:text-[#1a1a1a]">Terms</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({ number, title, description }: { number: string, title: string, description: string }) {
  return (
    <div className="flex flex-col gap-8 group">
      <div className="text-6xl font-serif text-stone-100 group-hover:text-stone-200 transition-colors duration-500">
        {number}
      </div>
      <div>
        <h4 className="text-lg font-bold text-[#1a1a1a] mb-4 tracking-tight">{title}</h4>
        <p className="text-stone-500 text-sm leading-relaxed font-light">{description}</p>
      </div>
      <div className="w-12 h-[1px] bg-stone-200 group-hover:w-full transition-all duration-700"></div>
    </div>
  )
}
