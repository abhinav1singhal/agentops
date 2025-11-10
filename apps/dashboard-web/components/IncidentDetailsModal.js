import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import StatusBadge from './StatusBadge';
import { format } from 'date-fns';

const IncidentDetailsModal = ({ incident, isOpen, onClose }) => {
  if (!incident) return null;

  const formatDate = (timestamp) => {
    if (!timestamp) return 'N/A';
    try {
      return format(new Date(timestamp), 'PPpp');
    } catch {
      return timestamp;
    }
  };

  const calculateDuration = () => {
    if (!incident.detected_at) return 'N/A';
    const start = new Date(incident.detected_at);
    const end = incident.resolved_at ? new Date(incident.resolved_at) : new Date();
    const diffMinutes = Math.floor((end - start) / 60000);

    if (diffMinutes < 60) return `${diffMinutes} minutes`;
    const hours = Math.floor(diffMinutes / 60);
    const mins = diffMinutes % 60;
    return `${hours}h ${mins}m`;
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black bg-opacity-50 z-40"
          />

          {/* Modal */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 h-full w-full max-w-2xl bg-white dark:bg-gray-800 shadow-2xl z-50 overflow-y-auto"
          >
            {/* Header */}
            <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-6 z-10">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                      Incident Details
                    </h2>
                    <StatusBadge status={incident.status} size="md" />
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    ID: {incident.id || 'N/A'}
                  </p>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  aria-label="Close modal"
                >
                  <svg className="w-6 h-6 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6">
              {/* Service Information */}
              <section>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                  Service Information
                </h3>
                <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Service:</span>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {incident.service_name}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Region:</span>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {incident.region || 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">Duration:</span>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {calculateDuration()}
                    </span>
                  </div>
                </div>
              </section>

              {/* Timeline */}
              <section>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                  Timeline
                </h3>
                <div className="space-y-3">
                  {incident.detected_at && (
                    <div className="flex items-start gap-3">
                      <div className="w-2 h-2 mt-2 rounded-full bg-critical-500" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          Detected
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {formatDate(incident.detected_at)}
                        </p>
                      </div>
                    </div>
                  )}
                  {incident.remediation_started_at && (
                    <div className="flex items-start gap-3">
                      <div className="w-2 h-2 mt-2 rounded-full bg-warning-500" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          Remediation Started
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {formatDate(incident.remediation_started_at)}
                        </p>
                      </div>
                    </div>
                  )}
                  {incident.resolved_at && (
                    <div className="flex items-start gap-3">
                      <div className="w-2 h-2 mt-2 rounded-full bg-healthy-500" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          Resolved
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {formatDate(incident.resolved_at)}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </section>

              {/* Metrics */}
              {incident.metrics && (
                <section>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                    Metrics at Detection
                  </h3>
                  <div className="grid grid-cols-2 gap-4">
                    {incident.metrics.error_rate !== undefined && (
                      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Error Rate</p>
                        <p className="text-2xl font-bold text-critical-600 dark:text-critical-400">
                          {incident.metrics.error_rate.toFixed(2)}%
                        </p>
                      </div>
                    )}
                    {incident.metrics.latency_p95 !== undefined && (
                      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Latency P95</p>
                        <p className="text-2xl font-bold text-warning-600 dark:text-warning-400">
                          {incident.metrics.latency_p95.toFixed(0)}ms
                        </p>
                      </div>
                    )}
                    {incident.metrics.request_count !== undefined && (
                      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Request Count</p>
                        <p className="text-2xl font-bold text-gray-900 dark:text-white">
                          {incident.metrics.request_count.toLocaleString()}
                        </p>
                      </div>
                    )}
                    {incident.mttr_seconds !== undefined && (
                      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
                        <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">MTTR</p>
                        <p className="text-2xl font-bold text-healthy-600 dark:text-healthy-400">
                          {(incident.mttr_seconds / 60).toFixed(1)}m
                        </p>
                      </div>
                    )}
                  </div>
                </section>
              )}

              {/* AI Recommendation */}
              {incident.recommendation && (
                <section>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                    AI Recommendation
                  </h3>
                  <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-blue-900 dark:text-blue-300">
                        Action: {incident.recommendation.action}
                      </span>
                      {incident.recommendation.confidence && (
                        <span className="text-sm text-blue-700 dark:text-blue-400">
                          {(incident.recommendation.confidence * 100).toFixed(0)}% confidence
                        </span>
                      )}
                    </div>
                    {incident.recommendation.reasoning && (
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        {incident.recommendation.reasoning}
                      </p>
                    )}
                    {incident.recommendation.risk_assessment && (
                      <div className="pt-3 border-t border-blue-200 dark:border-blue-800">
                        <p className="text-xs font-medium text-blue-900 dark:text-blue-300 mb-1">
                          Risk Assessment
                        </p>
                        <p className="text-sm text-gray-700 dark:text-gray-300">
                          {incident.recommendation.risk_assessment}
                        </p>
                      </div>
                    )}
                  </div>
                </section>
              )}

              {/* AI Explanation */}
              {incident.explanation && (
                <section>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                    AI Explanation
                  </h3>
                  <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                    <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                      {incident.explanation}
                    </p>
                  </div>
                </section>
              )}

              {/* Action Result */}
              {incident.action_result && (
                <section>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                    Action Result
                  </h3>
                  <div className={`rounded-lg p-4 ${
                    incident.action_result.success
                      ? 'bg-healthy-50 dark:bg-healthy-900/20'
                      : 'bg-critical-50 dark:bg-critical-900/20'
                  }`}>
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-sm font-medium ${
                        incident.action_result.success
                          ? 'text-healthy-900 dark:text-healthy-300'
                          : 'text-critical-900 dark:text-critical-300'
                      }`}>
                        {incident.action_result.success ? '✓ Action Completed Successfully' : '✗ Action Failed'}
                      </span>
                    </div>
                    {incident.action_result.message && (
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        {incident.action_result.message}
                      </p>
                    )}
                    {incident.action_result.details && (
                      <pre className="mt-2 text-xs bg-gray-900 dark:bg-gray-950 text-gray-100 p-3 rounded overflow-x-auto">
                        {JSON.stringify(incident.action_result.details, null, 2)}
                      </pre>
                    )}
                  </div>
                </section>
              )}

              {/* Error Logs */}
              {incident.log_samples && incident.log_samples.length > 0 && (
                <section>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                    Error Logs ({incident.log_samples.length})
                  </h3>
                  <div className="space-y-2">
                    {incident.log_samples.slice(0, 10).map((log, index) => (
                      <div key={index} className="bg-gray-900 dark:bg-gray-950 rounded p-3">
                        <p className="text-xs font-mono text-red-400 break-all">
                          {log.message || log}
                        </p>
                        {log.timestamp && (
                          <p className="text-xs text-gray-500 mt-1">
                            {formatDate(log.timestamp)}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default IncidentDetailsModal;
