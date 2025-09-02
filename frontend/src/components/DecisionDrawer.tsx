'use client';

import { Fragment, useState, useRef } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { XMarkIcon, ChevronDownIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import { useDecisionStore } from '../store/decisionStore';
// DecisionListItem type is used in the component props

interface CollapsibleSectionProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

function CollapsibleSection({ title, children, defaultOpen = false }: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-gray-200 rounded-lg">
      <button
        type="button"
        className="w-full px-4 py-3 text-left bg-gray-50 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset rounded-t-lg"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-controls={`${title.toLowerCase().replace(/\s+/g, '-')}-content`}
        id={`${title.toLowerCase().replace(/\s+/g, '-')}-button`}
      >
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-900">{title}</span>
          {isOpen ? (
            <ChevronDownIcon className="h-5 w-5 text-gray-500" />
          ) : (
            <ChevronRightIcon className="h-5 w-5 text-gray-500" />
          )}
        </div>
      </button>
      
      {isOpen && (
        <div
          id={`${title.toLowerCase().replace(/\s+/g, '-')}-content`}
          className="px-4 py-3"
          role="region"
          aria-labelledby={`${title.toLowerCase().replace(/\s+/g, '-')}-button`}
        >
          {children}
        </div>
      )}
    </div>
  );
}

export default function DecisionDrawer() {
  const { selectedDecision, isDrawerOpen, closeDrawer } = useDecisionStore();
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  if (!selectedDecision) return null;

  const formatAmount = (amount: number) => {
    // Always show as Indian Rupees
    return `₹${amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
    timeZone: "America/Los_Angeles",
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'allow':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'review':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'block':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  return (
    <Transition.Root show={isDrawerOpen} as={Fragment}>
      <Dialog
        as="div"
        className="relative z-50"
        onClose={closeDrawer}
        initialFocus={closeButtonRef}
      >
        <Transition.Child
          as={Fragment}
          enter="ease-in-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in-out duration-300"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/40 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-hidden">
          <div className="absolute inset-0 overflow-hidden">
            <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
              <Transition.Child
                as={Fragment}
                enter="transform transition ease-in-out duration-300"
                enterFrom="translate-x-full"
                enterTo="translate-x-0"
                leave="transform transition ease-in-out duration-300"
                leaveFrom="translate-x-0"
                leaveTo="translate-x-full"
              >
                <Dialog.Panel className="pointer-events-auto w-screen max-w-md">
                  <div className="flex h-full flex-col bg-white shadow-xl">
                    {/* Header */}
                    <div className="px-6 py-4 border-b border-gray-200">
                      <div className="flex items-center justify-between">
                        <Dialog.Title className="text-lg font-medium text-gray-900">
                          Decision Details
                        </Dialog.Title>
                        <button
                          ref={closeButtonRef}
                          type="button"
                          className="rounded-md bg-white text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                          onClick={closeDrawer}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              closeDrawer();
                            }
                          }}
                        >
                          <span className="sr-only">Close panel</span>
                          <XMarkIcon className="h-6 w-6" />
                        </button>
                      </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
                      {/* Decision Summary */}
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <h3 className="text-sm font-medium text-gray-900">Decision</h3>
                          <span className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full border ${getDecisionColor(selectedDecision.decision)}`}>
                            {selectedDecision.decision.toUpperCase()}
                          </span>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <dt className="text-sm font-medium text-gray-500">Amount</dt>
                            <dd className="mt-1 text-sm text-gray-900">
                              {formatAmount(selectedDecision.amount)}
                            </dd>
                          </div>
                          <div>
                            <dt className="text-sm font-medium text-gray-500">Currency</dt>
                            <dd className="mt-1 text-sm text-gray-900">{selectedDecision.currency}</dd>
                          </div>
                          <div>
                            <dt className="text-sm font-medium text-gray-500">Customer ID</dt>
                            <dd className="mt-1 text-sm text-gray-900">{selectedDecision.maskedCustomerId}</dd>
                          </div>
                          <div>
                            <dt className="text-sm font-medium text-gray-500">Payee ID</dt>
                            <dd className="mt-1 text-sm text-gray-900">{selectedDecision.payeeId}</dd>
                          </div>
                        </div>
                        
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Created</dt>
                          <dd className="mt-1 text-sm text-gray-900">
                            {formatDate(selectedDecision.createdAt)}
                          </dd>
                        </div>
                        
                        <div>
                          <dt className="text-sm font-medium text-gray-500">Request ID</dt>
                          <dd className="mt-1 text-sm text-gray-900 font-mono">
                            {selectedDecision.requestId}
                          </dd>
                        </div>
                      </div>

                      {/* Reasons */}
                      <CollapsibleSection title="Reasons" defaultOpen={true}>
                        {selectedDecision.reasons.length > 0 ? (
                          <ul className="space-y-2">
                            {selectedDecision.reasons.map((reason, index) => (
                              <li key={index} className="flex items-start">
                                <span className="flex-shrink-0 w-2 h-2 bg-red-400 rounded-full mt-2 mr-3" />
                                <span className="text-sm text-gray-700">{reason}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-sm text-gray-500 italic">No reasons provided</p>
                        )}
                      </CollapsibleSection>

                      {/* Agent Trace */}
                      <CollapsibleSection title="Agent Trace" defaultOpen={false}>
                        {selectedDecision.agentTrace.length > 0 ? (
                          <div className="space-y-3">
                            {selectedDecision.agentTrace.map((step, index) => (
                              <div key={index} className="bg-gray-50 rounded-lg p-3">
                                <div className="flex items-start space-x-3">
                                  <div className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-medium">
                                    {index + 1}
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-gray-900">
                                      {step.step}
                                    </p>
                                    <p className="text-sm text-gray-600 mt-1">
                                      {step.detail}
                                    </p>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-gray-500 italic">No agent trace available</p>
                        )}
                      </CollapsibleSection>
                    </div>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  );
}
