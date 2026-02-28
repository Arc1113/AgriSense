import { useState } from 'react'

/**
 * Circular Confidence Ring Component
 * Modern animated ring with gradient colors
 * Green (≥85%), Amber (60-84%), Red (<60%)
 */
export const ConfidenceRing = ({ value }) => {
    const percentage = Math.round(value * 100)
    const circumference = 2 * Math.PI * 22 // radius = 22
    const offset = circumference - (percentage / 100) * circumference

    const getColor = () => {
        if (percentage >= 85) return { primary: '#22c55e', secondary: '#16a34a' }
        if (percentage >= 60) return { primary: '#eab308', secondary: '#ca8a04' }
        return { primary: '#f43f5e', secondary: '#e11d48' }
    }

    const colors = getColor()

    return (
        <div className="confidence-ring">
            <svg width="56" height="56" viewBox="0 0 56 56">
                <defs>
                    <linearGradient id={`conf-gradient-${percentage}`} x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor={colors.primary} />
                        <stop offset="100%" stopColor={colors.secondary} />
                    </linearGradient>
                </defs>
                <circle
                    className="confidence-ring-bg"
                    cx="28"
                    cy="28"
                    r="22"
                />
                <circle
                    className="confidence-ring-progress"
                    cx="28"
                    cy="28"
                    r="22"
                    stroke={`url(#conf-gradient-${percentage})`}
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                />
            </svg>
            <span className="confidence-ring-text" style={{ color: colors.primary }}>
                {percentage}%
            </span>
        </div>
    )
}

/**
 * Status Chip Component
 * Modern pill-shaped badges with subtle gradients
 */
export const StatusChip = ({ type, label, icon }) => {
    const chipClass = `status-chip chip-${type}`

    return (
        <span className={chipClass}>
            {icon && <span className="status-chip-icon">{icon}</span>}
            {label}
        </span>
    )
}

/**
 * Image Thumbnail Component with modern hover effects
 */
export const ImageThumbnail = ({ src, alt, onZoom, isOffline }) => {
    return (
        <div className="thumbnail-container" onClick={onZoom}>
            {src ? (
                <img src={src} alt={alt} loading="lazy" />
            ) : (
                <div className="w-full h-full flex items-center justify-center text-slate-300 bg-gradient-to-br from-slate-100 to-slate-200">
                    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                </div>
            )}
            <div className="thumbnail-zoom-icon">
                <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
                </svg>
            </div>
            {isOffline && (
                <div className="offline-indicator" title="Saved offline">
                    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414" />
                    </svg>
                </div>
            )}
        </div>
    )
}

/**
 * Image Zoom Modal with modern backdrop blur
 */
export const ImageZoomModal = ({ src, alt, onClose }) => {
    if (!src) return null

    return (
        <div className="zoom-modal" onClick={onClose}>
            <button className="zoom-modal-close" onClick={onClose}>
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
            <img src={src} alt={alt} onClick={(e) => e.stopPropagation()} />
        </div>
    )
}

/**
 * Collapsible Detail Section Component
 * Modern card-based design with smooth animations
 */
export const DetailSection = ({ title, icon, accentColor, defaultOpen = false, children }) => {
    const [isOpen, setIsOpen] = useState(defaultOpen)

    const accentColors = {
        treatment: { bg: '#f0fdf4', accent: '#22c55e', icon: '#16a34a' },
        prevention: { bg: '#eff6ff', accent: '#3b82f6', icon: '#2563eb' },
        precaution: { bg: '#fffbeb', accent: '#f59e0b', icon: '#d97706' },
        info: { bg: '#f0f9ff', accent: '#0ea5e9', icon: '#0284c7' }
    }

    const colors = accentColors[accentColor] || accentColors.treatment

    return (
        <div className="detail-section" style={{ background: isOpen ? colors.bg : '#fafafa' }}>
            <button
                className="detail-section-header"
                onClick={() => setIsOpen(!isOpen)}
            >
                <span
                    className="detail-section-accent"
                    style={{ backgroundColor: colors.accent }}
                />
                <span className="detail-section-icon" style={{ color: colors.icon }}>{icon}</span>
                <h3 className="detail-section-title">{title}</h3>
                <svg
                    className={`detail-section-chevron ${isOpen ? 'open' : ''}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </button>
            <div
                className="detail-section-content"
                style={{
                    maxHeight: isOpen ? '500px' : '0',
                    opacity: isOpen ? 1 : 0,
                    paddingBottom: isOpen ? '16px' : '0'
                }}
            >
                {children}
            </div>
        </div>
    )
}

/**
 * Action List Component (bullet points)
 * Enhanced with subtle animations
 */
export const ActionList = ({ items, maxItems = 2, showAll = false, onShowMore }) => {
    if (!items || items.length === 0) {
        return (
            <p className="text-sm text-slate-400 italic py-2">
                No specific recommendations available.
            </p>
        )
    }

    const displayItems = showAll ? items : items.slice(0, maxItems)
    const hasMore = items.length > maxItems && !showAll

    return (
        <ul className="action-list">
            {displayItems.map((item, index) => (
                <li key={index} style={{ animationDelay: `${index * 50}ms` }}>
                    <span className="action-list-bullet" />
                    <span>{item}</span>
                </li>
            ))}
            {hasMore && (
                <li className="action-list-more" onClick={onShowMore}>
                    <span className="flex items-center gap-1">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                        </svg>
                        {items.length - maxItems} more recommendations
                    </span>
                </li>
            )}
        </ul>
    )
}

/**
 * Precaution Box Component
 * Warning style with icon
 */
export const PrecautionBox = ({ text }) => {
    if (!text) return null

    return (
        <div className="precaution-box animate-fade-in-up">
            <div className="precaution-icon">
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
            </div>
            <div className="precaution-content">
                <h4>⚠️ Safety Precautions</h4>
                <p>{text}</p>
            </div>
        </div>
    )
}

/**
 * Primary CTA Button
 * Gradient button with hover effects
 */
export const PrimaryCTA = ({ label, icon, onClick }) => {
    return (
        <button className="cta-primary group" onClick={onClick}>
            <span className="transition-transform group-hover:scale-110">{icon}</span>
            {label}
        </button>
    )
}

/**
 * Secondary Action Button
 * Minimal style with label
 */
export const SecondaryAction = ({ icon, label, onClick, isActive }) => {
    return (
        <button 
            className={`action-btn-secondary ${isActive ? 'bg-emerald-50 border-emerald-200 text-emerald-600' : ''}`} 
            onClick={onClick}
        >
            <span className="transition-transform hover:scale-110">{icon}</span>
            <span>{label}</span>
        </button>
    )
}
