// SERP Loop Radio Player - Brand-Insight Audio Hooks with Scorecard

class SERPRadioPlayer {
    constructor() {
        this.ws = null;
        this.sessionId = null;
        this.isStreaming = false;
        this.synths = new Map();
        this.canvas = null;
        this.ctx = null;
        this.animationFrame = null;
        this.recapData = [];
        this.recapInsights = [];
        this.leagueTable = [];
        
        // Initialize Tone.js and canvas
        this.initAudio();
        this.initCanvas();
        
        // Bind elements
        this.elements = {
            keywords: document.getElementById('keywords'),
            domain: document.getElementById('domain'),
            skin: document.getElementById('skin'),
            streamBtn: document.getElementById('streamBtn'),
            stopBtn: document.getElementById('stopBtn'),
            status: document.getElementById('status'),
            statusText: document.querySelector('.status-text'),
            trackTitle: document.querySelector('.track-title'),
            trackArtist: document.querySelector('.track-artist'),
            replayBtn: document.getElementById('replayBtn'),
            recapList: document.getElementById('recap-list'),
            insightsList: document.getElementById('insights-list'),
            totalKeywords: document.getElementById('totalKeywords'),
            totalResults: document.getElementById('totalResults'),
            aiOverviewCount: document.getElementById('aiOverviewCount')
        };
        
        // Bind events
        this.bindEvents();
        
        // Initialize with sample keywords
        this.elements.keywords.value = 'AI tools\nmachine learning\ndata science\nweb development\nSEO optimization';
    }
    
    async initAudio() {
        try {
            // -----------  GLOBAL FILTER + LIMITER -------------
            this.masterLimiter = new Tone.Limiter(-2).toDestination();
            this.filter = new Tone.Filter(400, "lowpass").connect(this.masterLimiter);
            
            // Add light reverb for gluing overlays to the motif
            this.reverb = new Tone.Reverb({
                decay: 1.5,
                wet: 0.2
            }).connect(this.masterLimiter);
            
            // -----------  JUMP RIFF MIDI SYSTEM  -----------------
            // Enhanced motif object for full riff control
            this.motif = {
                transpose: 0,
                velocity: 0.8,
                tempo: 120
            };
            
            // Initialize MIDI-based Jump riff
            this.jumpMidiPart = null;
            await this.loadJumpMidi();
            
            // -----------  LEGACY BASS SYNTH (fallback)  -----------------
            this.bass = new Tone.Synth({
                oscillator: {type: "sawtooth"},
                envelope: {attack: 0.02, decay: 0.1, sustain: 0.5, release: 0.1}
            }).connect(this.filter);
            this.bass.volume.value = -4;   // sits nicely under overlays
            this.notes = ["C2","C3","G2","C3"];
            
            // Set up the Jump bass loop
            let step = 0;
            this.bassLoop = Tone.Transport.scheduleRepeat((time) => {
                const n = this.notes[step % 4];
                const freq = Tone.Frequency(n).transpose(this.motif.transpose);
                console.log(`🎸 Playing bass note: ${n} (step ${step % 4}) -> ${freq.toFrequency()}Hz`);
                this.bass.triggerAttackRelease(freq, "8n", time, 0.9);
                step++;
            }, "4n");
            
            // Don't start transport here - let the motif message start it
            console.log('🎵 Van Halen bass loop scheduled, waiting for motif message to start');
            
            // Create synths for different waveforms with enhanced effects
            this.synths.set('sine', new Tone.Synth().connect(this.filter));
            this.synths.set('sawtooth', new Tone.Synth({oscillator: {type: 'sawtooth'}}).connect(this.filter));
            this.synths.set('square', new Tone.Synth({oscillator: {type: 'square'}}).connect(this.filter));
            this.synths.set('triangle', new Tone.Synth({oscillator: {type: 'triangle'}}).connect(this.filter));
            
            // Special synth for drone notes
            this.droneSynth = new Tone.Synth({
                oscillator: { type: 'sine' },
                envelope: { attack: 0.5, decay: 0.5, sustain: 0.8, release: 1.0 }
            }).connect(this.masterLimiter);
            
            // Upgrade to MembraneSynth for warmer, punchier bass
            this.bassSynth = new Tone.MembraneSynth({
                pitchDecay: 0.05,
                octaves: 10,
                oscillator: {type: "sine"},
                envelope: {attack: 0.02, decay: 0.2, sustain: 0.2, release: 0.8}
            }).connect(this.masterLimiter);

            this.bassNotes = ["C2","C3","G2","C3"];   // Jump riff
            this.motif = {transpose: 0, tempo: 120};

            Tone.Transport.bpm.value = this.motif.tempo;
            this.loop = new Tone.Loop(time => {
                const n = this.bassNotes[(this.loop.iterations) % 4];
                const freq = Tone.Frequency(n).transpose(this.motif.transpose);
                this.bassSynth.triggerAttackRelease(freq, "8n", time);
            }, "4n").start(0);
            
            // Initialize professional sample players
            await this.initSamplePlayers();
            
            console.log('Audio initialized with professional sample chain and -2dB limiting');
        } catch (error) {
            console.error('Audio initialization failed:', error);
        }
    }
    
    async loadJumpMidi() {
        try {
            console.log('🎸 Loading Jump MIDI theme...');
            
            // Load MIDI file from server
            const midi = await Tone.Midi.fromUrl("/midi/jump_theme.mid");
            console.log(`🎵 MIDI loaded: ${midi.duration}s duration, ${midi.tracks.length} tracks`);
            
            // Create polyphonic synth for full riff
            const jumpSynth = new Tone.PolySynth(Tone.Synth, {
                oscillator: { type: "sawtooth" },
                envelope: { attack: 0.02, decay: 0.2, sustain: 0.6, release: 0.3 }
            }).connect(this.filter);
            jumpSynth.volume.value = -2; // Prominent but not overwhelming
            
            // Create the MIDI part with dynamic parameters
            this.jumpMidiPart = new Tone.Part((time, note) => {
                const transposedFreq = Tone.Frequency(note.name).transpose(this.motif.transpose);
                jumpSynth.triggerAttackRelease(
                    transposedFreq,
                    note.duration,
                    time,
                    this.motif.velocity
                );
            }, midi.tracks[0].notes).start(0);
            
            // Configure looping
            this.jumpMidiPart.loop = true;
            this.jumpMidiPart.loopEnd = midi.duration;
            
            console.log('🎸 Jump MIDI riff loaded and ready');
            
        } catch (error) {
            console.warn('❌ MIDI loading failed, falling back to bass loop:', error);
            // MIDI loading failed, bass loop will continue as fallback
        }
    }
    
    initCanvas() {
        this.canvas = document.getElementById('viz');
        this.ctx = this.canvas.getContext('2d');
        this.visualizerData = new Array(32).fill(0);
        this.drawVisualizer();
    }
    
    bindEvents() {
        this.elements.streamBtn.addEventListener('click', () => this.startStream());
        this.elements.stopBtn.addEventListener('click', () => this.stopStream());
        this.elements.replayBtn.addEventListener('click', () => this.replayRecap());
        
        // Upload event handlers
        document.getElementById('uploadBtn').addEventListener('click', () => this.uploadCSV());
        document.getElementById('playBtn').addEventListener('click', () => this.playUploadedData());
        
        // Time series event handlers
        document.getElementById('timeseriesUploadBtn').addEventListener('click', () => this.uploadTimeSeries());
        document.getElementById('timeseriesPlayBtn').addEventListener('click', () => this.playTimeSeries());
    }
    
    async startStream() {
        try {
            const keywords = this.getKeywords();
            if (keywords.length === 0) {
                this.showError('Please enter at least one keyword');
                return;
            }
            
            if (Tone.context.state !== 'running') {
                await Tone.start();
            }
            
            // Clear previous recap data
            this.recapData = [];
            this.recapInsights = [];
            this.leagueTable = [];
            
            this.setLoading(true);
            this.updateStatus('Fetching SERP data...', 'connected');
            
            const response = await fetch('/fetch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    keywords: keywords,
                    domain: this.elements.domain.value.trim() || null
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.sessionId = data.session_id;
            
            await this.connectWebSocket();
            
        } catch (error) {
            console.error('Stream start failed:', error);
            this.showError('Failed to start stream: ' + error.message);
            this.setLoading(false);
        }
    }
    
    async connectWebSocket() {
        try {
            // SSL-safe WebSocket URL
            const protocol = location.protocol === "https:" ? "wss" : "ws";
            const skin = this.elements.skin.value;
            const wsUrl = `${protocol}://${location.host}/ws/serp?session_id=${this.sessionId}&skin=${skin}`;
            
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                this.isStreaming = true;
                this.setLoading(false);
                this.updateStatus('Connected - Streaming live', 'streaming');
                this.elements.stopBtn.disabled = false;
                this.startVisualizerAnimation();
            };
            
            this.ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleMessage(message);
            };
            
            this.ws.onclose = () => {
                this.isStreaming = false;
                this.updateStatus('Disconnected', 'disconnected');
                this.elements.stopBtn.disabled = true;
                this.elements.streamBtn.disabled = false;
                this.stopVisualizerAnimation();
            };
            
            this.ws.onerror = (error) => {
                this.showError('Connection error');
            };
            
        } catch (error) {
            this.showError('Failed to connect');
            this.setLoading(false);
        }
    }
    
    handleMessage(message) {
        switch (message.type) {
            case 'connection':
                this.updateTrackInfo('Connected', 'Session: ' + message.data.session_id.substring(0, 8) + '...');
                break;
            case 'status':
                this.updateStatus(message.data.message, 'streaming');
                break;
            case 'motif':
                // Update motif parameters for full riff control
                this.motif.transpose = message.data.transpose || 0;
                this.motif.velocity = 0.5 + Math.min(0.5, Math.abs(message.data.top3_delta || 0) / 10);
                
                // Smooth tempo transition
                if (message.data.tempo) {
                    Tone.Transport.bpm.rampTo(message.data.tempo, 0.3);
                }
                
                // CTR jump detection for solo fills
                if (message.data.ctr_delta && message.data.ctr_delta >= 0.005) {
                    console.log(`🎸 CTR jump detected: +${(message.data.ctr_delta * 100).toFixed(2)}%`);
                    this.playSample("guitar_fill.wav");
                }
                
                // AI steal filter effect
                if (message.data.ai_steal) {
                    // Improved filter glide: sweep up quickly, then breathe back down over 1 second
                    this.filter.frequency.rampTo(1200, 0.3);
                    setTimeout(() => this.filter.frequency.rampTo(400, 1.0), 800);
                }
                
                console.log(`🎵 Motif updated: transpose=${this.motif.transpose}, velocity=${this.motif.velocity}, tempo=${message.data.tempo}`);
                break;
            case 'note_event':
                this.playNote(message.data);
                // Pass badge field to status display
                if (message.data.badge) {
                    this.elements.statusText.textContent = message.data.badge;
                }
                break;
            case 'drone_event':
                this.playDrone(message.data);
                break;
            case 'recap_chord':
                this.recapData.push(message);
                this.addRecapRow(message.meta.domain, message.meta.share, message.meta.rank);
                this.playChord(message);
                break;
            case 'recap_insights':
                this.recapInsights = message.data.insights;
                this.leagueTable = message.data.league;
                this.updateStatsDisplay(message.data);
                this.displayInsights();
                break;
            case 'complete':
                this.updateStatus('Stream complete - Check scorecard!', 'connected');
                this.elements.replayBtn.disabled = false;
                // Auto-switch to scorecard tab
                setTimeout(() => {
                    switchTab('recap');
                }, 1500);
                setTimeout(() => this.stopStream(), 3000);
                break;
            case 'error':
                this.showError(message.data.message);
                break;
        }
        
        this.playSample(message.data.overlay);
    }
    
    playSample(sampleName) {
        // Professional sample playback with proper routing
        if (!sampleName || !this.samplePlayers) return;
        
        console.log('Playing overlay sample:', sampleName);
        
        // Add humanized timing (±20ms swing)
        const humanizeDelay = (Math.random() - 0.5) * 0.04;
        const playTime = Tone.now() + humanizeDelay;
        
        // Map sample names to player keys
        const sampleKeyMap = {
            'video_cymbal.wav': 'video',
            'video_cymbal': 'video',
            'cash_register.wav': 'cash',
            'cash_register': 'cash',
            'snare.wav': 'shopping',
            'snare': 'shopping',
            'jump_bass.mid': 'jump_bass',
            'jump_bass': 'jump_bass',
            'ai_steal_bell.mid': 'ai_bell',
            'ai_bell': 'ai_bell'
        };
        
        const playerKey = sampleKeyMap[sampleName];
        if (playerKey && this.samplePlayers[playerKey]) {
            const player = this.samplePlayers[playerKey];
            
            if (player.trigger) {
                // Synth fallback
                player.trigger(playTime);
            } else if (player.start) {
                // Real audio sample
                try {
                    player.start(playTime);
                } catch (error) {
                    console.warn(`Sample ${playerKey} failed to play:`, error);
                    // Trigger fallback
                    this.createSynthFallback(playerKey).trigger(playTime);
                }
            }
        } else {
            console.warn(`No sample player found for: ${sampleName}`);
        }
    }
    
    playNote(noteData) {
        try {
            const synth = this.synths.get(noteData.waveform) || this.synths.get('sine');
            const frequency = noteData.frequency || 440;
            const duration = noteData.duration || 0.5;
            const amplitude = noteData.amplitude || 0.3;
            
            // Add humanized timing (±20ms swing for musical feel)
            const humanizeDelay = (Math.random() - 0.5) * 0.04;
            const playTime = Tone.now() + humanizeDelay;
            
            // Apply transpose if present
            let finalFrequency = frequency;
            if (noteData.transpose) {
                finalFrequency = frequency * Math.pow(2, noteData.transpose / 12);
            }
            
            // Apply amplitude modulation for brand wins, rank drops, etc.
            let finalAmplitude = amplitude;
            if (noteData.amp_mod) {
                finalAmplitude = amplitude * noteData.amp_mod;
            }
            
            // Play overlay samples for SERP features
            if (noteData.overlay === "video_cymbal") this.playSample("video_cymbal.wav");
            if (noteData.overlay === "cash_register") this.playSample("cash_register.wav");
            if (noteData.overlay === "snare") this.playSample("snare.wav");
            
            // Display badge and keyword info
            const badge = noteData.badge || '';
            const brandHit = noteData.brand_hit ? ' 🏆' : '';
            
            this.updateTrackInfo(
                noteData.keyword + ' - ' + noteData.domain + brandHit + badge,
                'Rank ' + noteData.rank + ' • ' + noteData.note + ' • ' + Math.round(finalFrequency) + 'Hz'
            );
            
            // Color-flash on brand win
            if (noteData.badge === '🏆') {
                this.elements.trackTitle.classList.add('flash-win');
                setTimeout(() => {
                    this.elements.trackTitle.classList.remove('flash-win');
                }, 600);
            }
            
            // Play the note with enhanced parameters and humanized timing
            synth.triggerAttackRelease(finalFrequency, duration, playTime, finalAmplitude);
            this.animateVisualizer(finalFrequency, finalAmplitude);
            
        } catch (error) {
            console.error('Error playing note:', error);
        }
    }
    
    playChord(message) {
        try {
            const chordData = message.data;
            const frequency = chordData.frequency || 261.63;
            const duration = chordData.duration || 2.0;
            const amplitude = chordData.amplitude || 0.5;
            
            // Use sine wave for recap chords
            const synth = this.synths.get('sine');
            synth.triggerAttackRelease(frequency, duration, Tone.now(), amplitude);
            
            // Visual feedback
            this.animateVisualizer(frequency, amplitude);
            
        } catch (error) {
            console.error('Error playing recap chord:', error);
        }
    }
    
    playDrone(droneData) {
        try {
            // Play low-C drone for brand dominance
            const frequency = droneData.frequency || 65.4; // C2
            const duration = droneData.duration || 2.0;
            const amplitude = droneData.amplitude || 0.3;
            
            console.log('Playing brand dominance drone:', frequency + 'Hz');
            
            this.droneSynth.triggerAttackRelease(frequency, duration, Tone.now(), amplitude);
            
            // Visual feedback for drone
            this.updateStatus('Brand dominance detected 🎯', 'streaming');
            setTimeout(() => {
                if (this.isStreaming) {
                    this.updateStatus('Streaming live', 'streaming');
                }
            }, 2000);
            
        } catch (error) {
            console.error('Error playing drone:', error);
        }
    }
    
    addRecapRow(domain, share, rank) {
        const recapList = this.elements.recapList;
        
        // Clear placeholder on first add
        if (recapList.querySelector('.placeholder')) {
            recapList.innerHTML = '';
        }
        
        const li = document.createElement('li');
        li.innerHTML = `
            <div style="display: flex; align-items: center;">
                <span class="domain-rank">${rank}</span>
                <span class="domain-name">${domain}</span>
            </div>
            <span class="domain-share">${(share * 100).toFixed(1)}%</span>
        `;
        
        recapList.appendChild(li);
    }
    
    displayInsights() {
        const insightsList = this.elements.insightsList;
        
        // Clear placeholder
        insightsList.innerHTML = '';
        
        this.recapInsights.forEach(insight => {
            const li = document.createElement('li');
            li.textContent = insight;
            insightsList.appendChild(li);
        });
        
        if (this.recapInsights.length === 0) {
            const li = document.createElement('li');
            li.className = 'placeholder';
            li.textContent = 'No insights generated';
            insightsList.appendChild(li);
        }
    }
    
    updateStatsDisplay(data) {
        this.elements.totalKeywords.textContent = data.total_keywords || '-';
        this.elements.totalResults.textContent = data.total_results || '-';
        
        // Calculate AI overview count from insights
        const aiInsight = this.recapInsights.find(insight => insight.includes('AI Overview'));
        if (aiInsight) {
            const match = aiInsight.match(/(\d+\.?\d*)%/);
            if (match) {
                const percentage = parseFloat(match[1]);
                const count = Math.round((percentage / 100) * data.total_results);
                this.elements.aiOverviewCount.textContent = count;
            }
        } else {
            this.elements.aiOverviewCount.textContent = '0';
        }
    }
    
    async replayRecap() {
        if (this.recapData.length === 0) {
            this.showError('No recap data to replay');
            return;
        }
        
        try {
            if (Tone.context.state !== 'running') {
                await Tone.start();
            }
            
            this.elements.replayBtn.disabled = true;
            this.updateStatus('Replaying recap overture...', 'streaming');
            
            // Replay each chord with timing
            for (let i = 0; i < this.recapData.length; i++) {
                const message = this.recapData[i];
                this.playChord(message);
                
                // Update track info during replay
                const meta = message.meta;
                this.updateTrackInfo(
                    `#${meta.rank} ${meta.domain}`,
                    `${meta.percentage}% share - Recap chord`
                );
                
                if (i < this.recapData.length - 1) {
                    await new Promise(resolve => setTimeout(resolve, 800));
                }
            }
            
            setTimeout(() => {
                this.elements.replayBtn.disabled = false;
                this.updateStatus('Recap complete', 'connected');
                this.updateTrackInfo('Scorecard ready', 'Replay available');
            }, 1000);
            
        } catch (error) {
            console.error('Replay failed:', error);
            this.elements.replayBtn.disabled = false;
            this.showError('Replay failed: ' + error.message);
        }
    }
    
    animateVisualizer(frequency, amplitude) {
        // Map frequency to visualizer bars
        const barIndex = Math.floor((frequency - 200) / 50) % this.visualizerData.length;
        this.visualizerData[barIndex] = Math.min(amplitude * 2, 1.0);
        
        // Add some randomness to nearby bars
        for (let i = 0; i < this.visualizerData.length; i++) {
            if (Math.abs(i - barIndex) <= 2 && Math.random() > 0.6) {
                this.visualizerData[i] = Math.max(this.visualizerData[i], amplitude * 0.5);
            }
        }
    }
    
    startVisualizerAnimation() {
        const animate = () => {
            this.drawVisualizer();
            
            // Decay visualizer data
            for (let i = 0; i < this.visualizerData.length; i++) {
                this.visualizerData[i] *= 0.95;
            }
            
            if (this.isStreaming) {
                this.animationFrame = requestAnimationFrame(animate);
            }
        };
        animate();
    }
    
    stopVisualizerAnimation() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }
        // Reset visualizer
        this.visualizerData.fill(0);
        this.drawVisualizer();
    }
    
    drawVisualizer() {
        const width = this.canvas.width;
        const height = this.canvas.height;
        
        this.ctx.fillStyle = 'rgba(15, 52, 96, 0.8)';
        this.ctx.fillRect(0, 0, width, height);
        
        const barWidth = width / this.visualizerData.length;
        
        for (let i = 0; i < this.visualizerData.length; i++) {
            const barHeight = this.visualizerData[i] * height * 0.8;
            const x = i * barWidth;
            const y = height - barHeight;
            
            // Create gradient for bars
            const gradient = this.ctx.createLinearGradient(0, height, 0, 0);
            gradient.addColorStop(0, '#32ff7e');
            gradient.addColorStop(0.5, '#2ed573');
            gradient.addColorStop(1, '#B4FF39'); // Brighter top for brand wins
            
            this.ctx.fillStyle = gradient;
            this.ctx.fillRect(x + 1, y, barWidth - 2, barHeight);
        }
    }
    
    stopStream() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.isStreaming = false;
        this.setLoading(false);
        this.updateStatus('Ready to rock', 'disconnected');
        this.updateTrackInfo('Ready to stream', 'Enter keywords above');
        this.elements.stopBtn.disabled = true;
        this.elements.streamBtn.disabled = false;
        this.stopVisualizerAnimation();
    }
    
    getKeywords() {
        return this.elements.keywords.value.split('\n').map(kw => kw.trim()).filter(kw => kw.length > 0).slice(0, 50);
    }
    
    setLoading(loading) {
        this.elements.streamBtn.disabled = loading;
        const btnText = this.elements.streamBtn.querySelector('.btn-text');
        const btnLoading = this.elements.streamBtn.querySelector('.btn-loading');
        if (loading) {
            btnText.style.display = 'none';
            btnLoading.style.display = 'inline';
        } else {
            btnText.style.display = 'inline';
            btnLoading.style.display = 'none';
        }
    }
    
    updateStatus(text, type) {
        this.elements.statusText.textContent = text;
        this.elements.status.className = 'status ' + type;
    }
    
    updateTrackInfo(title, artist) {
        this.elements.trackTitle.textContent = title;
        this.elements.trackArtist.textContent = artist;
    }
    
    showError(message) {
        this.updateStatus('Error: ' + message, 'disconnected');
        this.updateTrackInfo('Error occurred', message);
    }
    
    // Helper function to get selected CSV type
    selType() {
        const selected = document.querySelector('input[name="csvtype"]:checked');
        return selected ? selected.value : 'gsc';
    }
    
    async uploadCSV() {
        try {
            const fileInput = document.getElementById("csvFile");
            const file = fileInput.files[0];
            
            if (!file) {
                this.showError("Please select a CSV file");
                return;
            }
            
            this.setUploadLoading(true);
            this.updateUploadStatus('Uploading and analyzing...', 'connected');
            
            const formData = new FormData();
            formData.append("file", file);
            formData.append("declared_type", this.selType());
            
            const response = await fetch("/upload", {
                method: "POST",
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Upload failed: ${response.status}`);
            }
            
            const data = await response.json();
            this.sessionId = data.session_id;
            
            this.setUploadLoading(false);
            this.updateUploadStatus(`Uploaded successfully - ${data.row_count} rows`, 'connected');
            document.getElementById("playBtn").disabled = false;
            
            this.updateUploadTrackInfo(
                `${file.name} - ${data.format || 'Unknown format'}`,
                `${data.row_count} rows ready for sonification`
            );
            
        } catch (error) {
            console.error('Upload failed:', error);
            this.showError('Upload failed: ' + error.message);
            this.setUploadLoading(false);
        }
    }
    
    async playUploadedData() {
        if (!this.sessionId) {
            this.showError('No data uploaded');
            return;
        }
        
        try {
            if (Tone.context.state !== 'running') {
                await Tone.start();
            }
            
            const skin = document.getElementById('uploadSkin').value;
            await this.connectWebSocketForUpload(skin);
            
        } catch (error) {
            console.error('Play failed:', error);
            this.showError('Failed to play: ' + error.message);
        }
    }
    
    async connectWebSocketForUpload(skin) {
        try {
            const protocol = location.protocol === "https:" ? "wss" : "ws";
            const wsUrl = `${protocol}://${location.host}/ws/serp?session_id=${this.sessionId}&skin=${skin}`;
            
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                this.isStreaming = true;
                this.updateUploadStatus('Playing uploaded data...', 'streaming');
                this.startUploadVisualizerAnimation();
            };
            
            this.ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleUploadMessage(message);
            };
            
            this.ws.onclose = () => {
                this.isStreaming = false;
                this.updateUploadStatus('Playback complete', 'connected');
                this.stopUploadVisualizerAnimation();
            };
            
            this.ws.onerror = (error) => {
                this.showError('Connection error during playback');
            };
            
        } catch (error) {
            this.showError('Failed to connect for playback');
        }
    }
    
    handleUploadMessage(message) {
        switch (message.type) {
            case 'note_event':
                this.playNote(message.data);
                
                // Update track info with CSV-specific data
                const subtitle = message.data.metric_type === "gsc" 
                    ? `${message.data.clicks || 0} clicks • ${message.data.impressions || 0} impr`
                    : `${message.data.search_volume || 0} vol`;
                
                this.updateUploadTrackInfo(
                    message.data.keyword + ' - ' + message.data.domain,
                    subtitle + ' • Rank ' + message.data.rank
                );
                this.animateUploadVisualizer(message.data.frequency || 440, message.data.amplitude || 0.3);
                break;
            case 'recap_chord':
                this.recapData.push(message);
                this.addRecapRow(message.meta.domain, message.meta.share, message.meta.rank);
                this.playChord(message);
                break;
            case 'recap_insights':
                this.recapInsights = message.data.insights;
                this.leagueTable = message.data.league;
                this.updateStatsDisplay(message.data);
                this.displayInsights();
                break;
            case 'complete':
                this.updateUploadStatus('Playback complete - Check scorecard!', 'connected');
                
                // Add MIDI download button
                this.addMidiDownloadButton();
                
                setTimeout(() => {
                    switchTab('recap');
                }, 1500);
                break;
            default:
                // Handle other message types with existing logic
                this.handleMessage(message);
                break;
        }
    }
    
    setUploadLoading(loading) {
        const btn = document.getElementById('uploadBtn');
        const text = btn.querySelector('.btn-text');
        const spinner = btn.querySelector('.btn-loading');
        
        if (loading) {
            text.style.display = 'none';
            spinner.style.display = 'inline';
            btn.disabled = true;
        } else {
            text.style.display = 'inline';
            spinner.style.display = 'none';
            btn.disabled = false;
        }
    }
    
    updateUploadStatus(text, type) {
        const statusElement = document.getElementById('uploadStatus');
        const statusText = statusElement.querySelector('.status-text');
        statusText.textContent = text;
        statusElement.className = `status ${type}`;
    }
    
    updateUploadTrackInfo(title, artist) {
        const titleElement = document.querySelector('#uploadNowPlaying .track-title');
        const artistElement = document.querySelector('#uploadNowPlaying .track-artist');
        titleElement.textContent = title;
        artistElement.textContent = artist;
    }
    
    animateUploadVisualizer(frequency, amplitude) {
        // Map frequency to visualizer bars for upload canvas
        const barIndex = Math.floor((frequency - 200) / 50) % this.visualizerData.length;
        this.visualizerData[barIndex] = Math.min(amplitude * 2, 1.0);
        
        // Add some randomness to nearby bars
        for (let i = 0; i < this.visualizerData.length; i++) {
            if (Math.abs(i - barIndex) <= 2 && Math.random() > 0.6) {
                this.visualizerData[i] = Math.max(this.visualizerData[i], amplitude * 0.5);
            }
        }
    }
    
    startUploadVisualizerAnimation() {
        const canvas = document.getElementById('uploadViz');
        const ctx = canvas.getContext('2d');
        
        const animate = () => {
            this.drawUploadVisualizer(ctx, canvas);
            
            // Decay visualizer data
            for (let i = 0; i < this.visualizerData.length; i++) {
                this.visualizerData[i] *= 0.95;
            }
            
            if (this.isStreaming) {
                this.animationFrame = requestAnimationFrame(animate);
            }
        };
        animate();
    }
    
    stopUploadVisualizerAnimation() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }
        // Reset visualizer
        this.visualizerData.fill(0);
        const canvas = document.getElementById('uploadViz');
        const ctx = canvas.getContext('2d');
        this.drawUploadVisualizer(ctx, canvas);
    }
    
    drawUploadVisualizer(ctx, canvas) {
        const width = canvas.width;
        const height = canvas.height;
        
        ctx.fillStyle = 'rgba(15, 52, 96, 0.8)';
        ctx.fillRect(0, 0, width, height);
        
        const barWidth = width / this.visualizerData.length;
        
        for (let i = 0; i < this.visualizerData.length; i++) {
            const barHeight = this.visualizerData[i] * height * 0.8;
            const x = i * barWidth;
            const y = height - barHeight;
            
            // Create gradient for bars
            const gradient = ctx.createLinearGradient(0, height, 0, 0);
            gradient.addColorStop(0, '#32ff7e');
            gradient.addColorStop(0.5, '#2ed573');
            gradient.addColorStop(1, '#B4FF39');
            
            ctx.fillStyle = gradient;
            ctx.fillRect(x + 1, y, barWidth - 2, barHeight);
        }
    }
    
    async initSamplePlayers() {
        // Professional sample loading with robust synth fallbacks
        this.samplePlayers = {};
        
        const sampleMap = {
            'jump_bass': 'samples/jump_bass.wav',
            'video': 'samples/video.wav', 
            'shopping': 'samples/shopping.wav',
            'cash': 'samples/cash.wav',
            'ai_bell': 'samples/ai_bell.wav',
            'guitar_fill': 'samples/guitar_fill.wav'
        };
        
        // Always create synth fallbacks first (they always work)
        for (const [key, url] of Object.entries(sampleMap)) {
            // Create synth fallback as primary
            this.samplePlayers[key] = this.createSynthFallback(key);
            console.log(`Created synth fallback for: ${key}`);
            
            // Try to load real sample as enhancement (optional)
            try {
                const player = new Tone.Player({
                    url: url,
                    volume: -6,
                    onload: () => {
                        console.log(`Enhanced with real sample: ${key}`);
                        // Replace synth with real sample if loaded
                        this.samplePlayers[key] = player.connect(this.reverb);
                    },
                    onerror: () => {
                        console.log(`Sample file missing for ${key}, using synth (this is fine)`);
                    }
                });
            } catch (error) {
                // Synth fallback already set up, continue
                console.log(`Using synth for ${key} (sample unavailable)`);
            }
        }
        
        console.log('Sample players initialized with guaranteed synth fallbacks');
    }
    
    playSample(name) {
        if (!this.samplers) {
            this.samplers = {};
        }
        
        if (!this.samplers[name]) {
            this.samplers[name] = new Tone.Player({
                url: `/widget/samples/${name}`,
                onload: () => {
                    console.log(`✅ Sample ${name} loaded successfully`);
                    this.samplers[name].start();
                },
                onerror: () => {
                    console.warn(`⚠️ Sample ${name} missing; using synth fallback`);
                    // Use existing synth fallback system
                    if (this.samplePlayers[name.replace('.wav', '')]) {
                        this.samplePlayers[name.replace('.wav', '')].trigger();
                    }
                }
            }).toDestination();
            this.samplers[name].volume.value = -6;
        } else {
            try {
                this.samplers[name].start();
            } catch (error) {
                console.warn(`⚠️ Sample ${name} failed to play, using synth fallback`);
                // Use existing synth fallback system
                if (this.samplePlayers[name.replace('.wav', '')]) {
                    this.samplePlayers[name.replace('.wav', '')].trigger();
                }
            }
        }
    }
    
    createSynthFallback(sampleType) {
        // Create synth-based fallbacks for missing samples
        const synthPlayer = {
            trigger: (time = Tone.now()) => {
                const synthTone = new Tone.Synth().connect(this.reverb);
                synthTone.volume.value = -6;
                
                switch(sampleType) {
                    case 'jump_bass':
                        synthTone.triggerAttackRelease('C2', '0.2', time);
                        break;
                    case 'video':
                        synthTone.triggerAttackRelease('C6', '0.1', time);
                        break;
                    case 'shopping':
                        synthTone.triggerAttackRelease('F4', '0.08', time);
                        break;
                    case 'cash':
                        synthTone.triggerAttackRelease('G5', '0.05', time);
                        break;
                    case 'ai_bell':
                        // Quick arpeggio for AI bell
                        ['C5', 'E5', 'G5'].forEach((note, i) => {
                            synthTone.triggerAttackRelease(note, '0.1', time + i * 0.05);
                        });
                        break;
                    case 'guitar_fill':
                        // Guitar-like fill for CTR jumps
                        ['E3', 'G3', 'B3', 'E4'].forEach((note, i) => {
                            synthTone.triggerAttackRelease(note, '0.15', time + i * 0.08);
                        });
                        break;
                }
                
                setTimeout(() => synthTone.dispose(), 500);
            }
        };
        
        return synthPlayer;
    }
    
    addMidiDownloadButton() {
        if (!this.sessionId) return;
        
        // Check if button already exists
        const existingBtn = document.getElementById('midiDownloadBtn');
        if (existingBtn) return;
        
        // Create download button
        const downloadBtn = document.createElement('button');
        downloadBtn.id = 'midiDownloadBtn';
        downloadBtn.className = 'stream-btn';
        downloadBtn.innerHTML = '<span class="btn-text">Download MIDI 🎹</span>';
        downloadBtn.style.marginTop = '10px';
        
        // Add click handler
        downloadBtn.addEventListener('click', () => {
            this.downloadMidi();
        });
        
        // Insert after the play button
        const playBtn = document.getElementById('playBtn');
        if (playBtn && playBtn.parentNode) {
            playBtn.parentNode.insertBefore(downloadBtn, playBtn.nextSibling);
        }
    }
    
    async downloadMidi() {
        if (!this.sessionId) {
            this.showError('No session available for MIDI export');
            return;
        }
        
        try {
            const response = await fetch(`/download/midi?session=${this.sessionId}&mode=time`);
            
            if (!response.ok) {
                throw new Error(`Download failed: ${response.status}`);
            }
            
            // Trigger download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `serpradio_${this.sessionId.substring(0, 8)}_time.mid`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            this.updateUploadStatus('MIDI downloaded successfully!', 'connected');
            
        } catch (error) {
            console.error('MIDI download failed:', error);
            this.showError('Failed to download MIDI: ' + error.message);
        }
    }
    
    // Time Series Methods
    async uploadTimeSeries() {
        try {
            const fileInput = document.getElementById('timeseriesFiles');
            const files = Array.from(fileInput.files);
            
            if (files.length < 2) {
                this.showError('Please select at least 2 CSV files for time series analysis');
                return;
            }
            
            if (files.length > 12) {
                this.showError('Maximum 12 periods supported');
                return;
            }
            
            // Validate all files are CSV
            for (const file of files) {
                if (!file.name.toLowerCase().endsWith('.csv')) {
                    this.showError(`File ${file.name} is not a CSV file`);
                    return;
                }
            }
            
            this.setTimeSeriesLoading(true);
            this.updateTimeSeriesStatus('Uploading and processing CSV files...', 'connected');
            
            // Create FormData with all files
            const formData = new FormData();
            files.forEach(file => {
                formData.append('files', file);
            });
            
            const response = await fetch('/upload/timeseries', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }
            
            const data = await response.json();
            this.timeSeriesSessionId = data.session_id;
            
            // Update UI with results
            this.updateTimeSeriesStatus(
                `Processed ${data.periods} periods successfully`,
                'connected'
            );
            
            // Show period summary
            this.displayPeriodSummary(data.summary);
            
            // Enable play button
            document.getElementById('timeseriesPlayBtn').disabled = false;
            
            this.setTimeSeriesLoading(false);
            
        } catch (error) {
            console.error('Time series upload failed:', error);
            this.showError('Upload failed: ' + error.message);
            this.setTimeSeriesLoading(false);
        }
    }
    
    async playTimeSeries() {
        if (!this.timeSeriesSessionId) {
            this.showError('Please upload CSV files first');
            return;
        }
        
        try {
            if (Tone.context.state !== 'running') {
                await Tone.start();
            }
            
            await this.connectTimeSeriesWebSocket();
            
        } catch (error) {
            console.error('Time series playback failed:', error);
            this.showError('Playback failed: ' + error.message);
        }
    }
    
    async connectTimeSeriesWebSocket() {
        try {
            const protocol = location.protocol === "https:" ? "wss" : "ws";
            const skin = document.getElementById('timeseriesSkin').value;
            const wsUrl = `${protocol}://${location.host}/ws/serp?session_id=${this.timeSeriesSessionId}&skin=${skin}`;
            
            this.timeSeriesWs = new WebSocket(wsUrl);
            
            this.timeSeriesWs.onopen = () => {
                this.isTimeSeriesPlaying = true;
                this.updateTimeSeriesStatus('Playing time series...', 'streaming');
                document.getElementById('timeseriesPlayBtn').disabled = true;
                this.startTimeSeriesVisualization();
            };
            
            this.timeSeriesWs.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleTimeSeriesMessage(message);
            };
            
            this.timeSeriesWs.onclose = () => {
                this.isTimeSeriesPlaying = false;
                this.updateTimeSeriesStatus('Playback complete', 'connected');
                document.getElementById('timeseriesPlayBtn').disabled = false;
                this.stopTimeSeriesVisualization();
            };
            
            this.timeSeriesWs.onerror = (error) => {
                this.showError('Time series connection error');
                this.isTimeSeriesPlaying = false;
            };
            
        } catch (error) {
            this.showError('Failed to connect for time series playback');
        }
    }
    
    handleTimeSeriesMessage(message) {
        switch (message.type) {
            case 'connection':
                this.updateTimeSeriesTrackInfo(
                    'Time Series Connected',
                    `Session: ${message.data.session_id.substring(0, 8)}... Mode: ${message.data.mode}`
                );
                break;
                
            case 'status':
                this.updateTimeSeriesStatus(message.data.message, 'streaming');
                break;
                
            case 'motif':
                console.log('🎸 Van Halen motif received:', message);
                // Handle direct format (backend sends fields at root level)
                this.motif.transpose = message.transpose || message.data?.transpose || 0;
                const tempo = message.tempo || message.data?.tempo || 120;
                
                console.log(`🎵 Setting tempo=${tempo}, transpose=${this.motif.transpose}`);
                
                // Update global tempo
                Tone.Transport.bpm.rampTo(tempo, 0.3);
                
                // Ensure Transport is running for the bass loop
                if (Tone.Transport.state !== 'started') {
                    console.log('🚀 Starting Tone.Transport for Van Halen riff');
                    Tone.Transport.start();
                }
                
                // Visual feedback for tempo/key changes
                this.animateTimeSeriesVisualizer(tempo, this.motif.transpose);
                
                // AI steal brightness
                if (message.ai_steal || message.data?.ai_steal) {
                    this.filter.frequency.rampTo(1200, 0.3);
                    setTimeout(() => this.filter.frequency.rampTo(400, 1.0), 800);
                }
                break;
                
            case 'overlay':
                console.log('🎺 Overlay sample received:', message);
                const sampleName = message.sample || message.data?.sample;
                if (sampleName) {
                    this.playSample(sampleName);
                }
                
                // Show overlay reason
                const reason = message.reason || message.data?.reason;
                if (reason) {
                    const badge = message.badge || message.data?.badge || '🎵';
                    this.updateTimeSeriesStatus(`${badge} ${reason}`, 'streaming');
                }
                break;
                
            case 'progress_init':
                this.initTimeSeriesProgress(message.data.total_periods);
                break;
                
            case 'progress_update':
                this.updateTimeSeriesProgress(message.data.current_period);
                break;
                
            case 'period_start':
                const period = message.data;
                this.updateTimeSeriesTrackInfo(
                    `Period: ${period.period_label}`,
                    `Rank: ${period.metrics.avg_rank.toFixed(1)} | Clicks: ${period.metrics.click_total} | Top 3: ${period.metrics.top3_count}`
                );
                
                // Update tempo and key info
                this.updateTimeSeriesStatus(
                    `Playing ${period.period_label} - Tempo: ${period.tempo} BPM, Transpose: ${period.transpose > 0 ? '+' : ''}${period.transpose}`,
                    'streaming'
                );
                break;
                

                
            case 'timeseries_complete':
                const summary = message.data.summary;
                this.updateTimeSeriesTrackInfo(
                    'Time Series Complete!',
                    `${summary.periods_played} periods | Total click change: ${summary.total_click_change > 0 ? '+' : ''}${summary.total_click_change}`
                );
                
                this.updateTimeSeriesStatus(
                    `Journey complete: ${summary.baseline_period} → ${summary.final_period}`,
                    'connected'
                );
                
                // Reset progress
                setTimeout(() => {
                    this.resetTimeSeriesProgress();
                }, 3000);
                break;
                
            case 'error':
                this.showError(message.data.message);
                break;
        }
    }
    
    displayPeriodSummary(summary) {
        const summaryDiv = document.getElementById('periodSummary');
        const gridDiv = document.getElementById('periodsGrid');
        
        // Clear previous content
        gridDiv.innerHTML = '';
        
        // Create period cards
        summary.period_labels.forEach((label, index) => {
            const card = document.createElement('div');
            card.className = 'period-card';
            
            const avgRank = summary.metrics_preview.avg_ranks[index];
            const clickTotal = summary.metrics_preview.click_totals[index];
            const top3Count = summary.metrics_preview.top3_counts[index];
            
            card.innerHTML = `
                <div class="period-label">${label}</div>
                <div class="period-metrics">
                    <div>Avg Rank: ${avgRank}</div>
                    <div>Clicks: ${clickTotal}</div>
                    <div>Top 3: ${top3Count}</div>
                </div>
            `;
            
            gridDiv.appendChild(card);
        });
        
        summaryDiv.style.display = 'block';
    }
    
    initTimeSeriesProgress(totalPeriods) {
        const progressContainer = document.getElementById('timeseriesProgress');
        const totalSpan = document.getElementById('totalPeriods');
        const currentSpan = document.getElementById('currentPeriod');
        const progressFill = document.getElementById('timeseriesProgressFill');
        
        totalSpan.textContent = totalPeriods;
        currentSpan.textContent = '0';
        progressFill.style.width = '0%';
        progressContainer.style.display = 'block';
    }
    
    updateTimeSeriesProgress(currentPeriod) {
        const currentSpan = document.getElementById('currentPeriod');
        const totalSpan = document.getElementById('totalPeriods');
        const progressFill = document.getElementById('timeseriesProgressFill');
        
        const total = parseInt(totalSpan.textContent);
        const percentage = (currentPeriod / total) * 100;
        
        currentSpan.textContent = currentPeriod;
        progressFill.style.width = percentage + '%';
    }
    
    resetTimeSeriesProgress() {
        const progressContainer = document.getElementById('timeseriesProgress');
        progressContainer.style.display = 'none';
    }
    
    startTimeSeriesVisualization() {
        const canvas = document.getElementById('timeseriesViz');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        const animate = () => {
            this.drawTimeSeriesVisualizer(ctx, canvas);
            if (this.isTimeSeriesPlaying) {
                this.timeSeriesAnimationFrame = requestAnimationFrame(animate);
            }
        };
        animate();
    }
    
    stopTimeSeriesVisualization() {
        if (this.timeSeriesAnimationFrame) {
            cancelAnimationFrame(this.timeSeriesAnimationFrame);
        }
    }
    
    drawTimeSeriesVisualizer(ctx, canvas) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Create a simple waveform visualization
        const centerY = canvas.height / 2;
        const barWidth = canvas.width / 32;
        
        ctx.fillStyle = '#32ff7e';
        
        for (let i = 0; i < 32; i++) {
            const x = i * barWidth;
            const height = Math.random() * (canvas.height * 0.6);
            const y = centerY - height / 2;
            
            ctx.fillRect(x, y, barWidth - 2, height);
        }
    }
    
    animateTimeSeriesVisualizer(tempo, transpose) {
        // Visual feedback for tempo and key changes
        console.log(`Time series visual: tempo=${tempo}, transpose=${transpose}`);
    }
    
    setTimeSeriesLoading(loading) {
        const btn = document.getElementById('timeseriesUploadBtn');
        const btnText = btn.querySelector('.btn-text');
        const btnLoading = btn.querySelector('.btn-loading');
        
        btn.disabled = loading;
        btnText.style.display = loading ? 'none' : 'inline';
        btnLoading.style.display = loading ? 'inline' : 'none';
    }
    
    updateTimeSeriesStatus(text, type) {
        const status = document.getElementById('timeseriesStatus');
        const statusText = status.querySelector('.status-text');
        
        statusText.textContent = text;
        status.className = `status ${type}`;
    }
    
    updateTimeSeriesTrackInfo(title, artist) {
        const trackTitle = document.querySelector('#timeseriesNowPlaying .track-title');
        const trackArtist = document.querySelector('#timeseriesNowPlaying .track-artist');
        
        if (trackTitle) trackTitle.textContent = title;
        if (trackArtist) trackArtist.textContent = artist;
    }

    // Add loudness monitoring for production validation
    validateLoudness() {
        if (!this.masterLimiter || !this.masterLimiter.volume) return;
        
        // Simple peak monitoring (would use proper LUFS metering in production)
        const currentLevel = this.masterLimiter.volume.value;
        if (currentLevel > -6) {
            console.warn(`Audio level high: ${currentLevel}dB - consider reducing input gain`);
        }
        
        // Target: -14 LUFS integrated for streaming/upload compatibility
        // This is a simplified check - production would use Web Audio API meters
    }
    
    // Audio test function for debugging
    testBass() {
        console.log('🎸 Testing bass synth...');
        if (this.bass) {
            console.log('🎵 Playing Jump bass sequence: C2-C3-G2-C3');
            this.bass.triggerAttackRelease("C2", "4n");
            setTimeout(() => this.bass.triggerAttackRelease("C3", "4n"), 500);
            setTimeout(() => this.bass.triggerAttackRelease("G2", "4n"), 1000);
            setTimeout(() => this.bass.triggerAttackRelease("C3", "4n"), 1500);
        } else {
            console.error('❌ Bass synth not initialized');
        }
    }
    
    // Test the time series motif handling
    testTimeSeriesMotif() {
        console.log('🎸 Testing time series motif...');
        
        // Simulate motif message from backend
        const testMessage = {
            type: 'motif',
            tempo: 125,
            transpose: 3,
            period: 'test_period'
        };
        
        this.handleTimeSeriesMessage(testMessage);
        
        setTimeout(() => {
            console.log('🔄 Testing second motif...');
            testMessage.tempo = 130;
            testMessage.transpose = -2;
            this.handleTimeSeriesMessage(testMessage);
        }, 3000);
    }
}

// Tab switching function
function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.style.display = 'none';
        tab.classList.remove('active');
    });
    
    // Remove active class from all tab buttons
    document.querySelectorAll('.tab').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    const targetTab = document.getElementById(tabName + '-container');
    if (targetTab) {
        targetTab.style.display = 'block';
        targetTab.classList.add('active');
    }
    
    // Activate corresponding tab button
    const targetBtn = document.getElementById('tab-' + tabName);
    if (targetBtn) {
        targetBtn.classList.add('active');
    }
}

// Screenshot function
function takeScreenshot() {
    // Use html2canvas if available, otherwise show message
    if (typeof html2canvas !== 'undefined') {
        html2canvas(document.querySelector('.scorecard')).then(canvas => {
            const link = document.createElement('a');
            link.download = 'serp-radio-scorecard.png';
            link.href = canvas.toDataURL();
            link.click();
        });
    } else {
        alert('Screenshot feature requires html2canvas library. Use browser\'s built-in screenshot instead.');
    }
}

// Initialize player when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.serpRadio = new SERPRadioPlayer();
    console.log('🎵 SERP Loop Radio Player initialized with Van Halen time series support');
    console.log('🎸 Test bass with: window.serpRadio.testBass()');
    console.log('🎼 Test time series motif with: window.serpRadio.testTimeSeriesMotif()');
});

// Global functions for backward compatibility
function startStream() { window.serpRadio?.startStream(); }
function stopStream() { window.serpRadio?.stopStream(); }
function replayRecap() { window.serpRadio?.replayRecap(); }
