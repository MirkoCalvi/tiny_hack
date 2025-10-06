import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { EmotionProvider } from './context/EmotionContext'
import SetupPage from './pages/SetupPage'
import VideoPage from './pages/VideoPage'
import DashboardPage from './pages/DashboardPage.tsx'

function App() {
  return (
    <BrowserRouter>
      <EmotionProvider>
        <Routes>
          <Route path="/" element={<SetupPage />} />
          <Route path="/video" element={<VideoPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </EmotionProvider>
    </BrowserRouter>
  )
}

export default App
