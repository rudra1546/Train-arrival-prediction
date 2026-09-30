import React from 'react';
import { RotateCw } from 'lucide-react';

export const LoadingSkeleton: React.FC = () => {
  return (
    <div className="skeleton-container" aria-label="Loading live train data" aria-busy="true">
      {/* Banner */}
      <div className="skeleton-loading-banner">
        <RotateCw size={18} className="skeleton-spin-icon" aria-hidden="true" />
        <span className="banner-text">Ingesting live RailRadar telemetry & computing XGBoost multi-horizon ETA forecasts...</span>
      </div>

      {/* Overview Skeleton */}
      <div className="skeleton-card overview-skel">
        <div className="skel-bone skel-title" />
        <div className="skel-bone skel-sub" />
      </div>

      {/* Metric Cards Skeleton (4 columns) */}
      <div className="skeleton-metric-grid">
        <div className="skeleton-card metric-skel">
          <div className="skel-bone skel-badge" />
          <div className="skel-bone skel-val" />
        </div>
        <div className="skeleton-card metric-skel">
          <div className="skel-bone skel-badge" />
          <div className="skel-bone skel-val" />
        </div>
        <div className="skeleton-card metric-skel">
          <div className="skel-bone skel-badge" />
          <div className="skel-bone skel-val" />
        </div>
        <div className="skeleton-card metric-skel">
          <div className="skel-bone skel-badge" />
          <div className="skel-bone skel-val" />
        </div>
      </div>

      {/* Prediction Cards Skeleton (3 columns) */}
      <div className="skeleton-prediction-grid">
        <div className="skeleton-card pred-skel">
          <div className="skel-bone skel-pred-header" />
          <div className="skel-bone skel-pred-body" />
        </div>
        <div className="skeleton-card pred-skel">
          <div className="skel-bone skel-pred-header" />
          <div className="skel-bone skel-pred-body" />
        </div>
        <div className="skeleton-card pred-skel">
          <div className="skel-bone skel-pred-header" />
          <div className="skel-bone skel-pred-body" />
        </div>
      </div>
    </div>
  );
};
