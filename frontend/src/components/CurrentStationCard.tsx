import React from 'react';
import { MapPin, Clock, Navigation, Milestone } from 'lucide-react';
import type { CurrentStation, HorizonPrediction } from '../types/eta';

interface CurrentStationCardProps {
  currentStation: CurrentStation;
  h1Prediction?: HorizonPrediction;
  totalHorizons?: number;
}

function formatTime(isoStr?: string): string {
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

export const CurrentStationCard: React.FC<CurrentStationCardProps> = ({
  currentStation,
  h1Prediction
}) => {
  const delay = currentStation.delay_minutes ?? 0;

  let delayVariant = 'ontime';
  let delayText = delay <= 0 ? 'On Time (0m)' : `+${delay} min`;

  if (delay > 20) {
    delayVariant = 'severe';
    delayText = `+${delay} min`;
  } else if (delay > 5) {
    delayVariant = 'moderate';
    delayText = `+${delay} min`;
  }

  const h1Delay = h1Prediction?.predicted_delay_minutes ?? 0;
  const h1DelayText = h1Delay <= 0 ? 'On Time' : `+${h1Delay.toFixed(1)}m`;

  return (
    <section className="live-status-cards-section" aria-label="Live Telemetry Status Cards">
      <div className="status-cards-grid">
        {/* Card 1: Current Location */}
        <div className="status-metric-card" id="card-current-location">
          <div className="card-top-strip">
            <span className="metric-caption">Current Location</span>
            <span className="metric-icon-wrap blue" aria-hidden="true">
              <MapPin size={17} />
            </span>
          </div>
          <div className="metric-body">
            <div className="metric-primary-row">
              <h3 className="metric-station-name">{currentStation.name || currentStation.code}</h3>
              <span className="station-code-badge">{currentStation.code}</span>
            </div>
            <span className="metric-subtext">Last recorded telemetry stop</span>
          </div>
        </div>

        {/* Card 2: Delay */}
        <div className="status-metric-card" id="card-current-delay">
          <div className="card-top-strip">
            <span className="metric-caption">Delay</span>
            <span className={`metric-icon-wrap ${delayVariant}`} aria-hidden="true">
              <Clock size={17} />
            </span>
          </div>
          <div className="metric-body">
            <div className="metric-primary-row">
              <span className={`metric-delay-pill ${delayVariant}`}>{delayText}</span>
            </div>
            <span className="metric-subtext">Live operational delay at location</span>
          </div>
        </div>

        {/* Card 3: Next Station */}
        <div className="status-metric-card" id="card-next-station">
          <div className="card-top-strip">
            <span className="metric-caption">Next Station</span>
            <span className="metric-icon-wrap cyan" aria-hidden="true">
              <Milestone size={17} />
            </span>
          </div>
          <div className="metric-body">
            <div className="metric-primary-row">
              <h3 className="metric-station-name">
                {h1Prediction ? h1Prediction.station : 'Final Stop Reached'}
              </h3>
              {h1Prediction && <span className="station-code-badge cyan">H1</span>}
            </div>
            <span className="metric-subtext">
              {h1Prediction
                ? `Scheduled: ${formatTime(h1Prediction.scheduled_arrival)}`
                : 'Journey Completed'}
            </span>
          </div>
        </div>

        {/* Card 4: ETA Prediction */}
        <div className="status-metric-card" id="card-eta-prediction">
          <div className="card-top-strip">
            <span className="metric-caption">ETA Prediction</span>
            <span className="metric-icon-wrap navy" aria-hidden="true">
              <Navigation size={17} />
            </span>
          </div>
          <div className="metric-body">
            <div className="metric-primary-row">
              <span className="metric-eta-time">
                {h1Prediction ? formatTime(h1Prediction.predicted_eta) : '--:--'}
              </span>
            </div>
            <span className="metric-subtext">
              {h1Prediction
                ? `Predicted delay: ${h1DelayText}`
                : 'No pending stops'}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};
