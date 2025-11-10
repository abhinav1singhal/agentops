import React from 'react';

const LoadingSkeleton = ({ type = 'card', count = 1 }) => {
  const shimmerClass = 'animate-shimmer bg-gradient-to-r from-gray-200 via-gray-300 to-gray-200 dark:from-gray-700 dark:via-gray-600 dark:to-gray-700';

  const ServiceCardSkeleton = () => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className={`h-6 w-32 rounded ${shimmerClass}`} style={{ backgroundSize: '1000px 100%' }} />
        <div className={`h-6 w-20 rounded-full ${shimmerClass}`} style={{ backgroundSize: '1000px 100%' }} />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className={`h-4 w-24 rounded mb-2 ${shimmerClass}`} style={{ backgroundSize: '1000px 100%' }} />
          <div className={`h-6 w-16 rounded ${shimmerClass}`} style={{ backgroundSize: '1000px 100%' }} />
        </div>
        <div>
          <div className={`h-4 w-24 rounded mb-2 ${shimmerClass}`} style={{ backgroundSize: '1000px 100%' }} />
          <div className={`h-6 w-20 rounded ${shimmerClass}`} style={{ backgroundSize: '1000px 100%' }} />
        </div>
      </div>
      <div className={`h-4 w-40 rounded ${shimmerClass}`} style={{ backgroundSize: '1000px 100%' }} />
    </div>
  );

  const IncidentCardSkeleton = () => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 space-y-3">
      <div className="flex items-start justify-between">
        <div className="space-y-2 flex-1">
          <div className={`h-5 w-48 rounded ${shimmerClass}`} style={{ backgroundSize: '1000px 100%' }} />
          <div className={`h-4 w-32 rounded ${shimmerClass}`} style={{ backgroundSize: '1000px 100%' }} />
        </div>
        <div className={`h-6 w-20 rounded-full ${shimmerClass}`} style={{ backgroundSize: '1000px 100%' }} />
      </div>
      <div className={`h-16 w-full rounded ${shimmerClass}`} style={{ backgroundSize: '1000px 100%' }} />
    </div>
  );

  const ChartSkeleton = () => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 space-y-4">
      <div className={`h-6 w-40 rounded ${shimmerClass}`} style={{ backgroundSize: '1000px 100%' }} />
      <div className={`h-64 w-full rounded ${shimmerClass}`} style={{ backgroundSize: '1000px 100%' }} />
    </div>
  );

  const skeletonComponents = {
    card: ServiceCardSkeleton,
    incident: IncidentCardSkeleton,
    chart: ChartSkeleton,
  };

  const SkeletonComponent = skeletonComponents[type] || ServiceCardSkeleton;

  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <SkeletonComponent key={index} />
      ))}
    </>
  );
};

export default LoadingSkeleton;
