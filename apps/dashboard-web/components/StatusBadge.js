import React from 'react';

const StatusBadge = ({ status, size = 'md', animated = false }) => {
  const getStatusConfig = (status) => {
    switch (status?.toLowerCase()) {
      case 'healthy':
      case 'resolved':
      case 'success':
        return {
          color: 'bg-healthy-100 text-healthy-800 dark:bg-healthy-900 dark:text-healthy-200',
          icon: '🟢',
          label: 'Healthy'
        };
      case 'warning':
      case 'degraded':
        return {
          color: 'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-200',
          icon: '🟡',
          label: 'Warning'
        };
      case 'critical':
      case 'action_pending':
      case 'remediating':
      case 'failed':
        return {
          color: 'bg-critical-100 text-critical-800 dark:bg-critical-900 dark:text-critical-200',
          icon: '🔴',
          label: status === 'remediating' ? 'Remediating' : 'Critical'
        };
      default:
        return {
          color: 'bg-unknown-100 text-unknown-800 dark:bg-unknown-900 dark:text-unknown-200',
          icon: '⚪',
          label: 'Unknown'
        };
    }
  };

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-base'
  };

  const config = getStatusConfig(status);
  const animationClass = animated ? 'animate-pulse-slow' : '';

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 rounded-full font-medium
        ${config.color}
        ${sizeClasses[size]}
        ${animationClass}
      `}
    >
      <span className="text-xs">{config.icon}</span>
      {config.label}
    </span>
  );
};

export default StatusBadge;
