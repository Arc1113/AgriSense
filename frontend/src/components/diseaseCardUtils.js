/**
 * Utility functions for Disease Result Card
 * Separated to avoid React Fast Refresh lint warnings
 */

/**
 * Get chip configuration based on disease type
 */
export const getCategoryChip = (diseaseName) => {
    if (!diseaseName) return { type: 'healthy', label: 'Unknown' }

    const name = diseaseName.toLowerCase()

    if (name.includes('healthy')) {
        return { type: 'healthy', label: 'Healthy' }
    }
    if (name.includes('blight') || name.includes('mold') || name.includes('mildew') ||
        name.includes('spot') || name.includes('wilt') || name.includes('leaf mold')) {
        return { type: 'fungal', label: 'Fungal' }
    }
    if (name.includes('bacterial') || name.includes('canker')) {
        return { type: 'bacterial', label: 'Bacterial' }
    }
    if (name.includes('virus') || name.includes('mosaic') || name.includes('yellow leaf curl')) {
        return { type: 'viral', label: 'Viral' }
    }

    return { type: 'fungal', label: 'Pathogen' }
}

/**
 * Get risk chip configuration based on severity
 */
export const getRiskChip = (severity) => {
    const severityMap = {
        High: { type: 'risk-high', label: 'High Risk' },
        Medium: { type: 'risk-medium', label: 'Medium Risk' },
        Low: { type: 'risk-low', label: 'Low Risk' },
        None: { type: 'risk-low', label: 'No Risk' }
    }
    return severityMap[severity] || severityMap.Medium
}

/**
 * Split action plan text into clean sentences.
 * Handles numbered steps ("1. ..."), newline-delimited items,
 * and free-form prose without breaking on decimals (0.5),
 * abbreviations (e.g., i.e., Dr., lb.), or parentheticals.
 */
const smartSplit = (text) => {
    if (!text) return []

    // 0. Normalize: insert newlines before inline numbered steps
    //    e.g. "...expected. 2. Alternate..." → "...expected.\n2. Alternate..."
    //    Also handles "...expected 2. Alternate..." without trailing period
    const normalized = text.replace(/(?<=.)\s+(\d+[.):])\s/g, '\n$1 ')

    // 1. Try numbered-step format first  ("1. Do X\n2. Do Y")
    const numberedSteps = normalized.match(/(?:^|\n)\s*\d+[.):]\s*[^\n]+/g)
    if (numberedSteps && numberedSteps.length >= 2) {
        return numberedSteps.map(s => s.replace(/^\s*\d+[.):]+\s*/, '').trim()).filter(Boolean)
    }

    // 2. Try bullet / dash / asterisk delimited
    const bulletItems = normalized.match(/(?:^|\n)\s*[-•*]\s+[^\n]+/g)
    if (bulletItems && bulletItems.length >= 2) {
        return bulletItems.map(s => s.replace(/^\s*[-•*]+\s+/, '').trim()).filter(Boolean)
    }

    // 3. Try plain newline-delimited (each line is a step)
    const lines = normalized.split(/\n+/).map(l => l.trim()).filter(l => l.length > 15)
    if (lines.length >= 2) return lines

    // 4. Fallback: sentence boundary regex that avoids splitting on
    //    decimals (0.5), abbreviations (e.g., i.e., Dr., lb.), etc.
    //    Split on ". " or "! " or "? " only when the period is preceded
    //    by a lowercase/uppercase letter (not a digit or abbreviation).
    const safeSplit = text
        .replace(/\b(e\.g|i\.e|etc|Dr|Mr|Mrs|lb|oz|approx|vs)\.\s/gi, (m, abbr) => `${abbr}{{DOT}} `)
        .replace(/(\d)\.(\d)/g, '$1{{DECIMAL}}$2')
        .split(/(?<=[a-zA-Z)\]"'])[.!?]\s+/)
        .map(s => s.replace(/\{\{DOT\}\}/g, '.').replace(/\{\{DECIMAL\}\}/g, '.').trim())
        .filter(s => s.length > 15)

    return safeSplit
}

/**
 * Parse action plan text into categorized bullet points.
 * Treatment and prevention items are mutually exclusive — no duplicates.
 */
export const parseActionPlan = (actionPlan, type) => {
    if (!actionPlan) return []

    const sentences = smartSplit(actionPlan)

    // Check if text has explicit "PREVENTION:" or "Prevention:" marker
    const preventionMarkerIdx = actionPlan.search(/\b(?:PREVENTION|Prevention\s*(?:Tips|Steps)?):?/i)
    if (preventionMarkerIdx > -1) {
        // Split at the marker — everything before is treatment, after is prevention
        const before = actionPlan.substring(0, preventionMarkerIdx)
        const after = actionPlan.substring(preventionMarkerIdx)
        if (type === 'treatment') return smartSplit(before).slice(0, 5)
        if (type === 'prevention') {
            // Strip the marker line itself
            const cleaned = after.replace(/^[^\n]*\n?/, '')
            return smartSplit(cleaned).slice(0, 5)
        }
    }

    const treatmentKeywords = ['apply', 'spray', 'remove', 'treat', 'use', 'fungicide', 'pesticide', 'prune', 'cut', 'rate', 'dose', 'solution', 'window', 'reapply']
    const preventionKeywords = ['prevent', 'avoid', 'ensure', 'maintain', 'rotate', 'space', 'drainage', 'inspect', 'resistant', 'sanitize', 'disinfect', 'crop rotation']
    // 'monitor' and 'water' classified context-dependently below

    const isTreatment = (s) => {
        const low = s.toLowerCase()
        return treatmentKeywords.some(k => low.includes(k))
    }
    const isPrevention = (s) => {
        const low = s.toLowerCase()
        return preventionKeywords.some(k => low.includes(k))
    }

    if (type === 'treatment') {
        // Strictly treatment items, exclude anything that's prevention-only
        const treatments = sentences.filter(s => isTreatment(s) || (!isPrevention(s) && !isTreatment(s)))
        // Deduplicate: remove items that are purely prevention
        const unique = treatments.filter(s => !isPrevention(s) || isTreatment(s))
        return unique.length > 0 ? unique.slice(0, 5) : sentences.slice(0, 3)
    }

    if (type === 'prevention') {
        // Only items with prevention keywords AND NOT already claimed by treatment
        const treatmentSet = new Set(
            sentences.filter(s => isTreatment(s) || (!isPrevention(s) && !isTreatment(s)))
                .filter(s => !isPrevention(s) || isTreatment(s))
        )
        const preventions = sentences.filter(s => isPrevention(s) && !treatmentSet.has(s))
        return preventions.length > 0 ? preventions.slice(0, 5) : []
    }

    return sentences.slice(0, 5)
}

/**
 * Get one-line treatment summary
 */
export const getTreatmentSummary = (actionPlan) => {
    if (!actionPlan) return 'No treatment information available.'

    const items = smartSplit(actionPlan)
    if (items.length === 0) return 'No treatment information available.'

    const firstSentence = items[0].trim()
    return firstSentence.length > 80 ? firstSentence.substring(0, 77) + '...' : firstSentence
}
