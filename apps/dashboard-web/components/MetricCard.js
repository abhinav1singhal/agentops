import React from 'react';
import StatusBadge from './StatusBadge';

const MetricCard = ({
  service,
  onClick
}) => {
  const { name, status, error_rate, latency_p95, request_count, last_checked } = service;

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
        return 'border-healthy-200 dark:border-healthy-800';
      case 'warning':
        return 'border-warning-200 dark:border-warning-800';
      case 'critical':
        return 'border-critical-200 dark:border-critical-800';
      default:
        return 'border-gray-200 dark:border-gray-700';
    }
  };

  const formatNumber = (num) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num?.toLocaleString() || '0';
  };

  const formatTime = (timestamp) => {
    if (!timestamp) return 'Never';
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

  return (
    <div
      onClick={onClick}
      className={`
        bg-white dark:bg-gray-800 rounded-lg shadow-md p-6
        border-l-4 ${getStatusColor(status)}
        hover:shadow-lg transition-all duration-200 cursor-pointer
        transform hover:-translate-y-1
      `}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {name}
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Last checked: {formatTime(last_checked)}
          </p>
        </div>
        <StatusBadge status={status} animated={status === 'critical' || status === 'warning'} />
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Error Rate */}
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Error Rate</p>
          <div className="flex items-baseline gap-1">
            <p className={`text-2xl font-bold ${
              parseFloat(error_rate) > 5 ? 'text-critical-600 dark:text-critical-400' :
              parseFloat(error_rate) > 2 ? 'text-warning-600 dark:text-warning-400' :
              'text-healthy-600 dark:text-healthy-400'
            }`}>
              {parseFloat(error_rate).toFixed(1)}
            </p>
            <span className="text-sm text-gray-500">%</span>
          </div>
        </div>

        {/* Latency */}
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Latency P95</p>
          <div className="flex items-baseline gap-1">
            <p className={`text-2xl font-bold ${
              parseFloat(latency_p95) > 500 ? 'text-critical-600 dark:text-critical-400' :
              parseFloat(latency_p95) > 300 ? 'text-warning-600 dark:text-warning-400' :
              'text-healthy-600 dark:text-healthy-400'
            }`}>
              {parseFloat(latency_p95).toFixed(0)}
            </p>
            <span className="text-sm text-gray-500">ms</span>
          </div>
        </div>
      </div>

      {/* Request Count */}
      <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500 dark:text-gray-400">Requests</span>
          <span className="text-sm font-semibold text-gray-900 dark:text-white">
            {formatNumber(request_count)}
          </span>
        </div>
      </div>
    </div>
  );
};

export default MetricCard;
