import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import './index.css'

// Lazy load heavy components
const Webcam = lazy(() => import('react-webcam'))
const DiseaseResultCard = lazy(() => import('./components/DiseaseResultCard'))
const ESP32ScannerPage = lazy(() => import('./pages/ESP32ScannerPage'))

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Loading fallback for lazy components
const LoadingFallback = () => (
  <div className="flex items-center justify-center h-full w-full bg-slate-900">
    <div className="w-10 h-10 border-3 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin"></div>
  </div>
)

function App() {
  const location = useLocation()

  // If on ESP32 page, render that directly (no splash)
  if (location.pathname === '/esp32') {
    return (
      <Suspense fallback={<LoadingFallback />}>
        <ESP32ScannerPage />
      </Suspense>
    )
  }

  return <CameraPage />
}

function CameraPage() {
  const webcamRef = useRef(null)
  const fileInputRef = useRef(null)
  const [result, setResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [activeStep, setActiveStep] = useState(0)
  const [windowSize, setWindowSize] = useState({ width: window.innerWidth, height: window.innerHeight })
  const [previewImage, setPreviewImage] = useState(null)
  const [isCameraReady, setIsCameraReady] = useState(false)
  const [isAppReady, setIsAppReady] = useState(false)
  const [splashProgress, setSplashProgress] = useState(0)

  // Splash screen loading simulation
  useEffect(() => {
    const progressInterval = setInterval(() => {
      setSplashProgress(prev => {
        if (prev >= 100) {
          clearInterval(progressInterval)
          return 100
        }
        return prev + Math.random() * 15 + 5
      })
    }, 200)

    // Minimum splash screen time of 2.5 seconds
    const timer = setTimeout(() => {
      setIsAppReady(true)
    }, 2500)

    return () => {
      clearTimeout(timer)
      clearInterval(progressInterval)
    }
  }, [])

  // Handle Resize for responsive layout calculations
  useEffect(() => {
    const handleResize = () => setWindowSize({ width: window.innerWidth, height: window.innerHeight })
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const videoConstraints = {
    facingMode: { ideal: 'environment' },
    width: { ideal: 1920 },
    height: { ideal: 1080 },
    aspectRatio: windowSize.width < 768 ? windowSize.height / windowSize.width : 16 / 9
  }

  const simulateProgress = () => {
    setActiveStep(0)
    setTimeout(() => setActiveStep(1), 1000)
    setTimeout(() => setActiveStep(2), 2200)
  }

  const sendToApi = async (blob) => {
    setIsLoading(true)
    setError(null)
    simulateProgress()

    // Minimum loading time of 2.5s for UX
    const startTime = Date.now()

    try {
      const formData = new FormData()
      formData.append('file', blob, 'capture.jpg')

      const response = await fetch(`${API_URL}/predict/image`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error('Failed to analyze image')
      }

      const data = await response.json()

      const elapsed = Date.now() - startTime
      if (elapsed < 2500) {
        await new Promise(r => setTimeout(r, 2500 - elapsed))
      }

      setResult(data)
    } catch (err) {
      setError(err.message)
      console.error('Analysis error:', err)
    } finally {
      setIsLoading(false)
      setActiveStep(0)
    }
  }

  const captureFromCamera = useCallback(async () => {
    if (!webcamRef.current) return

    // Visual flash
    const shutter = document.getElementById('camera-flash')
    if (shutter) {
      shutter.style.opacity = '1'
      setTimeout(() => shutter.style.opacity = '0', 150)
    }

    const imageSrc = webcamRef.current.getScreenshot()
    if (!imageSrc) return

    setPreviewImage(imageSrc)

    const base64Response = await fetch(imageSrc)
    const blob = await base64Response.blob()

    await sendToApi(blob)
  }, [webcamRef])

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    const objectUrl = URL.createObjectURL(file)
    setPreviewImage(objectUrl)

    await sendToApi(file)
    event.target.value = ''
  }

  const handleCloseResult = () => {
    setResult(null)
    setPreviewImage(null)
  }

  const handleSaveResult = (data) => {
    // Save to local storage for offline access
    const savedResults = JSON.parse(localStorage.getItem('savedResults') || '[]')
    const newResult = {
      ...data,
      savedAt: new Date().toISOString(),
      image: previewImage
    }
    savedResults.unshift(newResult)
    localStorage.setItem('savedResults', JSON.stringify(savedResults.slice(0, 20))) // Keep last 20
    console.log('Result saved!')
  }

  const handleReportResult = (data) => {
    // For now, log the report - in production this would send to backend
    console.log('Report submitted for:', data.disease)
    alert('Thanks for your feedback! This helps improve our AI accuracy.')
  }

  // === SPLASH SCREEN ===
  if (!isAppReady) {
    return (
      <div className="splash-screen">
        {/* Background gradient orbs */}
        <div className="splash-bg-orb splash-bg-orb-1"></div>
        <div className="splash-bg-orb splash-bg-orb-2"></div>
        <div className="splash-bg-orb splash-bg-orb-3"></div>
        
        {/* Logo and branding */}
        <div className="splash-content">
          {/* Animated logo */}
          <div className="splash-logo">
            <div className="splash-logo-ring"></div>
            <div className="splash-logo-ring splash-logo-ring-2"></div>
            <div className="splash-logo-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 3c.132 0 .263 0 .393 0a7.5 7.5 0 0 0 7.92 12.446a9 9 0 1 1 -8.313 -12.454z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 4a2 2 0 0 0 2 2a2 2 0 0 0 -2 2a2 2 0 0 0 -2 -2a2 2 0 0 0 2 -2" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M19 11h2m-1 -1v2" />
              </svg>
            </div>
          </div>

          {/* App name */}
          <h1 className="splash-title">
            <span className="splash-title-agri">Agri</span>
            <span className="splash-title-sense">Sense</span>
          </h1>
          <p className="splash-subtitle">AI-Powered Plant Health Analysis</p>

          {/* Loading progress */}
          <div className="splash-progress">
            <div className="splash-progress-track">
              <div 
                className="splash-progress-bar" 
                style={{ width: `${Math.min(splashProgress, 100)}%` }}
              ></div>
            </div>
            <p className="splash-progress-text">
              {splashProgress < 30 ? 'Initializing AI...' : 
               splashProgress < 60 ? 'Loading models...' : 
               splashProgress < 90 ? 'Preparing camera...' : 'Ready!'}
            </p>
          </div>
        </div>

        {/* Bottom branding */}
        <div className="splash-footer">
          <p>Powered by Deep Learning</p>
        </div>
      </div>
    )
  }

  return (
    // Main Container - Modern gradient background
    <div className="relative h-screen w-full flex items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 overflow-hidden">
      
      {/* Ambient background effects */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-20 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl animate-breathe"></div>
        <div className="absolute bottom-1/4 -right-20 w-80 h-80 bg-sky-500/10 rounded-full blur-3xl animate-breathe" style={{ animationDelay: '1.5s' }}></div>
      </div>

      {/* Mobile App Frame / Wrapper */}
      <div className="relative w-full h-full md:max-w-[420px] md:h-[90vh] md:max-h-[900px] md:rounded-[2.5rem] bg-black shadow-2xl overflow-hidden md:border-4 md:border-slate-700/50 md:ring-1 md:ring-white/10">

        {/* === CAMERA VIEWFINDER === */}
        <div className="absolute inset-0 z-0">
          <Webcam
            ref={webcamRef}
            audio={false}
            screenshotFormat="image/jpeg"
            videoConstraints={videoConstraints}
            className="h-full w-full object-cover"
            forceScreenshotSourceSize={true}
            onUserMedia={() => setIsCameraReady(true)}
          />
          {/* Modern gradient overlays for depth */}
          <div className="absolute inset-0 bg-gradient-to-b from-black/50 via-transparent to-black/70 pointer-events-none"></div>
          
          {/* Subtle vignette effect */}
          <div className="absolute inset-0 pointer-events-none" style={{
            background: 'radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.4) 100%)'
          }}></div>
        </div>

        {/* === FLASH EFFECT === */}
        <div id="camera-flash" className="absolute inset-0 bg-white opacity-0 pointer-events-none z-40 transition-opacity duration-150"></div>

        {/* === MODERN HEADER === */}
        <div className="absolute top-0 left-0 right-0 z-20 pt-12 pb-6 px-6">
          <div className="flex items-center justify-between">
            {/* Logo/Brand */}
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center shadow-lg shadow-emerald-500/30">
                  <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                  </svg>
                </div>
                <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-emerald-400 border-2 border-black animate-pulse"></div>
              </div>
              <div>
                <h1 className="text-white font-bold text-lg tracking-tight">AgriSense</h1>
                <p className="text-white/50 text-xs font-medium">AI Plant Doctor</p>
              </div>
            </div>

            {/* Status Indicator */}
            <div className="glass rounded-full px-3 py-1.5 flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${isCameraReady ? 'bg-emerald-400' : 'bg-amber-400'} animate-pulse`}></span>
              <span className="text-white/80 text-xs font-medium">{isCameraReady ? 'Ready' : 'Loading...'}</span>
            </div>
          </div>
        </div>

        {/* === SCAN FRAME OVERLAY === */}
        {!isLoading && !result && (
          <div className="absolute inset-0 z-10 pointer-events-none flex items-center justify-center">
            <div className="relative w-64 h-64">
              {/* Corner brackets */}
              <div className="absolute top-0 left-0 w-12 h-12 border-l-2 border-t-2 border-white/40 rounded-tl-lg"></div>
              <div className="absolute top-0 right-0 w-12 h-12 border-r-2 border-t-2 border-white/40 rounded-tr-lg"></div>
              <div className="absolute bottom-0 left-0 w-12 h-12 border-l-2 border-b-2 border-white/40 rounded-bl-lg"></div>
              <div className="absolute bottom-0 right-0 w-12 h-12 border-r-2 border-b-2 border-white/40 rounded-br-lg"></div>
              
              {/* Center crosshair */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-8 h-8 opacity-30">
                  <div className="absolute left-1/2 top-0 bottom-0 w-px bg-white/50 -translate-x-1/2"></div>
                  <div className="absolute top-1/2 left-0 right-0 h-px bg-white/50 -translate-y-1/2"></div>
                </div>
              </div>
            </div>
            
            {/* Instruction text */}
            <div className="absolute bottom-28 left-0 right-0 text-center">
              <p className="text-white/70 text-sm font-medium">Position leaf within the frame</p>
            </div>
          </div>
        )}

        {/* === ERROR TOAST === */}
        {error && (
          <div className="absolute top-28 left-4 right-4 z-50 animate-slide-down">
            <div className="glass bg-red-500/20 backdrop-blur-xl text-white px-5 py-4 rounded-2xl shadow-xl border border-red-400/30 flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-red-500/30 flex items-center justify-center shrink-0">
                <svg className="w-5 h-5 text-red-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="flex-1">
                <p className="font-semibold text-sm">Analysis Failed</p>
                <p className="text-red-200/80 text-xs mt-0.5">{error}</p>
              </div>
              <button onClick={() => setError(null)} className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* === MODERN LOADING OVERLAY === */}
        {isLoading && (
          <div 
            className="absolute inset-0 z-50 bg-[#f8f9fb] flex flex-col items-center justify-center p-8 animate-fade-in"
            role="status"
            aria-live="polite"
            aria-label="Analyzing plant image"
          >
            {/* Animated Loader */}
            <div className="relative mb-12">
              {/* Outer static ring */}
              <div className="w-36 h-36 rounded-full border-4 border-slate-200 absolute inset-0"></div>
              
              {/* Animated progress ring - FIXED rotation */}
              <svg className="w-36 h-36 loading-ring-rotate" viewBox="0 0 144 144">
                <defs>
                  <linearGradient id="loading-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#22c55e" />
                    <stop offset="50%" stopColor="#0ea5e9" />
                    <stop offset="100%" stopColor="#22c55e" />
                  </linearGradient>
                </defs>
                <circle 
                  cx="72" cy="72" r="66" 
                  fill="none" 
                  stroke="url(#loading-gradient)" 
                  strokeWidth="5" 
                  strokeLinecap="round"
                  strokeDasharray="120 295"
                />
              </svg>
              
              {/* Pulsing glow effect */}
              <div className="absolute inset-0 rounded-full bg-emerald-500/20 blur-xl animate-pulse"></div>
              
              {/* Center icon with floating animation */}
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="w-24 h-24 rounded-full bg-gradient-to-br from-emerald-500 via-emerald-600 to-teal-600 flex items-center justify-center shadow-2xl shadow-emerald-500/50 animate-float">
                  <svg className="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
              </div>
            </div>

            <h3 className="text-2xl font-bold text-slate-800 mb-2 tracking-tight">Analyzing Plant</h3>
            <p className="text-slate-500 text-sm font-medium mb-10">AI is examining the leaf for diseases...</p>

            {/* Progress Steps */}
            <div className="w-full max-w-[280px] space-y-3" role="list" aria-label="Analysis progress steps">
              <StepItem step={0} active={activeStep} label="Processing Image" />
              <StepItem step={1} active={activeStep} label="AI Diagnosis" />
              <StepItem step={2} active={activeStep} label="Generating Report" />
            </div>
          </div>
        )}

        {/* === BOTTOM CONTROLS === */}
        <div className="absolute bottom-0 left-0 right-0 z-30 pt-20 pb-10 safe-area-bottom flex flex-col items-center" style={{
          background: 'linear-gradient(to top, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.7) 50%, transparent 100%)'
        }}>

          {/* Quick tips */}
          <div className="glass rounded-full px-4 py-2 mb-6 animate-fade-in-up">
            <p className="text-white/60 text-xs font-medium">💡 Tip: Get close for better accuracy</p>
          </div>

          <div className="relative w-full max-w-sm flex items-center justify-center gap-6 px-6">

            {/* Upload Button - Left Side */}
            <div className="flex flex-col items-center">
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isLoading}
                aria-label="Upload image from gallery"
                className="w-14 h-14 rounded-2xl glass flex items-center justify-center active:scale-90 transition-all text-white shadow-lg hover:bg-white/15 group disabled:opacity-50"
              >
                <svg className="w-6 h-6 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </button>
              <span className="text-[10px] font-semibold text-white/50 uppercase tracking-wider mt-2">Gallery</span>
            </div>

            {/* Shutter Button - Center */}
            <div className="flex flex-col items-center -mt-4">
              <button
                onClick={captureFromCamera}
                disabled={isLoading || !isCameraReady}
                className="group relative w-20 h-20 rounded-full border-4 border-white/30 flex items-center justify-center active:scale-95 transition-all hover:border-white/50 disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Take Picture"
              >
                {/* Glow effect on hover */}
                <div className="absolute inset-0 rounded-full bg-emerald-500/20 opacity-0 group-hover:opacity-100 blur-xl transition-opacity"></div>
                <div className="w-16 h-16 rounded-full bg-white shadow-lg shadow-white/20 transition-all duration-200 group-active:scale-90 group-hover:shadow-white/40"></div>
              </button>
              <span className="text-[10px] font-semibold text-white/50 uppercase tracking-wider mt-3">Capture</span>
            </div>

            {/* Hidden Input */}
            <input 
              ref={fileInputRef} 
              type="file" 
              accept="image/*" 
              onChange={handleFileUpload} 
              className="hidden" 
              aria-label="Upload plant image for analysis"
            />

            {/* History Button - Right Side */}
            <div className="flex flex-col items-center">
              <button
                disabled={isLoading}
                aria-label="View scan history"
                className="w-14 h-14 rounded-2xl glass flex items-center justify-center active:scale-90 transition-all text-white shadow-lg hover:bg-white/15 group disabled:opacity-50"
              >
                <svg className="w-6 h-6 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </button>
              <span className="text-[10px] font-semibold text-white/50 uppercase tracking-wider mt-2">History</span>
            </div>

          </div>

          {/* ESP32 Scanner Link */}
          <div className="mt-4">
            <Link
              to="/esp32"
              className="glass rounded-full px-5 py-2.5 flex items-center gap-2 hover:bg-white/15 transition-all active:scale-95"
            >
              <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
              </svg>
              <span className="text-white/70 text-xs font-semibold">ESP32 Scanner</span>
            </Link>
          </div>
        </div>

        {/* === REDESIGNED RESULT CARD === */}
        {result && (
          <DiseaseResultCard
            result={result}
            previewImage={previewImage}
            onClose={handleCloseResult}
            onSave={handleSaveResult}
            onReport={handleReportResult}
          />
        )}

      </div>
    </div>
  )
}

/* --- SUBCOMPONENTS --- */

const StepItem = ({ step, active, label }) => {
  const isDone = active > step
  const isCurrent = active === step
  const isPending = active < step

  return (
    <div 
      className={`flex items-center gap-4 w-full p-4 rounded-2xl transition-all duration-500 ${
        isCurrent ? 'bg-gradient-to-r from-emerald-500/15 to-transparent scale-[1.02] shadow-sm' : 
        isDone ? 'bg-emerald-50' : 'bg-slate-100/60'
      }`}
      role="listitem"
      aria-current={isCurrent ? 'step' : undefined}
    >
      <div 
        className={`relative w-8 h-8 rounded-full flex items-center justify-center shrink-0 transition-all duration-500 ${
          isDone ? 'bg-gradient-to-br from-emerald-400 to-emerald-600 text-white shadow-lg shadow-emerald-500/30' :
          isCurrent ? 'bg-white border-2 border-emerald-400 shadow-sm' : 
          'bg-white/60 border-2 border-slate-200'
        }`}
        aria-hidden="true"
      >
        {isDone && (
          <svg className="w-4 h-4 animate-scale-in" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        )}
        {isCurrent && (
          <div className="relative">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500"></div>
            <div className="absolute inset-0 w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping"></div>
          </div>
        )}
        {isPending && <div className="w-1.5 h-1.5 rounded-full bg-slate-300"></div>}
      </div>
      
      <span className={`flex-1 text-sm font-semibold transition-all duration-500 ${
        isPending ? 'text-slate-400' : isCurrent ? 'text-emerald-600' : 'text-slate-700'
      }`}>{label}</span>
      
      {isCurrent && (
        <div className="loading-spinner w-5 h-5 border-2 border-emerald-400/30 border-t-emerald-500 rounded-full"></div>
      )}
    </div>
  )
}

export default App
