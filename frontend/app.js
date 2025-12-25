/**
 * ============================================================
 * MRD Agent - Frontend Application
 * ============================================================
 * Handles UI interactions and API communication.
 * ============================================================
 */

// Configuration
const CONFIG = {
    API_BASE_URL: 'http://localhost:8000',
    POLL_INTERVAL: 1000, // ms
    MAX_POLL_ATTEMPTS: 300, // 5 minutes max
};

// State
let currentJobId = null;
let pollAttempts = 0;
let mrdResult = null;

// DOM Elements
const elements = {
    statusIndicator: document.getElementById('statusIndicator'),
    statusDot: document.querySelector('.status-dot'),
    statusText: document.querySelector('.status-text'),
    generateForm: document.getElementById('generateForm'),
    generateBtn: document.getElementById('generateBtn'),
    promptInput: document.getElementById('prompt'),
    domainSelect: document.getElementById('domain'),
    progressSection: document.getElementById('progressSection'),
    progressFill: document.getElementById('progressFill'),
    progressPhase: document.getElementById('progressPhase'),
    resultsSection: document.getElementById('resultsSection'),
    executiveSummary: document.getElementById('executiveSummary'),
    competitorsGrid: document.getElementById('competitorsGrid'),
    swotGrid: document.getElementById('swotGrid'),
    featuresList: document.getElementById('featuresList'),
    regulatoryContent: document.getElementById('regulatoryContent'),
    gapList: document.getElementById('gapList'),
    downloadJson: document.getElementById('downloadJson'),
    copyToClipboard: document.getElementById('copyToClipboard'),
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkApiHealth();
    setupEventListeners();
    setDefaultPrompt();
});

/**
 * Set default prompt in textarea
 */
function setDefaultPrompt() {
    elements.promptInput.value =
        'I want to build a skill-based gambling app targeting young men, ' +
        'similar to Triumph but for the European market. ' +
        'Analyze why Triumph is succeeding where Skillz is failing.';
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    elements.generateForm.addEventListener('submit', handleGenerate);
    elements.downloadJson.addEventListener('click', handleDownloadJson);
    elements.copyToClipboard.addEventListener('click', handleCopyToClipboard);
}

/**
 * Check API health status
 */
async function checkApiHealth() {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/health`);
        const data = await response.json();

        if (data.status === 'healthy') {
            setApiStatus('online', `API Online (v${data.version})`);
        } else {
            setApiStatus('offline', 'API Unhealthy');
        }
    } catch (error) {
        setApiStatus('offline', 'API Unavailable');
        console.error('Health check failed:', error);
    }
}

/**
 * Set API status indicator
 */
function setApiStatus(status, text) {
    elements.statusDot.className = `status-dot ${status}`;
    elements.statusText.textContent = text;
}

/**
 * Handle form submission
 */
async function handleGenerate(event) {
    event.preventDefault();

    const prompt = elements.promptInput.value.trim();
    const domain = elements.domainSelect.value;

    if (!prompt) {
        alert('Please enter a product strategy query');
        return;
    }

    // Disable form
    elements.generateBtn.disabled = true;
    elements.generateBtn.querySelector('.btn-text').textContent = 'Generating...';

    // Show progress section
    elements.progressSection.classList.remove('hidden');
    elements.resultsSection.classList.add('hidden');

    // Reset progress
    updateProgress(0, 'Initializing...');
    resetSteps();

    try {
        // Start generation
        const response = await fetch(`${CONFIG.API_BASE_URL}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: prompt,
                domain: domain,
                skip_human_review: true
            })
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const job = await response.json();
        currentJobId = job.job_id;

        // Start polling
        pollAttempts = 0;
        pollJobStatus();

    } catch (error) {
        console.error('Generation failed:', error);
        alert(`Failed to start generation: ${error.message}`);
        resetForm();
    }
}

/**
 * Poll job status
 */
async function pollJobStatus() {
    if (!currentJobId || pollAttempts >= CONFIG.MAX_POLL_ATTEMPTS) {
        resetForm();
        return;
    }

    pollAttempts++;

    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/jobs/${currentJobId}`);
        const job = await response.json();

        updateProgress(job.progress, job.current_phase || 'Processing...');
        updateSteps(job.progress);

        if (job.status === 'complete') {
            mrdResult = job.result;
            displayResults(job.result);
            resetForm();
        } else if (job.status === 'failed') {
            alert(`Generation failed: ${job.error || 'Unknown error'}`);
            resetForm();
        } else {
            // Continue polling
            setTimeout(pollJobStatus, CONFIG.POLL_INTERVAL);
        }

    } catch (error) {
        console.error('Poll failed:', error);
        setTimeout(pollJobStatus, CONFIG.POLL_INTERVAL);
    }
}

/**
 * Update progress bar and phase text
 */
function updateProgress(percent, phase) {
    elements.progressFill.style.width = `${percent}%`;
    elements.progressPhase.textContent = phase;
}

/**
 * Reset step indicators
 */
function resetSteps() {
    const steps = ['init', 'research', 'analyze', 'synthesize', 'complete'];
    steps.forEach(step => {
        const el = document.getElementById(`step-${step}`);
        if (el) {
            el.className = 'step';
            el.querySelector('.step-icon').textContent = '⏳';
        }
    });
}

/**
 * Update step indicators based on progress
 */
function updateSteps(progress) {
    const steps = [
        { id: 'init', threshold: 10 },
        { id: 'research', threshold: 30 },
        { id: 'analyze', threshold: 50 },
        { id: 'synthesize', threshold: 70 },
        { id: 'complete', threshold: 100 }
    ];

    steps.forEach(step => {
        const el = document.getElementById(`step-${step.id}`);
        if (el) {
            if (progress >= step.threshold) {
                el.classList.add('complete');
                el.querySelector('.step-icon').textContent = '✅';
            } else if (progress >= step.threshold - 20) {
                el.classList.add('active');
                el.querySelector('.step-icon').textContent = '🔄';
            }
        }
    });
}

/**
 * Reset form to initial state
 */
function resetForm() {
    elements.generateBtn.disabled = false;
    elements.generateBtn.querySelector('.btn-text').textContent = 'Generate MRD';
    currentJobId = null;
}

/**
 * Display MRD results
 */
function displayResults(mrd) {
    elements.progressSection.classList.add('hidden');
    elements.resultsSection.classList.remove('hidden');

    // Executive Summary
    if (mrd.strategic_analysis) {
        elements.executiveSummary.innerHTML = `
            <p>${mrd.strategic_analysis.executive_summary}</p>
            ${mrd.strategic_analysis.market_size?.tam ? `
            <div class="market-stats">
                <strong>Market Size:</strong> 
                TAM: $${formatNumber(mrd.strategic_analysis.market_size.tam)} |
                CAGR: ${mrd.strategic_analysis.market_size.cagr || 'N/A'}%
            </div>` : ''}
        `;
    }

    // Competitors
    if (mrd.competitors && mrd.competitors.length > 0) {
        elements.competitorsGrid.innerHTML = mrd.competitors.map(comp => `
            <div class="competitor-item">
                <h4>${comp.name}</h4>
                <p>${comp.description}</p>
                <div class="strength-weakness">
                    <div class="strength-list">
                        <h5>💪 Strengths</h5>
                        <ul>
                            ${(comp.key_strengths || []).slice(0, 3).map(s => `<li>${s}</li>`).join('')}
                        </ul>
                    </div>
                    <div class="weakness-list">
                        <h5>⚠️ Weaknesses</h5>
                        <ul>
                            ${(comp.key_weaknesses || []).slice(0, 3).map(w => `<li>${w}</li>`).join('')}
                        </ul>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // SWOT
    if (mrd.swot) {
        elements.swotGrid.innerHTML = `
            <div class="swot-quadrant strengths">
                <h4>💪 Strengths</h4>
                <ul>${(mrd.swot.strengths || []).map(s => `<li>${s.statement}</li>`).join('')}</ul>
            </div>
            <div class="swot-quadrant weaknesses">
                <h4>⚠️ Weaknesses</h4>
                <ul>${(mrd.swot.weaknesses || []).map(w => `<li>${w.statement}</li>`).join('')}</ul>
            </div>
            <div class="swot-quadrant opportunities">
                <h4>🚀 Opportunities</h4>
                <ul>${(mrd.swot.opportunities || []).map(o => `<li>${o.statement}</li>`).join('')}</ul>
            </div>
            <div class="swot-quadrant threats">
                <h4>⚡ Threats</h4>
                <ul>${(mrd.swot.threats || []).map(t => `<li>${t.statement}</li>`).join('')}</ul>
            </div>
        `;
    }

    // Features
    if (mrd.feature_recommendations && mrd.feature_recommendations.length > 0) {
        elements.featuresList.innerHTML = mrd.feature_recommendations.map(f => `
            <div class="feature-item">
                <div class="feature-info">
                    <h4>${f.name}</h4>
                    <p>${f.description}</p>
                </div>
                <span class="feature-priority ${f.priority?.replace(' ', '_') || 'should_have'}">
                    ${f.priority?.replace('_', ' ') || 'Should Have'}
                </span>
            </div>
        `).join('');
    }

    // Regulatory
    if (mrd.regulatory && mrd.regulatory.jurisdictions) {
        elements.regulatoryContent.innerHTML = `
            <div class="regulatory-summary">
                <p><strong>Overall Risk:</strong> ${mrd.regulatory.overall_risk_level || 'Medium'}</p>
                <p><strong>Recommended Markets:</strong> ${(mrd.regulatory.recommended_launch_markets || []).join(', ')}</p>
            </div>
            ${mrd.regulatory.jurisdictions.map(j => `
                <div class="jurisdiction-item">
                    <div class="jurisdiction-info">
                        <h4>${j.jurisdiction?.toUpperCase() || 'Unknown'}</h4>
                        <p>${j.licensing_authority || 'Licensing required'}</p>
                    </div>
                    <span class="jurisdiction-status ${j.status === 'legal' ? 'legal' : 'restricted'}">
                        ${j.status?.replace('_', ' ') || 'Restricted'}
                    </span>
                </div>
            `).join('')}
        `;
    }

    // Gap Analysis
    if (mrd.gap_analysis && mrd.gap_analysis.length > 0) {
        elements.gapList.innerHTML = mrd.gap_analysis.map(gap => `
            <span class="gap-item">${gap}</span>
        `).join('');
    }
}

/**
 * Format large numbers
 */
function formatNumber(num) {
    if (!num) return 'N/A';
    if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B';
    if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M';
    if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K';
    return num.toString();
}

/**
 * Download MRD as JSON
 */
function handleDownloadJson() {
    if (!mrdResult) {
        alert('No MRD data available');
        return;
    }

    const blob = new Blob([JSON.stringify(mrdResult, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mrd_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * Copy MRD to clipboard
 */
async function handleCopyToClipboard() {
    if (!mrdResult) {
        alert('No MRD data available');
        return;
    }

    try {
        await navigator.clipboard.writeText(JSON.stringify(mrdResult, null, 2));
        elements.copyToClipboard.textContent = '✅ Copied!';
        setTimeout(() => {
            elements.copyToClipboard.textContent = '📋 Copy';
        }, 2000);
    } catch (error) {
        console.error('Copy failed:', error);
        alert('Failed to copy to clipboard');
    }
}
