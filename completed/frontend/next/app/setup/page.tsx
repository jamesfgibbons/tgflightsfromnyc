'use client'

import React, { useState } from 'react'
import { useUser } from '@auth0/nextjs-auth0/client'
import { useRouter } from 'next/navigation'
import toast from 'react-hot-toast'

interface SetupState {
  ambience: 'lofi' | 'synthwave' | 'jazz' | null
  narrationDensity: number
  keywordsFile: File | null
}

export default function SetupPage() {
  const { user, isLoading } = useUser()
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState(1)
  const [setup, setSetup] = useState<SetupState>({
    ambience: null,
    narrationDensity: 0.5,
    keywordsFile: null
  })

  const handleAmbienceSelect = (ambience: 'lofi' | 'synthwave' | 'jazz') => {
    setSetup(prev => ({ ...prev, ambience }))
  }

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file && file.type === 'text/csv') {
      setSetup(prev => ({ ...prev, keywordsFile: file }))
    } else {
      toast.error('Please upload a CSV file')
    }
  }

  const handleComplete = async () => {
    if (!user) {
      toast.error('Please log in to complete setup')
      return
    }

    try {
      const formData = new FormData()
      formData.append('user_id', user.sub || '')
      formData.append('ambience', setup.ambience || 'lofi')
      formData.append('narration_density', setup.narrationDensity.toString())
      
      if (setup.keywordsFile) {
        formData.append('keywords_file', setup.keywordsFile)
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/setup`, {
        method: 'POST',
        body: formData
      })

      if (response.ok) {
        toast.success('Setup completed successfully!')
        router.push('/play')
      } else {
        throw new Error('Setup failed')
      }
    } catch (error) {
      toast.error('Failed to complete setup. Please try again.')
      console.error('Setup error:', error)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-t-2 border-b-2 border-white"></div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="card text-center">
          <h1 className="text-2xl font-bold text-white mb-4">
            Please log in to set up your SERP Loop
          </h1>
          <a href="/api/auth/login" className="btn-primary">
            Log In
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="max-w-2xl mx-auto">
        <div className="card">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-white mb-2">
              Setup Your SERP Loop
            </h1>
            <div className="flex items-center space-x-2 mb-4">
              {[1, 2, 3].map((step) => (
                <div
                  key={step}
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    currentStep >= step
                      ? 'bg-serp-green text-white'
                      : 'bg-white/20 text-white/60'
                  }`}
                >
                  {step}
                </div>
              ))}
            </div>
            <p className="text-white/70">
              Step {currentStep} of 3: {
                currentStep === 1 ? 'Choose Your Ambience' :
                currentStep === 2 ? 'Set Narration Density' :
                'Upload Keywords File'
              }
            </p>
          </div>

          {currentStep === 1 && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-white mb-4">
                Choose Your Musical Ambience
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {[
                  { id: 'lofi', name: 'Lo-Fi', emoji: '🎵', desc: 'Chill, relaxed vibes' },
                  { id: 'synthwave', name: 'Synthwave', emoji: '🌆', desc: 'Retro electronic energy' },
                  { id: 'jazz', name: 'Jazz', emoji: '🎷', desc: 'Smooth, sophisticated tones' }
                ].map((option) => (
                  <button
                    key={option.id}
                    onClick={() => handleAmbienceSelect(option.id as any)}
                    className={`p-4 rounded-lg border-2 transition-all ${
                      setup.ambience === option.id
                        ? 'border-serp-green bg-serp-green/20'
                        : 'border-white/30 bg-white/10 hover:border-white/50'
                    }`}
                  >
                    <div className="text-3xl mb-2">{option.emoji}</div>
                    <h3 className="text-white font-medium">{option.name}</h3>
                    <p className="text-white/70 text-sm">{option.desc}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-white mb-4">
                Set Narration Density
              </h2>
              <div className="space-y-4">
                <div className="flex items-center justify-between text-white">
                  <span>Minimal</span>
                  <span>Current: {Math.round(setup.narrationDensity * 100)}%</span>
                  <span>Maximum</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={setup.narrationDensity}
                  onChange={(e) => setSetup(prev => ({ 
                    ...prev, 
                    narrationDensity: parseFloat(e.target.value) 
                  }))}
                  className="w-full h-2 bg-white/20 rounded-lg appearance-none cursor-pointer slider"
                />
                <div className="text-white/70 text-sm">
                  {setup.narrationDensity < 0.3
                    ? 'Only major ranking changes will be narrated'
                    : setup.narrationDensity < 0.7
                    ? 'Moderate narration for significant changes'
                    : 'Detailed narration for most ranking movements'
                  }
                </div>
              </div>
            </div>
          )}

          {currentStep === 3 && (
            <div className="space-y-6">
              <h2 className="text-xl font-semibold text-white mb-4">
                Upload Keywords File
              </h2>
              <div className="border-2 border-dashed border-white/30 rounded-lg p-8 text-center">
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="file-upload"
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  <div className="text-4xl mb-4">📁</div>
                  <p className="text-white mb-2">
                    {setup.keywordsFile ? setup.keywordsFile.name : 'Click to upload CSV file'}
                  </p>
                  <p className="text-white/70 text-sm">
                    CSV should contain: keyword, current_rank, previous_rank, market_share_pct
                  </p>
                </label>
              </div>
              {setup.keywordsFile && (
                <div className="bg-serp-green/20 border border-serp-green/50 rounded-lg p-4">
                  <p className="text-serp-green font-medium">
                    ✓ File uploaded successfully
                  </p>
                </div>
              )}
            </div>
          )}

          <div className="flex justify-between mt-8">
            <button
              onClick={() => setCurrentStep(Math.max(1, currentStep - 1))}
              disabled={currentStep === 1}
              className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              ← Previous
            </button>
            
            {currentStep < 3 ? (
              <button
                onClick={() => setCurrentStep(currentStep + 1)}
                disabled={
                  (currentStep === 1 && !setup.ambience) ||
                  (currentStep === 2 && setup.narrationDensity === null)
                }
                className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next →
              </button>
            ) : (
              <button
                onClick={handleComplete}
                disabled={!setup.keywordsFile}
                className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Complete Setup ✨
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
} 