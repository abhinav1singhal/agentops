import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import FaultConfigModal from './FaultConfigModal';
import { injectFault, disableFault, getFaultStatus, disableAllFaults, FAULT_TEMPLATES } from '../utils/faultInjection';

const FaultInjectionPanel = ({ services }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedService, setSelectedService] = useState('');
  const [faultType, setFaultType] = useState('5xx');
  const [errorRate, setErrorRate] = useState(15);
  const [latencyMs, setLatencyMs] = useState(1000);
  const [duration, setDuration] = useState(300); // 5 minutes
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [faultStatuses, setFaultStatuses] = useState({});
  const [message, setMessage] = useState(null);

  // Set default service when services load
  useEffect(() => {
    if (services.length > 0 && !selectedService) {
      setSelectedService(services[0].name);
    }
  }, [services, selectedService]);

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

  const handleInjectClick = () => {
    if (!selectedService) {
      showMessage('Please select a service', 'error');
      return;
    }
    setIsModalOpen(true);
  };

  const handleConfirmInject = async () => {
    setIsModalOpen(false);
    setLoading(true);

    try {
      const config = {
        faultType,
        errorRate,
        latencyMs,
        duration,
      };

      await injectFault(selectedService, config);
      showMessage(`Fault injected successfully on ${selectedService}`, 'success');

      // Refresh fault status immediately
      const response = await getFaultStatus(selectedService);
      setFaultStatuses(prev => ({
        ...prev,
        [selectedService]: response.fault_status,
      }));
    } catch (error) {
      showMessage(`Failed to inject fault: ${error.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleDisableFault = async (serviceName) => {
    setLoading(true);

    try {
      await disableFault(serviceName);
      showMessage(`Fault disabled on ${serviceName}`, 'success');

      // Refresh fault status
      const response = await getFaultStatus(serviceName);
      setFaultStatuses(prev => ({
        ...prev,
        [serviceName]: response.fault_status,
      }));
    } catch (error) {
      showMessage(`Failed to disable fault: ${error.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleDisableAll = async () => {
    setLoading(true);

    try {
      const serviceNames = services.map(s => s.name);
      const results = await disableAllFaults(serviceNames);

      const successCount = results.filter(r => r.success).length;
      showMessage(`Disabled faults on ${successCount}/${serviceNames.length} services`, 'success');

      // Refresh all statuses
      const response = await getFaultStatus();
      if (response.services) {
        const statusMap = {};
        response.services.forEach(svc => {
          statusMap[svc.service] = svc.fault_status;
        });
        setFaultStatuses(statusMap);
      }
    } catch (error) {
      showMessage(`Failed to disable all faults: ${error.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const applyTemplate = (template) => {
    const config = FAULT_TEMPLATES[template].config;
    setFaultType(config.faultType);
    setErrorRate(config.errorRate);
    setLatencyMs(config.latencyMs);
    setDuration(config.duration);
  };

  const showMessage = (text, type) => {
    setMessage({ text, type });
    setTimeout(() => setMessage(null), 5000);
  };

  const getActiveFaultsCount = () => {
    return Object.values(faultStatuses).filter(status => status?.active === true).length;
  };

  return (
    <div className="mb-8">
      {/* Header - Always Visible */}
      <div
        className="bg-gradient-to-r from-warning-100 to-critical-100 dark:from-warning-900/20 dark:to-critical-900/20 rounded-lg p-3 cursor-pointer hover:shadow-md transition-all duration-200"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-warning-600 dark:text-warning-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                Fault Injection (Demo)
                {getActiveFaultsCount() > 0 && (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-critical-100 text-critical-800 dark:bg-critical-900/30 dark:text-critical-300">
                    {getActiveFaultsCount()} active
                  </span>
                )}
              </h2>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                {isExpanded ? 'Click to collapse' : 'Click to expand and inject faults for testing'}
              </p>
            </div>
          </div>
          <svg
            className={`h-4 w-4 text-gray-500 dark:text-gray-400 transition-transform duration-200 ${isExpanded ? 'transform rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* Expanded Panel */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mt-4 transition-colors duration-200">
              {/* Message Toast */}
              {message && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className={`mb-4 p-3 rounded-lg ${
                    message.type === 'success'
                      ? 'bg-healthy-100 dark:bg-healthy-900/20 text-healthy-700 dark:text-healthy-300'
                      : 'bg-critical-100 dark:bg-critical-900/20 text-critical-700 dark:text-critical-300'
                  }`}
                >
                  {message.text}
                </motion.div>
              )}

              <div className="grid md:grid-cols-2 gap-6">
                {/* Left Column - Configuration */}
                <div className="space-y-4">
                  {/* Service Selector */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Target Service
                    </label>
                    <select
                      value={selectedService}
                      onChange={(e) => setSelectedService(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-warning-500 focus:border-transparent transition-colors duration-200"
                      disabled={loading}
                    >
                      {services.map(service => (
                        <option key={service.name} value={service.name}>
                          {service.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Fault Type */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Fault Type
                    </label>
                    <div className="flex gap-2">
                      {['5xx', 'latency', 'timeout'].map(type => (
                        <button
                          key={type}
                          onClick={() => setFaultType(type)}
                          disabled={loading}
                          className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                            faultType === type
                              ? 'bg-warning-500 text-white shadow-md'
                              : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                          } disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                          {type === '5xx' ? '5xx Errors' : type === 'latency' ? 'Latency' : 'Timeout'}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Error Rate Slider (for 5xx and timeout) */}
                  {(faultType === '5xx' || faultType === 'timeout') && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Error Rate: {errorRate}%
                      </label>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        step="5"
                        value={errorRate}
                        onChange={(e) => setErrorRate(parseInt(e.target.value))}
                        disabled={loading}
                        className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
                      />
                      <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                        <span>0%</span>
                        <span>50%</span>
                        <span>100%</span>
                      </div>
                    </div>
                  )}

                  {/* Latency Input (for latency type) */}
                  {faultType === 'latency' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Latency (milliseconds)
                      </label>
                      <input
                        type="number"
                        min="100"
                        max="5000"
                        step="100"
                        value={latencyMs}
                        onChange={(e) => setLatencyMs(parseInt(e.target.value))}
                        disabled={loading}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-warning-500 focus:border-transparent transition-colors duration-200"
                      />
                    </div>
                  )}

                  {/* Duration */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Duration
                    </label>
                    <div className="flex gap-2">
                      {[60, 300, 600].map(dur => {
                        const label = dur === 60 ? '1 min' : dur === 300 ? '5 min' : '10 min';
                        return (
                          <button
                            key={dur}
                            onClick={() => setDuration(dur)}
                            disabled={loading}
                            className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                              duration === dur
                                ? 'bg-warning-500 text-white shadow-md'
                                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                            } disabled:opacity-50 disabled:cursor-not-allowed`}
                          >
                            {label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Right Column - Templates & Actions */}
                <div className="space-y-4">
                  {/* Quick Templates */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Quick Templates
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(FAULT_TEMPLATES).map(([key, template]) => (
                        <button
                          key={key}
                          onClick={() => applyTemplate(key)}
                          disabled={loading}
                          className="p-3 text-left border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <div className="font-medium text-sm text-gray-900 dark:text-white">
                            {template.name}
                          </div>
                          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            {template.description}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Fault Status */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Active Faults
                    </label>
                    <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 max-h-32 overflow-y-auto transition-colors duration-200">
                      {getActiveFaultsCount() === 0 ? (
                        <p className="text-sm text-gray-500 dark:text-gray-400">No active faults</p>
                      ) : (
                        <div className="space-y-2">
                          {Object.entries(faultStatuses).map(([service, status]) => {
                            if (!status?.active) return null;
                            return (
                              <div key={service} className="flex items-center justify-between text-sm">
                                <div>
                                  <span className="font-medium text-gray-900 dark:text-white">{service}</span>
                                  <span className="text-gray-500 dark:text-gray-400 ml-2">
                                    {status.type} fault
                                  </span>
                                </div>
                                <button
                                  onClick={() => handleDisableFault(service)}
                                  className="text-critical-600 dark:text-critical-400 hover:underline"
                                  disabled={loading}
                                >
                                  Disable
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="space-y-2 pt-4">
                    <button
                      onClick={handleInjectClick}
                      disabled={loading || !selectedService}
                      className="w-full px-4 py-3 bg-critical-600 hover:bg-critical-700 dark:bg-critical-500 dark:hover:bg-critical-600 text-white font-medium rounded-lg transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {loading ? (
                        <>
                          <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          Injecting...
                        </>
                      ) : (
                        <>
                          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          Inject Fault
                        </>
                      )}
                    </button>
                    <button
                      onClick={handleDisableAll}
                      disabled={loading || getActiveFaultsCount() === 0}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-medium rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Disable All Faults
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Confirmation Modal */}
      <FaultConfigModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onConfirm={handleConfirmInject}
        serviceName={selectedService}
        config={{ faultType, errorRate, latencyMs, duration }}
      />
    </div>
  );
};

export default FaultInjectionPanel;
