import React from 'react';
import { Compass } from 'lucide-react';

interface EmptyStateProps {
  onSelectTrain: (trainNo: string) => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ onSelectTrain }) => {
  return (
    <div className="empty-state-card">
      <div className="empty-state-icon" aria-hidden="true">
        <Compass size={28} />
      </div>
      <h3>Enter a train number to view its live ETA</h3>
      <p>
        Tracks real-time running telemetry across Indian Railways and generates dynamic multi-horizon
        arrival forecasts powered by machine learning.
      </p>
      <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'center' }}>
        <button
          type="button"
          className="quick-chip"
          onClick={() => onSelectTrain('12301')}
        >
          Track 12301 (Howrah Rajdhani)
        </button>
        <button
          type="button"
          className="quick-chip"
          onClick={() => onSelectTrain('12951')}
        >
          Track 12951 (Mumbai Rajdhani)
        </button>
      </div>
    </div>
  );
};
