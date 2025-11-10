import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const AnalyticsSection = ({ incidents, services }) => {
  // Calculate analytics data
  const calculateAnalytics = () => {
    const totalIncidents = incidents.length;
    const resolvedIncidents = incidents.filter(i => i.status === 'resolved').length;
    const failedIncidents = incidents.filter(i => i.status === 'failed').length;
    const pendingIncidents = incidents.filter(i => i.status === 'action_pending' || i.status === 'remediating').length;

    // Calculate average MTTR
    const resolvedWithMTTR = incidents.filter(i => i.mttr_seconds);
    const avgMTTR = resolvedWithMTTR.length > 0
      ? resolvedWithMTTR.reduce((sum, i) => sum + i.mttr_seconds, 0) / resolvedWithMTTR.length / 60
      : 0;

    // Calculate success rate
    const completedActions = resolvedIncidents + failedIncidents;
    const successRate = completedActions > 0 ? (resolvedIncidents / completedActions) * 100 : 0;

    // Incidents by service
    const incidentsByService = {};
    incidents.forEach(incident => {
      const service = incident.service_name;
      if (!incidentsByService[service]) {
        incidentsByService[service] = { total: 0, resolved: 0, failed: 0 };
      }
      incidentsByService[service].total++;
      if (incident.status === 'resolved') incidentsByService[service].resolved++;
      if (incident.status === 'failed') incidentsByService[service].failed++;
    });

    const chartData = Object.entries(incidentsByService).map(([service, data]) => ({
      service: service.replace('demo-app-', ''),
      resolved: data.resolved,
      failed: data.failed,
      pending: data.total - data.resolved - data.failed,
    }));

    return {
      totalIncidents,
      resolvedIncidents,
      failedIncidents,
      pendingIncidents,
      avgMTTR,
      successRate,
      chartData,
    };
  };

  const analytics = calculateAnalytics();

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 transition-colors duration-200">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Analytics</h2>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
          <p className="text-xs text-blue-600 dark:text-blue-400 mb-1">Total Incidents</p>
          <p className="text-3xl font-bold text-blue-900 dark:text-blue-300">
            {analytics.totalIncidents}
          </p>
        </div>

        <div className="bg-healthy-50 dark:bg-healthy-900/20 rounded-lg p-4">
          <p className="text-xs text-healthy-600 dark:text-healthy-400 mb-1">Resolved</p>
          <p className="text-3xl font-bold text-healthy-900 dark:text-healthy-300">
            {analytics.resolvedIncidents}
          </p>
        </div>

        <div className="bg-critical-50 dark:bg-critical-900/20 rounded-lg p-4">
          <p className="text-xs text-critical-600 dark:text-critical-400 mb-1">Failed</p>
          <p className="text-3xl font-bold text-critical-900 dark:text-critical-300">
            {analytics.failedIncidents}
          </p>
        </div>

        <div className="bg-warning-50 dark:bg-warning-900/20 rounded-lg p-4">
          <p className="text-xs text-warning-600 dark:text-warning-400 mb-1">Pending</p>
          <p className="text-3xl font-bold text-warning-900 dark:text-warning-300">
            {analytics.pendingIncidents}
          </p>
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Average MTTR</p>
          <div className="flex items-baseline gap-2">
            <p className="text-4xl font-bold text-gray-900 dark:text-white">
              {analytics.avgMTTR.toFixed(1)}
            </p>
            <span className="text-sm text-gray-500">minutes</span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Mean Time To Recovery
          </p>
        </div>

        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Action Success Rate</p>
          <div className="flex items-baseline gap-2">
            <p className="text-4xl font-bold text-gray-900 dark:text-white">
              {analytics.successRate.toFixed(0)}
            </p>
            <span className="text-sm text-gray-500">%</span>
          </div>
          <div className="mt-2">
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div
                className="bg-healthy-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${analytics.successRate}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Incidents by Service Chart */}
      {analytics.chartData.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Incidents by Service
          </h3>
          <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={analytics.chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                <XAxis
                  dataKey="service"
                  stroke="#9CA3AF"
                  style={{ fontSize: '12px' }}
                />
                <YAxis
                  stroke="#9CA3AF"
                  style={{ fontSize: '12px' }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1F2937',
                    border: '1px solid #374151',
                    borderRadius: '8px',
                    color: '#F9FAFB',
                  }}
                />
                <Legend />
                <Bar dataKey="resolved" fill="#22c55e" name="Resolved" />
                <Bar dataKey="failed" fill="#ef4444" name="Failed" />
                <Bar dataKey="pending" fill="#f59e0b" name="Pending" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* No Data State */}
      {analytics.totalIncidents === 0 && (
        <div className="text-center py-8">
          <p className="text-gray-500 dark:text-gray-400">
            No incident data available for analytics
          </p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
            Analytics will appear after incidents are detected
          </p>
        </div>
      )}
    </div>
  );
};

export default AnalyticsSection;
