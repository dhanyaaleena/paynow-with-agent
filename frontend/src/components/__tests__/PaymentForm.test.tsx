import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import PaymentForm from '../PaymentForm';
import { useDecisionStore } from '../../store/decisionStore';

jest.mock('../../store/decisionStore');

const mockStore = {
  formData: { customerId: '', amount: 0, currency: 'INR', payeeId: '', idempotencyKey: '' },
  updateFormData: jest.fn(),
  setLatency: jest.fn(),
  setLoading: jest.fn(),
  setError: jest.fn(),
  resetForm: jest.fn(),
  addRecentDecision: jest.fn(),
  error: null,
};

describe('PaymentForm', () => {
  beforeEach(() => {
    (useDecisionStore as unknown as jest.Mock).mockReturnValue({ ...mockStore });
    jest.clearAllMocks();
  });

  it('renders all form fields', () => {
    render(<PaymentForm />);
    expect(screen.getByLabelText(/Customer ID/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Amount/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Payee ID/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Idempotency Key/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit/i })).toBeInTheDocument();
  });

  it('shows error if required fields are empty and submit is clicked', () => {
    (useDecisionStore as unknown as jest.Mock).mockReturnValue({ ...mockStore, error: 'Customer ID is required' });
    render(<PaymentForm />);
    expect(screen.getByRole('alert')).toHaveTextContent('Customer ID is required');
  });
});
