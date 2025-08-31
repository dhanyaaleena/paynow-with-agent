import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import DecisionDrawer from '../DecisionDrawer'
import { useDecisionStore } from '../../store/decisionStore'

// Mock the store
jest.mock('../../store/decisionStore')

const mockDecision = {
  id: 1,
  decision: 'review' as const,
  amount: 1500.50,
  currency: 'USD',
  customerId: 'c_123',
  maskedCustomerId: 'c_***123',
  payeeId: 'p_789',
  createdAt: '2025-08-29T15:30:00.000Z',
  requestId: 'req_abc123',
  reasons: ['recent_disputes', 'amount_above_daily_threshold'],
  agentTrace: [
    { step: 'plan', detail: 'Check balance, risk, and limits' },
    { step: 'tool:getBalance', detail: 'balance=1000.00' },
    { step: 'tool:getRiskSignals', detail: 'recent_disputes=2, device_change=False' },
    { step: 'tool:recommend', detail: 'route to manual review' }
  ],
  latency: 0.123,
}

describe('DecisionDrawer', () => {
  const mockCloseDrawer = jest.fn()
  const mockSelectDecision = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    ;(useDecisionStore as unknown as jest.Mock).mockReturnValue({
      selectedDecision: mockDecision,
      isDrawerOpen: true,
      closeDrawer: mockCloseDrawer,
      selectDecision: mockSelectDecision,
    })
  })

  it('renders drawer when open with decision data', () => {
    render(<DecisionDrawer />)
    
    // Check that the drawer is visible
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Decision Details')).toBeInTheDocument()
    
    // Check decision information is displayed
    expect(screen.getByText('REVIEW')).toBeInTheDocument()
    expect(screen.getByText('₹1,500.50')).toBeInTheDocument()
    // Removed USD check since currency is now always INR and not displayed
    expect(screen.getByText('c_***123')).toBeInTheDocument()
    expect(screen.getByText('p_789')).toBeInTheDocument()
  })

  it('shows collapsible sections with proper accessibility', () => {
    render(<DecisionDrawer />)
    
    // Check that collapsible sections exist
    const reasonsSection = screen.getByRole('button', { name: 'Reasons' })
    const agentTraceSection = screen.getByRole('button', { name: 'Agent Trace' })
    
    expect(reasonsSection).toBeInTheDocument()
    expect(agentTraceSection).toBeInTheDocument()
    
    // Check ARIA attributes
    expect(reasonsSection).toHaveAttribute('aria-expanded', 'true')
    expect(agentTraceSection).toHaveAttribute('aria-expanded', 'false')
  })

  it('expands and collapses sections when clicked', () => {
    render(<DecisionDrawer />)
    
    const agentTraceSection = screen.getByRole('button', { name: 'Agent Trace' })
    
    // Initially collapsed - check ARIA attribute
    expect(agentTraceSection).toHaveAttribute('aria-expanded', 'false')
    
    // Click to expand
    fireEvent.click(agentTraceSection)
    expect(agentTraceSection).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Check balance, risk, and limits')).toBeInTheDocument()
    
    // Click to collapse
    fireEvent.click(agentTraceSection)
    expect(agentTraceSection).toHaveAttribute('aria-expanded', 'false')
    
    // Check that the content is no longer visible by looking for the step text
    expect(screen.queryByText('plan')).not.toBeInTheDocument()
  })

  it('displays reasons correctly', () => {
    render(<DecisionDrawer />)
    
    // Reasons section should be open by default
    expect(screen.getByText('recent_disputes')).toBeInTheDocument()
    expect(screen.getByText('amount_above_daily_threshold')).toBeInTheDocument()
  })

  it('displays agent trace steps correctly', () => {
    render(<DecisionDrawer />)
    
    // Open agent trace section
    fireEvent.click(screen.getByRole('button', { name: 'Agent Trace' }))
    
    // Check all steps are displayed
    expect(screen.getByText('plan')).toBeInTheDocument()
    expect(screen.getByText('Check balance, risk, and limits')).toBeInTheDocument()
    expect(screen.getByText('tool:getBalance')).toBeInTheDocument()
    expect(screen.getByText('balance=1000.00')).toBeInTheDocument()
    expect(screen.getByText('tool:getRiskSignals')).toBeInTheDocument()
    expect(screen.getByText('recent_disputes=2, device_change=False')).toBeInTheDocument()
    expect(screen.getByText('tool:recommend')).toBeInTheDocument()
    expect(screen.getByText('route to manual review')).toBeInTheDocument()
  })

  it('handles close button correctly', () => {
    render(<DecisionDrawer />)
    
    const closeButton = screen.getByRole('button', { name: /close panel/i })
    fireEvent.click(closeButton)
    
    expect(mockCloseDrawer).toHaveBeenCalledTimes(1)
  })

  it('handles keyboard navigation for close button', () => {
    render(<DecisionDrawer />)
    
    const closeButton = screen.getByRole('button', { name: /close panel/i })
    
    // Focus should be on close button initially
    closeButton.focus()
    expect(closeButton).toHaveFocus()
    
    // Enter key should close drawer
    fireEvent.keyDown(closeButton, { key: 'Enter' })
    expect(mockCloseDrawer).toHaveBeenCalledTimes(1)
  })

  it('does not render when no decision is selected', () => {
    ;(useDecisionStore as unknown as jest.Mock).mockReturnValue({
      selectedDecision: null,
      isDrawerOpen: false,
      closeDrawer: mockCloseDrawer,
      selectDecision: mockSelectDecision,
    })
    
    const { container } = render(<DecisionDrawer />)
    expect(container.firstChild).toBeNull()
  })

  it('handles empty reasons and agent trace gracefully', () => {
    const decisionWithNoData = {
      ...mockDecision,
      reasons: [],
      agentTrace: []
    }
    
    ;(useDecisionStore as unknown as jest.Mock).mockReturnValue({
      selectedDecision: decisionWithNoData,
      isDrawerOpen: true,
      closeDrawer: mockCloseDrawer,
      selectDecision: mockSelectDecision,
    })
    
    render(<DecisionDrawer />)
    
    // Check that appropriate messages are shown
    expect(screen.getByText('No reasons provided')).toBeInTheDocument()
    
    // Agent Trace section is collapsed by default, so we need to open it to see the message
    const agentTraceSection = screen.getByRole('button', { name: 'Agent Trace' })
    fireEvent.click(agentTraceSection)
    expect(screen.getByText('No agent trace available')).toBeInTheDocument()
  })
})
