import React, { useState, useEffect, useRef } from 'react'
import { API_BASE_URL } from '../config'
import { Camera, Upload as UploadIcon } from 'lucide-react'

export default function CustomUploadVisualizer({ onBack, onLogout, userName, userId, initialImage }: { onBack: () => void, onLogout?: () => void, userName?: string, userId?: string | number, initialImage?: File | null }) {
  const [wallImage, setWallImage] = useState<File | null>(null)
  const [wallPreview, setWallPreview] = useState<string | null>(null)
  
  const [extractedTextures, setExtractedTextures] = useState<any[]>([])
  const [selectedTextureUrl, setSelectedTextureUrl] = useState<string | null>(null)
  const [customTextureFile, setCustomTextureFile] = useState<File | null>(null)
  const [customTexturePreview, setCustomTexturePreview] = useState<string | null>(null)
  
  const [resultImage, setResultImage] = useState<string | null>(null)
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const [isDragging, setIsDragging] = useState(false)
  const [compareMode, setCompareMode] = useState(false)
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [selectedCode, setSelectedCode] = useState<string | null>(null)
  const [showSidebar, setShowSidebar] = useState(false)
  const [filterCategory, setFilterCategory] = useState('All')
  const [filterStyle, setFilterStyle] = useState('All')
  const [zoom, setZoom] = useState(1.1) // Reset zoom to a safer 1.1x default
  const requestIdRef = useRef(0)
 
  const handleSaveDesign = () => {
    if (!resultImage) {
      setError('No design to save yet. Please apply a material first.')
      return
    }
    setShowSaveModal(true)
  }

  const handleDownload = async () => {
    if (!resultImage) return;
    try {
      const response = await fetch(resultImage);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `room_design_${new Date().getTime()}.jpg`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download image", err);
      // Fallback
      window.open(resultImage, '_blank');
    }
  }

  // Real coordinate sent to backend
  const [clickPoint, setClickPoint] = useState<{x: number, y: number} | null>(null)
  // Percentage coordinate for frontend dot display
  const [visualClick, setVisualClick] = useState<{x: number, y: number} | null>(null)

  const imageRef = useRef<HTMLImageElement>(null)

  useEffect(() => {
    fetchExtractedTextures()
    if (initialImage) {
      handleWallSelect(initialImage)
    }
  }, [userId, initialImage])

  const fetchExtractedTextures = async () => {
    try {
      const url = userId 
        ? `${API_BASE_URL}/api/extracted-textures?user_id=${userId}`
        : `${API_BASE_URL}/api/extracted-textures`;
      const res = await fetch(url)
      const data = await res.json()
      setExtractedTextures(data)
    } catch (err) {
      console.error('Failed to fetch extracted textures', err)
    }
  }

  const executeProcess = async (wImage: File, cTexture: File | null, sUrl: string | null, cx?: number, cy?: number) => {
    if (!wImage || (!cTexture && !sUrl)) return

    const requestId = ++requestIdRef.current

    setProcessing(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('wall_image', wImage)
      if (cTexture) {
        formData.append('texture_image', cTexture)
      } else if (sUrl) {
        formData.append('texture_url', sUrl)
      }
      
      const x = cx !== undefined ? cx : clickPoint?.x
      const y = cy !== undefined ? cy : clickPoint?.y
      
      if (x !== undefined && y !== undefined) {
        formData.append('click_x', x.toString())
        formData.append('click_y', y.toString())
      }

      const response = await fetch(`${API_BASE_URL}/api/process-wall`, {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()
      
      // 🚫 Ignore OLD responses to prevent race conditions
      if (requestId !== requestIdRef.current) return

      if (!response.ok) throw new Error(data.error || 'Failed to process image')

      setResultImage(data.resultUrl)
      setCompareMode(false)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setProcessing(false)
    }
  }

  const handleWallDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleWallSelect(e.dataTransfer.files[0])
    }
  }

  const handleWallSelect = (file: File) => {
    setWallImage(file)
    setWallPreview(URL.createObjectURL(file))
    setResultImage(null)
    setClickPoint(null)
    setVisualClick(null)
    setCompareMode(false)
  }

  const handleTextureSelect = (url: string, code?: string) => {
    setSelectedTextureUrl(url)
    setSelectedCode(code || null)
    setCustomTextureFile(null)
    setCustomTexturePreview(null)
    if (wallImage) {
      executeProcess(wallImage, null, url)
    }
  }

  const handleCustomTextureSelect = (file: File) => {
    setCustomTextureFile(file)
    setCustomTexturePreview(URL.createObjectURL(file))
    setSelectedTextureUrl(null)
    setSelectedCode(null)
    if (wallImage) {
      executeProcess(wallImage, file, null)
    }
  }

  const handleImageClick = (e: React.MouseEvent<HTMLImageElement>) => {
    if (!imageRef.current || !wallImage) return
    const rect = imageRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const naturalWidth = imageRef.current.naturalWidth
    const naturalHeight = imageRef.current.naturalHeight
    
    const scaleX = naturalWidth / rect.width
    const scaleY = naturalHeight / rect.height
    
    const realX = Math.round(x * scaleX)
    const realY = Math.round(y * scaleY)
    
    setClickPoint({x: realX, y: realY})
    setVisualClick({x: (x / rect.width) * 100, y: (y / rect.height) * 100})
    
    if (customTextureFile || selectedTextureUrl) {
      executeProcess(wallImage, customTextureFile, selectedTextureUrl, realX, realY)
    }
  }

  const handleReset = () => {
    setResultImage(null)
    setSelectedTextureUrl(null)
    setSelectedCode(null)
    setCustomTextureFile(null)
    setCustomTexturePreview(null)
    setClickPoint(null)
    setVisualClick(null)
  }

  // Generate unique categories for the mock display
  const getTextureCategory = (index: number) => {
    return index % 3 === 0 ? "Wallpaper" : index % 2 === 0 ? "Paint" : "Tile"
  }

  return (
    <div className="h-screen bg-[#fcfcfb] flex flex-col font-sans overflow-hidden selection:bg-stone-200">
      <header className="bg-white border-b border-stone-100 h-14 sm:h-20 flex items-center px-4 sm:px-8 shrink-0 z-20 justify-between">
        <div className="flex items-center gap-2">
           <button onClick={onBack} className="bg-red-600 text-white px-3 py-1.5 text-[9px] font-bold uppercase tracking-widest rounded-sm hover:bg-red-700 transition-all">
             Exit Studio
           </button>
        </div>
        
        <div className="font-bold text-[10px] sm:text-lg text-[#1a1a1a] tracking-tight flex items-center gap-2 sm:gap-3 font-serif italic truncate">
          Material Workspace
        </div>

        <div className="flex items-center gap-3 sm:gap-8">
          {wallPreview && (
            <label className="text-[9px] sm:text-[10px] font-bold uppercase tracking-widest text-stone-500 hover:text-[#1a1a1a] cursor-pointer transition-all flex items-center gap-2">
              <Camera size={14} />
              <span className="hidden sm:inline">Change Photo</span>
              <span className="sm:hidden">Photo</span>
              <input type="file" className="hidden" accept="image/*" onChange={(e) => {
                if (e.target.files?.[0]) handleWallSelect(e.target.files[0])
              }} />
            </label>
          )}
          <div className="h-4 w-px bg-stone-200 hidden sm:block"></div>
          {onLogout && (
            <button onClick={onLogout} className="text-[18px] text-stone-300 hover:text-red-500 transition-colors">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" /></svg>
            </button>
          )}
        </div>
      </header>

      <div className="flex flex-col lg:flex-row flex-1 overflow-hidden">
        <aside className={`${!wallPreview ? 'hidden' : 'flex'} order-2 lg:order-1 w-full lg:w-[360px] h-auto lg:h-full bg-white border-t lg:border-t-0 lg:border-r border-stone-100 shrink-0 flex-col z-10 transition-all duration-300`}>
          {/* Tabs/Toolbar above materials for mobile */}
          <div className="lg:hidden flex items-center justify-between px-4 py-3 bg-stone-50 border-b border-stone-100">
             <div className="flex gap-4">
               <button onClick={handleReset} className="text-[9px] font-bold uppercase tracking-widest text-stone-400 flex items-center gap-1">
                 <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                 Reset
               </button>
             </div>
             {resultImage && (
               <label className="flex items-center gap-2 cursor-pointer">
                 <span className={`text-[9px] font-bold uppercase tracking-widest ${compareMode ? 'text-[#1a1a1a]' : 'text-stone-300'}`}>Compare</span>
                 <div className="relative inline-flex h-3 w-6 items-center rounded-full bg-stone-200">
                   <input type="checkbox" className="sr-only" checked={!compareMode} onChange={() => setCompareMode(!compareMode)} />
                   <span className={`inline-block h-2 w-2 transform rounded-full bg-white transition-transform ${!compareMode ? 'translate-x-3 bg-[#1a1a1a]' : 'translate-x-1'}`} />
                 </div>
               </label>
             )}
          </div>

          <div className="p-4 lg:p-6 border-b border-stone-100 flex flex-col gap-4 lg:gap-6 shrink-0 bg-white">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-[#1a1a1a] text-[10px] uppercase tracking-[0.2em]">Material Library</h3>
              <span className="text-[9px] font-bold text-stone-400 bg-stone-50 px-2 py-0.5 rounded-sm">{extractedTextures.length} Items</span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-[9px] font-bold uppercase tracking-widest text-stone-500">Category</label>
                <select 
                  value={filterCategory} 
                  onChange={(e) => setFilterCategory(e.target.value)}
                  className="w-full bg-stone-50 border border-stone-200 text-[#1a1a1a] text-[10px] font-bold uppercase tracking-widest p-2 outline-none focus:border-[#1a1a1a] transition-all"
                >
                  <option>All</option>
                  <option>Wallpaper</option>
                  <option>Paint</option>
                  <option>Tile</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="text-[9px] font-bold uppercase tracking-widest text-stone-500">Style</label>
                <select 
                  value={filterStyle} 
                  onChange={(e) => setFilterStyle(e.target.value)}
                  className="w-full bg-stone-50 border border-stone-200 text-[#1a1a1a] text-[10px] font-bold uppercase tracking-widest p-2 outline-none focus:border-[#1a1a1a] transition-all"
                >
                  <option>All</option>
                  <option>Modern</option>
                  <option>Classic</option>
                  <option>Luxury</option>
                </select>
              </div>
            </div>

            <label className="w-full flex items-center justify-center gap-3 py-3 border border-stone-200 text-[#1a1a1a] text-[10px] font-bold uppercase tracking-widest hover:bg-stone-50 transition-all cursor-pointer">
              <UploadIcon size={14} />
              Custom Texture
              <input 
                type="file" 
                className="hidden" 
                accept="image/*" 
                onChange={(e) => {
                  if (e.target.files?.[0]) handleCustomTextureSelect(e.target.files[0])
                }} 
              />
            </label>
          </div>
          
          <div className="flex-1 overflow-x-auto lg:overflow-y-auto p-4 sm:p-6 custom-scrollbar bg-white">
            <div className="flex lg:grid lg:grid-cols-2 gap-4 lg:gap-6">
              {customTexturePreview && (
                <div 
                  onClick={() => handleCustomTextureSelect(customTextureFile!)}
                  className={`flex-shrink-0 lg:flex-shrink-1 w-24 lg:w-full group relative bg-white rounded-none overflow-hidden transition-all duration-300 cursor-pointer ${!selectedTextureUrl && customTexturePreview ? 'ring-2 ring-[#1a1a1a] ring-offset-2' : 'border border-stone-100'}`}
                >
                  <div className="relative aspect-square overflow-hidden bg-stone-50">
                    <img src={customTexturePreview} className={`w-full h-full object-cover transition-transform duration-700 group-hover:scale-110`} />
                    {(!selectedTextureUrl && customTexturePreview) && (
                      <div className="absolute inset-0 bg-[#1a1a1a]/10 flex items-center justify-center backdrop-blur-[1px]">
                        <div className="bg-white p-2 shadow-xl animate-in zoom-in-50 duration-300">
                          <svg className="w-4 h-4 text-[#1a1a1a]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
                        </div>
                      </div>
                    )}
                  </div>
                  <div className={`p-3 text-center transition-all ${!selectedTextureUrl && customTexturePreview ? 'bg-[#1a1a1a]' : 'bg-stone-100'}`}>
                    <p className={`font-bold text-[9px] truncate uppercase tracking-widest ${!selectedTextureUrl && customTexturePreview ? 'text-white' : 'text-[#1a1a1a]'}`}>
                      Custom Upload
                    </p>
                  </div>
                </div>
              )}

              {extractedTextures
                .filter(tex => {
                  const cat = getTextureCategory(extractedTextures.indexOf(tex))
                  const categoryMatch = filterCategory === 'All' || cat === filterCategory
                  return categoryMatch
                })
                .map((tex, i) => {
                const isSelected = selectedTextureUrl === tex.url
                return (
                  <div 
                    key={tex.id}
                    onClick={() => handleTextureSelect(tex.url, tex.name)}
                    className={`flex-shrink-0 lg:flex-shrink-1 w-24 lg:w-full group relative bg-white rounded-none overflow-hidden transition-all duration-300 cursor-pointer ${isSelected ? 'ring-2 ring-[#1a1a1a] ring-offset-2' : 'border border-stone-100'}`}
                  >
                    <div className="relative aspect-square overflow-hidden bg-stone-50">
                      <img src={tex.url} className={`w-full h-full object-cover transition-transform duration-700 group-hover:scale-110 grayscale-[0.2] group-hover:grayscale-0`} />
                      {isSelected && (
                        <div className="absolute inset-0 bg-[#1a1a1a]/10 flex items-center justify-center backdrop-blur-[1px]">
                          <div className="bg-white p-2 shadow-xl animate-in zoom-in-50 duration-300">
                            <svg className="w-4 h-4 text-[#1a1a1a]" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
                          </div>
                        </div>
                      )}
                    </div>
                    <div className={`p-3 text-center transition-all ${isSelected ? 'bg-[#1a1a1a]' : 'bg-stone-50'}`}>
                      <p className={`font-bold text-[9px] truncate uppercase tracking-widest ${isSelected ? 'text-white' : 'text-stone-400'}`}>
                        {tex.name || "Unnamed"}
                      </p>
                    </div>
                  </div>
                )
              })}
            </div>
            
            {extractedTextures.length === 0 && !customTexturePreview && (
              <div className="text-center py-16 px-4 text-gray-400 text-sm bg-white rounded-2xl border border-dashed border-gray-200">
                <svg className="w-10 h-10 mx-auto mb-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                No materials available.
              </div>
            )}
          </div>
        </aside>


        {/* Main Center Area */}
        <main className="flex-1 flex flex-col relative bg-[#f1f3f5]">
          
          {error && (
            <div className="absolute top-6 left-1/2 -translate-x-1/2 bg-red-900/95 backdrop-blur text-white px-6 py-3 rounded-full shadow-xl flex items-center gap-4 z-50 animate-in fade-in slide-in-from-top-4 border border-red-800">
              <span className="text-sm font-medium">{error}</span>
              <button onClick={() => setError(null)} className="text-red-200 hover:text-white transition-colors">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
          )}

          <div className="flex-1 relative overflow-hidden bg-gray-900 flex items-center justify-center">
            {wallPreview ? (
              <>
                {/* Blurred Background Layer */}
                <div className="absolute inset-0 z-0">
                  <img 
                    src={compareMode ? wallPreview : (resultImage || wallPreview)} 
                    className="w-full h-full object-cover blur-2xl opacity-40 scale-110"
                    alt=""
                  />
                  <div className="absolute inset-0 bg-black/20" />
                </div>

                {/* Main Image Layer - fills entire available space */}
                <div className="absolute inset-0 z-10 flex items-center justify-center p-3 sm:p-5 group">
                  <img 
                    ref={imageRef}
                    src={compareMode ? wallPreview : (resultImage || wallPreview)} 
                    className={`w-full h-full object-contain rounded-xl shadow-[0_20px_60px_rgba(0,0,0,0.6)] cursor-crosshair transition-opacity duration-300 ${processing ? 'opacity-60 blur-[1px]' : 'opacity-100'}`}
                    onClick={handleImageClick}
                    alt="Wall preview"
                  />

                  {/* Visual Click Indicator */}
                  {visualClick && !compareMode && (
                    <div 
                      className="absolute w-6 h-6 -ml-3 -mt-3 pointer-events-none z-20 flex items-center justify-center transition-all duration-300"
                      style={{ left: `${visualClick.x}%`, top: `${visualClick.y}%` }}
                    >
                      <div className="absolute inset-0 bg-white/30 rounded-full animate-ping"></div>
                      <div className="w-2.5 h-2.5 bg-white rounded-full shadow-[0_0_12px_rgba(0,0,0,0.6)] border-2 border-gray-900"></div>
                    </div>
                  )}

                  {processing && (
                    <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-black/5">
                      <div className="bg-white/95 backdrop-blur-md px-6 py-4 rounded-2xl shadow-2xl flex items-center gap-4">
                        <div className="relative flex h-6 w-6">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-gray-900 opacity-20"></span>
                          <span className="relative inline-flex rounded-full h-6 w-6 bg-gray-900 items-center justify-center">
                             <svg className="animate-spin h-3.5 w-3.5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                          </span>
                        </div>
                        <span className="font-bold text-gray-900 text-sm tracking-wide">Applying Magic to the Wall...</span>
                      </div>
                    </div>
                  )}

                  {/* Zoom Controls */}
                  <div className="absolute bottom-6 left-6 flex flex-col gap-3 z-30 opacity-60 hover:opacity-100 transition-opacity">
                    <button onClick={(e) => { e.stopPropagation(); setZoom(prev => Math.min(prev + 0.1, 2)) }} className="w-8 h-8 bg-white/80 backdrop-blur rounded-lg shadow-lg flex items-center justify-center hover:bg-white text-gray-800">
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                    </button>
                    <button onClick={(e) => { e.stopPropagation(); setZoom(prev => Math.max(prev - 0.1, 0.5)) }} className="w-8 h-8 bg-white/80 backdrop-blur rounded-lg shadow-lg flex items-center justify-center hover:bg-white text-gray-800">
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" /></svg>
                    </button>
                  </div>

                  {!resultImage && !processing && (
                    <div className="absolute inset-0 pointer-events-none flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/5">
                      <div className="bg-gray-900/90 backdrop-blur text-white px-5 py-2.5 rounded-xl font-medium text-sm shadow-xl flex items-center gap-2">
                        <svg className="w-4 h-4 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" /></svg>
                        Click to set target area
                      </div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div 
                className={`w-full max-w-2xl aspect-[16/10] border-2 border-dashed rounded-[2rem] flex flex-col items-center justify-center transition-all duration-300 ${isDragging ? 'border-gray-900 bg-gray-100 scale-[1.02]' : 'border-gray-300 bg-white hover:border-gray-400 hover:bg-gray-50 shadow-sm'}`}
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleWallDrop}
              >
                <div className="w-24 h-24 bg-gray-50 rounded-full flex items-center justify-center mb-6 shadow-inner border border-gray-100">
                  <svg className="w-10 h-10 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-3">Upload your space</h3>
                <p className="text-gray-500 mb-8 max-w-md text-center leading-relaxed px-4">Take a live photo or upload a high-quality image of your room to begin visualizing.</p>
                
                <div className="flex flex-col sm:flex-row gap-4 w-full max-w-xs px-6 sm:max-w-none sm:px-0 sm:justify-center">
                  <label className="flex-1 sm:flex-none bg-gray-900 text-white px-8 py-3.5 rounded-xl font-bold cursor-pointer hover:bg-gray-800 shadow-lg hover:shadow-xl transition-all active:scale-95 flex items-center justify-center gap-2">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                    Take a Photo
                    <input 
                      type="file" 
                      className="hidden" 
                      accept="image/*" 
                      capture="environment" 
                      onChange={(e) => {
                        if (e.target.files?.[0]) handleWallSelect(e.target.files[0])
                      }} 
                    />
                  </label>
                  <label className="flex-1 sm:flex-none bg-white text-gray-900 border-2 border-gray-200 px-8 py-3.5 rounded-xl font-bold cursor-pointer hover:bg-gray-50 hover:border-gray-300 shadow-sm transition-all active:scale-95 flex items-center justify-center gap-2">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0l-4-4m4 4v12" /></svg>
                    Browse
                    <input 
                      type="file" 
                      className="hidden" 
                      accept="image/*" 
                      onChange={(e) => {
                        if (e.target.files?.[0]) handleWallSelect(e.target.files[0])
                      }} 
                    />
                  </label>
                </div>
              </div>
            )}
          </div>

          {/* Bottom Action Bar for Mobile */}
          <div className="lg:hidden flex items-center justify-between px-6 py-4 bg-white border-t border-stone-100">
             <div className="flex items-center gap-3">
               <div className="w-8 h-8 rounded-full bg-stone-100 flex items-center justify-center">
                 <UploadIcon size={14} className="text-stone-400" />
               </div>
               <div className="text-[10px] font-bold text-[#1a1a1a] uppercase tracking-widest">Ideal Studio</div>
             </div>
             
             <button onClick={() => setShowSidebar(!showSidebar)} className="w-10 h-10 bg-[#1a1a1a] rounded-full flex items-center justify-center text-white shadow-lg">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16m-7 6h7" /></svg>
             </button>

             <div className="flex items-center gap-4">
                <button onClick={handleSaveDesign} className="bg-[#1a1a1a] text-white px-4 py-2 text-[9px] font-bold uppercase tracking-widest rounded-sm">Save</button>
             </div>
          </div>

          {/* Desktop Bottom Bar (Hidden on Mobile) */}
          <div className="hidden lg:flex h-24 bg-white border-t border-stone-100 items-center px-12 justify-between shrink-0 z-20 gap-3">
            <div className="flex gap-4">
              <button 
                onClick={handleReset}
                disabled={!wallPreview}
                className="px-6 py-2 text-[10px] font-bold uppercase tracking-[0.2em] border border-stone-200 text-stone-400 hover:text-[#1a1a1a] hover:border-[#1a1a1a] disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                Reset Canvas
              </button>
            </div>

            <div className="flex-1 flex justify-center">
              {selectedCode && (
                <div className="flex items-center gap-4 bg-stone-50 px-6 py-2 border border-stone-100 animate-in fade-in slide-in-from-bottom-2">
                  <div className="w-1.5 h-1.5 bg-[#1a1a1a]"></div>
                  <span className="text-[10px] font-bold text-stone-300 uppercase tracking-widest whitespace-nowrap">Selected Finish:</span>
                  <span className="text-xs font-bold text-[#1a1a1a] uppercase tracking-widest">{selectedCode}</span>
                </div>
              )}
            </div>
            
            <div className="flex items-center justify-between gap-12">
              {resultImage && (
                <label className="flex items-center gap-4 cursor-pointer group">
                  <span className={`text-[10px] font-bold uppercase tracking-widest transition-colors ${compareMode ? 'text-[#1a1a1a]' : 'text-stone-300'}`}>Original</span>
                  <div className="relative inline-flex h-4 w-8 items-center rounded-full bg-stone-100 transition-colors">
                    <input type="checkbox" className="sr-only" checked={!compareMode} onChange={() => setCompareMode(!compareMode)} />
                    <span className={`inline-block h-3 w-3 transform rounded-full bg-white shadow-sm transition-transform duration-300 ${!compareMode ? 'translate-x-4 bg-[#1a1a1a]' : 'translate-x-1'}`} />
                  </div>
                  <span className={`text-[10px] font-bold uppercase tracking-widest transition-colors ${!compareMode ? 'text-[#1a1a1a]' : 'text-stone-300'}`}>Visualized</span>
                </label>
              )}
              
              <button 
                onClick={handleSaveDesign}
                className="bg-[#1a1a1a] text-white px-10 py-3 text-[10px] font-bold uppercase tracking-[0.2em] shadow-lg hover:bg-stone-800 transition-all active:scale-95 whitespace-nowrap"
              >
                Save Archive
              </button>
            </div>
          </div>
        </main>
      </div>

      {/* Save Modal Overlay */}
      {showSaveModal && resultImage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-gray-900/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl shadow-2xl max-w-5xl w-full overflow-hidden flex flex-col md:flex-row relative">
            <button 
              onClick={() => setShowSaveModal(false)}
              className="absolute top-4 right-4 z-10 w-10 h-10 bg-white/50 backdrop-blur hover:bg-gray-100 rounded-full flex items-center justify-center text-gray-500 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
            
            <div className="w-full md:w-1/2 bg-gray-100 flex items-center justify-center p-8 relative">
               <div className="absolute inset-0 opacity-10" style={{backgroundImage: 'radial-gradient(#000 1px, transparent 1px)', backgroundSize: '16px 16px'}}></div>
               <div className="relative inline-block">
                 <img src={resultImage} alt="Saved Design" className="relative z-10 max-w-full max-h-[60vh] object-contain rounded-xl shadow-lg ring-1 ring-black/5" />
               </div>
            </div>
            
            <div className="w-full md:w-1/2 p-8 sm:p-12 flex flex-col justify-center">
              <div className="w-14 h-14 bg-green-100 text-green-600 rounded-2xl flex items-center justify-center mb-6 shadow-sm border border-green-200">
                <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
              </div>
              <h2 className="text-3xl font-extrabold text-gray-900 mb-3 tracking-tight">Design saved successfully!</h2>
              <p className="text-gray-500 mb-8 leading-relaxed text-lg">Your beautiful new room design has been saved. You can download a high-quality copy to share with contractors, friends, or family.</p>
              
              <div className="flex flex-col gap-4">
                <button 
                  onClick={handleDownload}
                  className="bg-gray-900 text-white text-center px-6 py-4 rounded-xl font-bold text-lg hover:bg-gray-800 transition-all shadow-md active:scale-[0.98] flex justify-center items-center gap-3"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                  Download Image
                </button>
                <button 
                  onClick={() => setShowSaveModal(false)}
                  className="bg-white border-2 border-gray-200 text-gray-900 text-center px-6 py-4 rounded-xl font-bold text-lg hover:border-gray-900 hover:bg-gray-50 transition-all active:scale-[0.98]"
                >
                  Continue Editing
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
