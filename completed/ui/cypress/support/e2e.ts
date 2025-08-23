/// <reference types="cypress" />

// Custom commands for SERP Radio testing
Cypress.Commands.add('startAudio', () => {
  cy.get('[data-testid="start-audio-btn"]').click()
  cy.get('[data-testid="connection-status"]', { timeout: 10000 })
    .should('contain.text', 'Connected')
})

Cypress.Commands.add('selectStation', (station: string) => {
  cy.get(`[data-testid="station-${station}"]`).click()
  cy.get(`[data-testid="station-${station}"]`).should('have.class', 'active')
})

Cypress.Commands.add('waitForEvents', (minEvents: number = 1) => {
  cy.get('[data-testid="event-counter"]', { timeout: 30000 })
    .should('not.contain.text', '0')
    .invoke('text')
    .then((text) => {
      const eventCount = parseInt(text.match(/\d+/)?.[0] || '0')
      expect(eventCount).to.be.at.least(minEvents)
    })
})

// Add custom command types
declare global {
  namespace Cypress {
    interface Chainable {
      startAudio(): Chainable<void>
      selectStation(station: string): Chainable<void>
      waitForEvents(minEvents?: number): Chainable<void>
    }
  }
}

// Suppress expected console warnings
Cypress.on('window:before:load', (win) => {
  // Suppress Web Audio API warnings
  const originalConsoleWarn = win.console.warn
  win.console.warn = (...args: any[]) => {
    if (args[0] && typeof args[0] === 'string' && args[0].includes('Web Audio API')) {
      return
    }
    originalConsoleWarn.apply(win.console, args)
  }
}) 