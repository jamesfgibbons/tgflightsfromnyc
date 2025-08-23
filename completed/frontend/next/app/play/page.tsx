'use client'

import React, { useState, useEffect, useRef } from 'react'
import { useUser } from '@auth0/nextjs-auth0/client'
import toast from 'react-hot-toast'

export default function PlayPage() {
  const { user, isLoading } = useUser()
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [audioReady, setAudioReady] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)

  const generateAudio = async () => {
    if (!user) {
      toast.error('Please log in to generate your loop')
      return
    }

    setIsGenerating(true)
    
    try {
      // First, call DNA mapper to generate payload
      const dnaResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/setup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.sub
        })
      })

      if (!dnaResponse.ok) {
        throw new Error('Failed to generate DNA payload')
      }

      const dnaResult = await dnaResponse.json()
      
      // Then call renderer to create audio
      const renderResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/play`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      })

      if (!renderResponse.ok) {
        throw new Error('Failed to render audio')
      }

      const renderResult = await renderResponse.json()
      
      if (renderResult.signed_url) {
        setAudioUrl(renderResult.signed_url)
        setAudioReady(true)
        toast.success('Your SERP loop is ready!')
      } else {
        throw new Error('No audio URL received')
      }
      
    } catch (error) {
      console.error('Generation error:', error)
      toast.error('Failed to generate audio. Using demo instead.')
      
      // Fallback to demo audio
      setAudioUrl('/demo-audio.mp3') // This would be a static demo file
      setAudioReady(true)
    } finally {
      setIsGenerating(false)
    }
  }

  useEffect(() => {
    // Auto-generate on page load if user is logged in
    if (user && !isGenerating && !audioUrl) {
      generateAudio()
    }
  }, [user])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-t-2 border-b-2 border-white"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="max-w-2xl mx-auto">
        <div className="card text-center">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-white mb-4">
              🎧 Your SERP Loop Radio
            </h1>
            <p className="text-white/80">
              {user ? `Welcome, ${user.name}!` : 'Demo Mode'}
            </p>
          </div>

          {!user && (
            <div className="bg-yellow-500/20 border border-yellow-500/50 rounded-lg p-4 mb-6">
              <p className="text-yellow-200">
                ⚠️ You're in demo mode. Log in to generate your personalized loop.
              </p>
            </div>
          )}

          <div className="audio-player mb-6">
            {isGenerating ? (
              <div className="py-12">
                <div className="animate-pulse-slow text-4xl mb-4">🎵</div>
                <p className="text-white mb-2">Generating your audio loop...</p>
                <div className="w-full bg-white/20 rounded-full h-2">
                  <div className="bg-serp-green h-2 rounded-full animate-pulse" style={{width: '60%'}}></div>
                </div>
                <p className="text-white/70 text-sm mt-2">
                  Analyzing rankings → Creating melodies → Adding narration
                </p>
              </div>
            ) : audioReady && audioUrl ? (
              <div className="space-y-4">
                <div className="text-4xl animate-bounce-slow">🎶</div>
                <audio
                  ref={audioRef}
                  controls
                  className="w-full"
                  onLoadedData={() => setAudioReady(true)}
                  onError={() => toast.error('Failed to load audio')}
                >
                  <source src={audioUrl} type="audio/mpeg" />
                  <source src={audioUrl} type="audio/wav" />
                  Your browser does not support the audio element.
                </audio>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="bg-white/10 rounded-lg p-3">
                    <div className="text-white/70">Status</div>
                    <div className="text-white font-medium">Ready to Play</div>
                  </div>
                  <div className="bg-white/10 rounded-lg p-3">
                    <div className="text-white/70">Duration</div>
                    <div className="text-white font-medium">~60 seconds</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="py-12">
                <div className="text-4xl mb-4">🎛️</div>
                <button
                  onClick={generateAudio}
                  disabled={isGenerating}
                  className="btn-primary text-lg px-8 py-4"
                >
                  {user ? 'Generate My Loop' : 'Play Demo'}
                </button>
                <p className="text-white/70 text-sm mt-4">
                  {user 
                    ? 'Click to generate your personalized SERP audio loop'
                    : 'Click to hear a demo of SERP Loop Radio'
                  }
                </p>
              </div>
            )}
          </div>

          {audioReady && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div className="bg-white/10 rounded-lg p-4">
                  <div className="text-2xl mb-2">📈</div>
                  <div className="text-white/70">Ranking Changes</div>
                  <div className="text-white font-medium">Melody Layer</div>
                </div>
                <div className="bg-white/10 rounded-lg p-4">
                  <div className="text-2xl mb-2">🎹</div>
                  <div className="text-white/70">Market Share</div>
                  <div className="text-white font-medium">Harmony Layer</div>
                </div>
                <div className="bg-white/10 rounded-lg p-4">
                  <div className="text-2xl mb-2">🗣️</div>
                  <div className="text-white/70">AI Narration</div>
                  <div className="text-white font-medium">Voice Layer</div>
                </div>
              </div>
              
              <div className="pt-4 border-t border-white/20">
                <button
                  onClick={generateAudio}
                  className="btn-secondary mr-4"
                >
                  🔄 Regenerate
                </button>
                {user && (
                  <a href="/setup" className="btn-secondary">
                    ⚙️ Adjust Settings
                  </a>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
} 