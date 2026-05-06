import { useState, useEffect, useRef } from 'react'
import ReactCrop, { centerCrop, makeAspectCrop, type Crop, type PixelCrop } from 'react-image-crop'
import 'react-image-crop/dist/ReactCrop.css'
import { 
  Upload, 
  ChevronLeft, 
  Grid, 
  Crop as CropIcon, 
  Save, 
  Trash2, 
  Plus, 
  Check, 
  Loader2,
  Image as ImageIcon,
  FileText,
  MousePointer2,
  Target,
  Copy,
  ExternalLink,
  AlertCircle,
  RotateCcw,
  Edit3
} from 'lucide-react'

interface FilterItem {
  id?: number;
  url: string;
  image_path: string;
  code: string;
  isNew?: boolean;
}

interface DetectedCode {
  code: string;
  left: number;
  top: number;
  width: number;
  height: number;
  x: number;
  y: number;
}

export default function AdminPanel({ onBack, onLogout, userName, userId }: { onBack: () => void, onLogout: () => void, userName?: string, userId?: string | number }) {
  const [view, setView] = useState<'upload' | 'gallery' | 'editor'>('upload')
  const [mobileTab, setMobileTab] = useState<'canvas' | 'queue'>('canvas')
  const [pdfs, setPdfs] = useState<any[]>([])
  const [selectedPdfId, setSelectedPdfId] = useState<number | null>(null)
  const [pdfPages, setPdfPages] = useState<string[]>([])
  const [selectedPage, setSelectedPage] = useState<string | null>(null)
  const [pdfPath, setPdfPath] = useState<string | null>(localStorage.getItem('pdf_path'))
  const [uploading, setUploading] = useState(false)
  
  // Modes
  const [mode, setMode] = useState<'crop' | 'select'>('crop')
  
  // Crop state
  const [crop, setCrop] = useState<Crop>()
  const [completedCrop, setCompletedCrop] = useState<PixelCrop>()
  const [imgDimensions, setImgDimensions] = useState({ width: 0, height: 0, naturalWidth: 0, naturalHeight: 0 })
  const imgRef = useRef<HTMLImageElement>(null)

  // Filters grid state
  const [filters, setFilters] = useState<FilterItem[]>([])
  const [cropping, setCropping] = useState(false)
  const [zoom, setZoom] = useState(1)
  
  // OCR & Selection state
  const [activeIndex, setActiveIndex] = useState<number | null>(null)
  const [detectingCode, setDetectingCode] = useState(false)
  const [detectedCodes, setDetectedCodes] = useState<DetectedCode[]>([])
  const [clickPos, setClickPos] = useState<{ x: number, y: number } | null>(null)
  const [copiedCode, setCopiedCode] = useState<string | null>(null)
  const [manualCode, setManualCode] = useState('')
  const [toast, setToast] = useState<{ message: string, type: 'info' | 'success' | 'warning' } | null>(null)

  const showToast = (message: string, type: 'info' | 'success' | 'warning' = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  useEffect(() => {
    fetchFilters()
    fetchPdfs()
  }, [])

  const fetchPdfs = async () => {
    try {
      const res = await fetch(`http://localhost:5000/api/pdfs?user_id=${userId}`)
      const data = await res.json()
      setPdfs(data)
    } catch (err) {
      console.error('Error fetching PDFs:', err)
    }
  }

  const fetchPages = async (pdfId: number) => {
    try {
      const res = await fetch(`http://localhost:5000/api/pages?user_id=${userId}&pdf_id=${pdfId}`)
      const data = await res.json()
      if (Array.isArray(data) && data.length > 0) {
        setPdfPages(data)
        setSelectedPage(data[0])
        setView('gallery')
        setSelectedPdfId(pdfId)
      }
    } catch (err) {
      console.error('Error fetching pages:', err)
    }
  }

  const fetchFilters = async () => {
    try {
      const res = await fetch(`http://localhost:5000/api/filters?user_id=${userId}`)
      const data = await res.json()
      setFilters(data)
    } catch (err) {
      console.error('Failed to fetch filters', err)
    }
  }

  const fetchDetectedCodes = async (url: string) => {
    setDetectingCode(true)
    try {
      const res = await fetch('http://localhost:5000/api/detect-codes', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-User-ID': userId?.toString() || ''
        },
        body: JSON.stringify({ page_url: url })
      })
      const data = await res.json()
      if (data.success) {
        setDetectedCodes(data.codes)
      }
    } catch (err) {
      console.error('Failed to detect codes', err)
    } finally {
      setDetectingCode(false)
    }
  }

  useEffect(() => {
    if (selectedPage) {
      fetchDetectedCodes(selectedPage)
    }
  }, [selectedPage])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    const formData = new FormData()
    formData.append('pdf_file', file)
    if (userId) formData.append('user_id', userId.toString())

    try {
      const res = await fetch('http://localhost:5000/api/upload-pdf', {
        method: 'POST',
        headers: { 'X-User-ID': userId?.toString() || '' },
        body: formData
      })
      const data = await res.json()
      if (data.success) {
        showToast('PDF Uploaded successfully!', 'success')
        fetchPdfs()
        fetchPages(data.pdf_id)
      } else {
        showToast(data.error || 'Upload failed', 'warning')
      }
    } catch (err) {
      showToast('Connection error', 'warning')
    } finally {
      setUploading(false)
    }
  }

  const handleDeletePdf = async (id: number) => {
    if (!window.confirm('Delete this PDF and all its extracted pages?')) return
    
    try {
      const res = await fetch(`http://localhost:5000/api/delete-pdf?id=${id}&user_id=${userId}`, {
        method: 'DELETE'
      })
      const data = await res.json()
      if (data.success) {
        showToast('PDF Deleted', 'success')
        fetchPdfs()
        if (selectedPdfId === id) {
          setView('upload')
          setPdfPages([])
          setSelectedPage(null)
          setSelectedPdfId(null)
        }
      }
    } catch (err) {
      showToast('Delete failed', 'warning')
    }
  }

  const handlePageClick = (pageUrl: string) => {
    setSelectedPage(pageUrl)
    setView('editor')
    setCrop(undefined)
    setCompletedCrop(undefined)
    setZoom(1)
    setActiveIndex(null)
    setDetectedCodes([])
    setManualCode('')
    setMode('crop')
    setMobileTab('canvas')
  }

  const onImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const { width, height, naturalWidth, naturalHeight } = e.currentTarget
    setImgDimensions({ width, height, naturalWidth, naturalHeight })
    
    const initialCrop = centerCrop(
      makeAspectCrop({ unit: '%', width: 50 }, 1, width, height),
      width,
      height
    )
    setCrop(initialCrop)
  }

  const handleAddToGrid = async () => {
    if (!completedCrop || !selectedPage) return

    setCropping(true)
    try {
      // PRO FIX: Calculate scale based on ACTUAL rendered dimensions at this moment
      if (!imgRef.current) throw new Error("Image reference not found");
      
      const displayedWidth = imgRef.current.width;
      const displayedHeight = imgRef.current.height;
      const naturalWidth = imgRef.current.naturalWidth;
      const naturalHeight = imgRef.current.naturalHeight;

      const scaleX = naturalWidth / displayedWidth;
      const scaleY = naturalHeight / displayedHeight;

      const cropData = {
        page_url: selectedPage,
        x: completedCrop.x * scaleX,
        y: completedCrop.y * scaleY,
        width: completedCrop.width * scaleX,
        height: completedCrop.height * scaleY,
        manual_code: manualCode,
        detected_codes: detectedCodes // Pass pre-detected codes for nearest-match association
      }

      // Call api/crop which now handles BOTH cropping and saving to MongoDB
      const res = await fetch('http://localhost:5000/api/crop', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-User-ID': userId?.toString() || ''
        },
        body: JSON.stringify(cropData)
      })
      
      const data = await res.json()
      if (!data.success) throw new Error(data.error || 'Crop failed')

      // Update UI with the result from the backend
      const newFilter: FilterItem = {
        id: data.id,
        url: data.url,
        image_path: data.image_path,
        code: data.code,
        isNew: false
      }
      
      setFilters(prev => [newFilter, ...prev])
      fetchFilters()
      setActiveIndex(0)
      setManualCode('') // Clear manual code after successful commit
      
      showToast('Material committed successfully!', 'success')
      if (data.code === 'UNKNOWN' && !manualCode) {
        showToast('Code not detected, edit manually.', 'info')
      }

    } catch (err: any) {
      showToast(err.message || 'Failed to create material', 'warning')
    } finally {
      setCropping(false)
    }
  }

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code)
    setCopiedCode(code)
    setTimeout(() => setCopiedCode(null), 2000)
  }

  const handleManualCodeAssign = (code: string) => {
    if (activeIndex === null) return
    const newFilters = [...filters]
    newFilters[activeIndex].code = code
    setFilters(newFilters)
    setCopiedCode(code)
    setTimeout(() => setCopiedCode(null), 1000)
  }

  const handleSaveFilter = async (index: number) => {
    const filterToSave = filters[index];
    if (filterToSave.code === 'UNKNOWN') {
      showToast('Assign a code before saving.', 'warning');
      return;
    }

    try {
      const res = await fetch('http://localhost:5000/api/save-filter', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-User-ID': userId?.toString() || ''
        },
        body: JSON.stringify({
          image_path: filterToSave.image_path,
          code: filterToSave.code,
          user_id: userId
        })
      })
      const data = await res.json()
      if (data.success) {
        showToast('Saved!', 'success')
        fetchFilters()
      }
    } catch (err) {
      showToast('Save failed', 'warning')
    }
  }

  const handleDeleteFilter = async (index: number) => {
    const filter = filters[index]
    if (!filter.id) {
      setFilters(prev => prev.filter((_, i) => i !== index))
      return
    }

    try {
      const res = await fetch(`http://localhost:5000/api/filter?id=${filter.id}&user_id=${userId}`, {
        method: 'DELETE'
      })
      const data = await res.json()
      if (data.success) {
        setFilters(prev => prev.filter((_, i) => i !== index))
        fetchFilters()
      }
    } catch (err) {
      showToast('Delete failed', 'warning')
    }
  }

  const scaleX = imgDimensions.naturalWidth / imgDimensions.width;
  const scaleY = imgDimensions.naturalHeight / imgDimensions.height;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-sans overflow-hidden">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-20 left-1/2 -translate-x-1/2 z-[100] px-6 py-3 rounded-2xl shadow-2xl flex items-center gap-3 animate-in fade-in slide-in-from-top-4 duration-300 ${
          toast.type === 'success' ? 'bg-green-600 text-white' : 
          toast.type === 'warning' ? 'bg-red-600 text-white' : 'bg-indigo-600 text-white'
        }`}>
          {toast.type === 'warning' && <AlertCircle className="w-5 h-5" />}
          {toast.type === 'success' && <Check className="w-5 h-5" />}
          <span className="font-bold text-sm">{toast.message}</span>
        </div>
      )}

      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm px-4 sm:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2 sm:gap-4">
          <button onClick={view === 'editor' ? () => setView('gallery') : (view === 'gallery' ? () => setView('upload') : onBack)} className="p-2 hover:bg-gray-100 rounded-full transition-colors group">
            <ChevronLeft className="w-6 h-6 text-gray-400 group-hover:text-gray-900" />
          </button>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-100">
              <FileText className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-base sm:text-xl font-bold text-gray-900 tracking-tight leading-none">Catalog Manager</h1>
              <p className="text-[9px] sm:text-[10px] text-indigo-600 font-bold uppercase tracking-widest mt-1">Admin Workspace</p>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-3 sm:gap-6">
          <div className="flex items-center gap-2 sm:gap-3 pr-3 sm:pr-6 border-r border-gray-200">
            <div className="text-right hidden sm:block">
              <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider leading-none mb-1">Administrator</p>
              <p className="text-sm font-bold text-gray-900">Hello, {userName || 'Admin'}</p>
            </div>
            <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center text-white font-bold shadow-md ring-2 ring-white">
              {(userName || 'A').charAt(0).toUpperCase()}
            </div>
          </div>
          <button onClick={onLogout} className="flex items-center gap-2 text-gray-500 hover:text-red-600 transition-all font-bold text-sm">
             <Trash2 className="w-5 h-5" /> Logout
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-auto p-4 sm:p-8">
        <div className="max-w-7xl mx-auto h-full">
          
          {/* VIEW: UPLOAD / LIBRARY */}
          {view === 'upload' && (
            <div className="space-y-10 animate-in fade-in duration-500">
              {/* Compact Upload Card */}
              <div className="bg-white rounded-[2rem] shadow-xl shadow-indigo-100/30 p-6 sm:p-8 border border-gray-100 flex flex-col md:flex-row items-center gap-8 md:gap-12">
                <div className="flex-1 text-center md:text-left space-y-3">
                  <div className="flex items-center justify-center md:justify-start gap-4 mb-2">
                    <div className="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center shadow-inner">
                      <Upload className="w-6 h-6 text-indigo-600" />
                    </div>
                    <h2 className="text-2xl font-black text-gray-900 tracking-tight">Upload New Catalog</h2>
                  </div>
                  <p className="text-gray-500 font-medium text-sm leading-relaxed max-w-xl">
                    Extract material textures and codes automatically using our AI-powered vision system. Supported format: PDF only.
                  </p>
                </div>

                <div className="w-full md:w-80 shrink-0">
                  <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-200 rounded-[1.5rem] cursor-pointer hover:bg-gray-50 hover:border-indigo-300 transition-all group relative overflow-hidden shadow-sm">
                    <div className="flex flex-col items-center justify-center p-4">
                      <ImageIcon className="w-8 h-8 text-gray-200 group-hover:text-indigo-300 transition-colors mb-2" />
                      <p className="text-[10px] text-gray-400 font-black uppercase tracking-widest text-center">
                        {uploading ? 'Processing...' : 'Click to browse PDF'}
                      </p>
                    </div>
                    <input type="file" className="hidden" accept=".pdf" onChange={handleUpload} disabled={uploading} />
                    {uploading && (
                      <div className="absolute inset-0 bg-white/90 backdrop-blur-sm flex flex-col items-center justify-center gap-2">
                        <Loader2 className="w-6 h-6 text-indigo-600 animate-spin" />
                        <span className="text-[8px] font-black text-indigo-600 uppercase tracking-widest">AI Extraction</span>
                      </div>
                    )}
                  </label>
                </div>
              </div>

              {/* PDF Library */}
              <div className="space-y-8">
                <div className="flex items-center justify-between border-b border-gray-200 pb-6">
                  <div>
                    <h3 className="text-2xl font-black text-gray-900 tracking-tight">Document Library</h3>
                    <p className="text-xs text-gray-400 font-bold uppercase tracking-[0.25em] mt-2">Historical Catalogs & Archives</p>
                  </div>
                  <div className="bg-white px-6 py-3 rounded-2xl border border-gray-100 text-sm font-black text-indigo-600 shadow-sm flex items-center gap-2">
                    <div className="w-2 h-2 bg-indigo-600 rounded-full animate-pulse" />
                    {pdfs.length} TOTAL DOCUMENTS
                  </div>
                </div>

                {pdfs.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
                    {pdfs.map((pdf) => (
                      <div key={pdf.id} className="group bg-white rounded-[2rem] border border-gray-100 hover:border-indigo-200 hover:shadow-2xl hover:shadow-indigo-100/50 transition-all duration-500 overflow-hidden flex flex-col relative">
                        <div className="aspect-[4/5] bg-gray-50 relative overflow-hidden">
                          <img src={pdf.thumbnail} alt={pdf.name} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
                          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-all duration-500 flex flex-col items-center justify-end p-6 gap-4">
                            <button 
                              onClick={() => fetchPages(pdf.id)}
                              className="w-full py-4 bg-white rounded-2xl text-sm font-black text-gray-900 shadow-2xl hover:bg-indigo-600 hover:text-white transition-all transform translate-y-4 group-hover:translate-y-0 duration-500"
                            >
                              OPEN CATALOG
                            </button>
                            <button 
                              onClick={() => handleDeletePdf(pdf.id)}
                              className="w-full py-3 bg-red-600/20 backdrop-blur-md border border-red-500/30 rounded-2xl text-xs font-black text-red-200 hover:bg-red-600 hover:text-white transition-all transform translate-y-8 group-hover:translate-y-0 duration-700"
                            >
                              PERMANENT DELETE
                            </button>
                          </div>
                          <div className="absolute top-4 left-4 bg-white/90 backdrop-blur-md px-4 py-2 rounded-xl text-[10px] font-black text-indigo-600 shadow-xl border border-white/50">
                            {pdf.page_count} PAGES
                          </div>
                        </div>
                        <div className="p-6">
                          <h4 className="font-black text-gray-900 truncate text-lg mb-2">{pdf.name}</h4>
                          <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-widest text-gray-400">
                             <span>Added {new Date(pdf.created_at).toLocaleDateString()}</span>
                             <span className="text-indigo-400">ID: #{pdf.id}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="bg-white rounded-[3rem] border-2 border-dashed border-gray-200 p-20 text-center space-y-6">
                    <div className="w-20 h-20 bg-gray-50 rounded-[1.5rem] flex items-center justify-center mx-auto opacity-50">
                      <FileText className="w-10 h-10 text-gray-300" />
                    </div>
                    <p className="text-gray-400 font-black text-sm uppercase tracking-[0.3em]">No documents archived</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* VIEW: GALLERY (PAGES) */}
          {view === 'gallery' && (
            <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex items-center justify-between">
                 <div>
                    <h2 className="text-3xl font-black text-gray-900 tracking-tight flex items-center gap-4">
                       <ImageIcon className="w-8 h-8 text-indigo-600" />
                       Document Index
                    </h2>
                    <p className="text-xs text-gray-400 font-bold uppercase tracking-[0.3em] mt-2">Select a page to start extraction</p>
                 </div>
                 <button 
                   onClick={() => setView('upload')}
                   className="px-6 py-3 bg-white border border-gray-200 rounded-2xl text-sm font-black text-gray-600 hover:bg-gray-50 hover:text-indigo-600 transition-all shadow-sm flex items-center gap-2"
                 >
                    <ChevronLeft className="w-4 h-4" /> Back to Library
                 </button>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
                {pdfPages.map((url, i) => (
                  <div key={`${url}-${i}`} onClick={() => handlePageClick(url)} className="group relative aspect-[3/4.5] bg-white rounded-[1.5rem] overflow-hidden shadow-sm hover:shadow-2xl hover:shadow-indigo-100 transition-all border border-gray-100 cursor-pointer">
                    <img src={url} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
                    <div className="absolute inset-0 bg-gradient-to-t from-indigo-900/60 to-transparent opacity-0 group-hover:opacity-100 transition-all duration-300 flex items-center justify-center p-4">
                       <div className="bg-white text-indigo-600 px-4 py-2 rounded-xl font-black text-[10px] uppercase tracking-widest shadow-2xl transform translate-y-4 group-hover:translate-y-0 transition-all">
                          EXTRACT MATERIALS
                       </div>
                    </div>
                    <div className="absolute top-4 left-4 bg-indigo-600 text-white px-3 py-1.5 rounded-lg text-[9px] font-black shadow-lg">
                       PG. {i + 1}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* VIEW: EDITOR */}
          {view === 'editor' && selectedPage && (
            <div className="flex flex-col lg:flex-row gap-0 h-auto lg:h-[calc(100vh-64px)] -m-4 sm:-m-8 lg:overflow-hidden bg-white relative animate-in fade-in duration-500">
               
              {/* Mobile Tabs */}
              <div className="lg:hidden flex border-b border-gray-100 bg-white shrink-0 sticky top-0 z-50">
                <button onClick={() => setMobileTab('canvas')} className={`flex-1 py-4 text-[10px] font-black uppercase tracking-[0.2em] border-b-4 transition-all ${mobileTab === 'canvas' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-400'}`}>Visual Editor</button>
                <button onClick={() => setMobileTab('queue')} className={`flex-1 py-4 text-[10px] font-black uppercase tracking-[0.2em] border-b-4 transition-all relative ${mobileTab === 'queue' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-gray-400'}`}>
                   Queue
                   {filters.length > 0 && <span className="absolute top-3 right-1/4 w-5 h-5 bg-indigo-600 text-white text-[10px] rounded-full flex items-center justify-center shadow-lg">{filters.length}</span>}
                </button>
              </div>

              {/* LEFT: Toolbar */}
              <div className={`${mobileTab === 'canvas' ? 'flex' : 'hidden'} lg:flex w-full lg:w-80 border-r border-gray-100 flex-col bg-slate-50/30 shrink-0 overflow-y-auto`}>
                 <div className="p-6 space-y-8">
                    <div className="space-y-4">
                       <h3 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.3em]">Precision Tools</h3>
                       <div className="space-y-6 bg-white p-6 rounded-3xl border border-gray-100 shadow-sm">
                          <div className="space-y-3">
                             <div className="flex items-center justify-between">
                                <span className="text-[10px] font-black text-gray-400 uppercase">Magnification</span>
                                <span className="text-sm font-black text-indigo-600">{zoom.toFixed(1)}x</span>
                             </div>
                             <input type="range" min="1" max="4" step="0.1" value={zoom} onChange={(e) => setZoom(parseFloat(e.target.value))} className="w-full h-1.5 bg-gray-100 rounded-lg appearance-none cursor-pointer accent-indigo-600" />
                          </div>
                           <div className="space-y-3">
                              <span className="text-[10px] font-black text-gray-400 uppercase">Manual Code Entry</span>
                              <div className="relative">
                                 <input 
                                   type="text" 
                                   value={manualCode} 
                                   onChange={(e) => {
                                      const val = e.target.value.toUpperCase();
                                      setManualCode(val);
                                      // Optional: auto-focus if matches a detected code
                                      const match = detectedCodes.find(d => d.code === val);
                                      if (match) {
                                         const sX = imgDimensions.naturalWidth / imgDimensions.width;
                                         const sY = imgDimensions.naturalHeight / imgDimensions.height;
                                         const nc: Crop = {
                                            unit: 'px',
                                            x: match.left / sX,
                                            y: match.top / sY,
                                            width: match.width / sX,
                                            height: match.height / sY
                                         };
                                         setCrop(nc);
                                         setCompletedCrop(nc as PixelCrop);
                                      }
                                   }}
                                   className="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 text-sm font-black uppercase outline-none focus:border-indigo-500 focus:bg-white focus:ring-4 focus:ring-indigo-50 transition-all pr-10"
                                   placeholder="TYPE CODE..."
                                 />
                                 <Edit3 className="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 text-gray-300" />
                              </div>
                           </div>
                           <button onClick={handleAddToGrid} disabled={!completedCrop || cropping} className="w-full py-4 bg-indigo-600 text-white rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-indigo-700 disabled:opacity-30 transition-all shadow-xl shadow-indigo-100 flex items-center justify-center gap-3">
                              {cropping ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />} Commit Selection
                           </button>
                       </div>
                    </div>

                    <div className="space-y-4">
                       <h3 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.3em]">Detected Codes</h3>
                       {detectedCodes.length > 0 ? (
                         <div className="flex flex-wrap gap-2">
                           {detectedCodes.map((d, i) => (
                             <button 
                               key={i} 
                               onClick={() => {
                                 const sX = imgDimensions.naturalWidth / imgDimensions.width;
                                 const sY = imgDimensions.naturalHeight / imgDimensions.height;
                                 const nc: Crop = {
                                   unit: 'px',
                                   x: d.left / sX,
                                   y: d.top / sY,
                                   width: d.width / sX,
                                   height: d.height / sY
                                 };
                                 setCrop(nc);
                                 setCompletedCrop(nc as PixelCrop);
                                 setManualCode(d.code);
                               }}
                               className={`px-3 py-1.5 rounded-lg text-[10px] font-black transition-all shadow-sm border ${
                                 manualCode === d.code 
                                   ? 'bg-indigo-600 border-indigo-600 text-white' 
                                   : 'bg-white border-gray-200 text-gray-700 hover:border-indigo-600 hover:text-indigo-600'
                               }`}
                             >
                               {d.code}
                             </button>
                           ))}
                         </div>
                       ) : (
                         <div className="bg-gray-100 rounded-2xl p-4 text-center">
                            <p className="text-[9px] font-bold text-gray-400 uppercase tracking-widest">No codes detected yet</p>
                         </div>
                       )}
                    </div>

                    <div className="space-y-4">
                       <h3 className="text-[10px] font-black text-gray-400 uppercase tracking-[0.3em]">AI Insights</h3>
                       <div className="bg-indigo-600 rounded-3xl p-6 text-white space-y-4 shadow-xl shadow-indigo-100">
                          <AlertCircle className="w-8 h-8 opacity-50" />
                          <p className="text-xs font-bold leading-relaxed">Our AI has mapped the text coordinates on this page. Clicking a detected code in the library sidebar will automatically focus the crop area.</p>
                       </div>
                    </div>
                 </div>
              </div>

              {/* CENTER: Canvas */}
              <div className={`${mobileTab === 'canvas' ? 'flex' : 'hidden'} lg:flex flex-1 flex-col bg-slate-100/50 relative lg:overflow-auto p-4 lg:p-12`}>
                 <div className="flex items-center justify-center min-h-full">
                    <div style={{ transform: `scale(${zoom})`, transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)', transformOrigin: 'center center' }} className="bg-white shadow-2xl relative inline-block rounded-sm">
                       <ReactCrop crop={crop} onChange={c => setCrop(c)} onComplete={c => setCompletedCrop(c)}>
                          <img ref={imgRef} src={selectedPage} onLoad={onImageLoad} className="max-w-full lg:max-w-[none] lg:max-h-[85vh] h-auto object-contain select-none block" />
                       </ReactCrop>
                       {detectingCode && <div className="absolute inset-0 bg-white/40 backdrop-blur-sm flex items-center justify-center z-50"><Loader2 className="w-12 h-12 text-indigo-600 animate-spin" /></div>}
                    </div>
                 </div>
              </div>

              {/* RIGHT: Queue */}
              <div className={`${mobileTab === 'queue' ? 'flex' : 'hidden'} lg:flex w-full lg:w-96 border-l border-gray-100 flex-col bg-white shrink-0`}>
                 <div className="p-6 border-b border-gray-100 flex items-center justify-between sticky top-0 bg-white z-10">
                    <h3 className="text-sm font-black text-gray-900 uppercase tracking-widest">Selection Queue</h3>
                    <div className="w-8 h-8 bg-indigo-50 rounded-xl flex items-center justify-center text-indigo-600"><Grid className="w-4 h-4" /></div>
                 </div>
                 <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/30">
                    {filters.map((filter, i) => (
                      <div key={filter.id || i} id={`filter-card-${i}`} onClick={() => setActiveIndex(i)} className={`group relative bg-white p-4 rounded-3xl border-2 transition-all duration-300 cursor-pointer ${activeIndex === i ? 'border-indigo-600 shadow-2xl shadow-indigo-100' : 'border-transparent hover:border-gray-200'}`}>
                         <div className="flex gap-4">
                            <div className="w-20 h-20 rounded-2xl overflow-hidden border border-gray-100 shrink-0">
                               <img src={filter.url} className="w-full h-full object-cover" />
                            </div>
                            <div className="flex-1 space-y-3 min-w-0">
                               <div className="relative group/input">
                                 <input 
                                   type="text" 
                                   value={filter.code} 
                                   onChange={(e) => { const n = [...filters]; n[i].code = e.target.value.toUpperCase(); setFilters(n); }} 
                                   className={`w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm font-black uppercase outline-none focus:border-indigo-500 focus:bg-white focus:ring-4 focus:ring-indigo-50 transition-all ${filter.code === 'UNKNOWN' ? 'text-red-500 border-red-200 bg-red-50' : 'text-gray-900'}`}
                                   placeholder="ASSIGN CODE..."
                                 />
                                 <Edit3 className="w-3.5 h-3.5 absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 opacity-0 group-hover/input:opacity-100 transition-opacity pointer-events-none" />
                               </div>
                               <div className="flex gap-2">
                                  <button onClick={(e) => { e.stopPropagation(); handleSaveFilter(i); }} className="flex-1 bg-gray-900 text-white py-2 rounded-xl text-[10px] font-black uppercase hover:bg-black transition-all">COMMIT</button>
                                  <button onClick={(e) => { e.stopPropagation(); handleDeleteFilter(i); }} className="p-2 text-gray-300 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all"><Trash2 className="w-4 h-4" /></button>
                               </div>
                            </div>
                         </div>
                      </div>
                    ))}
                 </div>
              </div>
            </div>
          )}

        </div>
      </main>

      {/* Global Material Library (Sticky Bottom Toggle or dedicated view?) */}
      <div className="bg-white border-t border-gray-200 p-8">
         <div className="max-w-7xl mx-auto space-y-8">
            <div className="flex items-center justify-between">
               <h3 className="text-2xl font-black text-gray-900 tracking-tight">Material Repository</h3>
               <button onClick={fetchFilters} className="p-3 hover:bg-gray-100 rounded-2xl transition-all text-gray-400 hover:text-indigo-600"><RotateCcw className="w-5 h-5" /></button>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 xl:grid-cols-10 gap-4">
                {filters.reduce((acc: any[], curr) => {
                  if (!acc.find(f => f.code === curr.code)) acc.push(curr);
                  return acc;
                }, []).map((filter, i) => (
                  <div key={i} className="group relative aspect-square rounded-[1.5rem] overflow-hidden border border-gray-100 bg-white hover:shadow-2xl transition-all">
                     <img src={filter.url} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
                     <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center p-2">
                        <button onClick={() => handleDeleteFilter(filters.findIndex(f => f.id === filter.id))} className="w-full py-2 bg-white rounded-xl text-[8px] font-black text-red-600 uppercase shadow-xl">Delete</button>
                     </div>
                     <div className="absolute bottom-2 left-2 right-2 bg-white/90 backdrop-blur-md px-2 py-1 rounded-lg text-[7px] font-black text-gray-900 truncate shadow-lg border border-white/50">{filter.code}</div>
                  </div>
                ))}
            </div>
         </div>
      </div>
    </div>
  )
}
