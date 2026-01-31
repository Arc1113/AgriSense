import { useState, useRef, useCallback } from 'react'
import Webcam from 'react-webcam'
import './index.css'

const API_URL = 'http://localhost:8000'

function App() {
  const webcamRef = useRef(null)
  const [result, setResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('organic')
  const [error, setError] = useState(null)

  const videoConstraints = {
    facingMode: { ideal: 'environment' },
    width: { ideal: 1280 },
    height: { ideal: 720 }
  }

  const capture = useCallback(async () => {
    if (!webcamRef.current) return

    setIsLoading(true)
    setError(null)

    try {
      const imageSrc = webcamRef.current.getScreenshot()

      // Convert base64 to blob
      const base64Response = await fetch(imageSrc)
      const blob = await base64Response.blob()

      // Create form data
      const formData = new FormData()
      formData.append('file', blob, 'capture.jpg')

      // Send to backend
      const response = await fetch(`${API_URL}/predict`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error('Failed to analyze image')
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err.message)
      console.error('Capture error:', err)
    } finally {
      setIsLoading(false)
    }
  }, [webcamRef])

  const closeResult = () => {
    setResult(null)
    setActiveTab('organic')
  }

  return (
    <div className="relative h-full w-full bg-black">
      {/* Full-screen Webcam Viewfinder */}
      <Webcam
        ref={webcamRef}
        audio={false}
        screenshotFormat="image/jpeg"
        videoConstraints={videoConstraints}
        className="h-full w-full object-cover"
      />

      {/* Header Overlay */}
      <div className="absolute top-0 left-0 right-0 bg-gradient-to-b from-black/60 to-transparent p-4 safe-top">
        <div className="flex items-center justify-center gap-2">
          <div className="w-8 h-8 bg-agri-green rounded-full flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
            </svg>
          </div>
          <h1 className="text-white text-xl font-bold tracking-tight">AgriSense</h1>
        </div>
      </div>

      {/* Scanning Guide Overlay */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="w-64 h-64 border-2 border-white/40 rounded-2xl">
          <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-black/50 px-4 py-2 rounded-full">
            <span className="text-white text-sm">Position leaf in frame</span>
          </div>
        </div>
      </div>

      {/* Capture Button */}
      <div className="absolute bottom-8 left-0 right-0 flex justify-center safe-bottom">
        <button
          onClick={capture}
          disabled={isLoading}
          className={`
            w-24 h-24 rounded-full 
            bg-agri-amber 
            border-4 border-white 
            shadow-2xl
            flex items-center justify-center
            transition-all duration-200
            active:scale-95
            disabled:opacity-50
            ${!isLoading && 'capture-btn-pulse'}
          `}
        >
          {isLoading ? (
            <svg className="w-10 h-10 text-white animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          ) : (
            <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          )}
        </button>
      </div>

      {/* Error Toast */}
      {error && (
        <div className="absolute top-20 left-4 right-4 bg-red-500 text-white px-4 py-3 rounded-xl shadow-lg">
          <p className="text-sm font-medium">{error}</p>
          <button onClick={() => setError(null)} className="absolute top-2 right-2 text-white/80 hover:text-white">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Result Card (Slide-up) */}
      {result && (
        <div className="absolute inset-0 bg-black/50 flex items-end" onClick={closeResult}>
          <div
            className="bg-white w-full rounded-t-3xl p-6 safe-bottom slide-up max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Handle Bar */}
            <div className="w-12 h-1 bg-gray-300 rounded-full mx-auto mb-6"></div>

            {/* Disease Name */}
            <div className="flex items-center gap-3 mb-2">
              <div className={`w-3 h-3 rounded-full ${result.confidence > 0.8 ? 'bg-red-500' :
                  result.confidence > 0.5 ? 'bg-agri-amber' : 'bg-agri-green'
                }`}></div>
              <h2 className="text-3xl font-bold text-gray-900">{result.disease}</h2>
            </div>

            {/* Confidence */}
            <p className="text-gray-500 mb-6">
              Confidence: <span className="font-semibold text-gray-700">{(result.confidence * 100).toFixed(1)}%</span>
              {result.advice?.severity && (
                <span className={`ml-3 px-2 py-1 rounded-full text-xs font-medium ${result.advice.severity === 'High' ? 'bg-red-100 text-red-700' :
                    result.advice.severity === 'Medium' ? 'bg-amber-100 text-amber-700' :
                      'bg-green-100 text-green-700'
                  }`}>
                  {result.advice.severity} Severity
                </span>
              )}
            </p>

            {/* Treatment Tabs */}
            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setActiveTab('organic')}
                className={`flex-1 py-3 px-4 rounded-xl font-medium transition-all touch-target ${activeTab === 'organic'
                    ? 'bg-agri-green text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
              >
                🌿 Organic
              </button>
              <button
                onClick={() => setActiveTab('chemical')}
                className={`flex-1 py-3 px-4 rounded-xl font-medium transition-all touch-target ${activeTab === 'chemical'
                    ? 'bg-agri-amber text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
              >
                🧪 Chemical
              </button>
            </div>

            {/* Treatment Content */}
            <div className="bg-gray-50 rounded-xl p-4 min-h-[100px]">
              {activeTab === 'organic' ? (
                <div>
                  <h3 className="font-semibold text-agri-green mb-2">Organic Treatment</h3>
                  <p className="text-gray-700">{result.advice?.organic_treatment || 'No organic treatment advice available.'}</p>
                </div>
              ) : (
                <div>
                  <h3 className="font-semibold text-agri-amber-dark mb-2">Chemical Treatment</h3>
                  <p className="text-gray-700">{result.advice?.chemical_treatment || 'No chemical treatment advice available.'}</p>
                </div>
              )}
            </div>

            {/* Close Button */}
            <button
              onClick={closeResult}
              className="w-full mt-6 py-4 bg-gray-900 text-white rounded-xl font-semibold touch-target-lg transition-all active:scale-98"
            >
              Scan Another Leaf
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
