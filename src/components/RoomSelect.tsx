import { useState, useEffect } from 'react'

const tabs = ['All Rooms', 'Popular', 'Upload Your Own']

export default function RoomSelect({ onSelect }: { onSelect: (room: any) => void }) {
  const [activeTab, setActiveTab] = useState('All Rooms')
  const [hoveredRoom, setHoveredRoom] = useState<string | null>(null)
  const [rooms, setRooms] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('http://localhost:5000/api/rooms')
      .then(res => res.json())
      .then(data => {
        setRooms(data)
        setLoading(false)
      })
      .catch(err => console.error('Error fetching rooms:', err))
  }, [])

  const handleUpload = async (file: File) => {
    const formData = new FormData()
    formData.append('image', file)

    try {
      const res = await fetch('http://localhost:5000/api/upload', {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      onSelect({
        id: 'custom',
        name: 'My Room',
        image: data.imageUrl,
        description: 'Uploaded room photo',
      })
    } catch (err) {
      console.error('Error uploading image:', err)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
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
                Visualize My Walls & Floors
              </span>
            </div>
            <div className="flex items-center gap-4">
              <button className="text-sm text-gray-500 hover:text-gray-700 transition-colors hidden sm:block">
                Help
              </button>
              <button className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium">
                Upload Photo
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Progress Steps */}
      <div className="bg-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-center gap-2 sm:gap-4">
            <Step number={1} label="Select Room" active />
            <StepDivider />
            <Step number={2} label="Choose Product" />
            <StepDivider />
            <Step number={3} label="Visualize" />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        {/* Heading */}
        <div className="text-center mb-8 sm:mb-10">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-3">
            Select a Room to Get Started
          </h1>
          <p className="text-gray-500 text-base sm:text-lg max-w-2xl mx-auto">
            Choose a sample room below or upload your own photo to visualize how new walls and floors will look in your space.
          </p>
        </div>

        {/* Tabs */}
        <div className="flex items-center justify-center gap-1 mb-8 bg-gray-100 rounded-xl p-1 max-w-md mx-auto">
          {tabs.map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                activeTab === tab
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Upload Section */}
        {activeTab === 'Upload Your Own' ? (
          <UploadSection onUpload={handleUpload} />
        ) : (
          /* Room Grid */
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {loading ? (
              <div className="col-span-full text-center py-12">
                <div className="animate-spin w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
                <p className="text-gray-500">Loading rooms...</p>
              </div>
            ) : (activeTab === 'Popular' ? rooms.slice(0, 4) : rooms).map((room: any) => (
              <button
                key={room.id}
                onClick={() => onSelect(room)}
                onMouseEnter={() => setHoveredRoom(room.id)}
                onMouseLeave={() => setHoveredRoom(null)}
                className="group relative bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 text-left border border-gray-100 hover:border-blue-200 hover:-translate-y-1"
              >
                <div className="aspect-[3/2] overflow-hidden relative">
                  <img
                    src={room.image}
                    alt={room.name}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                  />
                  <div className={`absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent transition-opacity duration-300 ${hoveredRoom === room.id ? 'opacity-100' : 'opacity-0'}`} />
                  <div className={`absolute bottom-3 right-3 bg-white/95 backdrop-blur-sm rounded-full p-2.5 shadow-lg transition-all duration-300 ${hoveredRoom === room.id ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}`}>
                    <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                    </svg>
                  </div>
                </div>
                <div className="p-4">
                  <h3 className="font-semibold text-gray-900 text-base mb-1">{room.name}</h3>
                  <p className="text-sm text-gray-500 leading-relaxed">{room.description}</p>
                </div>
              </button>
            ))}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-sm text-gray-400">
              Powered by Visualize My Walls & Floors
            </p>
            <div className="flex items-center gap-6">
              <a href="#" className="text-sm text-gray-400 hover:text-gray-600 transition-colors">Privacy</a>
              <a href="#" className="text-sm text-gray-400 hover:text-gray-600 transition-colors">Terms</a>
              <a href="#" className="text-sm text-gray-400 hover:text-gray-600 transition-colors">Support</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}

function Step({ number, label, active }: { number: number, label: string, active?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
        active
          ? 'bg-blue-600 text-white'
          : 'bg-gray-200 text-gray-500'
      }`}>
        {number}
      </div>
      <span className={`text-sm font-medium hidden sm:block ${
        active ? 'text-gray-900' : 'text-gray-400'
      }`}>
        {label}
      </span>
    </div>
  )
}

function StepDivider() {
  return (
    <div className="w-8 sm:w-12 h-px bg-gray-300" />
  )
}

function UploadSection({ onUpload }: { onUpload: (file: File) => void }) {
  const [dragOver, setDragOver] = useState(false)

  const handleFile = (file: File) => {
    if (file && (file.type === 'image/jpeg' || file.type === 'image/png')) {
      onUpload(file)
    } else {
      alert('Please upload a valid JPG or PNG image.')
    }
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setDragOver(false)
        const file = e.dataTransfer.files[0]
        handleFile(file)
      }}
      className={`max-w-xl mx-auto border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-200 ${
        dragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 bg-white'
      }`}
    >
      <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-5">
        <svg className="w-8 h-8 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
        </svg>
      </div>
      <h3 className="text-lg font-semibold text-gray-900 mb-2">Upload Your Room Photo</h3>
      <p className="text-gray-500 mb-6 text-sm">
        Drag and drop your photo here, or click to browse.<br />
        Supports JPG, PNG up to 10MB
      </p>
      <input
        type="file"
        id="room-upload"
        className="hidden"
        accept="image/jpeg,image/png"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) handleFile(file)
        }}
      />
      <label
        htmlFor="room-upload"
        className="inline-block bg-blue-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-blue-700 transition-colors cursor-pointer"
      >
        Browse Files
      </label>
    </div>
  )
}
