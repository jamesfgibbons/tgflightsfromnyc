import React from 'react'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { UserProvider } from '@auth0/nextjs-auth0/client'
import { Toaster } from 'react-hot-toast'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'SERP Loop Radio',
  description: 'Personalized audio loops from your search ranking data',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <UserProvider>
        <body className={inter.className}>
          <div className="min-h-screen bg-gradient-to-br from-serp-blue to-serp-purple">
            <nav className="bg-white/10 backdrop-blur-md border-b border-white/20">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                  <div className="flex items-center">
                    <h1 className="text-xl font-bold text-white">
                      🎵 SERP Loop Radio
                    </h1>
                  </div>
                  <div className="flex items-center space-x-4">
                    <a
                      href="/api/auth/login"
                      className="text-white hover:text-gray-200 px-3 py-2 rounded-md text-sm font-medium"
                    >
                      Login
                    </a>
                    <a
                      href="/api/auth/logout"
                      className="text-white hover:text-gray-200 px-3 py-2 rounded-md text-sm font-medium"
                    >
                      Logout
                    </a>
                  </div>
                </div>
              </div>
            </nav>
            <main className="flex-1">
              {children}
            </main>
          </div>
          <Toaster position="top-right" />
        </body>
      </UserProvider>
    </html>
  )
} 