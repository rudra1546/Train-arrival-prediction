import React from 'react';
import { Calendar, RefreshCw, Radio, MapPin, ArrowRight, X, Navigation, Milestone } from 'lucide-react';
import { StatusBadge } from './StatusBadge';

interface TrainSummaryProps {
  trainNo: string;
  trainName: string;
  status: string;
  journeyDate: string;
  origin?: string;
  destination?: string;
  lastUpdatedText?: string;
  onRefresh: () => void;
  onClearTrain?: () => void;
  onViewLiveTracking?: () => void;
  onViewETAPrediction?: () => void;
  isLoading: boolean;
}

export const TrainSummary: React.FC<TrainSummaryProps> = ({
  trainNo,
  trainName,
  status,
  journeyDate,
  origin,
  destination,
  lastUpdatedText,
  onRefresh,
  onClearTrain,
  onViewLiveTracking,
  onViewETAPrediction,
  isLoading
}) => {
  return (
    <section className="train-overview-card" id="current-train-status-card" aria-label="Current Train Status">
      <div className="overview-header-row">
        <div className="train-identity-block">
          <div className="train-number-badge">
            <span className="train-number-text">{trainNo}</span>
          </div>
          <div className="train-name-block">
            <div className="train-top-meta-row">
              <span className="overview-section-tag">Current Train Status</span>
              {origin && destination && (
                <div className="train-route-pill" title={`${origin} to ${destination}`}>
                  <MapPin size={12} className="route-pin-icon" aria-hidden="true" />
                  <span className="route-terminal">{origin}</span>
                  <ArrowRight size={12} className="route-arrow-icon" aria-hidden="true" />
                  <span className="route-terminal">{destination}</span>
                </div>
              )}
            </div>
            <h2 className="train-name-heading">{trainName}</h2>
            <div className="train-meta-tags">
              <span className="telemetry-source-tag">
                <Radio size={12} className="tag-live-dot" />
                Live Railway Telemetry
              </span>
              <span className="journey-date-tag">
                <Calendar size={13} />
                Journey Date: {journeyDate || 'Today'}
              </span>
            </div>
          </div>
        </div>

        <div className="overview-actions-block">
          <StatusBadge status={status} />
          {lastUpdatedText && (
            <span className="overview-timestamp">{lastUpdatedText}</span>
          )}
          
          <div className="overview-buttons-group">
            {onViewLiveTracking && (
              <button
                id="view-live-tracking-btn"
                type="button"
                className="overview-action-btn tracking"
                onClick={onViewLiveTracking}
                title="View live tracking telemetry"
              >
                <Navigation size={13} aria-hidden="true" />
                <span>Live Tracking</span>
              </button>
            )}

            {onViewETAPrediction && (
              <button
                id="view-eta-prediction-btn"
                type="button"
                className="overview-action-btn prediction"
                onClick={onViewETAPrediction}
                title="View multi-horizon arrival predictions"
              >
                <Milestone size={13} aria-hidden="true" />
                <span>ETA Forecasts</span>
              </button>
            )}

            <button
              id="refresh-eta-btn"
              type="button"
              className="overview-action-btn refresh"
              onClick={onRefresh}
              disabled={isLoading}
              title="Refresh live telemetry and recompute ETA"
            >
              <RefreshCw size={13} className={isLoading ? 'spinning' : ''} aria-hidden="true" />
              <span>Refresh ETA</span>
            </button>

            {onClearTrain && (
              <button
                id="clear-selected-train-btn"
                type="button"
                className="overview-action-btn clear"
                onClick={onClearTrain}
                title="Clear selected train and return to empty search"
              >
                <X size={13} aria-hidden="true" />
                <span>Clear</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};
