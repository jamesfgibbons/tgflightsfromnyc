/**
 * SERP Loop Radio Player - Fixed for Current HTML Structure
 * Handles textarea input and Van Halen musical features
 */

class MusicalSerpPlayer {
    constructor() {
        this.ws = null;
        this.audioContextStarted = false;
        this.motifLoop = null;
        this.synth = null;
        this.filter = null;
        this.effects = {};
        this.clientDomain = '';
        this.currentMotif = {
            transpose: 0,
            tempo: 120,
            minor: false,
            cutoff: 400
        };
        this.recapData = null;
    }
    
    async initializeAudio() {
        if (this.audioContextStarted) return;
        try {
            await Tone.start();
            this.audioContextStarted = true;
            console.log('🎵 Tone.js audio context started');
            
            this.synth = new Tone.PolySynth(Tone.Synth, {
                oscillator: { type: "sawtooth" },
                envelope: { attack: 0.01, decay: 0.2, sustain: 0.3, release: 0.8 }
            });
            
            this.filter = new Tone.Filter({
                frequency: 400,
                type: "lowpass",
                rolloff: -24
            });
            
            this.effects.distortion = new Tone.Distortion(0.4);
            this.effects.reverb = new Tone.Reverb(1.2);
            this.effects.chorus = new Tone.Chorus(4, 2.5, 0.5);
            
            this.synth.chain(
                this.filter,
                this.effects.distortion,
                this.effects.chorus,
                this.effects.reverb,
                Tone.Destination
            );
            
            this.setupJumpMotif();
            
        } catch (error) {
            console.error('Audio initialization failed:', error);
            this.showNotification('Audio initialization failed. Please click the page and try again.', 'error');
        }
    }
    
    setupJumpMotif() {
        const bassNotes = ["C2", "C2", "G1", "C2"];
        let noteIndex = 0;
        
        this.motifLoop = new Tone.Loop((time) => {
            const note = bassNotes[noteIndex % 4];
            const finalNote = this.currentMotif.minor ? Tone.Frequency(note).transpose(-1) : note;
            const transposedNote = Tone.Frequency(finalNote).transpose(this.currentMotif.transpose);
            
            this.synth.triggerAttackRelease(transposedNote, "8n", time, 0.6);
            noteIndex++;
        }, "4n");
    }

    startMotif() {
        if (!this.audioContextStarted) this.initializeAudio();
        if (this.motifLoop && Tone.Transport.state !== 'started') {
            Tone.Transport.start();
            this.motifLoop.start(0);
            console.log('🎸 Van Halen motif started');
        }
    }
    
    stopMotif() {
        if (Tone.Transport.state === 'started') {
            Tone.Transport.stop();
            if (this.motifLoop) this.motifLoop.stop(0);
            console.log('⏹️ Van Halen motif stopped');
        }
    }

    updateMotif(motifData) {
        this.currentMotif = { ...this.currentMotif, ...motifData };
        
        if (motifData.tempo) Tone.Transport.bpm.rampTo(motifData.tempo, 0.2);
        if (motifData.cutoff) this.filter.frequency.rampTo(motifData.cutoff, 0.3);
        
        if (motifData.ai_steal) this.showNotification('🤖 AI Overview Alert!', 'warning');
        if (motifData.minor) this.showNotification('⚠️ Competitor Threat!', 'danger');
    }
    
    playMusicalNote(noteData) {
        if (!this.synth) return;
        
        const { note, duration, velocity, pan, overlay, filter_sweep, transpose, badge, domain, keyword } = noteData;
        const finalTranspose = (transpose || 0) + this.currentMotif.transpose;
        const transposedNote = Tone.Frequency(note).transpose(finalTranspose);
        
        if (pan !== undefined) this.synth.set({ pan: pan });
        
        if (filter_sweep) {
            this.filter.frequency.rampTo(1200, 0.1);
            setTimeout(() => this.filter.frequency.rampTo(this.currentMotif.cutoff, 0.5), 200);
        }
        
        this.synth.triggerAttackRelease(transposedNote, duration || "8n", undefined, (velocity || 80) / 127);
        if (overlay) this.playOverlay(overlay);
        
        // Update now playing display
        this.updateNowPlaying(keyword, domain, badge);
    }
    
    updateNowPlaying(keyword, domain, badge) {
        const titleEl = document.querySelector('.track-title');
        const artistEl = document.querySelector('.track-artist');
        
        if (titleEl) titleEl.textContent = `${keyword} ${badge || ''}`;
        if (artistEl) artistEl.textContent = domain;
    }
    
    playOverlay(overlayType) {
        const effectsSynth = new Tone.Synth().toDestination();
        switch (overlayType) {
            case 'jump_bass_stab':
                effectsSynth.set({ oscillator: { type: "sawtooth" }, envelope: { attack: 0.001, decay: 0.1, sustain: 0, release: 0.1 } });
                effectsSynth.triggerAttackRelease("C1", "16n", undefined, 0.8);
                break;
            case 'bell_warning':
                effectsSynth.set({ oscillator: { type: "sine" }, envelope: { attack: 0.01, decay: 1, sustain: 0, release: 1 } });
                effectsSynth.triggerAttackRelease("C6", "4n", undefined, 0.3);
                break;
            case 'hihat_shuffle':
                const hihat = new Tone.NoiseSynth({ noise: { type: "white" }, envelope: { attack: 0.001, decay: 0.05, sustain: 0 } }).toDestination();
                hihat.triggerAttack();
                setTimeout(() => hihat.dispose(), 500);
                return;
            case 'cash_register':
                effectsSynth.set({ oscillator: { type: "square" }, envelope: { attack: 0.01, decay: 0.1, sustain: 0.1, release: 0.2 } });
                effectsSynth.triggerAttackRelease("G4", "32n");
                setTimeout(() => effectsSynth.triggerAttackRelease("C5", "32n"), 50);
                break;
        }
        setTimeout(() => effectsSynth.dispose(), 1000);
    }
    
    handleWebSocketMessage(event) {
        const msg = JSON.parse(event.data);
        console.log('Received message:', msg.type);
        
        switch (msg.type) {
            case 'motif_init':
                console.log('🎸 Motif initialized:', msg.data);
                this.startMotif();
                break;
            case 'motif':
                this.updateMotif(msg);
                break;
            case 'musical_note':
                this.playMusicalNote(msg.data);
                break;
            case 'recap_insights':
                this.recapData = msg.data;
                this.updateScorecard(msg.data);
                break;
            case 'complete':
                this.showNotification('🎵 Musical stream complete!', 'success');
                setTimeout(() => {
                    switchTab('recap');
                    document.getElementById('replayBtn').disabled = false;
                }, 2000);
                break;
            default:
                console.log('Unhandled message type:', msg.type);
        }
    }
    
    updateScorecard(data) {
        // Update stats
        document.getElementById('totalKeywords').textContent = data.total_keywords || 0;
        document.getElementById('totalResults').textContent = data.total_results || 0;
        document.getElementById('aiOverviewCount').textContent = data.ai_overviews || 0;
        
        // Update insights
        const insightsList = document.getElementById('insights-list');
        if (data.insights && data.insights.length > 0) {
            insightsList.innerHTML = data.insights.map(insight => 
                `<li>${insight}</li>`
            ).join('');
        }
        
        // Update league table
        const recapList = document.getElementById('recap-list');
        if (data.league && data.league.length > 0) {
            recapList.innerHTML = data.league.map((item, index) => 
                `<li class="domain-item">
                    <span class="rank">#${index + 1}</span>
                    <span class="domain">${item.domain}</span>
                    <span class="percentage">${item.percentage}%</span>
                </li>`
            ).join('');
        }
    }
    
    connect(sessionId, skin = 'arena_rock', domain = '') {
        this.initializeAudio();
        this.clientDomain = domain;
        
        const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/serp?session_id=${sessionId}&skin=${skin}`;
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('🎵 Connected to Musical SERP Radio');
            this.updateStatus('connected', 'Connected - Van Halen Mode');
        };
        
        this.ws.onmessage = (event) => {
            this.handleWebSocketMessage(event);
        };
        
        this.ws.onclose = () => {
            console.log('🎵 Disconnected');
            this.stopMotif();
            this.updateStatus('disconnected', 'Disconnected');
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateStatus('error', 'Connection failed');
        };
    }
    
    disconnect() {
        if (this.ws) this.ws.close();
        this.stopMotif();
        this.updateStatus('disconnected', 'Disconnected');
    }
    
    updateStatus(status, text) {
        const statusEl = document.getElementById('status');
        const statusTextEl = document.querySelector('.status-text');
        const statusIndicatorEl = document.querySelector('.status-indicator');
        
        if (statusEl) statusEl.className = `status ${status}`;
        if (statusTextEl) statusTextEl.textContent = text;
        if (statusIndicatorEl) statusIndicatorEl.className = `status-indicator ${status}`;
    }
    
    showNotification(message, type = 'info') {
        console.log(`${type.toUpperCase()}: ${message}`);
        // Could add toast notifications here if needed
    }
}

// Global instance
const musicalPlayer = new MusicalSerpPlayer();

// DOM Ready handler
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎸 Musical SERP Loop Radio initializing...');
    
    const streamBtn = document.getElementById('streamBtn');
    const stopBtn = document.getElementById('stopBtn');
    const keywordsEl = document.getElementById('keywords');
    const domainEl = document.getElementById('domain');
    const skinEl = document.getElementById('skin');
    
    if (streamBtn) {
        streamBtn.addEventListener('click', async function() {
            const keywords = keywordsEl.value.trim();
            const domain = domainEl.value.trim();
            const skin = skinEl.value;
            
            if (!keywords) {
                alert('Please enter some keywords');
                return;
            }
            
            try {
                // Show loading state
                streamBtn.disabled = true;
                streamBtn.querySelector('.btn-text').style.display = 'none';
                streamBtn.querySelector('.btn-loading').style.display = 'inline';
                
                console.log('Starting stream with keywords:', keywords);
                
                // Parse keywords (handle both newlines and commas)
                const keywordList = keywords.split(/[\n,]+/)
                    .map(k => k.trim())
                    .filter(k => k)
                    .slice(0, 50); // Limit to 50
                
                console.log('Parsed keywords:', keywordList);
                
                // Fetch SERP data
                const response = await fetch('/fetch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        keywords: keywordList, 
                        domain: domain || null 
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                console.log('Got session:', data.session_id);
                
                // Connect to WebSocket
                musicalPlayer.connect(data.session_id, skin, domain);
                
                // Update UI
                stopBtn.disabled = false;
                
            } catch (error) {
                console.error('Stream start failed:', error);
                alert('Failed to start stream: ' + error.message);
            } finally {
                // Reset button state
                streamBtn.disabled = false;
                streamBtn.querySelector('.btn-text').style.display = 'inline';
                streamBtn.querySelector('.btn-loading').style.display = 'none';
            }
        });
    }
    
    if (stopBtn) {
        stopBtn.addEventListener('click', function() {
            musicalPlayer.disconnect();
            stopBtn.disabled = true;
        });
    }
});

// Tab switching function
function switchTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.style.display = 'none';
        content.classList.remove('active');
    });
    
    // Remove active class from all tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab
    const targetContent = document.getElementById(tabName + '-container');
    const targetTab = document.getElementById('tab-' + tabName);
    
    if (targetContent) {
        targetContent.style.display = 'block';
        targetContent.classList.add('active');
    }
    
    if (targetTab) {
        targetTab.classList.add('active');
    }
}

// Replay function
function replayRecap() {
    if (musicalPlayer.recapData) {
        console.log('Replaying recap...');
        musicalPlayer.showNotification('🎼 Replaying scorecard overture...', 'info');
    }
}

// Screenshot function
function takeScreenshot() {
    console.log('Screenshot functionality would go here');
    alert('Screenshot feature coming soon!');
} 