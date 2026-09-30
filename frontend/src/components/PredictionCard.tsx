import React from 'react';
import type { HorizonPrediction } from '../types/eta';
import { Clock, Calendar, Navigation, ArrowUpRight } from 'lucide-react';

interface PredictionCardProps {
  prediction: HorizonPrediction;
}

function formatTimeString(isoStr: string): string {
  if (!isoStr) return '--:--';
  try {
    const d = new Date(isoStr);
    if (!isNaN(d.getTime())) {
      return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
    }
  } catch {
    // fallback
  }
  if (isoStr.includes('T')) {
    return isoStr.split('T')[1].substring(0, 5);
  }
  return isoStr;
}

function formatDateString(isoStr: string): string {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    if (!isNaN(d.getTime())) {
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  } catch {
    // fallback
  }
  if (isoStr.includes('T')) {
    return isoStr.split('T')[0];
  }
  return '';
}

export const PredictionCard: React.FC<PredictionCardProps> = ({ prediction }) => {
  const horizon = prediction.horizon;

  let horizonLabel = 'Next Station';
  let horizonClass = 'horizon-tag h1';
  let horizonColor = 'blue';

  if (horizon === 2) {
    horizonLabel = '2 Stations Ahead';
    horizonClass = 'horizon-tag h2';
    horizonColor = 'teal';
  } else if (horizon === 3) {
    horizonLabel = '3 Stations Ahead';
    horizonClass = 'horizon-tag h3';
    horizonColor = 'indigo';
  }

  const predDelay = prediction.predicted_delay_minutes ?? 0;
  const isEarly = predDelay < 0;
  const delayDisplay = isEarly
    ? `${predDelay.toFixed(1)} min (Early)`
    : predDelay === 0
    ? 'On Time (0.0 min)'
    : `+${predDelay.toFixed(1)} min delay`;

  const delaySeverity = predDelay <= 5 ? 'ontime' : predDelay <= 20 ? 'moderate' : 'severe';

  return (
    <div className={`prediction-card horizon-${horizonColor}`}>
      {/* Top Header */}
      <div className="pred-card-header">
        <div className="pred-horizon-group">
          <span className={horizonClass}>Horizon {horizon}</span>
          <span className="pred-horizon-subtitle">{horizonLabel}</span>
        </div>
        <div className="target-station-pill">
          <span className="target-station-name">{prediction.station}</span>
        </div>
      </div>

      {/* Comparison Grid: Scheduled vs Predicted ETA */}
      <div className="times-comparison-grid">
        <div className="time-comparison-col scheduled">
          <span className="col-label">
            <Clock size={12} />
            Scheduled
          </span>
          <div className="col-time-display">{formatTimeString(prediction.scheduled_arrival)}</div>
          <span className="col-date-display">
            <Calendar size={11} />
            {formatDateString(prediction.scheduled_arrival)}
          </span>
        </div>

        <div className="time-comparison-divider" aria-hidden="true">
          <ArrowUpRight size={16} />
        </div>

        <div className="time-comparison-col predicted">
          <span className="col-label highlight">
            <Navigation size={12} />
            Predicted ETA
          </span>
          <div className="col-time-display eta">{formatTimeString(prediction.predicted_eta)}</div>
          <span className="col-date-display eta">
            <Calendar size={11} />
            {formatDateString(prediction.predicted_eta)}
          </span>
        </div>
      </div>

      {/* Bottom Delay Row */}
      <div className="pred-delay-footer">
        <span className="footer-label">Predicted Delay:</span>
        <span className={`pred-delay-badge ${delaySeverity}`}>
          {delayDisplay}
        </span>
      </div>
    </div>
  );
};
