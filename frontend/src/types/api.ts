export interface PaymentRequest {
  customerId: string;
  amount: number;
  currency: string;
  payeeId: string;
  idempotencyKey: string;
}

export interface AgentTraceStep {
  step: string;
  detail: string;
}

export interface PaymentDecisionResponse {
  id: number;
  decision: 'allow' | 'review' | 'block';
  reasons: string[];
  user_display: string[];
  agentTrace: AgentTraceStep[];
  requestId: string;
  customerId: string;
  maskedCustomerId: string;
  payeeId: string;
  amount: number;
  latency: number;
  createdAt: string;
}

export interface DecisionListItem {
  id: number;
  decision: 'allow' | 'review' | 'block';
  amount: number;
  currency: string;
  customerId: string; // masked
  maskedCustomerId?: string;
  payeeId: string;
  createdAt: string;
  requestId: string;
  reasons: string[];
  agentTrace: { step: string; detail: string }[];
}

export interface RecentDecisionsResponse {
  decisions: DecisionListItem[];
}

export interface ApiError {
  detail: string;
}
