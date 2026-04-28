import { useState, useEffect } from 'react'

export default function Visualizer({ room, onBack }: { room: any, onBack: () => void }) {
  const [activeProduct, setActiveProduct] = useState<any>({ id: 1, name: 'Decent -88656-2', type: 'wall', color: '#b8956a', size: '21 X 10', finish: 'Matt' })
  const [filter, setFilter] = useState('all')
  const [wallColor, setWallColor] = useState<string | null>(null)
  const [products, setProducts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showFilters, setShowFilters] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list')

  useEffect(() => {
    fetch('http://localhost:5000/api/products')
      .then(res => res.json())
      .then(data => {
        // Enhance products with size and finish to match screenshot
        const enhanced = data.map((p: any) => ({
          ...p,
          size: p.type === 'wall' ? '21 X 10' : '60 X 60',
          finish: 'Matt'
        }))
        setProducts(enhanced)
        setLoading(false)
      })
      .catch(err => console.error('Error fetching products:', err))
  }, [])

  const filtered = products.filter(p => {
    const matchesFilter = filter === 'all' || p.type === filter
    const matchesSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesFilter && matchesSearch
  })

  return (
    <div className="h-screen bg-[#f3f4f6] flex flex-col overflow-hidden font-sans text-[#333]">
      {/* Top Navigation */}
      <header className="bg-white border-b border-gray-200 h-16 flex items-center justify-between px-6 shrink-0 z-10">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="p-2 hover:bg-gray-100 rounded-full transition-colors border border-gray-200">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button className="bg-[#a82b34] text-white px-6 py-2 rounded font-medium flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            Get In Touch
          </button>
        </div>

        <div className="flex items-center gap-6">
          <button className="flex items-center gap-2 text-sm font-medium hover:text-[#a82b34]">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add To Catalog
          </button>
          <button className="flex items-center gap-2 text-sm font-medium hover:text-[#a82b34]">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            Change Room
          </button>
          <button className="flex items-center gap-2 text-sm font-medium hover:text-[#a82b34]">
            Menu
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
            </svg>
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-[380px] bg-white border-r border-gray-200 flex flex-col shrink-0 overflow-hidden">
          <div className="p-4 border-b border-gray-100 flex flex-col items-center gap-2">
             <div className="text-center">
                <h1 className="text-2xl font-serif italic text-[#a82b34] font-bold leading-none">CJS</h1>
                <p className="text-[10px] uppercase tracking-widest text-gray-500">Inspire Decor Space</p>
             </div>
          </div>

          <div className="p-4 space-y-4">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <input 
                  type="text" 
                  placeholder="Search..." 
                  className="w-full pl-10 pr-4 py-2 bg-[#f9fafb] border border-gray-200 rounded text-sm focus:outline-none focus:border-[#a82b34]"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <svg className="w-5 h-5 absolute left-3 top-2.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <button 
                onClick={() => setShowFilters(true)}
                className="px-4 py-2 border border-gray-200 rounded flex items-center gap-2 text-sm font-medium hover:bg-gray-50"
              >
                <div className="relative">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" />
                  </svg>
                </div>
                Filters
              </button>
              <div className="flex border border-gray-200 rounded overflow-hidden">
                 <button 
                  onClick={() => setViewMode('list')}
                  className={`p-2 ${viewMode === 'list' ? 'bg-[#a82b34] text-white' : 'bg-white text-gray-500'}`}
                 >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
                 </button>
                 <button 
                  onClick={() => setViewMode('grid')}
                  className={`p-2 ${viewMode === 'grid' ? 'bg-[#a82b34] text-white' : 'bg-white text-gray-500'}`}
                 >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>
                 </button>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs font-semibold text-gray-500 uppercase tracking-wider">
               <div className="flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h6" /></svg>
                  New Products First
               </div>
               <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-4 pb-4 space-y-4">
            {loading ? (
               <div className="flex justify-center py-10"><div className="animate-spin w-8 h-8 border-4 border-[#a82b34] border-t-transparent rounded-full"></div></div>
            ) : filtered.map((product) => (
              <div 
                key={product.id}
                onClick={() => {
                  setActiveProduct(product)
                  if (product.type === 'wall') setWallColor(product.color)
                }}
                className={`relative border rounded-lg overflow-hidden transition-all cursor-pointer hover:shadow-md ${activeProduct?.id === product.id ? 'border-[#a82b34] ring-1 ring-[#a82b34]' : 'border-gray-200'}`}
              >
                <div className={`flex ${viewMode === 'grid' ? 'flex-col' : 'flex-row'}`}>
                  <div className={`${viewMode === 'grid' ? 'w-full aspect-square' : 'w-24 h-24'} shrink-0 bg-gray-100 relative`}>
                    <img src={product.preview || product.image} alt={product.name} className="w-full h-full object-cover" />
                    <button className="absolute top-1 right-1 p-1 bg-white/80 rounded-full hover:text-[#a82b34]">
                       <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" /></svg>
                    </button>
                  </div>
                  <div className="p-3 flex-1 flex flex-col justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-gray-800">{product.name}</h3>
                      <p className="text-[11px] text-gray-500">Size: {product.size}</p>
                      <p className="text-[11px] text-gray-500">{product.finish}</p>
                    </div>
                    <div className="flex items-center justify-between mt-2">
                       <button className="text-[11px] text-gray-600 underline hover:text-[#a82b34] flex items-center gap-1">
                          More Product Detail 
                          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
                       </button>
                       <button className="p-1 hover:text-[#a82b34]">
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" /></svg>
                       </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* Main Preview Area */}
        <main className="flex-1 relative flex flex-col bg-gray-200">
           <div className="flex-1 relative flex items-center justify-center p-8">
              <div className="relative w-full max-w-4xl shadow-2xl rounded-sm overflow-hidden bg-white">
                <img src={room.image} alt={room.name} className="w-full h-full object-cover" />
                {activeProduct?.type === 'wall' && (
                  <div
                    className="absolute inset-0 transition-all duration-700 pointer-events-none"
                    style={{ 
                      backgroundColor: activeProduct.pattern ? 'transparent' : activeProduct.color,
                      backgroundImage: activeProduct.pattern ? `url(${activeProduct.pattern})` : 'none',
                      backgroundSize: '200px',
                      backgroundRepeat: 'repeat',
                      mixBlendMode: 'multiply', 
                      opacity: 0.45 
                    }}
                  />
                )}
                
                {/* Marker - Matching the 'Wall' indicator */}
                <div className="absolute top-1/2 right-[20%] group">
                  <div className="bg-[#a82b34] text-white px-3 py-1 rounded-full text-[10px] font-bold flex items-center gap-1 cursor-pointer shadow-lg animate-pulse">
                    Wall
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M12 6v6m0 0v6m0-6h6m-6 0H6" /></svg>
                  </div>
                </div>

                {/* Zoom button */}
                <button className="absolute top-[50%] right-4 p-2 bg-white/80 rounded border border-gray-200 hover:bg-white">
                   <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" /></svg>
                </button>

                <div className="absolute bottom-0 right-0 p-2">
                   <p className="text-[10px] text-gray-400">Powered By <span className="font-bold">Tilesview.ai</span></p>
                </div>
              </div>
           </div>

           {/* Bottom Interaction Bar */}
           <div className="h-16 bg-white border-t border-gray-200 flex items-center justify-between px-8 shrink-0">
              <div className="flex items-center gap-4">
                 <div className="w-8 h-8 bg-gray-100 rounded flex items-center justify-center border border-gray-200">
                    <img src={activeProduct?.preview || activeProduct?.image} className="w-full h-full object-cover" />
                 </div>
                 <div className="leading-tight">
                    <p className="text-[10px] font-bold text-gray-400 uppercase tracking-tighter">CJ Sheth</p>
                    <p className="text-xs font-bold text-gray-800">{activeProduct?.name} <span className="text-gray-400 font-normal ml-1">ⓘ</span></p>
                 </div>
              </div>

              <div className="flex items-center gap-8">
                 <button className="flex items-center gap-2 text-sm font-medium hover:text-[#a82b34]">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                    Reset
                 </button>
                 <button className="flex items-center gap-2 text-sm font-medium hover:text-[#a82b34]">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" /></svg>
                    Grout
                 </button>
                 <button className="flex items-center gap-2 text-sm font-medium hover:text-[#a82b34]">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" /></svg>
                    Layout
                 </button>
                 <button className="flex items-center gap-2 text-sm font-medium hover:text-[#a82b34]">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012-2" /></svg>
                    Applied Products
                 </button>
                 <button className="flex items-center gap-2 text-sm font-medium hover:text-[#a82b34]">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
                    Compare
                 </button>
              </div>
           </div>
        </main>
      </div>

      {/* Filter Modal */}
      {showFilters && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white w-full max-w-2xl rounded-lg overflow-hidden shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-gray-100">
               <div className="flex items-center gap-2 font-bold text-gray-800">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" /></svg>
                  Filters (0)
               </div>
               <button onClick={() => setShowFilters(false)} className="p-2 hover:bg-gray-100 rounded-full">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
               </button>
            </div>
            <div className="flex h-96">
               <div className="w-48 border-r border-gray-100 bg-[#f9fafb]">
                  {['WALLPAPER', 'FLOORING', 'SIZES'].map(cat => (
                    <button key={cat} className={`w-full text-left px-6 py-4 text-xs font-bold tracking-widest ${cat === 'WALLPAPER' ? 'bg-white border-l-4 border-[#a82b34] text-[#a82b34]' : 'text-gray-500 hover:text-gray-700'}`}>
                      {cat}
                    </button>
                  ))}
               </div>
               <div className="flex-1 p-6 grid grid-cols-2 gap-4 overflow-y-auto">
                  {['ATHENA', 'FLAMES', 'NIHU 2', 'AMIRI', 'ARCADIA', 'B&B', 'BOARA', 'DREAM WORLD', 'DUBAI', 'E JOY 6'].map(item => (
                    <div key={item} className="flex items-center justify-between group cursor-pointer p-2 hover:bg-gray-50 rounded">
                       <span className="text-xs font-bold text-gray-600 uppercase tracking-tighter">{item}</span>
                       <div className="w-5 h-5 border-2 border-gray-300 rounded group-hover:border-[#a82b34]" />
                    </div>
                  ))}
               </div>
            </div>
            <div className="p-4 border-t border-gray-100 flex items-center justify-end gap-4">
               <button onClick={() => setShowFilters(false)} className="px-6 py-2 text-sm font-bold text-gray-600 hover:underline">Clear All</button>
               <button onClick={() => setShowFilters(false)} className="px-10 py-2 bg-[#a82b34] text-white rounded font-bold text-sm shadow-lg">Apply</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
