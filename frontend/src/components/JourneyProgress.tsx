import React from 'react';
import { MapPin, Navigation, Milestone, ArrowRight, Clock } from 'lucide-react';
import type { CurrentStation, HorizonPrediction } from '../types/eta';

interface JourneyProgressProps {
  currentStation: CurrentStation;
  predictions: HorizonPrediction[];
}

function formatTime(isoStr: string): string {
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

export const JourneyProgress: React.FC<JourneyProgressProps> = ({
  currentStation,
  predictions
}) => {
  const sortedPreds = [...predictions].sort((a, b) => a.horizon - b.horizon);
  const currentDelay = currentStation.delay_minutes ?? 0;

  return (
    <section className="journey-progress-section" id="journey-progress-section">
      <div className="section-header-block">
        <div className="section-title-with-icon">
          <Milestone size={18} className="section-icon" aria-hidden="true" />
          <h3 className="section-title">Journey Progress</h3>
        </div>
        <span className="route-status-badge">
          Live Telemetry Flow
        </span>
      </div>

      <div className="journey-timeline-container">
        {/* Step 1: Current Station */}
        <div className="journey-step current-step">
          <div className="step-node-col">
            <div className="step-node current" aria-label="Current station node">
              <MapPin size={16} />
              <div className="node-radar-ping" aria-hidden="true" />
            </div>
            {sortedPreds.length > 0 && <div className="step-track-line active" />}
          </div>
          <div className="step-content-card">
            <div className="step-tag current">Current / Last Station</div>
            <div className="step-station-header">
              <h4 className="step-station-name">{currentStation.name || currentStation.code}</h4>
              <span className="step-station-code">{currentStation.code}</span>
            </div>
            <div className="step-meta-row">
              <span className="step-meta-delay">
                <Clock size={13} />
                {currentDelay <= 0 ? 'Passed On Time' : `Passed with +${currentDelay.toFixed(0)} min delay`}
              </span>
            </div>
          </div>
        </div>

        {/* Subsequent Steps: Predicted Horizons */}
        {sortedPreds.map((pred, idx) => {
          const isNext = pred.horizon === 1;
          const isLast = idx === sortedPreds.length - 1;
          const predDelay = pred.predicted_delay_minutes ?? 0;
          const delayText = predDelay <= 0 ? 'On Time' : `+${predDelay.toFixed(1)}m delay`;

          return (
            <div key={pred.horizon} className={`journey-step predicted-step ${isNext ? 'next-step' : ''}`}>
              <div className="step-node-col">
                <div className={`step-node ${isNext ? 'next' : 'future'}`}>
                  {isNext ? <Navigation size={14} /> : <span className="horizon-num-pill">H{pred.horizon}</span>}
                </div>
                {!isLast && <div className="step-track-line" />}
              </div>
              <div className="step-content-card">
                <div className="step-tag-row">
                  <span className={`step-tag ${isNext ? 'next' : 'future'}`}>
                    {pred.horizon === 1 ? 'Next Scheduled Stop' : `Horizon ${pred.horizon} Ahead`}
                  </span>
                  <span className="step-eta-delay-badge">{delayText}</span>
                </div>
                <div className="step-station-header">
                  <h4 className="step-station-name">{pred.station}</h4>
                  <span className="step-station-code">{pred.station}</span>
                </div>
                <div className="step-schedule-flow">
                  <span className="sched-time">Sched: {formatTime(pred.scheduled_arrival)}</span>
                  <ArrowRight size={13} className="flow-arrow" />
                  <span className="eta-time">Predicted ETA: <strong>{formatTime(pred.predicted_eta)}</strong></span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
};
