/**
 * Musical SERP Loop Radio Player with Van Halen "Jump" Motif
 * Streamlined design support
 * Uses Tone.js for real-time audio synthesis and musical effects
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
            const keyName = this.getKeyName(this.currentMotif.transpose);
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

    setVolume(volume) {
        if (Tone && Tone.Destination) {
            Tone.Destination.volume.value = Tone.gainToDb(volume / 100);
        }
    }
    
    updateMotif(motifData) {
        this.currentMotif = { ...this.currentMotif, ...motifData };
        
        if (motifData.tempo) Tone.Transport.bpm.rampTo(motifData.tempo, 0.2);
        if (motifData.cutoff) this.filter.frequency.rampTo(motifData.cutoff, 0.3);
        
        const keyName = this.getKeyName(motifData.transpose);
        updatePlayerUI('motif', { ...motifData, key_name: keyName });
        
        if (motifData.ai_steal) this.showNotification('🤖 AI Overview Alert!', 'warning');
        if (motifData.minor) this.showNotification('⚠️ Competitor Threat!', 'danger');
    }

    getKeyName(transpose) {
        const keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
        return keys[(transpose % 12 + 12) % 12];
    }
    
    playMusicalNote(noteData) {
        if (!this.synth) return;
        
        const { note, duration, velocity, pan, overlay, filter_sweep, transpose, badge, domain, index, total } = noteData;
        const finalTranspose = (transpose || 0) + this.currentMotif.transpose;
        const transposedNote = Tone.Frequency(note).transpose(finalTranspose);
        
        if (pan !== undefined) this.synth.set({ pan: pan });
        
        if (filter_sweep) {
            this.filter.frequency.rampTo(1200, 0.1);
            setTimeout(() => this.filter.frequency.rampTo(this.currentMotif.cutoff, 0.5), 200);
        }
        
        this.synth.triggerAttackRelease(transposedNote, duration || "8n", undefined, (velocity || 80) / 127);
        if (overlay) this.playOverlay(overlay);
        
        updatePlayerUI('note', noteData);
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
                return; // Use different synth
            case 'cash_register':
                 effectsSynth.set({ oscillator: { type: "square" }, envelope: { attack: 0.01, decay: 0.1, sustain: 0.1, release: 0.2 } });
                 effectsSynth.triggerAttackRelease("G4", "32n");
                 setTimeout(() => effectsSynth.triggerAttackRelease("C5", "32n"), 50);
                break;
        }
        setTimeout(() => effectsSynth.dispose(), 1000);
    }
    
    playOverture(league) {
        this.showNotification('🎼 Playing Scorecard Overture...', 'info');
        league.forEach((item, index) => {
            setTimeout(() => {
                const chordNotes = this.getChord(item.note, item.chord_type);
                this.synth.set({ pan: item.pan });
                this.synth.triggerAttackRelease(chordNotes, item.duration || "2n", undefined, (item.velocity || 60) / 127);
                this.showNotification(`${item.is_client ? '🏆' : '🎵'} ${item.domain}: ${item.share}% share`, item.is_client ? 'success' : 'info');
            }, index * 800);
        });
    }

    getChord(rootNote, type = 'major') {
        const baseFreq = Tone.Frequency(rootNote);
        const third = type === 'major' ? baseFreq.transpose(4) : baseFreq.transpose(3);
        const fifth = baseFreq.transpose(7);
        return [rootNote, third, fifth];
    }
    
    handleWebSocketMessage(event) {
        const msg = JSON.parse(event.data);
        switch (msg.type) {
            case 'motif_init':
                console.log('🎸 Motif initialized:', msg.data);
                updatePlayerUI('client_domain', this.clientDomain);
                this.startMotif();
                break;
            case 'motif':
                this.updateMotif(msg);
                break;
            case 'musical_note':
                this.playMusicalNote(msg.data);
                break;
            case 'overture_chord': // Assuming server sends one chord at a time
                 this.playOverture([msg.data]);
                 break;
            case 'recap_insights':
                updatePlayerUI('recap', msg.data);
                break;
            case 'complete':
                this.showNotification('🎵 Musical stream complete!', 'success');
                updatePlayerUI('complete');
                break;
            default:
                console.log('Unhandled message type:', msg.type);
        }
    }
    
    connect(sessionId, skin = 'arena_rock', domain = '') {
        this.initializeAudio();
        this.clientDomain = domain;
        const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/serp?session_id=${sessionId}&skin=${skin}`;
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => this.showNotification('🎵 Connected to Musical SERP Radio', 'success');
        this.ws.onmessage = (event) => this.handleWebSocketMessage(event);
        this.ws.onclose = () => {
            this.showNotification('🎵 Disconnected', 'info');
            this.stopMotif();
            updatePlayerUI('disconnect');
        };
        this.ws.onerror = (error) => this.showNotification('WebSocket connection failed', 'error');
    }
    
    disconnect() {
        if (this.ws) this.ws.close();
        this.stopMotif();
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);
    }

    async testAudio() {
        await this.initializeAudio();
        const testSynth = new Tone.Synth().toDestination();
        const pattern = ['C3', 'C3', 'G2', 'C3'];
        pattern.forEach((note, index) => {
            setTimeout(() => testSynth.triggerAttackRelease(note, '8n'), index * 200);
        });
        setTimeout(() => testSynth.dispose(), 1000);
        this.showNotification('🎸 Audio test successful!', 'success');
    }
}

// Global instance
window.musicalPlayer = new MusicalSerpPlayer(); 