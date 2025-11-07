import { useState, useEffect } from 'react';
import Head from 'next/head';

export default function Dashboard() {
  const [services, setServices] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());

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

  // Fetch incidents
  const fetchIncidents = async () => {
    try {
      const response = await fetch(`${supervisorApiUrl}/incidents?limit=10`);
      if (response.ok) {
        const data = await response.json();
        setIncidents(data);
      }
    } catch (err) {
      console.error('Error fetching incidents:', err);
    }
  };

  // Inject fault in a service
  const injectFault = async (serviceName, serviceUrl) => {
    try {
      const response = await fetch(`${serviceUrl}/fault/enable?type=5xx&error_rate=15&duration=300`, {
        method: 'POST'
      });
      
      if (response.ok) {
        alert(`Fault injected in ${serviceName}! Wait 2-3 minutes for detection.`);
      } else {
        alert(`Failed to inject fault in ${serviceName}`);
      }
    } catch (err) {
      alert(`Error injecting fault: ${err.message}`);
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

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'healthy': return 'bg-green-500';
      case 'degraded': return 'bg-yellow-500';
      case 'unhealthy': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusEmoji = (status) => {
    switch (status?.toLowerCase()) {
      case 'healthy': return '✅';
      case 'degraded': return '⚠️';
      case 'unhealthy': return '🔴';
      default: return '❓';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <Head>
        <title>AgentOps Dashboard</title>
        <meta name="description" content="AI-powered Cloud Run monitoring" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">AgentOps Dashboard</h1>
              <p className="text-gray-600 mt-1">AI-powered Cloud Run health monitoring</p>
            </div>
            <div className="text-right">
              <button
                onClick={triggerScan}
                disabled={loading}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? 'Scanning...' : 'Trigger Scan'}
              </button>
              <p className="text-sm text-gray-500 mt-2">
                Last update: {lastUpdate.toLocaleTimeString()}
              </p>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-8 rounded">
            <p className="font-bold">Error</p>
            <p>{error}</p>
            <p className="text-sm mt-2">Check that supervisor-api is running and accessible</p>
          </div>
        )}

        {/* Services Grid */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          {services.length === 0 && !loading && !error && (
            <div className="col-span-2 bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 rounded">
              <p className="font-bold">No services found</p>
              <p>Configure TARGET_SERVICES in supervisor-api environment variables</p>
            </div>
          )}

          {services.map((service, index) => (
            <div key={index} className="bg-white rounded-lg shadow-lg p-6 hover:shadow-xl transition-shadow">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{getStatusEmoji(service.status)}</span>
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">{service.name}</h2>
                    <p className="text-sm text-gray-500">{service.region}</p>
                  </div>
                </div>
                <span className={`px-4 py-2 rounded-full text-white text-sm font-semibold ${getStatusColor(service.status)}`}>
                  {service.status || 'unknown'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <p className="text-sm text-gray-600">Error Rate</p>
                  <p className="text-2xl font-bold text-gray-900">{service.error_rate?.toFixed(2) || '0.00'}%</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Latency p95</p>
                  <p className="text-2xl font-bold text-gray-900">{service.latency_p95?.toFixed(0) || '0'}ms</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Requests</p>
                  <p className="text-2xl font-bold text-gray-900">{service.request_count || 0}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Last Check</p>
                  <p className="text-sm font-semibold text-gray-900">
                    {service.last_checked ? new Date(service.last_checked).toLocaleTimeString() : 'N/A'}
                  </p>
                </div>
              </div>

              <button
                onClick={() => {
                  // Construct demo app URL (you'll need to replace with actual URLs)
                  const demoUrl = `https://${service.name}-${process.env.NEXT_PUBLIC_PROJECT_ID}.${service.region}.run.app`;
                  injectFault(service.name, demoUrl);
                }}
                className="w-full bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors"
              >
                🔥 Inject Fault
              </button>
            </div>
          ))}
        </div>

        {/* Incidents Section */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Recent Incidents</h2>
          
          {incidents.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p className="text-lg">No incidents detected</p>
              <p className="text-sm mt-2">All services are healthy! 🎉</p>
            </div>
          ) : (
            <div className="space-y-4">
              {incidents.map((incident, index) => (
                <div key={index} className="border-l-4 border-blue-500 bg-blue-50 p-4 rounded">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-bold text-gray-900">{incident.service_name}</p>
                      <p className="text-sm text-gray-600">
                        {incident.started_at ? new Date(incident.started_at).toLocaleString() : 'N/A'}
                      </p>
                    </div>
                    <span className="px-3 py-1 bg-blue-600 text-white rounded-full text-sm">
                      {incident.status}
                    </span>
                  </div>
                  {incident.recommendation && (
                    <p className="mt-2 text-sm text-gray-700">
                      Action: {incident.recommendation}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-gray-600">
          <p className="text-sm">
            AgentOps v1.0.0 | Project: {process.env.NEXT_PUBLIC_PROJECT_ID || 'N/A'}
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