import { useState, useEffect, useRef } from 'react'
import { API_BASE_URL } from '../config'
import { 
  Send, 
  Upload, 
  Trash2, 
  RotateCcw, 
  Download, 
  Layers, 
  Sparkles, 
  MousePointer2, 
  ChevronRight,
  MessageSquare,
  Image as ImageIcon,
  Check,
  X,
  Loader2,
  Maximize2,
  History,
  Palette
} from 'lucide-react'

interface Message {
  role: 'user' | 'ai';
  content: string;
  timestamp: number;
  image?: string;
  task?: any;
}

export default function AIInteriorCopilot({ onBack, userId, userName }: { onBack: () => void, userId?: string | number, userName?: string }) {
  // State
  const [roomImage, setRoomImage] = useState<File | null>(null)
  const [roomPreview, setRoomPreview] = useState<string | null>(null)
  const [resultImage, setResultImage] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [processing, setProcessing] = useState(false)
  const [chatOpen, setChatOpen] = useState(true)
  const [messages, setMessages] = useState<Message[]>([
    { role: 'ai', content: "Hello! I'm your AI Interior Design Copilot. Upload a photo of your room to get started, or just tell me what you'd like to redesign!", timestamp: Date.now() }
  ])
  const [input, setInput] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [activeTask, setActiveTask] = useState<any>(null)
  const [history, setHistory] = useState<string[]>([])
  
  // Refs
  const scrollRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const imageRef = useRef<HTMLImageElement>(null)

  // Auto-scroll chat
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // Handle Image Upload
  const handleUpload = async (file: File) => {
    setIsUploading(true)
    setRoomImage(file)
    const preview = URL.createObjectURL(file)
    setRoomPreview(preview)
    setResultImage(null)
    
    try {
      const formData = new FormData()
      formData.append('wall_image', file)
      
      const response = await fetch(`${API_BASE_URL}/api/upload-room`, {
        method: 'POST',
        body: formData
      })
      
      const data = await response.json()
      if (data.success) {
        setSessionId(data.session_id)
        setMessages(prev => [...prev, { 
          role: 'ai', 
          content: "Room uploaded successfully! I've analyzed your space. You can now ask me to 'Make it a luxury kitchen', 'Change wall to blue', or 'Add more cabinets'.", 
          timestamp: Date.now() 
        }])
      } else {
        throw new Error(data.error)
      }
    } catch (err: any) {
      setMessages(prev => [...prev, { role: 'ai', content: `Error: ${err.message}`, timestamp: Date.now() }])
    } finally {
      setIsUploading(false)
    }
  }

  // Handle Chat Submit
  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!input.trim() || processing) return

    const userMessage: Message = { role: 'user', content: input, timestamp: Date.now() }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setProcessing(true)

    try {
      // Step 1: Parse the prompt via backend
      const parseRes = await fetch(`${API_BASE_URL}/api/ai-chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: input, session_id: sessionId })
      })
      const parseData = await parseRes.json()
      
      if (!parseData.success) throw new Error(parseData.error)

      const task = parseData.task
      setActiveTask(task)
      
      setMessages(prev => [...prev, { role: 'ai', content: parseData.response, timestamp: Date.now(), task: task.action !== 'chat' ? task : null }])

      // Step 2: Route to appropriate engine
      if (task.action === 'chat') {
        setProcessing(false)
        return
      }

      if (!sessionId || !roomPreview) {
        setMessages(prev => [...prev, { role: 'ai', content: "Please upload a photo of your room first so I can see what we're working with!", timestamp: Date.now() }])
        setProcessing(false)
        return
      }

      if (task.action === 'redesign' || task.action === 'add' || task.action === 'remove') {
        // Use Generative AI (DALL-E 3)
        const redesignRes = await fetch(`${API_BASE_URL}/api/ai-redesign`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            prompt: input, 
            image_url: roomPreview,
            session_id: sessionId,
            target: task.target
          })
        })
        const redesignData = await redesignRes.json()
        
        if (redesignData.success) {
          setResultImage(redesignData.resultUrl)
          setHistory(prev => [redesignData.resultUrl, ...prev])
          setMessages(prev => [...prev, { 
            role: 'ai', 
            content: redesignData.message, 
            timestamp: Date.now(),
            image: redesignData.resultUrl
          }])
        } else {
          throw new Error(redesignData.error)
        }
      } else if (task.action === 'recolor') {
        // Use Fast OpenCV Engine
        const color = task.color || '#3b82f6'
        const formData = new FormData()
        if (roomImage) formData.append('wall_image', roomImage)
        formData.append('session_id', sessionId || '')
        formData.append('texture_url', `https://www.thecolorapi.com/id?hex=${color.replace('#','')}&format=svg`)
        
        const processRes = await fetch(`${API_BASE_URL}/api/process-wall`, {
          method: 'POST',
          body: formData
        })
        const processData = await processRes.json()
        
        if (processData.resultUrl) {
          setResultImage(processData.resultUrl)
          setHistory(prev => [processData.resultUrl, ...prev])
          setMessages(prev => [...prev, { 
            role: 'ai', 
            content: "I've applied the color change! How does it look?", 
            timestamp: Date.now(),
            image: processData.resultUrl
          }])
        } else {
          throw new Error(processData.error)
        }
      }

    } catch (err: any) {
      setMessages(prev => [...prev, { role: 'ai', content: `Oops! Something went wrong: ${err.message}`, timestamp: Date.now() }])
    } finally {
      setProcessing(false)
      setActiveTask(null)
    }
  }

  const handleDownload = async () => {
    const img = resultImage || roomPreview
    if (!img) return
    const response = await fetch(img)
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ai_design_${Date.now()}.png`
    a.click()
  }

  return (
    <div className="h-screen bg-[#0f172a] text-white flex flex-col overflow-hidden font-sans">
      {/* Header */}
      <header className="h-16 shrink-0 border-b border-white/10 flex items-center justify-between px-6 bg-[#0f172a]/80 backdrop-blur-xl z-20">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="p-2 hover:bg-white/10 rounded-full transition-colors text-slate-400 hover:text-white">
            <X size={20} />
          </button>
          <div className="flex flex-col">
            <h1 className="text-lg font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">AI Interior Copilot</h1>
            <span className="text-[10px] text-slate-500 uppercase tracking-[0.2em] font-medium">Professional Redesign Studio</span>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="hidden md:flex items-center gap-3 px-4 py-1.5 bg-white/5 rounded-full border border-white/10">
            <div className={`w-2 h-2 rounded-full ${sessionId ? 'bg-emerald-500 shadow-[0_0_10px_#10b981]' : 'bg-slate-600'}`}></div>
            <span className="text-xs font-semibold text-slate-300">{sessionId ? 'AI Models Synced' : 'Awaiting Image'}</span>
          </div>
          
          <div className="flex items-center gap-2">
            <button onClick={handleDownload} disabled={!resultImage && !roomPreview} className="p-2.5 bg-white/5 hover:bg-white/10 rounded-xl transition-all text-slate-300 disabled:opacity-30 border border-white/10 shadow-lg active:scale-95">
              <Download size={18} />
            </button>
            <button className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 rounded-xl font-bold text-sm shadow-[0_10px_30px_rgba(37,99,235,0.3)] transition-all active:scale-95 flex items-center gap-2">
              <Sparkles size={16} />
              Save Design
            </button>
          </div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar - Assets & History */}
        <aside className="hidden lg:flex w-72 shrink-0 border-r border-white/10 flex-col bg-[#0f172a]/50">
          <div className="p-6 border-b border-white/10">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest flex items-center gap-2">
              <History size={14} /> History
            </h3>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
            {history.map((url, i) => (
              <div key={i} className="group relative aspect-video rounded-xl overflow-hidden border border-white/10 cursor-pointer hover:border-blue-500/50 transition-all shadow-lg" onClick={() => setResultImage(url)}>
                <img src={url} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <span className="text-[10px] font-bold uppercase tracking-widest">Restore</span>
                </div>
              </div>
            ))}
            {history.length === 0 && (
              <div className="h-40 flex flex-col items-center justify-center text-slate-600 border-2 border-dashed border-white/5 rounded-2xl">
                <ImageIcon size={24} className="mb-2 opacity-20" />
                <span className="text-xs font-medium">No history yet</span>
              </div>
            )}
          </div>
          
          <div className="p-6 border-t border-white/10 bg-[#0f172a]">
             <div className="p-4 bg-blue-500/10 rounded-2xl border border-blue-500/20">
                <p className="text-[10px] font-bold text-blue-400 uppercase tracking-widest mb-1">Pro Tip</p>
                <p className="text-xs text-slate-400 leading-relaxed">Try asking for "Luxury marble kitchen" or "Modern bedroom with warm lighting".</p>
             </div>
          </div>
        </aside>

        {/* Main Viewport */}
        <main className="flex-1 relative flex flex-col bg-[#020617]">
          <div className="flex-1 relative p-6 flex items-center justify-center overflow-hidden">
             {!roomPreview ? (
               <div 
                 onClick={() => fileInputRef.current?.click()}
                 className="w-full max-w-3xl aspect-[16/10] border-4 border-dashed border-white/10 rounded-[3rem] flex flex-col items-center justify-center group hover:border-blue-500/50 hover:bg-blue-500/5 transition-all duration-500 cursor-pointer shadow-2xl relative overflow-hidden"
               >
                 {/* Decorative background sparks */}
                 <div className="absolute top-1/4 left-1/4 w-32 h-32 bg-blue-500/10 blur-[80px] group-hover:bg-blue-500/20 transition-all"></div>
                 <div className="absolute bottom-1/4 right-1/4 w-32 h-32 bg-emerald-500/10 blur-[80px] group-hover:bg-emerald-500/20 transition-all"></div>
                 
                 <div className="w-24 h-24 bg-white/5 rounded-3xl flex items-center justify-center mb-6 border border-white/10 group-hover:scale-110 group-hover:rotate-3 transition-all duration-500 shadow-2xl">
                    {isUploading ? <Loader2 className="animate-spin text-blue-400" size={40} /> : <Upload className="text-slate-400 group-hover:text-blue-400 transition-colors" size={40} />}
                 </div>
                 <h2 className="text-3xl font-black text-white mb-2 tracking-tight">Upload Your Space</h2>
                 <p className="text-slate-400 max-w-sm text-center leading-relaxed">Drag your room photo here or click to browse. We'll handle the rest.</p>
                 
                 <input ref={fileInputRef} type="file" className="hidden" accept="image/*" onChange={(e) => {
                   if (e.target.files?.[0]) handleUpload(e.target.files[0])
                 }} />
               </div>
             ) : (
               <div className="relative w-full h-full flex items-center justify-center animate-in fade-in zoom-in-95 duration-700">
                  <div className="relative max-w-full max-h-full rounded-2xl overflow-hidden shadow-[0_30px_100px_rgba(0,0,0,0.8)] border border-white/10 group">
                    <img 
                      ref={imageRef}
                      src={resultImage || roomPreview} 
                      className={`w-full h-full object-contain transition-all duration-500 ${processing ? 'brightness-50 blur-sm scale-105' : 'brightness-100 blur-0 scale-100'}`}
                      alt="Interior view"
                    />
                    
                    {processing && (
                      <div className="absolute inset-0 flex flex-col items-center justify-center z-20">
                         <div className="w-20 h-20 relative flex items-center justify-center">
                            <div className="absolute inset-0 border-4 border-blue-500/30 rounded-full"></div>
                            <div className="absolute inset-0 border-4 border-t-blue-500 rounded-full animate-spin"></div>
                            <Sparkles className="text-blue-400 animate-pulse" size={32} />
                         </div>
                         <div className="mt-6 text-center">
                            <h3 className="text-xl font-bold text-white mb-1">AI Copilot at work...</h3>
                            <p className="text-sm text-slate-400 px-10">
                              {activeTask?.action === 'redesign' ? 'Performing high-fidelity generative redesign' : 'Applying precise modifications to your space'}
                            </p>
                         </div>
                      </div>
                    )}
                    
                    {/* Floating Tools Over Image */}
                    <div className="absolute top-6 right-6 flex flex-col gap-3 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-4 group-hover:translate-x-0">
                       <button onClick={() => setResultImage(null)} className="w-10 h-10 bg-white/10 backdrop-blur-xl hover:bg-white/20 rounded-full flex items-center justify-center border border-white/10 shadow-xl transition-all" title="Reset View">
                          <RotateCcw size={18} />
                       </button>
                       <button className="w-10 h-10 bg-white/10 backdrop-blur-xl hover:bg-white/20 rounded-full flex items-center justify-center border border-white/10 shadow-xl transition-all" title="Full Screen">
                          <Maximize2 size={18} />
                       </button>
                    </div>

                    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-black/60 backdrop-blur-xl px-4 py-1.5 rounded-full border border-white/10 text-[10px] font-bold text-slate-400 uppercase tracking-widest shadow-2xl">
                       {resultImage ? 'AI Generated Preview' : 'Original Photo'}
                    </div>
                  </div>
               </div>
             )}
          </div>
        </main>

        {/* Right Sidebar - Chat Interface */}
        <aside className={`${chatOpen ? 'w-96' : 'w-0'} shrink-0 border-l border-white/10 flex flex-col transition-all duration-500 bg-[#0f172a] shadow-[-20px_0_50px_rgba(0,0,0,0.3)] z-10`}>
           <div className="p-6 border-b border-white/10 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3">
                 <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg">
                    <MessageSquare size={20} className="text-white" />
                 </div>
                 <div>
                    <h3 className="text-sm font-bold text-white tracking-tight">AI Assistant</h3>
                    <div className="flex items-center gap-1.5">
                       <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                       <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Online & Thinking</span>
                    </div>
                 </div>
              </div>
           </div>

           <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
              {messages.map((m, i) => (
                <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'} animate-in slide-in-from-bottom-2 duration-300`}>
                  <div className={`max-w-[85%] p-4 rounded-2xl text-sm leading-relaxed shadow-lg ${m.role === 'user' ? 'bg-blue-600 text-white rounded-tr-none' : 'bg-white/5 border border-white/10 text-slate-200 rounded-tl-none'}`}>
                     {m.content}
                     {m.task && (
                       <div className="mt-3 p-2 bg-black/20 rounded-lg border border-white/5 flex items-center gap-2">
                          <div className="p-1.5 bg-blue-500/20 rounded-md">
                             {m.task.action === 'recolor' ? <Palette size={14} className="text-blue-400" /> : <Sparkles size={14} className="text-emerald-400" />}
                          </div>
                          <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{m.task.action}: {m.task.target}</span>
                       </div>
                     )}
                  </div>
                  {m.image && (
                    <div className="mt-3 w-full max-w-[85%] aspect-video rounded-xl overflow-hidden border border-white/10 shadow-2xl animate-in zoom-in-95 duration-500">
                       <img src={m.image} className="w-full h-full object-cover" />
                    </div>
                  )}
                  <span className="text-[9px] font-bold text-slate-600 mt-2 uppercase tracking-widest">{m.role === 'ai' ? 'Copilot' : 'You'} • {new Date(m.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                </div>
              ))}
              {processing && (
                <div className="flex flex-col items-start animate-in fade-in duration-300">
                   <div className="bg-white/5 border border-white/10 p-4 rounded-2xl flex gap-2">
                      <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                      <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                      <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"></div>
                   </div>
                </div>
              )}
           </div>

           <div className="p-6 border-t border-white/10 bg-[#0f172a]/80 backdrop-blur-xl shrink-0">
              <form onSubmit={handleSubmit} className="relative">
                 <input 
                   type="text" 
                   value={input}
                   onChange={(e) => setInput(e.target.value)}
                   disabled={processing}
                   placeholder={roomPreview ? "Describe your dream room..." : "Upload a photo to begin chat..."}
                   className="w-full pl-6 pr-14 py-4 bg-white/5 border border-white/10 rounded-2xl text-sm focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-all placeholder:text-slate-600"
                 />
                 <button 
                  type="submit" 
                  disabled={!input.trim() || processing}
                  className="absolute right-2 top-2 w-10 h-10 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 text-white rounded-xl flex items-center justify-center transition-all shadow-lg active:scale-95"
                 >
                    <Send size={18} />
                 </button>
              </form>
              <div className="mt-4 flex flex-wrap gap-2">
                 {['Luxury Modern', 'Minimalist', 'Cozy Warm', 'Office Style'].map(suggestion => (
                   <button 
                    key={suggestion}
                    onClick={() => setInput(suggestion)}
                    disabled={!roomPreview || processing}
                    className="px-3 py-1 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-[10px] font-bold text-slate-400 hover:text-white transition-all disabled:opacity-20"
                   >
                     {suggestion}
                   </button>
                 ))}
              </div>
           </div>
        </aside>
      </div>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 5px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.1);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.2);
        }
      `}</style>
    </div>
  )
}
