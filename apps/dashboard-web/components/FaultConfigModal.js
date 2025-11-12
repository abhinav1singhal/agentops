import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const FaultConfigModal = ({ isOpen, onClose, onConfirm, serviceName, config }) => {
  if (!isOpen) return null;

  const { faultType, errorRate, latencyMs, duration } = config;

  // Calculate expiration time
  const expiresAt = new Date(Date.now() + duration * 1000);
  const expiresAtStr = expiresAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  // Format duration
  const durationMin = Math.floor(duration / 60);
  const durationSec = duration % 60;
  const durationStr = durationSec > 0 ? `${durationMin}m ${durationSec}s` : `${durationMin}m`;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 overflow-y-auto">
        <div className="flex min-h-screen items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6 transition-colors duration-200"
          >
            {/* Header */}
            <div className="flex items-start mb-4">
              <div className="flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-warning-100 dark:bg-warning-900/20">
                <svg className="h-6 w-6 text-warning-600 dark:text-warning-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div className="ml-4 flex-1">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                  Confirm Fault Injection
                </h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  This will cause service degradation for demo purposes
                </p>
              </div>
            </div>

            {/* Configuration Summary */}
            <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-4 transition-colors duration-200">
              <dl className="space-y-2">
                <div className="flex justify-between">
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Service:</dt>
                  <dd className="text-sm font-semibold text-gray-900 dark:text-white">{serviceName}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Fault Type:</dt>
                  <dd className="text-sm font-semibold text-gray-900 dark:text-white">
                    {faultType === '5xx' ? '5xx Errors' : faultType === 'latency' ? 'High Latency' : 'Timeout'}
                  </dd>
                </div>
                {(faultType === '5xx' || faultType === 'timeout') && (
                  <div className="flex justify-between">
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Error Rate:</dt>
                    <dd className="text-sm font-semibold text-critical-600 dark:text-critical-400">{errorRate}%</dd>
                  </div>
                )}
                {faultType === 'latency' && (
                  <div className="flex justify-between">
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Added Latency:</dt>
                    <dd className="text-sm font-semibold text-warning-600 dark:text-warning-400">{latencyMs}ms</dd>
                  </div>
                )}
                <div className="flex justify-between">
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Duration:</dt>
                  <dd className="text-sm font-semibold text-gray-900 dark:text-white">{durationStr}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Auto-expires at:</dt>
                  <dd className="text-sm font-semibold text-gray-900 dark:text-white">{expiresAtStr}</dd>
                </div>
              </dl>
            </div>

            {/* Warning Message */}
            <div className="bg-warning-50 dark:bg-warning-900/10 border-l-4 border-warning-400 p-3 mb-4 transition-colors duration-200">
              <p className="text-sm text-warning-700 dark:text-warning-300">
                This will trigger automated monitoring alerts and may cause the AI to recommend remediation actions.
              </p>
            </div>

            {/* Actions */}
            <div className="flex space-x-3">
              <button
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors duration-200"
              >
                Cancel
              </button>
              <button
                onClick={onConfirm}
                className="flex-1 px-4 py-2 border border-transparent rounded-lg text-sm font-medium text-white bg-critical-600 hover:bg-critical-700 dark:bg-critical-500 dark:hover:bg-critical-600 transition-colors duration-200"
              >
                Confirm Injection
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    </AnimatePresence>
  );
};

export default FaultConfigModal;
