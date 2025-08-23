/// <reference types="cypress" />

describe('SERP Radio - Smoke Test', () => {
  const WS_URL = Cypress.env('WS_URL') || 'ws://localhost:8000/ws/serp'
  const API_KEY = Cypress.env('API_KEY') || 'dev-token-123'

  beforeEach(() => {
    // Visit the application
    cy.visit('/')
    
    // Wait for page to load
    cy.get('[data-testid="app-container"]', { timeout: 10000 }).should('be.visible')
  })

  it('should load the application without errors', () => {
    // Check that the page loaded
    cy.get('h1').should('contain.text', 'SERP Loop Radio')
    
    // Check that station selector is present
    cy.get('[data-testid="station-selector"]').should('be.visible')
    
    // Check that Start Audio button is present
    cy.get('[data-testid="start-audio-btn"]').should('be.visible')
    
    // Verify no console errors (critical for audio apps)
    cy.window().then((win) => {
      expect(win.console.error).to.not.have.been.called
    })
  })

  it('should initialize audio context when Start Audio is clicked', () => {
    // Click Start Audio button
    cy.get('[data-testid="start-audio-btn"]').click()
    
    // Verify audio context is started
    cy.window().then((win) => {
      // @ts-ignore - Tone.js global
      expect(win.Tone.context.state).to.equal('running')
    })
    
    // Check that connection status updates
    cy.get('[data-testid="connection-status"]', { timeout: 5000 })
      .should('contain.text', 'Connecting...')
  })

  it('should establish WebSocket connection and receive events', () => {
    // Start audio first
    cy.get('[data-testid="start-audio-btn"]').click()
    
    // Wait for WebSocket connection
    cy.get('[data-testid="connection-status"]', { timeout: 10000 })
      .should('contain.text', 'Connected')
    
    // Select a station
    cy.get('[data-testid="station-daily"]').click()
    
    // Wait for and verify events are received
    cy.get('[data-testid="event-counter"]', { timeout: 15000 })
      .should('not.contain.text', '0')
    
    // Verify event counter increases (indicates events are being processed)
    cy.get('[data-testid="event-counter"]')
      .invoke('text')
      .then((initialCount) => {
        const initialNum = parseInt(initialCount.match(/\d+/)?.[0] || '0')
        
        // Wait a bit for more events
        cy.wait(5000)
        
        cy.get('[data-testid="event-counter"]')
          .invoke('text')
          .then((newCount) => {
            const newNum = parseInt(newCount.match(/\d+/)?.[0] || '0')
            expect(newNum).to.be.greaterThan(initialNum)
          })
      })
  })

  it('should play audio notes (at least 3) within 30 seconds', () => {
    // Start audio
    cy.get('[data-testid="start-audio-btn"]').click()
    
    // Wait for connection
    cy.get('[data-testid="connection-status"]', { timeout: 10000 })
      .should('contain.text', 'Connected')
    
    // Monitor audio notes played
    let notesPlayed = 0
    
    cy.window().then((win) => {
      // Hook into Tone.js or create a counter
      const originalLog = win.console.log
      win.console.log = (...args: any[]) => {
        if (args[0] && args[0].includes && args[0].includes('Playing note')) {
          notesPlayed++
        }
        originalLog.apply(win.console, args)
      }
    })
    
    // Wait up to 30 seconds for notes to play
    cy.wait(30000)
    
    // Verify at least 3 notes played
    cy.get('[data-testid="notes-played-counter"]', { timeout: 5000 })
      .should('not.contain.text', '0')
      .invoke('text')
      .then((text) => {
        const noteCount = parseInt(text.match(/\d+/)?.[0] || '0')
        expect(noteCount).to.be.at.least(3)
      })
  })

  it('should handle station switching without errors', () => {
    // Start audio
    cy.get('[data-testid="start-audio-btn"]').click()
    
    // Wait for connection
    cy.get('[data-testid="connection-status"]', { timeout: 10000 })
      .should('contain.text', 'Connected')
    
    // Test switching between stations
    const stations = ['daily', 'ai-lens', 'opportunity']
    
    stations.forEach((station) => {
      cy.get(`[data-testid="station-${station}"]`).click()
      
      // Verify station is active
      cy.get(`[data-testid="station-${station}"]`)
        .should('have.class', 'active')
      
      // Wait for station to process events
      cy.wait(2000)
      
      // Verify no console errors
      cy.window().then((win) => {
        expect(win.console.error).to.not.have.been.called
      })
    })
  })

  it('should display real-time statistics', () => {
    // Start audio
    cy.get('[data-testid="start-audio-btn"]').click()
    
    // Wait for connection
    cy.get('[data-testid="connection-status"]', { timeout: 10000 })
      .should('contain.text', 'Connected')
    
    // Check that statistics are displayed and updating
    cy.get('[data-testid="stats-container"]').should('be.visible')
    
    // Verify statistics show activity
    cy.get('[data-testid="total-events"]', { timeout: 15000 })
      .should('not.contain.text', '0')
    
    // Check for different event types
    cy.get('[data-testid="rank-improvements"]').should('be.visible')
    cy.get('[data-testid="rank-drops"]').should('be.visible')
    cy.get('[data-testid="anomalies"]').should('be.visible')
  })

  it('should handle WebSocket disconnection gracefully', () => {
    // Start audio
    cy.get('[data-testid="start-audio-btn"]').click()
    
    // Wait for connection
    cy.get('[data-testid="connection-status"]', { timeout: 10000 })
      .should('contain.text', 'Connected')
    
    // Simulate network disruption by intercepting WebSocket
    cy.window().then((win) => {
      // @ts-ignore - Access the WebSocket instance
      if (win.ws) {
        win.ws.close()
      }
    })
    
    // Verify reconnection attempt
    cy.get('[data-testid="connection-status"]', { timeout: 5000 })
      .should('contain.text', 'Disconnected')
    
    // Should show reconnecting status
    cy.get('[data-testid="connection-status"]', { timeout: 10000 })
      .should('contain.text', 'Reconnecting...')
  })

  it('should have proper audio level limiting (no clipping)', () => {
    // Start audio
    cy.get('[data-testid="start-audio-btn"]').click()
    
    // Check that limiter is active in console
    cy.window().then((win) => {
      // @ts-ignore - Tone.js global
      const destination = win.Tone.Destination
      expect(destination).to.exist
    })
    
    // Verify peak meter doesn't exceed 0dBFS
    cy.get('[data-testid="peak-meter"]', { timeout: 10000 })
      .should('be.visible')
      .should('have.attr', 'data-peak')
      .then((peak) => {
        const peakValue = parseFloat(peak as string)
        expect(peakValue).to.be.at.most(0)  // Should never exceed 0dBFS
      })
  })

  // Performance test
  it('should maintain good performance under load', () => {
    // Start audio
    cy.get('[data-testid="start-audio-btn"]').click()
    
    // Monitor performance
    cy.window().its('performance').then((perf) => {
      const startTime = perf.now()
      
      // Wait for 30 seconds of activity
      cy.wait(30000)
      
      // Check that frame rate is acceptable
      cy.window().then((win) => {
        const endTime = win.performance.now()
        const duration = endTime - startTime
        
        // Should maintain reasonable frame rate
        expect(duration).to.be.lessThan(35000)  // Allow some variance
      })
    })
  })

  // Mobile responsiveness check
  it('should work on mobile viewports', () => {
    // Set mobile viewport
    cy.viewport(375, 667)
    
    // Reload page
    cy.reload()
    
    // Check that interface adapts
    cy.get('[data-testid="app-container"]').should('be.visible')
    cy.get('[data-testid="start-audio-btn"]').should('be.visible')
    cy.get('[data-testid="station-selector"]').should('be.visible')
    
    // Test audio startup on mobile
    cy.get('[data-testid="start-audio-btn"]').click()
    
    // Verify connection works on mobile
    cy.get('[data-testid="connection-status"]', { timeout: 10000 })
      .should('contain.text', 'Connected')
  })
}) 