import { act } from 'react';
import { useDecisionStore } from './decisionStore';

describe('decisionStore', () => {
  it('addRecentDecision adds a decision to recentDecisions', () => {
    const store = useDecisionStore.getState();
    const decision = {
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
    };
    act(() => {
      store.addRecentDecision(decision);
    });
    expect(useDecisionStore.getState().recentDecisions[0]).toEqual(decision);
  });

  it('setError updates error state', () => {
    const store = useDecisionStore.getState();
    act(() => {
      store.setError('Test error');
    });
    expect(useDecisionStore.getState().error).toBe('Test error');
  });
});
