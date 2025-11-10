import React from 'react';
import StatusBadge from './StatusBadge';

const IncidentCard = ({ incident, onClick }) => {
  const formatTime = (timestamp) => {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  const getConfidenceColor = (confidence) => {
    if (!confidence) return 'bg-gray-200 dark:bg-gray-700';
    if (confidence >= 0.8) return 'bg-healthy-500';
    if (confidence >= 0.6) return 'bg-warning-500';
    return 'bg-critical-500';
  };

  return (
    <div
      onClick={onClick}
      className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-5 border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all duration-200 cursor-pointer transform hover:-translate-y-0.5"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h4 className="text-base font-semibold text-gray-900 dark:text-white mb-1">
            {incident.service_name}
          </h4>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Started: {formatTime(incident.detected_at || incident.created_at)}
          </p>
        </div>
        <StatusBadge status={incident.status} size="sm" />
      </div>

      {/* AI Recommendation (if available) */}
      {incident.recommendation && (
        <div className="mb-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-blue-900 dark:text-blue-300">
              AI Recommendation: {incident.recommendation.action}
            </span>
            {incident.recommendation.confidence && (
              <span className="text-xs text-blue-700 dark:text-blue-400">
                {(incident.recommendation.confidence * 100).toFixed(0)}% confidence
              </span>
            )}
          </div>
          {incident.recommendation.confidence && (
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
              <div
                className={`h-1.5 rounded-full ${getConfidenceColor(incident.recommendation.confidence)}`}
                style={{ width: `${incident.recommendation.confidence * 100}%` }}
              />
            </div>
          )}
        </div>
      )}

      {/* Recommendation Text */}
      {incident.recommendation?.reasoning && (
        <p className="text-sm text-gray-700 dark:text-gray-300 mb-3 line-clamp-2">
          {incident.recommendation.reasoning}
        </p>
      )}

      {/* MTTR (if resolved) */}
      {incident.mttr_seconds && (
        <div className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
          <span className="font-medium">MTTR:</span>
          <span>{(incident.mttr_seconds / 60).toFixed(1)} minutes</span>
        </div>
      )}

      {/* Action Status (if available) */}
      {incident.action_result && (
        <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 dark:text-gray-400">Action:</span>
            <span className={`text-xs font-medium ${
              incident.action_result.success ? 'text-healthy-600 dark:text-healthy-400' : 'text-critical-600 dark:text-critical-400'
            }`}>
              {incident.action_result.success ? '✓ Completed' : '✗ Failed'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default IncidentCard;
