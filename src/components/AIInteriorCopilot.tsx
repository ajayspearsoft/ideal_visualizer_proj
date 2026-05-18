import { useState, useRef } from 'react'
import { API_BASE_URL } from '../config'
import {
  Upload,
  Download,
  Sparkles,
  X,
  Loader2,
  ArrowLeft,
  Camera,
  Image as ImageIcon,
  ChevronDown,
  RotateCcw,
  Wand2,
  BrainCircuit,
  Eye,
  ListPlus
} from 'lucide-react'

const ROOM_OPTIONS = [
  { value: 'bedroom', label: 'Bedroom', emoji: '🛏️' },
  { value: 'living_room', label: 'Living Room / Hall', emoji: '🛋️' },
  { value: 'kitchen', label: 'Kitchen', emoji: '🍳' },
  { value: 'bathroom', label: 'Bathroom', emoji: '🚿' },
  { value: 'other', label: 'Other (Custom)', emoji: '✨' },
]

export default function AIInteriorCopilot({ onBack }: { onBack: () => void, userId?: string | number, userName?: string }) {
  const [roomImage, setRoomImage] = useState<File | null>(null)
  const [roomPreview, setRoomPreview] = useState<string | null>(null)
  const [resultImage, setResultImage] = useState<string | null>(null)
  const [roomType, setRoomType] = useState('bedroom')
  const [customPrompt, setCustomPrompt] = useState('')
  const [additionalPrompt, setAdditionalPrompt] = useState('')
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [history, setHistory] = useState<string[]>([])
  const [statusText, setStatusText] = useState('')
  const [currentPromptIndex, setCurrentPromptIndex] = useState<number>(-1)
  const [totalVariations, setTotalVariations] = useState<number>(0)
  
  // AI Intent State
  const [analyzing, setAnalyzing] = useState(false)
  const [aiIntent, setAiIntent] = useState<any>(null)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)

  const handleImageSelect = (file: File) => {
    setRoomImage(file)
    setRoomPreview(URL.createObjectURL(file))
    setResultImage(null)
    setError(null)
    setStatusText('')
    setAiIntent(null)
  }

  const handleAnalyze = async () => {
    if (!roomImage) {
      setError('Please upload a room image first')
      return
    }
    setAnalyzing(true)
    setError(null)
    setStatusText('AI is analyzing room structure & intent...')

    try {
      const formData = new FormData()
      formData.append('room_image', roomImage)
      formData.append('room_type', roomType)
      formData.append('additional_prompt', additionalPrompt)
      if (roomType === 'other') {
        formData.append('custom_prompt', customPrompt)
      }

      const response = await fetch(`${API_BASE_URL}/api/ai-copilot-analyze`, {
        method: 'POST',
        body: formData
      })

      const data = await response.json()

      if (data.success) {
        setAiIntent(data.intent)
        // Auto-fill the suggested prompt so the generation uses it
        if (data.intent.suggested_prompt && !additionalPrompt) {
          setAdditionalPrompt(data.intent.suggested_prompt)
        }
        setStatusText('✅ Intent Analysis Complete!')
      } else {
        throw new Error(data.error || 'Analysis failed')
      }
    } catch (err: any) {
      setError(err.message || 'Something went wrong')
      setStatusText('')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleGenerate = async (forcedIndex?: number) => {
    if (!roomImage) {
      setError('Please upload a room image first')
      return
    }
    setProcessing(true)
    setError(null)
    if (forcedIndex === undefined) {
      setResultImage(null)
    }
    setStatusText('Uploading image & analyzing room geometry...')

    try {
      const formData = new FormData()
      formData.append('room_image', roomImage)
      formData.append('room_type', roomType)
      formData.append('additional_prompt', additionalPrompt)
      
      const targetIndex = forcedIndex !== undefined ? forcedIndex : -1
      formData.append('prompt_index', targetIndex.toString())
      
      if (roomType === 'other') {
        formData.append('custom_prompt', customPrompt)
      }

      setStatusText('Running depth estimation & generating floor mask...')
      await new Promise(r => setTimeout(r, 800))
      setStatusText('Analyzing room layout & generating with Flux...')

      const response = await fetch(`${API_BASE_URL}/api/ai-copilot-generate`, {
        method: 'POST',
        body: formData
      })

      const data = await response.json()

      if (data.success) {
        setResultImage(data.result_url)
        setHistory(prev => [data.result_url, ...prev])
        setCurrentPromptIndex(data.prompt_index)
        setTotalVariations(data.total_variations)
        setStatusText('✅ AI room generated successfully!')
      } else {
        throw new Error(data.error || 'Generation failed')
      }
    } catch (err: any) {
      setError(err.message || 'Something went wrong')
      setStatusText('')
    } finally {
      setProcessing(false)
    }
  }

  const handleDownload = async () => {
    const img = resultImage
    if (!img) return
    try {
      const response = await fetch(img)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `ai_redesigned_room_${Date.now()}.png`
      a.click()
      window.URL.revokeObjectURL(url)
    } catch {
      window.open(img, '_blank')
    }
  }

  const handleReset = () => {
    setRoomImage(null)
    setRoomPreview(null)
    setResultImage(null)
    setError(null)
    setStatusText('')
    setAdditionalPrompt('')
    setCustomPrompt('')
    setAiIntent(null)
  }

  return (
    <div className="min-h-screen bg-[#070b14] text-white font-sans">
      {/* Header */}
      <header className="sticky top-0 z-50 h-16 border-b border-white/[0.06] flex items-center justify-between px-6 bg-[#070b14]/80 backdrop-blur-2xl">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="p-2 hover:bg-white/10 rounded-xl transition-colors text-slate-400 hover:text-white">
            <ArrowLeft size={20} />
          </button>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-600 flex items-center justify-center shadow-lg shadow-violet-500/20">
              <Wand2 size={18} className="text-white" />
            </div>
            <div className="flex flex-col">
              <h1 className="text-base font-bold bg-gradient-to-r from-violet-300 to-fuchsia-300 bg-clip-text text-transparent tracking-tight">AI Interior Copilot</h1>
              <span className="text-[9px] text-slate-500 uppercase tracking-[0.2em] font-semibold">Geometry-Locked Engine</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {resultImage && (
            <button onClick={handleDownload} className="flex items-center gap-2 px-5 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-xl text-emerald-400 text-xs font-bold uppercase tracking-wider transition-all active:scale-95">
              <Download size={15} />
              Download
            </button>
          )}
          <button onClick={handleReset} className="p-2.5 bg-white/5 hover:bg-white/10 rounded-xl transition-all text-slate-400 border border-white/[0.06]">
            <RotateCcw size={16} />
          </button>
        </div>
      </header>

      <div className="flex flex-col lg:flex-row h-[calc(100vh-64px)]">
        {/* Left Panel — Controls */}
        <aside className="w-full lg:w-[380px] shrink-0 border-r border-white/[0.06] bg-[#0a0f1a] overflow-y-auto">
          <div className="p-6 space-y-6">

            {/* Step 1: Upload */}
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400">
                <span className="w-5 h-5 rounded-md bg-violet-500/20 text-violet-400 flex items-center justify-center text-[10px] font-black">1</span>
                Upload Room Photo
              </label>

              {!roomPreview ? (
                <div className="border-2 border-dashed border-white/10 rounded-2xl p-8 flex flex-col items-center gap-4 hover:border-violet-500/30 hover:bg-violet-500/[0.02] transition-all group cursor-pointer"
                  onClick={() => fileInputRef.current?.click()}>
                  <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center group-hover:scale-110 group-hover:bg-violet-500/10 transition-all">
                    <Upload size={28} className="text-slate-500 group-hover:text-violet-400 transition-colors" />
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-semibold text-slate-300">Click to upload</p>
                    <p className="text-xs text-slate-600 mt-1">or use camera below</p>
                  </div>
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); cameraInputRef.current?.click() }}
                      className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-xs font-bold text-slate-300 flex items-center gap-2 transition-all"
                    >
                      <Camera size={14} /> Camera
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click() }}
                      className="px-4 py-2 bg-violet-600/20 hover:bg-violet-600/30 border border-violet-500/20 rounded-xl text-xs font-bold text-violet-300 flex items-center gap-2 transition-all"
                    >
                      <ImageIcon size={14} /> Gallery
                    </button>
                  </div>
                </div>
              ) : (
                <div className="relative group rounded-2xl overflow-hidden border border-white/10">
                  <img src={roomPreview} className="w-full aspect-video object-cover" alt="Room" />
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <button onClick={() => { setRoomImage(null); setRoomPreview(null); setResultImage(null) }}
                      className="px-4 py-2 bg-red-500/80 rounded-xl text-xs font-bold flex items-center gap-2">
                      <X size={14} /> Remove
                    </button>
                  </div>
                  <div className="absolute bottom-2 left-2 px-2 py-1 bg-black/60 backdrop-blur-sm rounded-lg text-[9px] font-bold text-emerald-400 uppercase tracking-widest">
                    ✓ Uploaded
                  </div>
                </div>
              )}

              <input ref={fileInputRef} type="file" className="hidden" accept="image/*"
                onChange={(e) => { if (e.target.files?.[0]) handleImageSelect(e.target.files[0]) }} />
              <input ref={cameraInputRef} type="file" className="hidden" accept="image/*" capture="environment"
                onChange={(e) => { if (e.target.files?.[0]) handleImageSelect(e.target.files[0]) }} />
            </div>

            {/* Step 2: Room Type */}
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400">
                <span className="w-5 h-5 rounded-md bg-violet-500/20 text-violet-400 flex items-center justify-center text-[10px] font-black">2</span>
                Select Room Type
              </label>
              <div className="relative">
                <select
                  value={roomType}
                  onChange={(e) => setRoomType(e.target.value)}
                  className="w-full appearance-none bg-white/[0.04] border border-white/10 rounded-xl px-4 py-3.5 text-sm font-medium text-slate-200 focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 transition-all cursor-pointer"
                >
                  {ROOM_OPTIONS.map(opt => (
                    <option key={opt.value} value={opt.value} className="bg-[#0a0f1a] text-white">
                      {opt.emoji}  {opt.label}
                    </option>
                  ))}
                </select>
                <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
              </div>

              {roomType === 'other' && (
                <input
                  type="text"
                  value={customPrompt}
                  onChange={(e) => setCustomPrompt(e.target.value)}
                  placeholder="e.g. Luxury Spa Room, Home Theater..."
                  className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-violet-500/50 transition-all"
                />
              )}
            </div>

            {/* Step 3: Additional Requirements */}
            <div className="space-y-3">
              <label className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400">
                <span className="w-5 h-5 rounded-md bg-violet-500/20 text-violet-400 flex items-center justify-center text-[10px] font-black">3</span>
                Additional Requirements
                <span className="text-slate-600 font-normal normal-case tracking-normal">(optional)</span>
              </label>
              <textarea
                value={additionalPrompt}
                onChange={(e) => setAdditionalPrompt(e.target.value)}
                placeholder="e.g. Match reference: mint wardrobes, charcoal tufted bed, marble-vein floor, cove ceiling + fan..."
                rows={3}
                className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-violet-500/50 resize-none transition-all"
              />
            </div>

            {/* AI Intent Analyzer */}
            {roomPreview && (
              <div className="space-y-3">
                <button
                  onClick={handleAnalyze}
                  disabled={analyzing}
                  className="w-full py-3 bg-white/5 hover:bg-white/10 disabled:bg-white/5 disabled:opacity-50 border border-violet-500/30 rounded-xl font-bold text-xs uppercase tracking-widest transition-all flex items-center justify-center gap-2 text-violet-300"
                >
                  {analyzing ? (
                    <><Loader2 size={16} className="animate-spin" /> Analyzing Intent...</>
                  ) : (
                    <><BrainCircuit size={16} /> Analyze Intent / Brain</>
                  )}
                </button>

                {aiIntent && (
                  <div className="bg-slate-900/80 border border-violet-500/20 rounded-xl p-4 space-y-3 text-sm">
                    <div className="flex items-center gap-2 text-violet-400 font-bold uppercase tracking-wider text-[10px]">
                      <Eye size={14} /> AI Scene Analysis
                    </div>
                    <p className="text-slate-300 text-xs leading-relaxed border-b border-white/10 pb-2">
                      <span className="font-semibold text-white">Reasoning:</span> {aiIntent.reasoning}
                    </p>
                    
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div>
                        <span className="text-emerald-400 font-bold block mb-1">Preserving:</span>
                        <ul className="list-disc pl-4 text-slate-400 space-y-0.5">
                          {aiIntent.preserve?.map((item: string, i: number) => <li key={i}>{item}</li>)}
                        </ul>
                      </div>
                      <div>
                        <span className="text-fuchsia-400 font-bold block mb-1">Adding/Modifying:</span>
                        <ul className="list-disc pl-4 text-slate-400 space-y-0.5">
                          {aiIntent.add?.map((item: string, i: number) => <li key={i}>{item}</li>)}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Generate Button */}
            <button
              onClick={() => handleGenerate()}
              disabled={!roomImage || processing}
              className="w-full py-4 bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-600 rounded-xl font-bold text-sm uppercase tracking-widest shadow-lg shadow-violet-500/20 disabled:shadow-none transition-all active:scale-[0.98] flex items-center justify-center gap-3"
            >
              {processing ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  Generate AI Design
                </>
              )}
            </button>

            {/* Status */}
            {statusText && (
              <div className={`p-3 rounded-xl text-xs font-medium leading-relaxed ${statusText.startsWith('✅') ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400' : 'bg-violet-500/10 border border-violet-500/20 text-violet-300'}`}>
                {statusText}
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-medium">
                ⚠️ {error}
              </div>
            )}

            {/* History */}
            {history.length > 0 && (
              <div className="space-y-3 pt-4 border-t border-white/[0.06]">
                <h4 className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">Generation History</h4>
                <div className="grid grid-cols-2 gap-2">
                  {history.map((url, i) => (
                    <div key={i} className="relative aspect-video rounded-xl overflow-hidden border border-white/10 cursor-pointer hover:border-violet-500/40 transition-all group"
                      onClick={() => setResultImage(url)}>
                      <img src={url} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" alt={`Result ${i + 1}`} />
                      <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <span className="text-[9px] font-bold uppercase tracking-widest">View</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </aside>

        {/* Main Viewport */}
        <main className="flex-1 relative flex items-center justify-center bg-[#050810] p-6 overflow-hidden">
          {!roomPreview && !resultImage ? (
            <div className="flex flex-col items-center justify-center text-center max-w-md">
              <div className="w-24 h-24 rounded-3xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mb-6">
                <Wand2 size={40} className="text-slate-700" />
              </div>
              <h2 className="text-2xl font-bold text-slate-300 mb-3">Upload a Room Photo</h2>
              <p className="text-sm text-slate-600 leading-relaxed">
                Upload or capture a photo of your room. The AI will preserve the exact room geometry while adding luxury interiors and furniture.
              </p>
            </div>
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center gap-6">
              {/* Side by Side: Original + Result */}
              <div className={`flex flex-col ${resultImage ? 'lg:flex-row' : ''} gap-6 w-full max-w-6xl items-center justify-center`}>
                {/* Original */}
                {roomPreview && (
                  <div className="flex-1 max-w-2xl">
                    <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500 mb-3 text-center">Original Room</div>
                    <div className="rounded-2xl overflow-hidden border border-white/10 shadow-2xl">
                      <img src={roomPreview} className="w-full object-contain max-h-[60vh]" alt="Original" />
                    </div>
                  </div>
                )}

                {/* Result */}
                {resultImage && (
                  <div className="flex-1 max-w-2xl">
                    <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400 mb-3 text-center">
                      AI Redesigned Room {totalVariations > 1 && `(Variation ${currentPromptIndex + 1} of ${totalVariations})`}
                    </div>
                    <div className="rounded-2xl overflow-hidden border border-emerald-500/20 shadow-2xl shadow-emerald-500/5 relative group">
                      <img src={resultImage} className="w-full object-contain max-h-[60vh]" alt="AI Result" />
                      <div className="absolute bottom-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity flex gap-2">
                        {totalVariations > 1 && (
                          <button 
                            onClick={() => handleGenerate((currentPromptIndex + 1) % totalVariations)}
                            className="px-3 py-1.5 bg-violet-600/80 backdrop-blur-sm rounded-lg text-[10px] font-bold text-white flex items-center gap-2 border border-violet-400/30"
                          >
                            <RotateCcw size={12} /> Next Variation
                          </button>
                        )}
                        <button onClick={handleDownload} className="px-3 py-1.5 bg-black/60 backdrop-blur-sm rounded-lg text-[10px] font-bold text-white flex items-center gap-2 border border-white/10">
                          <Download size={12} /> Save
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Processing overlay */}
              {processing && roomPreview && (
                <div className="absolute inset-0 bg-[#050810]/80 backdrop-blur-sm flex flex-col items-center justify-center z-10">
                  <div className="w-20 h-20 relative flex items-center justify-center mb-6">
                    <div className="absolute inset-0 border-4 border-violet-500/20 rounded-full"></div>
                    <div className="absolute inset-0 border-4 border-t-violet-500 rounded-full animate-spin"></div>
                    <Sparkles className="text-violet-400 animate-pulse" size={32} />
                  </div>
                  <h3 className="text-xl font-bold text-white mb-2">AI Engine Processing</h3>
                  <p className="text-sm text-slate-400 max-w-sm text-center">{statusText || 'Generating your luxury interior...'}</p>
                  <div className="mt-6 flex gap-1">
                    {[0, 1, 2].map(i => (
                      <div key={i} className="w-2 h-2 bg-violet-500 rounded-full animate-bounce" style={{ animationDelay: `${i * 0.15}s` }}></div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      <style>{`
        select option {
          background: #0a0f1a;
          color: #e2e8f0;
          padding: 8px;
        }
      `}</style>
    </div>
  )
}
