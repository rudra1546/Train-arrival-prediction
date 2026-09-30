import React from 'react';

export const LoadingSkeleton: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="skeleton-card">
        <div className="loading-banner">
          <div className="spinner" aria-hidden="true"></div>
          <span>Fetching live train data and computing dynamic ETA forecast...</span>
        </div>
        <div className="skeleton-line short"></div>
        <div className="skeleton-line medium"></div>
        <div className="skeleton-line tall"></div>
      </div>
    </div>
  );
};
