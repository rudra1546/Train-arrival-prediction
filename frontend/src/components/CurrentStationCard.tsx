import React from 'react';
import { MapPin, Clock } from 'lucide-react';
import type { CurrentStation } from '../types/eta';

interface CurrentStationCardProps {
  currentStation: CurrentStation;
}

export const CurrentStationCard: React.FC<CurrentStationCardProps> = ({ currentStation }) => {
  const delay = currentStation.delay_minutes ?? 0;

  let delayClass = 'delay-tag ontime';
  let delayText = delay <= 0 ? 'On Time' : `+${delay} min`;

  if (delay > 20) {
    delayClass = 'delay-tag severe';
    delayText = `+${delay} min`;
  } else if (delay > 5) {
    delayClass = 'delay-tag moderate';
    delayText = `+${delay} min`;
  }

  return (
    <div className="current-station-card">
      <div className="station-info-left">
        <div className="station-pin-icon" aria-hidden="true">
          <MapPin size={24} />
        </div>
        <div className="station-names-box">
          <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
            Current / Last Station Passed
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.2rem' }}>
            <h3>{currentStation.name || currentStation.code}</h3>
            <span className="station-code-pill">{currentStation.code}</span>
          </div>
        </div>
      </div>

      <div className="delay-indicator-badge">
        <span className="delay-caption">Live Operational Delay</span>
        <span className={delayClass}>
          <Clock size={16} />
          {delayText}
        </span>
      </div>
    </div>
  );
};
