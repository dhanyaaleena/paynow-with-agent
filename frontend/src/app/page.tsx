'use client';

import { useEffect } from 'react';
import { useDecisionStore } from '../store/decisionStore';
import PaymentForm from '../components/PaymentForm';
import DecisionDrawer from '../components/DecisionDrawer';
import DecisionTable from '../components/DecisionTable';
import { 
  CheckCircleIcon, 
  ExclamationTriangleIcon, 
  XCircleIcon,
  InformationCircleIcon 
} from '@heroicons/react/24/outline';

export default function Home() {
  const { 
    error, 
    isLoading, 
    setError 
  } = useDecisionStore();

  // Clear error after 5 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error, setError]);

  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case 'allow':
        return <CheckCircleIcon className="h-8 w-8 text-green-500" />;
      case 'review':
        return <ExclamationTriangleIcon className="h-8 w-8 text-yellow-500" />;
      case 'block':
        return <XCircleIcon className="h-8 w-8 text-red-500" />;
      default:
        return <InformationCircleIcon className="h-8 w-8 text-gray-400" />;
    }
  };

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'allow':
        return 'bg-green-50 border-green-200 text-green-800';
      case 'review':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800';
      case 'block':
        return 'bg-red-50 border-red-200 text-red-800';
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Agent Decision Viewer
              </h1>
              <p className="mt-2 text-sm text-gray-600">
                AI-powered payment decision system with real-time analysis
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column - Payment Form */}
          <div className="space-y-6">
            <PaymentForm />
          </div>

          {/* Right Column - Decision Table */}
          <div>
            <DecisionTable />
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="fixed bottom-4 right-4 max-w-sm w-full bg-red-50 border border-red-200 rounded-lg shadow-lg p-4">
            <div className="flex items-start space-x-3">
              <XCircleIcon className="h-5 w-5 text-red-400 mt-0.5" />
              <div className="flex-1">
                <h4 className="text-sm font-medium text-red-800">Error</h4>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
              <button
                type="button"
                className="text-red-400 hover:text-red-600"
                onClick={() => setError(null)}
              >
                <span className="sr-only">Dismiss</span>
                <XCircleIcon className="h-5 w-5" />
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Decision Drawer */}
      <DecisionDrawer />
    </div>
  );
}
