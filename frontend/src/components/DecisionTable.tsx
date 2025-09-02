'use client';

import React, { useEffect, useMemo } from 'react';
import { useDecisionStore } from '../store/decisionStore';
import { getRecentDecisions } from '../services/api';
import { DecisionListItem } from '../types/api';
import { 
  CheckCircleIcon, 
  ExclamationTriangleIcon, 
  XCircleIcon,
  ClockIcon 
} from '@heroicons/react/24/outline';

// Performance optimization: Memoized row component
const DecisionTableRow = React.memo(({ 
  decision, 
  onRowClick, 
  rowLatencyGetter, 
  formatDate, 
  formatAmount
}: { 
  decision: DecisionListItem; 
  onRowClick: (decision: DecisionListItem) => void;
  rowLatencyGetter: (requestId: string) => number | undefined;
  formatDate: (dateString: string) => string;
  formatAmount: (amount: number, currency: string) => string;
}) => {
  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case 'allow':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
      case 'review':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />;
      case 'block':
        return <XCircleIcon className="h-5 w-5 text-red-500" />;
      default:
        return <ClockIcon className="h-5 w-5 text-gray-400" />;
    }
  };

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'allow':
        return 'bg-green-100 text-green-800';
      case 'review':
        return 'bg-yellow-100 text-yellow-800';
      case 'block':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <tr 
      className="hover:bg-gray-50 cursor-pointer transition-colors"
      onClick={() => onRowClick(decision)}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onRowClick(decision);
        }
      }}
      role="button"
      aria-label={`View details for ${decision.decision} decision of ${formatAmount(decision.amount, decision.currency)}`}
    >
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center">
          {getDecisionIcon(decision.decision)}
          <span className={`ml-2 inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getDecisionColor(decision.decision)}`}>
            {decision.decision}
          </span>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
        {formatAmount(decision.amount, decision.currency)}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {decision.customerId}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {typeof rowLatencyGetter(decision.requestId) === 'number' ? rowLatencyGetter(decision.requestId) : '-'}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {formatDate(decision.createdAt)}
      </td>
    </tr>
  );
});

DecisionTableRow.displayName = 'DecisionTableRow';

export default function DecisionTable() {
  const {
    recentDecisions,
    setRecentDecisions,
    setLoading,
    setError,
    selectDecision,
    openDrawer,
    getLatency,
  } = useDecisionStore();

  // Fetch recent decisions on component mount
  useEffect(() => {
    const fetchDecisions = async () => {
      try {
        setLoading(true);
        const response = await getRecentDecisions();
        setRecentDecisions(response.decisions);
      } catch (error) {
        setError('Failed to fetch recent decisions');
        console.error('Error fetching decisions:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDecisions();
  }, [setRecentDecisions, setLoading, setError]);

  const handleRowClick = (decision: DecisionListItem) => {
    selectDecision(decision);
    openDrawer();
  };

  // Performance optimization: Memoize sorted decisions
  const sortedDecisions = useMemo(() => {
    return [...recentDecisions].sort((a, b) => 
      new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );
  }, [recentDecisions]);

  if (recentDecisions.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="text-center py-12">
          <ClockIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">No decisions yet</h3>
          <p className="mt-1 text-sm text-gray-500">
            Submit a payment decision to see it appear here.
          </p>
        </div>
      </div>
    );
  }

  const formatAmount = (amount: number, currency: string) => {
    // Always show as Indian Rupees
    return `₹${amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDate = (dateString: string) => {
    const value = new Date(dateString).toLocaleString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    });
    return value;
  };

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-medium text-gray-900">
          Recent Decisions ({recentDecisions.length})
        </h2>
        <p className="text-sm text-gray-500">
          Click on any row to view detailed information
        </p>
      </div>
      
      <div className="overflow-x-auto overflow-y-auto max-h-96 min-h-[520px]">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Decision
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Amount
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Customer ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Latency (ms)
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Timestamp
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {sortedDecisions.map((decision) => (
              <DecisionTableRow
                key={decision.id}
                decision={decision}
                onRowClick={handleRowClick}
                rowLatencyGetter={getLatency}
                formatDate={formatDate}
                formatAmount={formatAmount}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
