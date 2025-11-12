/**
 * Fault Injection API Utilities
 * Provides functions to control fault injection on demo services
 */

const supervisorApiUrl = process.env.NEXT_PUBLIC_SUPERVISOR_API_URL || 'http://localhost:8080';

/**
 * Inject a fault into a service
 * @param {string} serviceName - Name of the service
 * @param {Object} config - Fault configuration
 * @param {string} config.faultType - Type of fault ('5xx', 'latency', 'timeout')
 * @param {number} config.errorRate - Error rate percentage (0-100)
 * @param {number} config.latencyMs - Latency in milliseconds
 * @param {number} config.duration - Duration in seconds
 * @returns {Promise<Object>} Response from API
 */
export async function injectFault(serviceName, config) {
  const { faultType, errorRate, latencyMs, duration } = config;

  const params = new URLSearchParams({
    service_name: serviceName,
    fault_type: faultType,
    duration: duration.toString(),
  });

  if (faultType === '5xx' || faultType === 'timeout') {
    params.append('error_rate', errorRate.toString());
  }

  if (faultType === 'latency') {
    params.append('latency_ms', latencyMs.toString());
  }

  const response = await fetch(`${supervisorApiUrl}/admin/fault/inject?${params}`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to inject fault');
  }

  return await response.json();
}

/**
 * Disable fault injection on a service
 * @param {string} serviceName - Name of the service
 * @returns {Promise<Object>} Response from API
 */
export async function disableFault(serviceName) {
  const params = new URLSearchParams({
    service_name: serviceName,
  });

  const response = await fetch(`${supervisorApiUrl}/admin/fault/disable?${params}`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to disable fault');
  }

  return await response.json();
}

/**
 * Get fault status for a service or all services
 * @param {string|null} serviceName - Name of the service (null for all services)
 * @returns {Promise<Object>} Fault status
 */
export async function getFaultStatus(serviceName = null) {
  const params = serviceName ? `?service_name=${serviceName}` : '';

  const response = await fetch(`${supervisorApiUrl}/admin/fault/status${params}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get fault status');
  }

  return await response.json();
}

/**
 * Disable faults on all services
 * @param {Array<string>} serviceNames - Array of service names
 * @returns {Promise<Array>} Array of results
 */
export async function disableAllFaults(serviceNames) {
  const results = await Promise.allSettled(
    serviceNames.map(serviceName => disableFault(serviceName))
  );

  return results.map((result, index) => ({
    service: serviceNames[index],
    success: result.status === 'fulfilled',
    error: result.status === 'rejected' ? result.reason.message : null,
  }));
}

/**
 * Format fault status for display
 * @param {Object} status - Fault status from API
 * @returns {Object} Formatted status
 */
export function formatFaultStatus(status) {
  if (!status || !status.fault_status) {
    return {
      active: false,
      message: 'No active fault',
    };
  }

  const faultData = status.fault_status;

  if (!faultData.active) {
    return {
      active: false,
      message: 'No active fault',
    };
  }

  const { type, config } = faultData;
  let message = '';

  switch (type) {
    case '5xx':
      message = `${config.error_rate}% 5xx errors`;
      break;
    case 'latency':
      message = `+${config.latency_ms}ms latency`;
      break;
    case 'timeout':
      message = `${config.error_rate}% timeouts`;
      break;
    default:
      message = `${type} fault active`;
  }

  // Calculate remaining time if expires_at is available
  if (config.expires_at) {
    const expiresAt = new Date(config.expires_at);
    const now = new Date();
    const remainingMs = expiresAt - now;
    const remainingMin = Math.ceil(remainingMs / 60000);

    if (remainingMin > 0) {
      message += ` (${remainingMin}m left)`;
    }
  }

  return {
    active: true,
    type,
    message,
    config,
  };
}

/**
 * Fault injection templates for quick access
 */
export const FAULT_TEMPLATES = {
  MODERATE_ERRORS: {
    name: 'Moderate Errors',
    description: '15% 5xx errors for 5 minutes',
    config: {
      faultType: '5xx',
      errorRate: 15,
      latencyMs: 0,
      duration: 300,
    },
  },
  HIGH_ERRORS: {
    name: 'High Errors',
    description: '30% 5xx errors for 3 minutes',
    config: {
      faultType: '5xx',
      errorRate: 30,
      latencyMs: 0,
      duration: 180,
    },
  },
  LATENCY_SPIKE: {
    name: 'Latency Spike',
    description: '1000ms latency for 5 minutes',
    config: {
      faultType: 'latency',
      errorRate: 0,
      latencyMs: 1000,
      duration: 300,
    },
  },
  SERVICE_OUTAGE: {
    name: 'Service Outage',
    description: '100% errors for 2 minutes',
    config: {
      faultType: '5xx',
      errorRate: 100,
      latencyMs: 0,
      duration: 120,
    },
  },
};
