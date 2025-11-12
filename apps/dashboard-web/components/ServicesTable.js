import React, { useState, useEffect } from 'react';
import StatusBadge from './StatusBadge';
import { getFaultStatus } from '../utils/faultInjection';

const ServicesTable = ({ services }) => {
  const [faultStatuses, setFaultStatuses] = useState({});

  // Poll fault status every 10 seconds
  useEffect(() => {
    const pollFaultStatus = async () => {
      try {
        const response = await getFaultStatus();
        if (response.services) {
          const statusMap = {};
          response.services.forEach(svc => {
            statusMap[svc.service] = svc.fault_status;
          });
          setFaultStatuses(statusMap);
        }
      } catch (error) {
        console.error('Failed to fetch fault status:', error);
      }
    };

    pollFaultStatus();
    const interval = setInterval(pollFaultStatus, 10000);

    return () => clearInterval(interval);
  }, []);
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

  const getErrorRateColor = (errorRate) => {
    const rate = parseFloat(errorRate);
    if (rate > 5) return 'text-critical-600 dark:text-critical-400';
    if (rate > 2) return 'text-warning-600 dark:text-warning-400';
    return 'text-healthy-600 dark:text-healthy-400';
  };

  const getLatencyColor = (latency) => {
    const lat = parseFloat(latency);
    if (lat > 500) return 'text-critical-600 dark:text-critical-400';
    if (lat > 300) return 'text-warning-600 dark:text-warning-400';
    return 'text-healthy-600 dark:text-healthy-400';
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden transition-colors duration-200">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Service Name
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Status
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Fault Active
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Error Rate
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Latency P95
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Requests
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Last Checked
              </th>
            </tr>
          </thead>
          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
            {services.map((service, index) => (
              <tr
                key={index}
                className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-150 cursor-pointer"
                onClick={() => console.log('Service clicked:', service.name)}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900 dark:text-white">
                    {service.name}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <StatusBadge
                    status={service.status}
                    animated={service.status === 'critical' || service.status === 'warning'}
                  />
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {faultStatuses[service.name]?.active ? (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-warning-100 text-warning-800 dark:bg-warning-900/30 dark:text-warning-300">
                      <svg className="mr-1 h-3 w-3" fill="currentColor" viewBox="0 0 8 8">
                        <circle cx="4" cy="4" r="3" />
                      </svg>
                      {faultStatuses[service.name].type}
                    </span>
                  ) : (
                    <span className="text-sm text-gray-400 dark:text-gray-500">-</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-baseline gap-1">
                    <span className={`text-lg font-bold ${getErrorRateColor(service.error_rate)}`}>
                      {parseFloat(service.error_rate).toFixed(1)}
                    </span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">%</span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-baseline gap-1">
                    <span className={`text-lg font-bold ${getLatencyColor(service.latency_p95)}`}>
                      {parseFloat(service.latency_p95).toFixed(0)}
                    </span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">ms</span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-semibold text-gray-900 dark:text-white">
                    {formatNumber(service.request_count)}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {formatTime(service.last_checked)}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ServicesTable;
