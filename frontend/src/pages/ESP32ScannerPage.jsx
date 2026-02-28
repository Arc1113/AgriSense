import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function ESP32ScannerPage() {
  // Connection state
  const [esp32Ip, setEsp32Ip] = useState(localStorage.getItem('esp32_ip') || '192.168.1.100')
  const [esp32Port, setEsp32Port] = useState(80)
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [connectionError, setConnectionError] = useState(null)

  // Scanner state
  const [scanState, setScanState] = useState('idle')
  const [yoloLoaded, setYoloLoaded] = useState(false)
  const [visionLoaded, setVisionLoaded] = useState(false)

  // Motor state
  const [stepSize, setStepSize] = useState(5)

  // Auto-scan config
  const [modelType, setModelType] = useState('mobilenet')
  const [detectionConfidence, setDetectionConfidence] = useState(0.25)

  // Detections and results
  const [detections, setDetections] = useState([])
  const [scanResults, setScanResults] = useState([])
  const [latestFrame, setLatestFrame] = useState(null)

  // WebSocket
  const wsRef = useRef(null)
  const canvasRef = useRef(null)
  const imgRef = useRef(null)

  // Check ESP32 status on mount
  useEffect(() => {
    checkStatus()
  }, [])

  // WebSocket connection
  useEffect(() => {
    if (!isConnected) return

    const wsUrl = `${API_URL.replace('http', 'ws')}/ws/scan`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      handleWsMessage(msg)
    }

    ws.onclose = () => {
      console.log('WebSocket closed')
    }

    ws.onerror = (err) => {
      console.error('WebSocket error:', err)
    }

    wsRef.current = ws

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close()
      }
    }
  }, [isConnected])

  // Draw bounding boxes on canvas when detections change
  useEffect(() => {
    drawDetections()
  }, [detections, latestFrame])

  const handleWsMessage = useCallback((msg) => {
    if (msg.event_type === 'state_change') {
      setScanState(msg.state)
    } else if (msg.event_type === 'frame') {
      setLatestFrame(msg.data.frame_base64)
      setDetections(msg.data.detections || [])
    } else if (msg.event_type === 'detection') {
      setDetections(msg.data.detections || [])
    } else if (msg.event_type === 'classification') {
      // Update latest classification in results
      setScanResults(prev => [{
        scanIndex: msg.data.scan_index,
        disease: msg.data.disease,
        confidence: msg.data.confidence,
        model: msg.data.model,
        inferenceTime: msg.data.inference_time_ms,
        allPredictions: msg.data.all_predictions,
        timestamp: new Date().toISOString(),
      }, ...prev])
    } else if (msg.event_type === 'advice') {
      // Update the latest result with advice
      setScanResults(prev => {
        const updated = [...prev]
        if (updated.length > 0) {
          updated[0] = { ...updated[0], advice: msg.data.advice }
        }
        return updated
      })
    } else if (msg.event_type === 'error') {
      setConnectionError(msg.data.message || 'Scanner error')
    }
  }, [])

  const drawDetections = useCallback(() => {
    const canvas = canvasRef.current
    const img = imgRef.current
    if (!canvas || !img) return

    const ctx = canvas.getContext('2d')
    canvas.width = img.clientWidth
    canvas.height = img.clientHeight
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    if (detections.length === 0) return

    // Scale factors (detections are in original image coords)
    const imgNaturalW = img.naturalWidth || 640
    const imgNaturalH = img.naturalHeight || 480
    const scaleX = canvas.width / imgNaturalW
    const scaleY = canvas.height / imgNaturalH

    detections.forEach((det) => {
      const x = det.x1 * scaleX
      const y = det.y1 * scaleY
      const w = (det.x2 - det.x1) * scaleX
      const h = (det.y2 - det.y1) * scaleY

      // Draw box
      ctx.strokeStyle = '#22c55e'
      ctx.lineWidth = 2
      ctx.strokeRect(x, y, w, h)

      // Draw label background
      const label = `Leaf ${(det.confidence * 100).toFixed(0)}%`
      ctx.font = 'bold 12px sans-serif'
      const textWidth = ctx.measureText(label).width
      ctx.fillStyle = '#22c55e'
      ctx.fillRect(x, y - 20, textWidth + 10, 20)

      // Draw label text
      ctx.fillStyle = '#000'
      ctx.fillText(label, x + 5, y - 5)
    })
  }, [detections])

  // API calls
  async function checkStatus() {
    try {
      const res = await fetch(`${API_URL}/esp32/status`)
      const data = await res.json()
      setIsConnected(data.connected)
      setScanState(data.scan_state)
      setYoloLoaded(data.yolo_loaded)
      setVisionLoaded(data.vision_engine_loaded)
    } catch {
      // Backend not reachable
    }
  }

  async function connectEsp32() {
    setIsConnecting(true)
    setConnectionError(null)
    localStorage.setItem('esp32_ip', esp32Ip)

    try {
      const res = await fetch(`${API_URL}/esp32/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ip_address: esp32Ip, port: esp32Port }),
      })
      if (res.ok) {
        setIsConnected(true)
      } else {
        const err = await res.json()
        setConnectionError(err.detail || 'Connection failed')
      }
    } catch (e) {
      setConnectionError('Backend not reachable')
    } finally {
      setIsConnecting(false)
    }
  }

  async function disconnectEsp32() {
    try {
      await fetch(`${API_URL}/esp32/disconnect`, { method: 'POST' })
      setIsConnected(false)
      setScanState('idle')
    } catch {
      // ignore
    }
  }

  async function sendMotorCommand(direction) {
    try {
      await fetch(`${API_URL}/esp32/motor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ direction, step: stepSize }),
      })
    } catch {
      // ignore
    }
  }

  async function startScan() {
    try {
      const res = await fetch(`${API_URL}/esp32/scan/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_type: modelType, detection_confidence: detectionConfidence }),
      })
      if (res.ok) {
        setScanState('scanning')
        setScanResults([])
      }
    } catch {
      setConnectionError('Failed to start scan')
    }
  }

  async function stopScan() {
    try {
      await fetch(`${API_URL}/esp32/scan/stop`, { method: 'POST' })
      setScanState('idle')
    } catch {
      // ignore
    }
  }

  async function singleDetect() {
    try {
      const res = await fetch(`${API_URL}/esp32/detect`, { method: 'POST' })
      const data = await res.json()
      setDetections(data.detections || [])
    } catch {
      setConnectionError('Detection failed')
    }
  }

  const isScanning = scanState === 'scanning' || scanState === 'leaf_detected' ||
                     scanState === 'capturing' || scanState === 'classifying' || scanState === 'advising'

  const stateLabel = {
    idle: 'Idle',
    scanning: 'Scanning...',
    leaf_detected: 'Leaf Detected!',
    capturing: 'Capturing...',
    classifying: 'Classifying...',
    advising: 'Getting Advice...',
    result_ready: 'Result Ready',
    error: 'Error',
  }

  const stateColor = {
    idle: 'bg-slate-500',
    scanning: 'bg-emerald-500 animate-pulse',
    leaf_detected: 'bg-amber-500',
    capturing: 'bg-sky-500 animate-pulse',
    classifying: 'bg-purple-500 animate-pulse',
    advising: 'bg-indigo-500 animate-pulse',
    result_ready: 'bg-emerald-500',
    error: 'bg-red-500',
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white">
      {/* Header */}
      <div className="sticky top-0 z-50 bg-slate-900/80 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/" className="w-9 h-9 rounded-xl bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </Link>
            <div>
              <h1 className="font-bold text-lg">ESP32 Scanner</h1>
              <p className="text-white/50 text-xs">Robotics Leaf Detection</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-red-400'}`}></span>
            <span className="text-xs text-white/60">{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">

        {/* Connection Panel */}
        <div className="bg-white/5 rounded-2xl border border-white/10 p-5">
          <h2 className="text-sm font-semibold text-white/80 mb-3 flex items-center gap-2">
            <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.14 0M1.394 9.393c5.857-5.858 15.355-5.858 21.213 0" />
            </svg>
            ESP32-CAM Connection
          </h2>

          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="text-xs text-white/50 mb-1 block">IP Address</label>
              <input
                type="text"
                value={esp32Ip}
                onChange={(e) => setEsp32Ip(e.target.value)}
                disabled={isConnected}
                placeholder="192.168.1.100"
                className="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/10 text-white text-sm focus:outline-none focus:border-emerald-500 disabled:opacity-50"
              />
            </div>
            <div className="w-20">
              <label className="text-xs text-white/50 mb-1 block">Port</label>
              <input
                type="number"
                value={esp32Port}
                onChange={(e) => setEsp32Port(parseInt(e.target.value) || 80)}
                disabled={isConnected}
                className="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/10 text-white text-sm focus:outline-none focus:border-emerald-500 disabled:opacity-50"
              />
            </div>
            <button
              onClick={isConnected ? disconnectEsp32 : connectEsp32}
              disabled={isConnecting}
              className={`px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
                isConnected
                  ? 'bg-red-500/20 text-red-300 hover:bg-red-500/30 border border-red-500/30'
                  : 'bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 border border-emerald-500/30'
              } disabled:opacity-50`}
            >
              {isConnecting ? 'Connecting...' : isConnected ? 'Disconnect' : 'Connect'}
            </button>
          </div>

          {connectionError && (
            <div className="mt-3 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300 text-xs">
              {connectionError}
            </div>
          )}

          {/* System status badges */}
          <div className="flex gap-2 mt-3">
            <span className={`text-xs px-2 py-1 rounded-full ${yoloLoaded ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300'}`}>
              YOLO {yoloLoaded ? 'Ready' : 'Not Loaded'}
            </span>
            <span className={`text-xs px-2 py-1 rounded-full ${visionLoaded ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300'}`}>
              Disease Models {visionLoaded ? 'Ready' : 'Not Loaded'}
            </span>
          </div>
        </div>

        {/* Live Feed + Controls Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Live Feed Panel */}
          <div className="lg:col-span-2 bg-white/5 rounded-2xl border border-white/10 overflow-hidden">
            <div className="p-4 border-b border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${stateColor[scanState] || 'bg-slate-500'}`}></div>
                <span className="text-sm font-medium">{stateLabel[scanState] || scanState}</span>
              </div>
              {detections.length > 0 && (
                <span className="text-xs px-2 py-1 rounded-full bg-emerald-500/20 text-emerald-300">
                  {detections.length} leaf{detections.length !== 1 ? 'es' : ''} detected
                </span>
              )}
            </div>
            <div className="relative bg-black aspect-video">
              {isConnected ? (
                <>
                  {latestFrame ? (
                    <img
                      ref={imgRef}
                      src={`data:image/jpeg;base64,${latestFrame}`}
                      alt="ESP32 Camera Feed"
                      className="w-full h-full object-contain"
                      onLoad={drawDetections}
                    />
                  ) : (
                    <img
                      ref={imgRef}
                      src={`${API_URL}/esp32/stream`}
                      alt="ESP32 Camera Feed"
                      className="w-full h-full object-contain"
                    />
                  )}
                  <canvas
                    ref={canvasRef}
                    className="absolute inset-0 w-full h-full pointer-events-none"
                  />
                </>
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-white/30">
                  <svg className="w-16 h-16 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  <p className="text-sm">Connect ESP32-CAM to view live feed</p>
                </div>
              )}
            </div>
          </div>

          {/* Motor & Scan Controls */}
          <div className="space-y-6">
            {/* Motor Controls */}
            <div className="bg-white/5 rounded-2xl border border-white/10 p-5">
              <h3 className="text-sm font-semibold text-white/80 mb-4">Pan-Tilt Control</h3>
              {/* D-pad layout */}
              <div className="flex flex-col items-center gap-2 mb-4">
                {/* Up button */}
                <button
                  onClick={() => sendMotorCommand('up')}
                  disabled={!isConnected}
                  className="w-14 h-14 rounded-xl bg-white/10 hover:bg-white/20 transition-all flex items-center justify-center disabled:opacity-30 active:scale-90"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                  </svg>
                </button>
                {/* Left, Center, Right row */}
                <div className="flex gap-2">
                  <button
                    onClick={() => sendMotorCommand('left')}
                    disabled={!isConnected}
                    className="w-14 h-14 rounded-xl bg-white/10 hover:bg-white/20 transition-all flex items-center justify-center disabled:opacity-30 active:scale-90"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                  </button>
                  <button
                    onClick={() => sendMotorCommand('center')}
                    disabled={!isConnected}
                    className="w-14 h-14 rounded-xl bg-sky-500/20 hover:bg-sky-500/30 border border-sky-500/30 transition-all flex items-center justify-center disabled:opacity-30 active:scale-90"
                  >
                    <svg className="w-6 h-6 text-sky-400" fill="currentColor" viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="4" />
                    </svg>
                  </button>
                  <button
                    onClick={() => sendMotorCommand('right')}
                    disabled={!isConnected}
                    className="w-14 h-14 rounded-xl bg-white/10 hover:bg-white/20 transition-all flex items-center justify-center disabled:opacity-30 active:scale-90"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                </div>
                {/* Down button */}
                <button
                  onClick={() => sendMotorCommand('down')}
                  disabled={!isConnected}
                  className="w-14 h-14 rounded-xl bg-white/10 hover:bg-white/20 transition-all flex items-center justify-center disabled:opacity-30 active:scale-90"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              </div>
              <div>
                <label className="text-xs text-white/50 mb-1 block">Step Size: {stepSize}&deg;</label>
                <input
                  type="range"
                  min="1"
                  max="45"
                  value={stepSize}
                  onChange={(e) => setStepSize(parseInt(e.target.value))}
                  className="w-full accent-emerald-500"
                />
              </div>
            </div>

            {/* Auto-Scan Controls */}
            <div className="bg-white/5 rounded-2xl border border-white/10 p-5">
              <h3 className="text-sm font-semibold text-white/80 mb-4">Auto-Scan</h3>

              <div className="mb-3">
                <label className="text-xs text-white/50 mb-1 block">Classification Model</label>
                <select
                  value={modelType}
                  onChange={(e) => setModelType(e.target.value)}
                  disabled={isScanning}
                  className="w-full px-3 py-2 rounded-lg bg-white/10 border border-white/10 text-white text-sm focus:outline-none focus:border-emerald-500 disabled:opacity-50"
                >
                  <option value="mobilenet">MobileNetV2 (Fast)</option>
                  <option value="resnet">ResNet50 (Accurate)</option>
                </select>
              </div>

              <div className="mb-4">
                <label className="text-xs text-white/50 mb-1 block">
                  Detection Confidence: {detectionConfidence.toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0.1"
                  max="1.0"
                  step="0.05"
                  value={detectionConfidence}
                  onChange={(e) => setDetectionConfidence(parseFloat(e.target.value))}
                  disabled={isScanning}
                  className="w-full accent-emerald-500"
                />
              </div>

              <div className="flex gap-2">
                {isScanning ? (
                  <button
                    onClick={stopScan}
                    className="flex-1 px-4 py-2.5 rounded-lg bg-red-500/20 text-red-300 border border-red-500/30 text-sm font-semibold hover:bg-red-500/30 transition-all"
                  >
                    Stop Scan
                  </button>
                ) : (
                  <button
                    onClick={startScan}
                    disabled={!isConnected || !yoloLoaded}
                    className="flex-1 px-4 py-2.5 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-sm font-semibold hover:bg-emerald-500/30 transition-all disabled:opacity-30"
                  >
                    Start Auto-Scan
                  </button>
                )}
                <button
                  onClick={singleDetect}
                  disabled={!isConnected || !yoloLoaded || isScanning}
                  className="px-4 py-2.5 rounded-lg bg-sky-500/20 text-sky-300 border border-sky-500/30 text-sm font-semibold hover:bg-sky-500/30 transition-all disabled:opacity-30"
                  title="Single YOLO detection"
                >
                  Detect
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Scan Results */}
        {scanResults.length > 0 && (
          <div className="bg-white/5 rounded-2xl border border-white/10 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white/80 flex items-center gap-2">
                <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                Scan Results ({scanResults.length})
              </h2>
              <button
                onClick={() => setScanResults([])}
                className="text-xs text-white/40 hover:text-white/70 transition-colors"
              >
                Clear
              </button>
            </div>

            <div className="space-y-3">
              {scanResults.map((result, i) => (
                <div
                  key={`${result.scanIndex}-${i}`}
                  className={`p-4 rounded-xl border ${
                    result.disease?.toLowerCase() === 'healthy'
                      ? 'bg-emerald-500/5 border-emerald-500/20'
                      : 'bg-red-500/5 border-red-500/20'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${
                        result.disease?.toLowerCase() === 'healthy' ? 'bg-emerald-400' : 'bg-red-400'
                      }`}></span>
                      <span className="text-sm font-semibold">{result.disease || 'Unknown'}</span>
                    </div>
                    <span className="text-xs text-white/50">
                      {result.confidence ? `${(result.confidence * 100).toFixed(1)}%` : ''}
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-2 text-xs text-white/50 mb-2">
                    <span>{result.model === 'mobilenet' ? 'MobileNetV2' : 'ResNet50'}</span>
                    {result.inferenceTime && <span>| {result.inferenceTime.toFixed(0)}ms</span>}
                    <span>| Scan #{result.scanIndex}</span>
                  </div>

                  {/* Confidence bar */}
                  {result.confidence && (
                    <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden mb-2">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          result.disease?.toLowerCase() === 'healthy' ? 'bg-emerald-400' : 'bg-red-400'
                        }`}
                        style={{ width: `${result.confidence * 100}%` }}
                      />
                    </div>
                  )}

                  {/* Advice */}
                  {result.advice && (
                    <div className="mt-2 pt-2 border-t border-white/10">
                      <p className="text-xs text-white/70 leading-relaxed">
                        <span className="font-semibold text-sky-400">Action: </span>
                        {result.advice.action_plan || 'No advice available'}
                      </p>
                      {result.advice.severity && (
                        <span className={`inline-block mt-1 text-xs px-2 py-0.5 rounded-full ${
                          result.advice.severity === 'High' ? 'bg-red-500/20 text-red-300' :
                          result.advice.severity === 'Medium' ? 'bg-amber-500/20 text-amber-300' :
                          'bg-emerald-500/20 text-emerald-300'
                        }`}>
                          {result.advice.severity} Severity
                        </span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
