import type { HorizonPrediction } from '../types/eta';

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
    // ignore
  }
  // Fallback to substring
  if (isoStr.includes('T')) {
    const timePart = isoStr.split('T')[1];
    return timePart.substring(0, 5);
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
    // ignore
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

  if (horizon === 2) {
    horizonLabel = '2 Stations Ahead';
    horizonClass = 'horizon-tag h2';
  } else if (horizon === 3) {
    horizonLabel = '3 Stations Ahead';
    horizonClass = 'horizon-tag h3';
  }

  const predDelay = prediction.predicted_delay_minutes ?? 0;
  const isDelayEarly = predDelay < 0;
  const delayDisplay = isDelayEarly
    ? `${predDelay.toFixed(1)} min (Early)`
    : predDelay === 0
    ? '0.0 min (On Time)'
    : `+${predDelay.toFixed(1)} min`;

  const delayColor = predDelay <= 5 ? 'var(--color-ontime)' : predDelay <= 20 ? 'var(--color-moderate)' : 'var(--color-severe)';

  return (
    <div className="prediction-card">
      <div className="pred-card-header">
        <span className={horizonClass}>{horizonLabel}</span>
        <span className="target-station-name">{prediction.station}</span>
      </div>

      <div className="times-comparison-grid">
        <div className="time-box">
          <div className="time-box-label">Scheduled</div>
          <div className="time-box-value">{formatTimeString(prediction.scheduled_arrival)}</div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
            {formatDateString(prediction.scheduled_arrival)}
          </div>
        </div>

        <div className="time-box eta-box">
          <div className="time-box-label">Predicted ETA</div>
          <div className="time-box-value">{formatTimeString(prediction.predicted_eta)}</div>
          <div style={{ fontSize: '0.6875rem', color: 'var(--brand-blue)', marginTop: '0.15rem' }}>
            {formatDateString(prediction.predicted_eta)}
          </div>
        </div>
      </div>

      <div className="pred-delay-row">
        <span className="pred-delay-label">Predicted Delay:</span>
        <span className="pred-delay-value" style={{ color: delayColor }}>
          {delayDisplay}
        </span>
      </div>
    </div>
  );
};
