import { useState } from 'react'
import RoomSelect from './components/RoomSelect'
import Visualizer from './components/Visualizer'

function App() {
  const [selectedRoom, setSelectedRoom] = useState<any>(null)

  if (selectedRoom) {
    return <Visualizer room={selectedRoom} onBack={() => setSelectedRoom(null)} />
  }

  return <RoomSelect onSelect={setSelectedRoom} />
}

export default App
