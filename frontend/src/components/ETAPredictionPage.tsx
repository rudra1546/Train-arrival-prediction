import React, { useState, useEffect, useCallback } from 'react';
import {
  Milestone,
  Clock,
  Calendar,
  Navigation,
  RefreshCw,
  Search,
  AlertCircle,
  MapPin,
  ArrowUpRight,
  Sparkles,
  Route,
  Activity,
  Layers
} from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { PredictionExplanation } from './PredictionExplanation';
import { LoadingSkeleton } from './LoadingSkeleton';
import { fetchTrainETA, fetchTrainRouteSchedule } from '../services/api';
import type { TrainETAResponse, HorizonPrediction, APIErrorState } from '../types/eta';
import type { LastSearchedTrain } from '../services/persistence';
import type { TrainRouteSchedule } from '../types/route';

interface ETAPredictionPageProps {
  savedTrain: LastSearchedTrain | null;
  onNavigateToSearch: () => void;
  onNavigateToTracking?: () => void;
}

function formatTimeString(isoStr?: string): string {
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

function formatDateString(isoStr?: string): string {
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

function computeTimeDifferenceMinutes(schedIso?: string, etaIso?: string): number | null {
  if (!schedIso || !etaIso) return null;
  try {
    const s = new Date(schedIso).getTime();
    const e = new Date(etaIso).getTime();
    if (!isNaN(s) && !isNaN(e)) {
      return Math.round((e - s) / 60000);
    }
  } catch {
    // fallback
  }
  return null;
}

export const ETAPredictionPage: React.FC<ETAPredictionPageProps> = ({
  savedTrain,
  onNavigateToSearch,
  onNavigateToTracking,
}) => {
  const [trainData, setTrainData] = useState<TrainETAResponse | null>(null);
  const [routeSchedule, setRouteSchedule] = useState<TrainRouteSchedule | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<APIErrorState | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const trainNo = savedTrain?.train_no || '';

  // 1. Fetch Real Live ETA and Route Schedule
  const loadData = useCallback(async (isManualRefresh = false) => {
    if (!trainNo) return;

    if (isManualRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const [etaRes, routeRes] = await Promise.all([
        fetchTrainETA(trainNo, savedTrain?.journey_date),
        fetchTrainRouteSchedule(trainNo).catch(() => null),
      ]);

      setTrainData(etaRes);
      if (routeRes) {
        setRouteSchedule(routeRes);
      }
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error('Failed to load ETA predictions:', err);
      setError(
        err?.title
          ? (err as APIErrorState)
          : {
              title: 'Telemetry Unavailable',
              message: `Could not retrieve live prediction data for Train ${trainNo}. Please verify connection and retry.`,
            }
      );
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [trainNo, savedTrain?.journey_date]);

  useEffect(() => {
    if (trainNo) {
      loadData(false);
    }
  }, [trainNo, loadData]);

  const handleRefresh = () => {
    loadData(true);
  };

  const formatLastUpdatedText = (date: Date | null): string => {
    if (!date) return 'Updated just now';
    const diffSec = Math.floor((Date.now() - date.getTime()) / 1000);
    if (diffSec < 20) return 'Updated just now';
    return `Updated ${date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true })}`;
  };

  // 2. EMPTY STATE — When no train has been selected
  if (!savedTrain) {
    return (
      <div className="eta-page-empty-container" role="region" aria-label="ETA Prediction Empty State">
        <div className="eta-page-empty-card">
          <div className="eta-empty-icon-wrap">
            <Milestone size={36} className="text-sky-600" />
          </div>
          <h2 className="eta-empty-title">No train selected</h2>
          <p className="eta-empty-description">
            Search and select a train from Indian Railways schedule records to view
            AI-powered multi-horizon arrival predictions (H1, H2, H3).
          </p>
          <button
            id="eta-search-train-btn"
            type="button"
            className="eta-search-btn primary"
            onClick={onNavigateToSearch}
          >
            <Search size={16} aria-hidden="true" />
            <span>Search Train</span>
          </button>
        </div>
      </div>
    );
  }

  // 3. Loading State (initial fetch)
  if (isLoading && !trainData) {
    return (
      <div className="eta-prediction-page" aria-label="Loading ETA Predictions">
        <LoadingSkeleton />
      </div>
    );
  }

  // 4. Calculate Journey Context Metrics
  const currentStationCode = trainData?.current_station?.code || '---';
  const currentStationName = trainData?.current_station?.name || currentStationCode;
  const currentDelayMinutes = trainData?.current_station?.delay_minutes ?? 0;

  // Find index in scheduled route if available
  const stops = routeSchedule?.stops || [];
  const currentIndex = stops.findIndex(
    (s) => s.station_code.toUpperCase() === currentStationCode.toUpperCase()
  );

  const totalStopsCount = routeSchedule?.total_stops || stops.length;
  const remainingStopsCount =
    currentIndex !== -1 && totalStopsCount > 0
      ? Math.max(0, totalStopsCount - currentIndex - 1)
      : trainData?.predictions?.length
      ? Math.max(0, totalStopsCount - 1)
      : 0;

  const currentStopNo = currentIndex !== -1 ? currentIndex + 1 : 1;
  const progressPercent =
    totalStopsCount > 1 && currentIndex !== -1
      ? Math.round((currentIndex / (totalStopsCount - 1)) * 100)
      : trainData?.predictions?.length
      ? 45
      : 0;

  // Remaining Distance calculation
  const currentDistanceKm = currentIndex !== -1 ? stops[currentIndex]?.distance || 0 : 0;
  const totalDistanceKm = stops.length > 0 ? stops[stops.length - 1]?.distance || 0 : 0;
  const remainingDistanceKm = totalDistanceKm > currentDistanceKm ? totalDistanceKm - currentDistanceKm : null;

  // Extract real H1, H2, H3 predictions
  const predictions = trainData?.predictions || [];
  const h1 = predictions.find((p) => p.horizon === 1);
  const h2 = predictions.find((p) => p.horizon === 2);
  const h3 = predictions.find((p) => p.horizon === 3);

  // Origin & Destination Terminals
  const originText = savedTrain?.origin || routeSchedule?.origin_name || 'Origin';
  const destText = savedTrain?.destination || routeSchedule?.dest_name || 'Destination';

  return (
    <div className="eta-prediction-page" aria-label="AI ETA Prediction Dashboard">
      {/* 1. PREDICTION HEADER */}
      <section className="eta-header-card" id="eta-prediction-header">
        <div className="eta-header-main">
          <div className="train-identity-col">
            <div className="train-no-box">
              <span className="train-no-text">{trainData?.train_no || trainNo}</span>
            </div>
            <div className="train-info-text">
              <div className="eta-header-meta-row">
                <span className="eta-model-pill">
                  <Sparkles size={12} className="text-amber-500" />
                  Multi-Horizon AI Inference
                </span>
                <span className="eta-date-pill">
                  <Calendar size={12} />
                  {trainData?.journey_date || savedTrain?.journey_date || 'Today'}
                </span>
              </div>
              <h2 className="eta-train-title">
                {trainData?.train_name || savedTrain?.train_name || `Train ${trainNo}`}
              </h2>
              <div className="eta-route-strip">
                <MapPin size={13} className="text-sky-600" />
                <span className="route-endpoints">{originText} &rarr; {destText}</span>
              </div>
            </div>
          </div>

          <div className="eta-header-status-col">
            <div className="status-badges-cluster">
              <StatusBadge status={trainData?.status || 'running'} />
              <span className={`delay-indicator-pill ${currentDelayMinutes <= 0 ? 'ontime' : currentDelayMinutes <= 15 ? 'minor' : 'major'}`}>
                {currentDelayMinutes <= 0
                  ? 'On Time (0m)'
                  : `+${currentDelayMinutes.toFixed(0)}m Delay`}
              </span>
            </div>

            <div className="eta-location-telemetry">
              <span className="loc-label">Current Location:</span>
              <strong className="loc-name">{currentStationName} ({currentStationCode})</strong>
            </div>

            <div className="eta-header-actions-group">
              {onNavigateToTracking && (
                <button
                  id="eta-nav-live-tracking-btn"
                  type="button"
                  className="eta-action-button tracking"
                  onClick={onNavigateToTracking}
                  title="View live GPS railway route map"
                >
                  <Navigation size={14} aria-hidden="true" />
                  <span>Live Tracking</span>
                </button>
              )}

              <button
                id="eta-refresh-btn"
                type="button"
                className="eta-action-button refresh"
                onClick={handleRefresh}
                disabled={isRefreshing || isLoading}
                title="Fetch fresh predictions from AI backend"
              >
                <RefreshCw size={14} className={isRefreshing ? 'spinning' : ''} aria-hidden="true" />
                <span>{isRefreshing ? 'Recomputing...' : 'Refresh ETA'}</span>
              </button>
            </div>

            <span className="eta-last-updated-text">
              <Clock size={11} />
              {formatLastUpdatedText(lastUpdated)}
            </span>
          </div>
        </div>
      </section>

      {/* ERROR BANNER IF API FAILED */}
      {error && (
        <div className="eta-error-banner" role="alert">
          <div className="eta-error-content">
            <AlertCircle size={20} className="text-rose-600 flex-shrink-0" />
            <div>
              <h4 className="error-title">{error.title}</h4>
              <p className="error-message">{error.message}</p>
            </div>
          </div>
          <button
            type="button"
            className="eta-retry-btn"
            onClick={() => loadData(false)}
          >
            Retry
          </button>
        </div>
      )}

      {/* 2. JOURNEY CONTEXT SUMMARY */}
      <section className="eta-journey-context-card" aria-label="Journey Progress Context">
        <div className="context-card-header">
          <div className="context-title-group">
            <Route size={18} className="text-sky-600" />
            <h3 className="context-title">Journey Operational Context</h3>
          </div>
          <span className="context-badge">
            Stop {currentStopNo} of {totalStopsCount || 'Route'}
          </span>
        </div>

        <div className="context-metrics-grid">
          {/* Current Station */}
          <div className="context-metric-cell">
            <span className="context-label">Current Station</span>
            <div className="context-val-box">
              <span className="context-primary-val">{currentStationName}</span>
              <span className="context-sub-val font-mono">{currentStationCode}</span>
            </div>
          </div>

          {/* Next Station (H1) */}
          <div className="context-metric-cell">
            <span className="context-label">Next Target Halt</span>
            <div className="context-val-box">
              <span className="context-primary-val text-brand">{h1?.station || 'Terminus'}</span>
              <span className="context-sub-val">Horizon 1 Forecast</span>
            </div>
          </div>

          {/* Remaining Halts */}
          <div className="context-metric-cell">
            <span className="context-label">Remaining Halts</span>
            <div className="context-val-box">
              <span className="context-primary-val">{remainingStopsCount} Stops</span>
              <span className="context-sub-val">Scheduled ahead</span>
            </div>
          </div>

          {/* Remaining Distance */}
          <div className="context-metric-cell">
            <span className="context-label">Remaining Distance</span>
            <div className="context-val-box">
              <span className="context-primary-val">
                {remainingDistanceKm !== null ? `${remainingDistanceKm} km` : 'Track Route'}
              </span>
              <span className="context-sub-val">
                {totalDistanceKm > 0 ? `of ${totalDistanceKm} km route` : 'to Destination'}
              </span>
            </div>
          </div>
        </div>

        {/* Progress Track Bar */}
        <div className="context-progress-bar-container">
          <div className="context-progress-labels">
            <span className="progress-origin-label">{originText}</span>
            <span className="progress-percent-label">{progressPercent}% Journey Completed</span>
            <span className="progress-dest-label">{destText}</span>
          </div>
          <div className="context-progress-track">
            <div
              className="context-progress-fill"
              style={{ width: `${Math.max(5, Math.min(100, progressPercent))}%` }}
            />
          </div>
        </div>
      </section>

      {/* 3. MAIN MULTI-HORIZON PREDICTIONS SECTION */}
      <section className="eta-main-predictions-section" aria-label="Multi-Horizon Forecasts">
        <div className="section-intro-header">
          <div className="intro-left">
            <div className="intro-icon-box">
              <Layers size={18} className="text-sky-600" />
            </div>
            <div>
              <h3 className="intro-title">Multi-Horizon Arrival Predictions</h3>
              <p className="intro-subtitle">
                Scheduled arrival timetable compared directly with AI machine learning forecasts
              </p>
            </div>
          </div>

          <div className="horizon-legend-pills">
            <span className="h-pill h1">H1: Next Halt</span>
            <span className="h-pill h2">H2: 2 Halts</span>
            <span className="h-pill h3">H3: 3 Halts</span>
          </div>
        </div>

        {/* Three Prediction Cards Grid */}
        <div className="prediction-cards-trio-grid">
          {/* CARD 1: Horizon 1 — Immediate Next Station */}
          <div className="horizon-prediction-card h1-card" id="prediction-card-h1">
            <div className="h-card-top-bar">
              <div className="h-tag-wrap">
                <span className="h-number-pill h1">Horizon 1</span>
                <span className="h-desc-text">Immediate Next Halt</span>
              </div>
              <span className="target-station-badge">{h1?.station || 'Next Station'}</span>
            </div>

            {h1 ? (
              <PredictionCardContent prediction={h1} />
            ) : (
              <div className="h-card-unavailable">
                <AlertCircle size={20} className="text-amber-500" />
                <p>Horizon 1 prediction unavailable from live telemetry stream.</p>
              </div>
            )}
          </div>

          {/* CARD 2: Horizon 2 — Following Station */}
          <div className="horizon-prediction-card h2-card" id="prediction-card-h2">
            <div className="h-card-top-bar">
              <div className="h-tag-wrap">
                <span className="h-number-pill h2">Horizon 2</span>
                <span className="h-desc-text">Two Halts Ahead</span>
              </div>
              <span className="target-station-badge">{h2?.station || 'Following Stop'}</span>
            </div>

            {h2 ? (
              <PredictionCardContent prediction={h2} />
            ) : (
              <div className="h-card-unavailable">
                <AlertCircle size={20} className="text-slate-400" />
                <p className="unavailable-title">Horizon 2 Forecast Unavailable</p>
                <span className="unavailable-desc">
                  {remainingStopsCount <= 1
                    ? 'Train is on its penultimate halt; fewer than 2 stops remain to destination.'
                    : 'Awaiting upstream telemetry synchronization for 2nd horizon.'}
                </span>
              </div>
            )}
          </div>

          {/* CARD 3: Horizon 3 — Third Station */}
          <div className="horizon-prediction-card h3-card" id="prediction-card-h3">
            <div className="h-card-top-bar">
              <div className="h-tag-wrap">
                <span className="h-number-pill h3">Horizon 3</span>
                <span className="h-desc-text">Three Halts Ahead</span>
              </div>
              <span className="target-station-badge">{h3?.station || 'Third Stop'}</span>
            </div>

            {h3 ? (
              <PredictionCardContent prediction={h3} />
            ) : (
              <div className="h-card-unavailable">
                <AlertCircle size={20} className="text-slate-400" />
                <p className="unavailable-title">Horizon 3 Forecast Unavailable</p>
                <span className="unavailable-desc">
                  {remainingStopsCount <= 2
                    ? 'Train is within 2 halts of destination terminus; Horizon 3 is beyond the final stop.'
                    : 'Awaiting upstream telemetry synchronization for 3rd horizon.'}
                </span>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* 4. DETAILED SIDE-BY-SIDE SCHEDULED VS PREDICTED TABLE */}
      {predictions.length > 0 && (
        <section className="eta-comparison-table-section" aria-label="Detailed Timetable Comparison">
          <div className="comparison-table-card">
            <div className="table-header-row">
              <div className="table-title-group">
                <Activity size={17} className="text-sky-600" />
                <h4 className="table-title">Scheduled Timetable vs AI Forecast Matrix</h4>
              </div>
              <span className="table-tag">Verified Indian Railways Schedule</span>
            </div>

            <div className="table-responsive-wrapper">
              <table className="eta-comparison-table">
                <thead>
                  <tr>
                    <th>Horizon</th>
                    <th>Target Station</th>
                    <th>Scheduled Arrival</th>
                    <th>AI Predicted ETA</th>
                    <th>Forecast Variance</th>
                    <th>Predicted Delay</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {predictions.map((p) => {
                    const delay = p.predicted_delay_minutes ?? 0;
                    const diffMin = computeTimeDifferenceMinutes(p.scheduled_arrival, p.predicted_eta);
                    const diffText =
                      diffMin === null
                        ? delay > 0
                          ? `+${delay.toFixed(1)}m`
                          : 'On Time'
                        : diffMin > 0
                        ? `+${diffMin}m late`
                        : diffMin < 0
                        ? `${diffMin}m early`
                        : 'On Time';

                    return (
                      <tr key={`table-pred-h${p.horizon}`}>
                        <td>
                          <span className={`table-h-tag h${p.horizon}`}>
                            Horizon {p.horizon}
                          </span>
                        </td>
                        <td>
                          <div className="table-stn-cell">
                            <strong>{p.station}</strong>
                          </div>
                        </td>
                        <td>
                          <div className="table-time-cell">
                            <Clock size={12} className="text-slate-400" />
                            <span>{formatTimeString(p.scheduled_arrival)}</span>
                            <small className="text-slate-400">{formatDateString(p.scheduled_arrival)}</small>
                          </div>
                        </td>
                        <td>
                          <div className="table-time-cell eta-highlight">
                            <Navigation size={12} className="text-sky-600" />
                            <strong>{formatTimeString(p.predicted_eta)}</strong>
                            <small>{formatDateString(p.predicted_eta)}</small>
                          </div>
                        </td>
                        <td>
                          <span className={`variance-pill ${delay > 15 ? 'major' : delay > 0 ? 'minor' : 'ontime'}`}>
                            {diffText}
                          </span>
                        </td>
                        <td>
                          <span className="font-mono font-semibold">
                            {delay <= 0 ? '0.0 min' : `+${delay.toFixed(1)} min`}
                          </span>
                        </td>
                        <td>
                          <span className={`table-status-dot ${delay <= 0 ? 'green' : delay <= 15 ? 'amber' : 'rose'}`}>
                            {delay <= 0 ? 'On Time' : delay <= 15 ? 'Moderate' : 'Delayed'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {/* 5. TECHNICAL ML PIPELINE EXPLANATION */}
      <PredictionExplanation />
    </div>
  );
};

// Subcomponent: Reusable visual comparison block for each Horizon card
function PredictionCardContent({ prediction }: { prediction: HorizonPrediction }) {
  const predDelay = prediction.predicted_delay_minutes ?? 0;
  const isEarly = predDelay < 0;
  const delayDisplay = isEarly
    ? `${predDelay.toFixed(1)} min (Early)`
    : predDelay === 0
    ? 'On Time (0.0 min)'
    : `+${predDelay.toFixed(1)} min delay`;

  const delaySeverity = predDelay <= 5 ? 'ontime' : predDelay <= 20 ? 'moderate' : 'severe';

  const diffMin = computeTimeDifferenceMinutes(prediction.scheduled_arrival, prediction.predicted_eta);
  const comparisonText =
    diffMin === null
      ? predDelay > 0
        ? `+${predDelay.toFixed(0)}m later than timetable`
        : 'Aligns with scheduled timetable'
      : diffMin > 0
      ? `+${diffMin}m later than timetable`
      : diffMin < 0
      ? `${Math.abs(diffMin)}m earlier than timetable`
      : 'Arriving exactly on schedule';

  return (
    <div className="h-card-inner-body">
      {/* Visual Comparison: Scheduled vs AI Predicted ETA */}
      <div className="times-comparison-grid eta-enhanced-grid">
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
          <ArrowUpRight size={18} />
        </div>

        <div className="time-comparison-col predicted">
          <span className="col-label highlight">
            <Navigation size={12} />
            AI Predicted ETA
          </span>
          <div className="col-time-display eta">{formatTimeString(prediction.predicted_eta)}</div>
          <span className="col-date-display eta">
            <Calendar size={11} />
            {formatDateString(prediction.predicted_eta)}
          </span>
        </div>
      </div>

      {/* Difference Pill */}
      <div className="comparison-delta-strip">
        <span className="delta-caption">Timetable vs AI:</span>
        <span className={`delta-tag ${predDelay > 15 ? 'severe' : predDelay > 0 ? 'late' : 'ontime'}`}>
          {comparisonText}
        </span>
      </div>

      {/* Bottom Footer */}
      <div className="pred-delay-footer">
        <span className="footer-label">Predicted Delay:</span>
        <span className={`pred-delay-badge ${delaySeverity}`}>
          {delayDisplay}
        </span>
      </div>
    </div>
  );
}
