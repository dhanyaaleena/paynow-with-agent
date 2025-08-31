import { create } from 'zustand';
import { PaymentRequest, PaymentDecisionResponse, DecisionListItem } from '../types/api';

const LATENCY_MAP_KEY = 'latencyMap';

function loadLatencyMap(): Record<string, number> {
  if (typeof window === 'undefined') return {};
  try {
    const raw = localStorage.getItem(LATENCY_MAP_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveLatencyMap(map: Record<string, number>) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(LATENCY_MAP_KEY, JSON.stringify(map));
  } catch {}
}

interface DecisionState {
  // Form data
  formData: PaymentRequest;

  // Recent decisions for table
  recentDecisions: DecisionListItem[];

  // Latency map: requestId -> latencyMs
  latencyMap: Record<string, number>;

  // UI state
  isLoading: boolean;
  error: string | null;
  selectedDecision: DecisionListItem | null;
  isDrawerOpen: boolean;

  // Actions
  updateFormData: (field: keyof PaymentRequest, value: string | number) => void;
  setRecentDecisions: (decisions: DecisionListItem[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  selectDecision: (decision: DecisionListItem | null) => void;
  openDrawer: () => void;
  closeDrawer: () => void;
  resetForm: () => void;
  setLatency: (requestId: string, latencyMs: number) => void;
  getLatency: (requestId: string) => number | undefined;
  addRecentDecision: (decision: any) => void;
}

const initialFormData: PaymentRequest = {
  customerId: '',
  amount: 0,
  currency: 'INR',
  payeeId: '',
  idempotencyKey: '',
};

export const useDecisionStore = create<DecisionState>((set, get) => ({
  // Initial state
  formData: initialFormData,
  recentDecisions: [],
  latencyMap: typeof window !== 'undefined' ? loadLatencyMap() : {},
  isLoading: false,
  error: null,
  selectedDecision: null,
  isDrawerOpen: false,

  // Actions
  updateFormData: (field, value) =>
    set((state) => ({
      formData: { ...state.formData, [field]: value }
    })),

  setRecentDecisions: (decisions) =>
    set({ recentDecisions: decisions }),

  setLoading: (loading) =>
    set({ isLoading: loading }),

  setError: (error) =>
    set({ error }),

  selectDecision: (decision) =>
    set({ selectedDecision: decision }),

  openDrawer: () =>
    set({ isDrawerOpen: true }),

  closeDrawer: () =>
    set({ isDrawerOpen: false }),

  resetForm: () =>
    set({
      formData: initialFormData,
      error: null
    }),

  setLatency: (requestId, latencyMs) => {
    set((state) => {
      const newMap = { ...state.latencyMap, [requestId]: latencyMs };
      saveLatencyMap(newMap);
      return { latencyMap: newMap };
    });
  },

  getLatency: (requestId) => get().latencyMap[requestId],

  addRecentDecision: (decision) =>
    set((state) => ({
      recentDecisions: [decision, ...state.recentDecisions].slice(0, 20)
    })),
}));
