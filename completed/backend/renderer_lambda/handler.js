const { S3Client, GetObjectCommand, PutObjectCommand } = require('@aws-sdk/client-s3');
const { getSignedUrl } = require('@aws-sdk/s3-request-presigner');
const OpenAI = require('openai');
const ffmpeg = require('fluent-ffmpeg');
const ffmpegInstaller = require('@ffmpeg-installer/ffmpeg');
const fs = require('fs');
const path = require('path');
const tmp = require('tmp');
const { v4: uuidv4 } = require('uuid');

// Configure FFmpeg
ffmpeg.setFfmpegPath(ffmpegInstaller.path);

// Initialize AWS and OpenAI clients
const s3Client = new S3Client({ region: process.env.AWS_REGION || 'us-east-1' });
const openai = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY
});

const handler = async (event, context) => {
    console.log('Renderer Lambda triggered:', JSON.stringify(event, null, 2));
    
    try {
        const { user_id, payload_key, generate_hls = true } = extractEventData(event);
        
        if (!user_id) {
            return createErrorResponse(400, 'User ID is required');
        }
        
        // Read payload from S3 or use demo data
        let audioPayload;
        if (payload_key) {
            audioPayload = await readPayloadFromS3(payload_key);
        } else {
            audioPayload = generateDemoPayload(user_id);
        }
        
        if (!audioPayload) {
            return createErrorResponse(404, 'Audio payload not found');
        }
        
        // Generate audio stems for each layer
        const audioStems = await generateAudioStems(audioPayload);
        
        // Generate TTS narration for significant events
        const narrationStem = await generateNarration(audioPayload.narrative_events);
        
        // Mix all stems together
        const mixedAudio = await mixAudioStems([...audioStems, narrationStem].filter(Boolean));
        
        // Convert to HLS if requested
        let outputUrl;
        if (generate_hls) {
            outputUrl = await convertToHLS(mixedAudio, user_id);
        } else {
            outputUrl = await uploadRawAudio(mixedAudio, user_id);
        }
        
        // Generate signed URL for playback
        const signedUrl = await generateSignedUrl(outputUrl);
        
        return createSuccessResponse({
            user_id,
            output_url: outputUrl,
            signed_url: signedUrl,
            duration: audioPayload.global_parameters.total_duration,
            timestamp: new Date().toISOString()
        });
        
    } catch (error) {
        console.error('Renderer error:', error);
        return createErrorResponse(500, `Internal server error: ${error.message}`);
    }
};

function extractEventData(event) {
    // API Gateway event
    if (event.requestContext) {
        const queryParams = event.queryStringParameters || {};
        const body = event.body ? JSON.parse(event.body) : {};
        
        return {
            user_id: queryParams.user_id || body.user_id,
            payload_key: queryParams.payload_key || body.payload_key,
            generate_hls: queryParams.generate_hls !== 'false'
        };
    }
    
    // Direct invocation
    return {
        user_id: event.user_id,
        payload_key: event.payload_key,
        generate_hls: event.generate_hls !== false
    };
}

async function readPayloadFromS3(payloadKey) {
    try {
        const bucket = process.env.S3_BUCKET_OUTPUT;
        const response = await s3Client.send(new GetObjectCommand({
            Bucket: bucket,
            Key: payloadKey
        }));
        
        const payloadData = await streamToString(response.Body);
        return JSON.parse(payloadData);
    } catch (error) {
        console.error('Error reading payload from S3:', error);
        return null;
    }
}

function generateDemoPayload(userId) {
    return {
        user_id: userId,
        timestamp: new Date().toISOString(),
        composition_layers: {
            lead_melody: {
                active: true,
                instrument: 'synth_lead',
                tempo: 130,
                intensity: 0.8,
                volume: 0.8,
                records: [
                    { KEYWORD: 'sustainable fashion', RANK_DELTA: -5, CURRENT_RANK: 3 }
                ]
            },
            harmony: {
                active: true,
                instrument: 'electric_piano',
                tempo: 125,
                intensity: 0.6,
                volume: 0.6,
                records: []
            },
            rhythm: {
                active: true,
                instrument: 'acoustic_guitar',
                tempo: 120,
                intensity: 0.5,
                volume: 0.7,
                records: []
            },
            bass: {
                active: true,
                instrument: 'bass_synth',
                tempo: 120,
                intensity: 0.4,
                volume: 0.9,
                records: []
            }
        },
        global_parameters: {
            overall_tempo: 125,
            key_signature: 'C_major',
            total_duration: 60,
            fade_in: 2,
            fade_out: 3
        },
        narrative_events: [
            {
                timestamp: 15,
                type: 'ranking_change',
                keyword: 'sustainable fashion',
                rank_delta: -5,
                current_rank: 3,
                tts_priority: 'high'
            }
        ]
    };
}

async function generateAudioStems(payload) {
    const stems = [];
    const tempDir = tmp.dirSync({ unsafeCleanup: true });
    
    try {
        for (const [layerName, layerConfig] of Object.entries(payload.composition_layers)) {
            if (!layerConfig.active) continue;
            
            console.log(`Generating ${layerName} stem...`);
            
            // Generate audio using Riffusion-lite
            const audioBuffer = await generateRiffusionLite(layerConfig, payload.global_parameters);
            
            // Save to temporary file
            const stemPath = path.join(tempDir.name, `${layerName}.wav`);
            fs.writeFileSync(stemPath, audioBuffer);
            
            stems.push({
                name: layerName,
                path: stemPath,
                volume: layerConfig.volume || 0.5
            });
        }
        
        return stems;
    } catch (error) {
        console.error('Error generating audio stems:', error);
        throw error;
    }
}

async function generateRiffusionLite(layerConfig, globalParams) {
    // Minimal Riffusion-lite implementation - generates simple sine tones
    const sampleRate = 44100;
    const duration = globalParams.total_duration || 60;
    const tempo = layerConfig.tempo || 120;
    const intensity = layerConfig.intensity || 0.5;
    
    // Calculate frequency based on instrument and tempo
    const baseFreq = getInstrumentFrequency(layerConfig.instrument);
    const tempoMultiplier = tempo / 120; // Normalize to 120 BPM
    const frequency = baseFreq * tempoMultiplier;
    
    // Generate sine wave audio buffer
    const numSamples = Math.floor(sampleRate * duration);
    const buffer = Buffer.alloc(numSamples * 2); // 16-bit samples
    
    for (let i = 0; i < numSamples; i++) {
        // Create a simple melody with some variation
        const t = i / sampleRate;
        const notePhase = (t * tempo / 60) % 1; // Note timing based on tempo
        const melodyFreq = frequency * (1 + 0.1 * Math.sin(notePhase * Math.PI * 2));
        
        // Add some harmonic content
        const fundamental = Math.sin(2 * Math.PI * melodyFreq * t);
        const harmonic = 0.3 * Math.sin(2 * Math.PI * melodyFreq * 2 * t);
        const subHarmonic = 0.2 * Math.sin(2 * Math.PI * melodyFreq * 0.5 * t);
        
        // Apply intensity and create stereo
        const amplitude = intensity * 0.3 * (0.8 + 0.2 * Math.sin(t * 0.5)); // Slow amplitude modulation
        const sample = Math.floor((fundamental + harmonic + subHarmonic) * amplitude * 32767);
        
        // Write 16-bit PCM samples (stereo)
        buffer.writeInt16LE(Math.max(-32768, Math.min(32767, sample)), i * 2);
    }
    
    // Add WAV header
    return createWAVBuffer(buffer, sampleRate, 1); // Mono for now
}

function getInstrumentFrequency(instrument) {
    const frequencies = {
        'synth_lead': 440,      // A4
        'electric_piano': 261.63, // C4
        'acoustic_guitar': 196,  // G3
        'bass_synth': 82.41,     // E2
        'synth_pad': 329.63      // E4
    };
    
    return frequencies[instrument] || 440;
}

function createWAVBuffer(audioData, sampleRate, channels) {
    const byteRate = sampleRate * channels * 2; // 16-bit
    const blockAlign = channels * 2;
    const dataSize = audioData.length;
    const fileSize = 36 + dataSize;
    
    const header = Buffer.alloc(44);
    
    // RIFF header
    header.write('RIFF', 0);
    header.writeUInt32LE(fileSize, 4);
    header.write('WAVE', 8);
    
    // fmt chunk
    header.write('fmt ', 12);
    header.writeUInt32LE(16, 16); // chunk size
    header.writeUInt16LE(1, 20);  // PCM format
    header.writeUInt16LE(channels, 22);
    header.writeUInt32LE(sampleRate, 24);
    header.writeUInt32LE(byteRate, 28);
    header.writeUInt16LE(blockAlign, 32);
    header.writeUInt16LE(16, 34); // bits per sample
    
    // data chunk
    header.write('data', 36);
    header.writeUInt32LE(dataSize, 40);
    
    return Buffer.concat([header, audioData]);
}

async function generateNarration(narrativeEvents) {
    if (!narrativeEvents || narrativeEvents.length === 0) {
        return null;
    }
    
    try {
        const tempDir = tmp.dirSync({ unsafeCleanup: true });
        const narrationSegments = [];
        
        for (const event of narrativeEvents.slice(0, 3)) { // Limit to 3 events
            if (event.tts_priority === 'high') {
                const text = createNarrationText(event);
                console.log(`Generating TTS for: ${text}`);
                
                // Generate TTS using OpenAI
                const mp3Response = await openai.audio.speech.create({
                    model: 'tts-1',
                    voice: 'nova',
                    input: text,
                    speed: 1.0
                });
                
                const mp3Buffer = Buffer.from(await mp3Response.arrayBuffer());
                const mp3Path = path.join(tempDir.name, `narration_${event.timestamp}.mp3`);
                fs.writeFileSync(mp3Path, mp3Buffer);
                
                narrationSegments.push({
                    path: mp3Path,
                    timestamp: event.timestamp
                });
            }
        }
        
        if (narrationSegments.length === 0) {
            return null;
        }
        
        // Combine narration segments
        const combinedPath = path.join(tempDir.name, 'narration_combined.wav');
        await combineNarrationSegments(narrationSegments, combinedPath, 60);
        
        return {
            name: 'narration',
            path: combinedPath,
            volume: 0.8
        };
        
    } catch (error) {
        console.error('Error generating narration:', error);
        return null; // Continue without narration if TTS fails
    }
}

function createNarrationText(event) {
    const { keyword, rank_delta, current_rank } = event;
    
    if (rank_delta > 0) {
        return `${keyword} dropped ${rank_delta} positions to rank ${current_rank}`;
    } else if (rank_delta < 0) {
        return `${keyword} climbed ${Math.abs(rank_delta)} positions to rank ${current_rank}`;
    } else {
        return `${keyword} maintains position at rank ${current_rank}`;
    }
}

async function combineNarrationSegments(segments, outputPath, totalDuration) {
    return new Promise((resolve, reject) => {
        let command = ffmpeg();
        
        // Add silence as base track
        command = command.input(`anullsrc=channel_layout=stereo:sample_rate=44100`);
        command = command.inputOptions([`-t ${totalDuration}`]);
        
        // Add narration segments at specific timestamps
        segments.forEach(segment => {
            command = command.input(segment.path);
        });
        
        // Build filter complex for mixing at specific times
        let filterComplex = '[0:a]';
        segments.forEach((segment, index) => {
            const inputIndex = index + 1;
            filterComplex += `[${inputIndex}:a]adelay=${segment.timestamp}s|${segment.timestamp}s[delayed${index}];`;
        });
        
        // Mix all delayed segments
        filterComplex += '[0:a]';
        segments.forEach((_, index) => {
            filterComplex += `[delayed${index}]`;
        });
        filterComplex += `amix=inputs=${segments.length + 1}:duration=first:dropout_transition=2[out]`;
        
        command
            .complexFilter(filterComplex)
            .map('[out]')
            .output(outputPath)
            .on('end', resolve)
            .on('error', reject)
            .run();
    });
}

async function mixAudioStems(stems) {
    if (stems.length === 0) {
        throw new Error('No audio stems to mix');
    }
    
    const tempDir = tmp.dirSync({ unsafeCleanup: true });
    const mixedPath = path.join(tempDir.name, 'mixed_audio.wav');
    
    return new Promise((resolve, reject) => {
        let command = ffmpeg();
        
        // Add all stem inputs
        stems.forEach(stem => {
            command = command.input(stem.path);
        });
        
        // Build filter for mixing with volume controls
        let filterComplex = '';
        stems.forEach((stem, index) => {
            filterComplex += `[${index}:a]volume=${stem.volume}[vol${index}];`;
        });
        
        // Mix all volume-adjusted streams
        filterComplex += stems.map((_, index) => `[vol${index}]`).join('');
        filterComplex += `amix=inputs=${stems.length}:duration=longest:dropout_transition=2[out]`;
        
        command
            .complexFilter(filterComplex)
            .map('[out]')
            .audioCodec('pcm_s16le')
            .audioChannels(2)
            .audioFrequency(44100)
            .output(mixedPath)
            .on('end', () => resolve(mixedPath))
            .on('error', reject)
            .run();
    });
}

async function convertToHLS(audioPath, userId) {
    const tempDir = tmp.dirSync({ unsafeCleanup: true });
    const hlsDir = path.join(tempDir.name, 'hls');
    fs.mkdirSync(hlsDir);
    
    const playlistPath = path.join(hlsDir, 'index.m3u8');
    
    return new Promise(async (resolve, reject) => {
        ffmpeg(audioPath)
            .audioCodec('aac')
            .audioBitrate('128k')
            .format('hls')
            .outputOptions([
                '-hls_time 10',           // 10-second segments
                '-hls_list_size 0',       // Keep all segments
                '-hls_flags single_file'  // Single file mode
            ])
            .output(playlistPath)
            .on('end', async () => {
                try {
                    // Upload HLS files to S3
                    const s3Key = await uploadHLSToS3(hlsDir, userId);
                    resolve(s3Key);
                } catch (error) {
                    reject(error);
                }
            })
            .on('error', reject)
            .run();
    });
}

async function uploadHLSToS3(hlsDir, userId) {
    const bucket = process.env.S3_BUCKET_OUTPUT;
    const timestamp = Date.now();
    const baseKey = `hls/${userId}/${timestamp}`;
    
    // Upload all HLS files
    const files = fs.readdirSync(hlsDir);
    
    for (const file of files) {
        const filePath = path.join(hlsDir, file);
        const fileContent = fs.readFileSync(filePath);
        const s3Key = `${baseKey}/${file}`;
        
        await s3Client.send(new PutObjectCommand({
            Bucket: bucket,
            Key: s3Key,
            Body: fileContent,
            ContentType: file.endsWith('.m3u8') ? 'application/vnd.apple.mpegurl' : 'audio/aac'
        }));
    }
    
    return `${baseKey}/index.m3u8`;
}

async function uploadRawAudio(audioPath, userId) {
    const bucket = process.env.S3_BUCKET_OUTPUT;
    const timestamp = Date.now();
    const s3Key = `audio/${userId}/${timestamp}.wav`;
    
    const audioContent = fs.readFileSync(audioPath);
    
    await s3Client.send(new PutObjectCommand({
        Bucket: bucket,
        Key: s3Key,
        Body: audioContent,
        ContentType: 'audio/wav'
    }));
    
    return s3Key;
}

async function generateSignedUrl(s3Key) {
    const bucket = process.env.S3_BUCKET_OUTPUT;
    const cloudFrontDomain = process.env.CLOUDFRONT_DOMAIN;
    
    if (cloudFrontDomain) {
        // Return CloudFront URL for better performance
        return `https://${cloudFrontDomain}/${s3Key}`;
    } else {
        // Generate signed S3 URL
        const command = new GetObjectCommand({
            Bucket: bucket,
            Key: s3Key
        });
        
        return await getSignedUrl(s3Client, command, { expiresIn: 3600 });
    }
}

async function streamToString(stream) {
    const chunks = [];
    return new Promise((resolve, reject) => {
        stream.on('data', chunk => chunks.push(chunk));
        stream.on('error', reject);
        stream.on('end', () => resolve(Buffer.concat(chunks).toString('utf-8')));
    });
}

function createSuccessResponse(data) {
    return {
        statusCode: 200,
        headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        body: JSON.stringify(data)
    };
}

function createErrorResponse(statusCode, message) {
    return {
        statusCode,
        headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        body: JSON.stringify({ error: message })
    };
}

module.exports = { handler }; 