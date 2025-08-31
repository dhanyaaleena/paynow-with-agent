'use client';

import { useState } from 'react';
import { useDecisionStore } from '../store/decisionStore';
import { submitPaymentDecision, generateIdempotencyKey, getRecentDecisions, generateRequestId } from '../services/api';
import { ApiError } from '../services/api';

export default function PaymentForm() {
  const {
    formData,
    updateFormData,
    setLatency,
    setLoading,
    setError,
    resetForm,
    addRecentDecision,
  } = useDecisionStore();

  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validation
    if (!formData.customerId.trim()) {
      setError('Customer ID is required');
      return;
    }
    
    if (formData.amount <= 0) {
      setError('Amount must be greater than 0');
      return;
    }
    
    if (!formData.payeeId.trim()) {
      setError('Payee ID is required');
      return;
    }

    setIsSubmitting(true);
    setLoading(true);
    setError(null);

    try {
      // Generate unique idempotency key if not provided
      const paymentData = {
        ...formData,
        idempotencyKey: formData.idempotencyKey || generateIdempotencyKey(),
        currency: 'INR', 
      };
      const requestId = generateRequestId();
      const start = performance.now();
      const decision = await submitPaymentDecision(paymentData, requestId);
      const latency = typeof decision.latency === 'number' ? Math.round(decision.latency * 1000) : undefined;
      if (typeof latency === 'number') setLatency(requestId, latency);
      // Optimistically add to recent decisions table
      addRecentDecision({
        ...decision,
        latency,
        // fallback for maskedCustomerId if not present
        customerId: decision.maskedCustomerId || decision.customerId,
        createdAt: decision.createdAt,
      });
      resetForm();
    } catch (error) {
      if (error instanceof ApiError) {
        setError(`Error ${error.status}: ${error.message}`);
      } else {
        setError('An unexpected error occurred');
      }
    } finally {
      setIsSubmitting(false);
      setLoading(false);
    }
  };

  const handleInputChange = (field: keyof typeof formData, value: string | number) => {
    updateFormData(field, value);
    setError(null); // Clear error when user types
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold text-gray-900 mb-6">
        Submit Payment
      </h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="customerId" className="block text-sm font-medium text-gray-700 mb-1">
            Customer ID *
          </label>
          <input
            type="text"
            id="customerId"
            value={formData.customerId}
            onChange={(e) => handleInputChange('customerId', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-black"
            placeholder="e.g., c_123"
            required
            aria-describedby="customerId-help"
          />
          <p id="customerId-help" className="mt-1 text-sm text-gray-500">
            Enter the customer identifier
          </p>
        </div>

        <div>
          <label htmlFor="amount" className="block text-sm font-medium text-gray-700 mb-1">
            Amount (INR) *
          </label>
          <input
            type="number"
            id="amount"
            value={formData.amount || ''}
            onChange={(e) => handleInputChange('amount', parseFloat(e.target.value) || 0)}
            step="0.01"
            min="0.01"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-black"
            placeholder="0.00"
            required
            aria-describedby="amount-help"
          />
          <p id="amount-help" className="mt-1 text-sm text-gray-500">
            Enter the payment amount in Rupees (must be greater than 0)
          </p>
        </div>

        <input type="hidden" name="currency" value="INR" />

        <div>
          <label htmlFor="payeeId" className="block text-sm font-medium text-gray-700 mb-1">
            Payee ID *
          </label>
          <input
            type="text"
            id="payeeId"
            value={formData.payeeId}
            onChange={(e) => handleInputChange('payeeId', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-black"
            placeholder="e.g., p_789"
            required
            aria-describedby="payeeId-help"
          />
          <p id="payeeId-help" className="mt-1 text-sm text-gray-500">
            Enter the payee identifier
          </p>
        </div>

        <div>
          <label htmlFor="idempotencyKey" className="block text-sm font-medium text-gray-700 mb-1">
            Idempotency Key
          </label>
          <input
            type="text"
            id="idempotencyKey"
            value={formData.idempotencyKey}
            onChange={(e) => handleInputChange('idempotencyKey', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-black"
            placeholder="Leave empty for auto-generation"
            aria-describedby="idempotencyKey-help"
          />
          <p id="idempotencyKey-help" className="mt-1 text-sm text-gray-500">
            Optional: Provide a unique key to prevent duplicate submissions
          </p>
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-describedby="submit-help"
        >
          {isSubmitting ? 'Submitting...' : 'Submit'}
        </button>
        
        <p id="submit-help" className="text-sm text-gray-500 text-center">
          The AI agent will analyze the payment and provide a decision
        </p>
      </form>
    </div>
  );
}
