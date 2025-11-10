import { useState, useEffect } from 'react';
import Head from 'next/head';
import MetricCard from '../components/MetricCard';
import IncidentCard from '../components/IncidentCard';
import StatusBadge from '../components/StatusBadge';
import LoadingSkeleton from '../components/LoadingSkeleton';
import DarkModeToggle from '../components/DarkModeToggle';

export default function Dashboard() {
  const [services, setServices] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [selectedIncident, setSelectedIncident] = useState(null);

  const supervisorApiUrl = process.env.NEXT_PUBLIC_SUPERVISOR_API_URL || 'http://localhost:8080';

  // Fetch service status
  const fetchServices = async () => {
    try {
      const response = await fetch(`${supervisorApiUrl}/services/status`);
      if (response.ok) {
        const data = await response.json();
        setServices(data);
        setError(null);
      } else {
        throw new Error('Failed to fetch services');
      }
    } catch (err) {
      console.error('Error fetching services:', err);
      setError(err.message);
    }
  };

  // Fetch incidents with enhanced data
  const fetchIncidents = async () => {
    try {
      const response = await fetch(`${supervisorApiUrl}/incidents?limit=10`);
      if (response.ok) {
        const data = await response.json();

        // Fetch full details for each incident including AI explanation
        const enhancedIncidents = await Promise.all(
          data.slice(0, 5).map(async (incident) => {
            try {
              // Fetch full incident details
              const detailsResponse = await fetch(`${supervisorApiUrl}/incidents/${incident.id}`);
              if (detailsResponse.ok) {
                const fullIncident = await detailsResponse.json();

                // Try to fetch AI explanation if not already present
                if (!fullIncident.explanation && fullIncident.status !== 'action_pending') {
                  try {
                    const explainResponse = await fetch(`${supervisorApiUrl}/explain/${incident.id}`, {
                      method: 'POST'
                    });
                    if (explainResponse.ok) {
                      const explanation = await explainResponse.json();
                      fullIncident.explanation = explanation.explanation;
                    }
                  } catch (err) {
                    console.log('Could not fetch explanation:', err);
                  }
                }

                return fullIncident;
              }
              return incident;
            } catch (err) {
              console.error('Error fetching incident details:', err);
              return incident;
            }
          })
        );

        setIncidents(enhancedIncidents);
      }
    } catch (err) {
      console.error('Error fetching incidents:', err);
    }
  };

  // Trigger manual scan
  const triggerScan = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${supervisorApiUrl}/health/scan`, {
        method: 'POST'
      });

      if (response.ok) {
        const data = await response.json();
        alert(`Scan complete: ${data.services_scanned} services scanned, ${data.anomalies_detected} anomalies detected`);
        await fetchServices();
        await fetchIncidents();
      } else {
        alert('Scan failed');
      }
    } catch (err) {
      alert(`Error triggering scan: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Initial load and auto-refresh
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await fetchServices();
      await fetchIncidents();
      setLoading(false);
      setLastUpdate(new Date());
    };

    loadData();

    // Auto-refresh every 10 seconds
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);

  // Calculate overall system health
  const getSystemHealth = () => {
    if (services.length === 0) return { status: 'unknown', count: { healthy: 0, warning: 0, critical: 0 } };

    const count = {
      healthy: services.filter(s => s.status?.toLowerCase() === 'healthy').length,
      warning: services.filter(s => s.status?.toLowerCase() === 'warning' || s.status?.toLowerCase() === 'degraded').length,
      critical: services.filter(s => s.status?.toLowerCase() === 'critical' || s.status?.toLowerCase() === 'unhealthy').length
    };

    if (count.critical > 0) return { status: 'critical', count };
    if (count.warning > 0) return { status: 'warning', count };
    return { status: 'healthy', count };
  };

  const systemHealth = getSystemHealth();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 transition-colors duration-200">
      <Head>
        <title>AgentOps Dashboard</title>
        <meta name="description" content="AI-powered Cloud Run monitoring" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-8 transition-colors duration-200">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">AgentOps Dashboard</h1>
                <StatusBadge status={systemHealth.status} size="lg" animated={systemHealth.status !== 'healthy'} />
              </div>
              <p className="text-gray-600 dark:text-gray-400">AI-powered Cloud Run health monitoring</p>
              <div className="flex items-center gap-4 mt-2 text-sm text-gray-500 dark:text-gray-400">
                <span>🟢 {systemHealth.count.healthy} Healthy</span>
                <span>🟡 {systemHealth.count.warning} Warning</span>
                <span>🔴 {systemHealth.count.critical} Critical</span>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <button
                  onClick={triggerScan}
                  disabled={loading}
                  className="bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? 'Scanning...' : 'Trigger Scan'}
                </button>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                  Last update: {lastUpdate.toLocaleTimeString()}
                </p>
              </div>
              <DarkModeToggle />
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-critical-100 dark:bg-critical-900/20 border-l-4 border-critical-500 text-critical-700 dark:text-critical-300 p-4 mb-8 rounded transition-colors duration-200">
            <p className="font-bold">Error</p>
            <p>{error}</p>
            <p className="text-sm mt-2">Check that supervisor-api is running and accessible at {supervisorApiUrl}</p>
          </div>
        )}

        {/* Services Section */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Services</h2>

          {loading && services.length === 0 ? (
            <div className="grid md:grid-cols-2 gap-6">
              <LoadingSkeleton type="card" count={2} />
            </div>
          ) : services.length === 0 && !error ? (
            <div className="bg-warning-100 dark:bg-warning-900/20 border-l-4 border-warning-500 text-warning-700 dark:text-warning-300 p-4 rounded transition-colors duration-200">
              <p className="font-bold">No services found</p>
              <p>Configure TARGET_SERVICES in supervisor-api environment variables</p>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {services.map((service, index) => (
                <MetricCard
                  key={index}
                  service={service}
                  onClick={() => console.log('Service clicked:', service.name)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Incidents Section */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 transition-colors duration-200">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">Recent Incidents</h2>

          {loading && incidents.length === 0 ? (
            <div className="space-y-4">
              <LoadingSkeleton type="incident" count={3} />
            </div>
          ) : incidents.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <p className="text-lg">No incidents detected</p>
              <p className="text-sm mt-2">All services are healthy! 🎉</p>
            </div>
          ) : (
            <div className="space-y-4">
              {incidents.map((incident, index) => (
                <IncidentCard
                  key={incident.id || index}
                  incident={incident}
                  onClick={() => setSelectedIncident(incident)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-gray-600 dark:text-gray-400">
          <p className="text-sm">
            AgentOps v2.0.0 | Project: {process.env.NEXT_PUBLIC_PROJECT_ID || 'N/A'}
          </p>
          <p className="text-xs mt-1">
            Enhanced with AI-powered insights and real-time monitoring
          </p>
        </div>
      </main>

      <style jsx global>{`
        * {
          box-sizing: border-box;
        }
        body {
          margin: 0;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        }
      `}</style>
    </div>
  );
}
