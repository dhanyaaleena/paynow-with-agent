import { PaymentRequest, PaymentDecisionResponse, RecentDecisionsResponse } from '../types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || 'test-api-key';

const headers = {
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY,
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

export function generateRequestId(): string {
  // Simple random hex string, 16 chars
  return 'req_' + Array.from(crypto.getRandomValues(new Uint8Array(8)))
    .map(b => b.toString(16).padStart(2, '0')).join('');
}

export async function submitPaymentDecision(
  payment: PaymentRequest,
  requestId: string
): Promise<PaymentDecisionResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/decide`, {
      method: 'POST',
      headers: {
        ...headers,
        'X-Request-Id': requestId,
      },
      body: JSON.stringify(payment),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new ApiError(response.status, errorData.detail || 'Failed to submit payment');
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(500, 'Network error occurred');
  }
}

export async function getRecentDecisions(): Promise<RecentDecisionsResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/decide`, {
      method: 'GET',
      headers,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new ApiError(response.status, errorData.detail || 'Failed to fetch decisions');
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(500, 'Network error occurred');
  }
}

// Utility function to generate unique idempotency keys
export function generateIdempotencyKey(): string {
  return `frontend_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}
