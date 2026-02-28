import { useEffect, useState } from 'react'
import {
    ActionList,
    ConfidenceRing,
    DetailSection,
    ImageThumbnail,
    ImageZoomModal,
    PrecautionBox,
    PrimaryCTA,
    SecondaryAction,
    StatusChip
} from './DiseaseCardComponents'
import {
    getCategoryChip,
    getRiskChip,
    getTreatmentSummary,
    parseActionPlan
} from './diseaseCardUtils'

/**
 * Disease Result Card Component
 * Modern glass-morphism design with smooth animations
 * Progressive disclosure pattern for better UX
 */
const DiseaseResultCard = ({
    result,
    previewImage,
    onClose,
    onSave,
    onReport
}) => {
    const [isExpanded, setIsExpanded] = useState(false)
    const [showZoom, setShowZoom] = useState(false)
    const [isSaved, setIsSaved] = useState(false)
    const [isOffline, setIsOffline] = useState(!navigator.onLine)
    const [isClosing, setIsClosing] = useState(false)
    const [showConfetti, setShowConfetti] = useState(false)

    // Listen for online/offline status
    useEffect(() => {
        const handleOnline = () => setIsOffline(false)
        const handleOffline = () => setIsOffline(true)

        window.addEventListener('online', handleOnline)
        window.addEventListener('offline', handleOffline)

        return () => {
            window.removeEventListener('online', handleOnline)
            window.removeEventListener('offline', handleOffline)
        }
    }, [])

    // Show confetti for healthy plants
    useEffect(() => {
        if (result?.disease?.toLowerCase().includes('healthy')) {
            setShowConfetti(true)
            setTimeout(() => setShowConfetti(false), 3000)
        }
    }, [result])

    if (!result) return null

    const categoryChip = getCategoryChip(result.disease)
    const riskChip = getRiskChip(result.advice?.severity)
    const isHealthy = result.disease?.toLowerCase().includes('healthy')
    const treatmentItems = parseActionPlan(result.advice?.action_plan, 'treatment')
    const preventionItems = parseActionPlan(result.advice?.action_plan, 'prevention')
    const treatmentSummary = getTreatmentSummary(result.advice?.action_plan)

    const handleSave = () => {
        setIsSaved(true)
        onSave?.(result)
        setTimeout(() => setIsSaved(false), 2000)
    }

    const handleReport = () => {
        onReport?.(result)
    }

    const handleClose = () => {
        setIsClosing(true)
        setTimeout(() => {
            setIsExpanded(false)
            setShowZoom(false)
            onClose?.()
        }, 300)
    }

    return (
        <>
            {/* Backdrop with blur */}
            <div
                className={`absolute inset-0 z-50 flex items-end ${isClosing ? 'animate-fade-out' : 'animate-fade-in'}`}
                onClick={handleClose}
            >
                {/* Gradient backdrop */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/70 to-black/50 backdrop-blur-md"></div>
                
                {/* Confetti effect for healthy plants */}
                {showConfetti && (
                    <div className="confetti-container">
                        {[...Array(20)].map((_, i) => (
                            <div 
                                key={i} 
                                className="confetti-piece"
                                style={{
                                    left: `${Math.random() * 100}%`,
                                    animationDelay: `${Math.random() * 0.5}s`,
                                    backgroundColor: ['#22c55e', '#0ea5e9', '#eab308', '#f43f5e', '#8b5cf6'][Math.floor(Math.random() * 5)]
                                }}
                            />
                        ))}
                    </div>
                )}

                {/* Card Container */}
                <div
                    className={`result-card-container ${isClosing ? 'result-card-closing' : 'result-card-enter'} ${isExpanded ? 'result-card-expanded' : ''}`}
                    onClick={(e) => e.stopPropagation()}
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="disease-result-title"
                >
                    {/* Gradient border top */}
                    <div className="result-card-gradient-border"></div>
                    
                    {/* ============ HEADER SECTION ============ */}
                    <div className="result-card-header">
                        {/* Drag Handle */}
                        <div className="result-card-handle" />

                        <div className="flex gap-5">
                            {/* Thumbnail with animated border */}
                            <div className="result-card-thumbnail-wrapper">
                                <div className="result-card-thumbnail-glow"></div>
                                <ImageThumbnail
                                    src={previewImage}
                                    alt="Analyzed leaf"
                                    onZoom={() => setShowZoom(true)}
                                    isOffline={isOffline}
                                />
                            </div>

                            {/* Disease Info */}
                            <div className="flex-1 min-w-0">
                                {/* Disease Name with gradient for diseased plants */}
                                <h2 
                                    id="disease-result-title"
                                    className={`result-card-title ${isHealthy ? 'result-card-title-healthy' : ''}`}
                                >
                                    {result.disease}
                                </h2>

                                {/* Confidence + Chips Row */}
                                <div className="flex items-center gap-3 mb-3">
                                    <ConfidenceRing value={result.confidence} />
                                    <div className="flex flex-wrap gap-1.5">
                                        <StatusChip type={categoryChip.type} label={categoryChip.label} />
                                        <StatusChip type={riskChip.type} label={riskChip.label} />
                                        {!isHealthy && <StatusChip type="treatable" label="Treatable" />}
                                    </div>
                                </div>
                            </div>

                            {/* Close Button */}
                            <button
                                onClick={handleClose}
                                className="result-card-close-btn"
                                aria-label="Close"
                            >
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        {/* Quick Treatment Summary (Compact View) */}
                        {!isExpanded && !isHealthy && (
                            <div className="result-card-quick-tip">
                                <div className="result-card-quick-tip-icon">
                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                    </svg>
                                </div>
                                <p className="flex-1 text-sm text-slate-600 line-clamp-2">
                                    <span className="font-semibold text-slate-700">Quick action: </span>
                                    {treatmentSummary}
                                </p>
                            </div>
                        )}
                    </div>

                    {/* ============ CONTENT SECTION (Scrollable) ============ */}
                    <div className="result-card-content">
                        {isHealthy ? (
                            /* Healthy Plant Celebration */
                            <div className="result-card-healthy">
                                <div className="result-card-healthy-icon-wrapper">
                                    <div className="result-card-healthy-glow"></div>
                                    <div className="result-card-healthy-icon">
                                        <svg className="w-12 h-12 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                        </svg>
                                    </div>
                                </div>
                                <h3 className="result-card-healthy-title">Your plant is thriving!</h3>
                                <p className="result-card-healthy-subtitle">No diseases detected. Keep up the excellent care!</p>
                                
                                {/* Care tips for healthy plants */}
                                <div className="result-card-healthy-tips">
                                    <div className="result-card-healthy-tip">
                                        <span className="result-card-healthy-tip-icon">💧</span>
                                        <span>Water regularly</span>
                                    </div>
                                    <div className="result-card-healthy-tip">
                                        <span className="result-card-healthy-tip-icon">☀️</span>
                                        <span>Ensure sunlight</span>
                                    </div>
                                    <div className="result-card-healthy-tip">
                                        <span className="result-card-healthy-tip-icon">🌱</span>
                                        <span>Monitor growth</span>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            /* Disease Details */
                            <>
                                {/* Treatment Section */}
                                <DetailSection
                                    title="Treatment Plan"
                                    icon={
                                        <svg className="w-full h-full" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                                        </svg>
                                    }
                                    accentColor="treatment"
                                    defaultOpen={true}
                                >
                                    <ActionList
                                        items={treatmentItems}
                                        maxItems={2}
                                        showAll={isExpanded}
                                        onShowMore={() => setIsExpanded(true)}
                                    />
                                </DetailSection>

                                {/* Prevention Section */}
                                <DetailSection
                                    title="Prevention Tips"
                                    icon={
                                        <svg className="w-full h-full" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                        </svg>
                                    }
                                    accentColor="prevention"
                                    defaultOpen={isExpanded}
                                >
                                    <ActionList
                                        items={preventionItems}
                                        maxItems={2}
                                        showAll={isExpanded}
                                        onShowMore={() => setIsExpanded(true)}
                                    />
                                </DetailSection>

                                {/* Weather Advisory Section */}
                                {result.advice?.weather_advisory && (
                                    <DetailSection
                                        title="Weather Advisory"
                                        icon={
                                            <svg className="w-full h-full" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                                            </svg>
                                        }
                                        accentColor="info"
                                        defaultOpen={isExpanded}
                                    >
                                        <p className="text-sm text-slate-600 leading-relaxed">
                                            {result.advice.weather_advisory}
                                        </p>
                                    </DetailSection>
                                )}

                                {/* Precautions (Expanded View Only) */}
                                {isExpanded && result.advice?.safety_warning && (
                                    <PrecautionBox text={result.advice.safety_warning} />
                                )}
                            </>
                        )}
                    </div>

                    {/* ============ BOTTOM ACTION BAR ============ */}
                    <div className="result-card-actions">
                        <div className="flex items-center gap-3">
                            {/* Primary CTA */}
                            <PrimaryCTA
                                label={isExpanded ? 'Show Less' : 'View Full Report'}
                                icon={
                                    isExpanded ? (
                                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                                        </svg>
                                    ) : (
                                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                        </svg>
                                    )
                                }
                                onClick={() => setIsExpanded(!isExpanded)}
                            />

                            {/* Save Button */}
                            <SecondaryAction
                                icon={
                                    isSaved ? (
                                        <svg className="w-5 h-5 text-emerald-600" fill="currentColor" viewBox="0 0 24 24">
                                            <path d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                                        </svg>
                                    ) : (
                                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                                        </svg>
                                    )
                                }
                                label={isSaved ? 'Saved!' : 'Save'}
                                onClick={handleSave}
                                isActive={isSaved}
                            />

                            {/* Report Button */}
                            <SecondaryAction
                                icon={
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9" />
                                    </svg>
                                }
                                label="Report"
                                onClick={handleReport}
                            />

                            {/* Scan Again Button */}
                            <button
                                onClick={handleClose}
                                className="result-card-scan-again"
                                title="Scan Again"
                                aria-label="Scan Again"
                            >
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Image Zoom Modal */}
            {showZoom && (
                <ImageZoomModal
                    src={previewImage}
                    alt="Analyzed leaf - full view"
                    onClose={() => setShowZoom(false)}
                />
            )}
        </>
    )
}

export default DiseaseResultCard
