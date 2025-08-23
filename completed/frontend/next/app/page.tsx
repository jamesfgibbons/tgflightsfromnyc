import React from 'react'
import { useUser } from '@auth0/nextjs-auth0/client'
import Link from 'next/link'

export default function HomePage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="max-w-4xl mx-auto text-center">
        <div className="card">
          <div className="mb-8">
            <h1 className="text-5xl font-bold text-white mb-4">
              🎵 SERP Loop Radio
            </h1>
            <p className="text-xl text-white/80 mb-8">
              Transform your search ranking data into personalized audio experiences
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            <div className="card">
              <div className="text-center">
                <div className="text-4xl mb-4">📊</div>
                <h3 className="text-xl font-semibold text-white mb-2">
                  Data-Driven Music
                </h3>
                <p className="text-white/70">
                  Your ranking changes become melodies, market share drives rhythm, 
                  and competition creates tension in your personalized audio loop.
                </p>
              </div>
            </div>
            
            <div className="card">
              <div className="text-center">
                <div className="text-4xl mb-4">🎧</div>
                <h3 className="text-xl font-semibold text-white mb-2">
                  Real-time Narration
                </h3>
                <p className="text-white/70">
                  Significant ranking changes are narrated with AI-generated voice,
                  keeping you informed while you listen.
                </p>
              </div>
            </div>
          </div>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Link href="/setup" className="btn-primary text-lg px-8 py-4">
              🎛️ Setup Your Loop
            </Link>
            <Link href="/play" className="btn-secondary text-lg px-8 py-4">
              ▶️ Play Demo
            </Link>
          </div>
          
          <div className="mt-8 pt-6 border-t border-white/20">
            <p className="text-white/60 text-sm">
              Connect your search ranking data via CSV upload or API integration.
              <br />
              Powered by Snowflake, AWS, and OpenAI.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
} 