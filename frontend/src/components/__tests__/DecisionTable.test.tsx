import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import DecisionTable from '../DecisionTable';
import { useDecisionStore } from '../../store/decisionStore';

jest.mock('../../store/decisionStore');

describe('DecisionTable', () => {
  it('renders empty state when no decisions', () => {
    (useDecisionStore as unknown as jest.Mock).mockReturnValue({
      recentDecisions: [],
      setRecentDecisions: jest.fn(),
      setLoading: jest.fn(),
      setError: jest.fn(),
      selectDecision: jest.fn(),
      openDrawer: jest.fn(),
      getLatency: jest.fn(),
    });
    render(<DecisionTable />);
    expect(screen.getByText(/No decisions yet/i)).toBeInTheDocument();
  });

  it('renders a row and handles click', () => {
    const selectDecision = jest.fn();
    const openDrawer = jest.fn();
    (useDecisionStore as unknown as jest.Mock).mockReturnValue({
      recentDecisions: [{
        id: 1,
        decision: 'allow',
        amount: 100,
        currency: 'INR',
        customerId: 'c_***234',
        payeeId: 'p_789',
        createdAt: new Date().toISOString(),
        requestId: 'req_1',
        reasons: [],
        agentTrace: [],
      }],
      setRecentDecisions: jest.fn(),
      setLoading: jest.fn(),
      setError: jest.fn(),
      selectDecision,
      openDrawer,
      getLatency: () => 123,
    });
    render(<DecisionTable />);
    const row = screen.getByRole('button', { name: /View details/i });
    fireEvent.click(row);
    expect(selectDecision).toHaveBeenCalled();
    expect(openDrawer).toHaveBeenCalled();
  });
});
