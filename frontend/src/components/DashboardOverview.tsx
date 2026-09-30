import React, { useState, useEffect, useCallback } from 'react';
import {
  Radio,
  MapPin,
  Clock,
  Milestone,
  Navigation,
  RefreshCw,
  Search,
  X,
  AlertCircle,
  Calendar,
  ArrowRight,
  ChevronRight,
  TrendingUp
} from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { EmptyState } from './EmptyState';
import { LoadingSkeleton } from './LoadingSkeleton';
import { PredictionExplanation } from './PredictionExplanation';
import { fetchTrainETA, fetchTrainRouteSchedule } from '../services/api';
import type { TrainETAResponse, APIErrorState, HorizonPrediction } from '../types/eta';
import type { LastSearchedTrain } from '../services/persistence';
import type { TrainRouteSchedule, RouteStop } from '../types/route';

interface DashboardOverviewProps {
  savedTrain: LastSearchedTrain | null;
  onNavigateToSearch: () => void;
  onNavigateToTracking: () => void;
  onNavigateToPrediction: () => void;
  onClearTrain: () => void;
  refreshTrigger?: number;
  onLoadingChange?: (loading: boolean) => void;
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

export const DashboardOverview: React.FC<DashboardOverviewProps> = ({
  savedTrain,
  onNavigateToSearch,
  onNavigateToTracking,
  onNavigateToPrediction,
  onClearTrain,
  refreshTrigger = 0,
  onLoadingChange
}) => {
  const [trainData, setTrainData] = useState<TrainETAResponse | null>(null);
  const [routeSchedule, setRouteSchedule] = useState<TrainRouteSchedule | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(Boolean(savedTrain?.train_no));
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<APIErrorState | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const trainNo = savedTrain?.train_no || '';

  const loadDashboardData = useCallback(async (isRefreshAction = false) => {
    if (!trainNo) {
      setIsLoading(false);
      onLoadingChange?.(false);
      return;
    }

    if (isRefreshAction) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    onLoadingChange?.(true);
    setError(null);

    try {
      // Fetch both real ETA and real route stops
      const livePromise = fetchTrainETA(trainNo, savedTrain?.journey_date);
      const routePromise = fetchTrainRouteSchedule(trainNo).catch(() => null);

      const [live, route] = await Promise.all([livePromise, routePromise]);

      setTrainData(live);
      setRouteSchedule(route);
      setLastUpdated(new Date());
    } catch (err: any) {
      setError(err as APIErrorState);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
      onLoadingChange?.(false);
    }
  }, [trainNo, savedTrain?.journey_date, onLoadingChange]);

  // Initial load when train number changes
  useEffect(() => {
    if (trainNo) {
      loadDashboardData(false);
    } else {
      setTrainData(null);
      setRouteSchedule(null);
      setIsLoading(false);
    }
  }, [trainNo, loadDashboardData]);

  // External refresh trigger from Header
  useEffect(() => {
    if (refreshTrigger > 0 && trainNo) {
      loadDashboardData(true);
    }
  }, [refreshTrigger, trainNo, loadDashboardData]);

  const handleRefresh = () => {
    loadDashboardData(true);
  };

  const formatLastUpdatedText = (date: Date | null): string => {
    if (!date) return 'Awaiting telemetry';
    const diffSec = Math.floor((Date.now() - date.getTime()) / 1000);
    if (diffSec < 20) return 'Updated just now';
    return `Updated ${date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true })}`;
  };

  // ---------------------------------------------------------------------------
  // CASE 1: NO PREVIOUSLY SEARCHED TRAIN
  // ---------------------------------------------------------------------------
  if (!savedTrain || !savedTrain.train_no) {
    return (
      <div className="dashboard-view-container" aria-label="Dashboard Overview - Empty State">
        <EmptyState onNavigateToSearch={onNavigateToSearch} isLoading={isLoading} />
        <PredictionExplanation />
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // INITIAL LOADING STATE
  // ---------------------------------------------------------------------------
  if (isLoading && !trainData && !error) {
    return (
      <div className="dashboard-view-container loading-view" aria-label="Loading Dashboard Data">
        <LoadingSkeleton />
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // ERROR STATE (API unavailable, but saved train identity kept visible)
  // ---------------------------------------------------------------------------
  if (error && !trainData) {
    return (
      <div className="dashboard-view-container error-view" aria-label="Dashboard Error State">
        {/* Saved Train Identity Banner */}
        <section className="train-overview-card" aria-label="Saved Train Overview">
          <div className="overview-header-row">
            <div className="train-identity-block">
              <div className="train-number-badge">
                <span className="train-number-text">{savedTrain.train_no}</span>
              </div>
              <div className="train-name-block">
                <div className="train-top-meta-row">
                  <span className="overview-section-tag">Saved Selected Train</span>
                  {savedTrain.origin && savedTrain.destination && (
                    <div className="train-route-pill" title={`${savedTrain.origin} to ${savedTrain.destination}`}>
                      <MapPin size={12} className="route-pin-icon" aria-hidden="true" />
                      <span className="route-terminal">{savedTrain.origin}</span>
                      <ArrowRight size={12} className="route-arrow-icon" aria-hidden="true" />
                      <span className="route-terminal">{savedTrain.destination}</span>
                    </div>
                  )}
                </div>
                <h2 className="train-name-heading">{savedTrain.train_name}</h2>
                <div className="train-meta-tags">
                  <span className="journey-date-tag">
                    <Calendar size={13} />
                    Journey Date: {savedTrain.journey_date || 'Today'}
                  </span>
                </div>
              </div>
            </div>

            <div className="overview-actions-block">
              <div className="overview-buttons-group">
                <button
                  type="button"
                  className="overview-action-btn refresh"
                  onClick={handleRefresh}
                  disabled={isRefreshing}
                >
                  <RefreshCw size={13} className={isRefreshing ? 'spinning' : ''} aria-hidden="true" />
                  <span>Retry</span>
                </button>
                <button
                  type="button"
                  className="overview-action-btn clear"
                  onClick={onClearTrain}
                  title="Clear selected train and return to empty dashboard"
                >
                  <X size={13} aria-hidden="true" />
                  <span>Clear Train</span>
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* API Error Notification Card */}
        <div className="error-state-card" role="alert">
          <div className="error-icon-box" aria-hidden="true">
            <AlertCircle size={22} className="error-icon" />
          </div>
          <div className="error-details-box">
            <div className="error-title-row">
              <h4 className="error-title-text">{error.title || 'Live Railway Telemetry Unavailable'}</h4>
              {error.statusCode ? (
                <span className="error-code-badge">HTTP {error.statusCode}</span>
              ) : null}
            </div>
            <p className="error-message-text">{error.message}</p>
            <div className="error-actions-row">
              <button
                id="dash-error-retry-btn"
                type="button"
                className="error-retry-btn"
                onClick={() => loadDashboardData(false)}
              >
                <RefreshCw size={14} aria-hidden="true" />
                <span>Retry Connection</span>
              </button>
              <button
                id="dash-error-search-btn"
                type="button"
                className="error-secondary-btn"
                onClick={onNavigateToSearch}
              >
                <Search size={14} aria-hidden="true" />
                <span>Search Another Train</span>
              </button>
              <button
                id="dash-error-clear-btn"
                type="button"
                className="error-clear-btn"
                onClick={onClearTrain}
              >
                <X size={14} aria-hidden="true" />
                <span>Clear Selected Train</span>
              </button>
            </div>
          </div>
        </div>

        <PredictionExplanation />
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // CASE 2: PREVIOUSLY SEARCHED TRAIN EXISTS WITH REAL TELEMETRY
  // ---------------------------------------------------------------------------
  const currentStation = trainData?.current_station || {
    code: '',
    name: 'Locating...',
    delay_minutes: 0
  };

  const delayMinutes = currentStation.delay_minutes ?? 0;
  let delaySeverity = 'ontime';
  let delayText = delayMinutes <= 0 ? 'On Time (0m)' : `+${delayMinutes.toFixed(0)} min delay`;
  if (delayMinutes > 20) {
    delaySeverity = 'severe';
  } else if (delayMinutes > 5) {
    delaySeverity = 'moderate';
  }

  // Compute station stops and progress from real route schedule
  const allStops: RouteStop[] = routeSchedule?.stops || [];
  const currentStnCode = (currentStation.code || '').toUpperCase();
  const currentIndex = allStops.findIndex(
    (s) => s.station_code.toUpperCase() === currentStnCode
  );

  // 1. Previous Station
  let prevStationName = 'Origin Terminal';
  let prevStationSub = 'Starting Point';
  if (currentIndex > 0) {
    const prevStop = allStops[currentIndex - 1];
    prevStationName = `${prevStop.station_name} (${prevStop.station_code})`;
    prevStationSub = prevStop.departure_time ? `Departed: ${prevStop.departure_time}` : 'Passed stop';
  } else if (savedTrain.origin && currentStnCode !== (routeSchedule?.origin_code || '')) {
    prevStationName = savedTrain.origin;
    prevStationSub = 'Starting Terminal';
  }

  // 2. Next Station
  let nextStationName = 'Final Destination';
  let nextStationSub = 'Approaching terminus';
  const h1Pred = trainData?.predictions?.[0];
  if (h1Pred) {
    nextStationName = h1Pred.station;
    nextStationSub = `Sched: ${formatTime(h1Pred.scheduled_arrival)} • ETA: ${formatTime(h1Pred.predicted_eta)}`;
  } else if (currentIndex !== -1 && currentIndex < allStops.length - 1) {
    const nextStop = allStops[currentIndex + 1];
    nextStationName = `${nextStop.station_name} (${nextStop.station_code})`;
    nextStationSub = nextStop.arrival_time ? `Sched: ${nextStop.arrival_time}` : 'Upcoming halt';
  }

  // 3. Journey Progress & Remaining Stations
  const totalStops = allStops.length;
  let progressPercent = 0;
  let remainingStopsCount = 0;

  if (totalStops > 1 && currentIndex !== -1) {
    progressPercent = Math.round((currentIndex / (totalStops - 1)) * 100);
    remainingStopsCount = Math.max(0, totalStops - currentIndex - 1);
  } else if (trainData?.predictions && trainData.predictions.length > 0) {
    progressPercent = Math.min(85, trainData.predictions.length * 25);
    remainingStopsCount = trainData.predictions.length;
  }

  // Real Multi-horizon predictions (sorted ascending by horizon, strictly omitting unavailable horizons)
  const availablePredictions: HorizonPrediction[] = [...(trainData?.predictions || [])]
    .filter((p) => p && typeof p.horizon === 'number')
    .sort((a, b) => a.horizon - b.horizon);

  return (
    <div className="dashboard-view-container" aria-label="Dynamic Train ETA Dashboard Overview">
      {/* =====================================================================
          1. TRAIN OVERVIEW
          ===================================================================== */}
      <section className="train-overview-card dashboard-hero-overview" id="dashboard-train-overview" aria-label="Train Overview">
        <div className="overview-header-row">
          <div className="train-identity-block">
            <div className="train-number-badge">
              <span className="train-number-text">{trainData?.train_no || savedTrain.train_no}</span>
            </div>
            <div className="train-name-block">
              <div className="train-top-meta-row">
                <span className="overview-section-tag">Train Overview</span>
                {(savedTrain.origin || routeSchedule?.origin_name) && (savedTrain.destination || routeSchedule?.dest_name) && (
                  <div className="train-route-pill">
                    <MapPin size={12} className="route-pin-icon" aria-hidden="true" />
                    <span className="route-terminal">{savedTrain.origin || routeSchedule?.origin_name}</span>
                    <ArrowRight size={12} className="route-arrow-icon" aria-hidden="true" />
                    <span className="route-terminal">{savedTrain.destination || routeSchedule?.dest_name}</span>
                  </div>
                )}
              </div>
              <h2 className="train-name-heading">{trainData?.train_name || savedTrain.train_name}</h2>
              <div className="train-meta-tags">
                <span className="telemetry-source-tag">
                  <Radio size={12} className="tag-live-dot" />
                  Live Railway Telemetry
                </span>
                <span className="journey-date-tag">
                  <Calendar size={13} />
                  Journey Date: {trainData?.journey_date || savedTrain.journey_date || 'Today'}
                </span>
              </div>
            </div>
          </div>

          <div className="overview-actions-block">
            <div className="overview-status-row">
              <StatusBadge status={trainData?.status || 'Active'} />
              <span className="overview-timestamp">{formatLastUpdatedText(lastUpdated)}</span>
            </div>

            {/* Current Station & Delay Highlight in Overview */}
            <div className="overview-quick-metrics">
              <div className="overview-stn-chip">
                <MapPin size={13} className="chip-icon" />
                <span className="chip-label">Current:</span>
                <span className="chip-val">{currentStation.name || currentStation.code}</span>
              </div>
              <div className={`overview-delay-chip ${delaySeverity}`}>
                <Clock size={13} className="chip-icon" />
                <span className="chip-val">{delayText}</span>
              </div>
            </div>
          </div>
        </div>

        {/* =====================================================================
            QUICK ACTIONS TOOLBAR
            ===================================================================== */}
        <div className="dashboard-quick-actions-toolbar" aria-label="Dashboard Quick Actions">
          <div className="quick-actions-left">
            <button
              id="dash-action-live-tracking"
              type="button"
              className="dash-action-btn primary tracking"
              onClick={onNavigateToTracking}
              title="Navigate to dedicated Live Tracking page"
            >
              <Navigation size={14} aria-hidden="true" />
              <span>Live Tracking</span>
              <ChevronRight size={13} aria-hidden="true" />
            </button>

            <button
              id="dash-action-eta-prediction"
              type="button"
              className="dash-action-btn primary prediction"
              onClick={onNavigateToPrediction}
              title="Navigate to dedicated ETA Prediction page"
            >
              <Milestone size={14} aria-hidden="true" />
              <span>ETA Prediction</span>
              <ChevronRight size={13} aria-hidden="true" />
            </button>

            <button
              id="dash-action-search-another"
              type="button"
              className="dash-action-btn secondary search"
              onClick={onNavigateToSearch}
              title="Search another train without clearing the current selection"
            >
              <Search size={14} aria-hidden="true" />
              <span>Search Another Train</span>
            </button>
          </div>

          <div className="quick-actions-right">
            <button
              id="dash-action-refresh"
              type="button"
              className="dash-action-btn secondary refresh"
              onClick={handleRefresh}
              disabled={isRefreshing}
              title="Fetch fresh real-time telemetry from FastAPI backend"
            >
              <RefreshCw size={14} className={isRefreshing ? 'spinning' : ''} aria-hidden="true" />
              <span>Refresh</span>
            </button>

            <button
              id="dash-action-clear"
              type="button"
              className="dash-action-btn secondary clear"
              onClick={onClearTrain}
              title="Clear selected train and return to empty dashboard"
            >
              <X size={14} aria-hidden="true" />
              <span>Clear Selected Train</span>
            </button>
          </div>
        </div>
      </section>

      {/* =====================================================================
          2. LIVE STATUS & JOURNEY PROGRESS
          ===================================================================== */}
      <section className="dashboard-live-status-section" aria-label="Live Status and Journey Progression">
        <div className="dashboard-section-header">
          <div className="section-title-with-icon">
            <Radio size={18} className="section-icon pulse" aria-hidden="true" />
            <div>
              <h3 className="section-title">Live Status</h3>
              <p className="section-subtitle">Real-time railway station progression and telemetry</p>
            </div>
          </div>
          {totalStops > 0 && (
            <div className="remaining-stations-pill">
              <Milestone size={13} aria-hidden="true" />
              <span><strong>{remainingStopsCount}</strong> remaining stations</span>
            </div>
          )}
        </div>

        {/* 3-Column Progression Station Cards */}
        <div className="live-stations-overview-grid">
          {/* Card A: Previous Station */}
          <div className="dash-status-card prev-station-card">
            <div className="card-top-caption">
              <span className="caption-label">Previous Station</span>
              <span className="caption-tag">Passed</span>
            </div>
            <div className="card-content-body">
              <h4 className="card-station-name">{prevStationName}</h4>
              <span className="card-sub-info">{prevStationSub}</span>
            </div>
          </div>

          {/* Card B: Current Station */}
          <div className="dash-status-card current-station-card">
            <div className="card-top-caption">
              <span className="caption-label">Current Station</span>
              <span className={`caption-delay-tag ${delaySeverity}`}>{delayText}</span>
            </div>
            <div className="card-content-body">
              <div className="card-station-with-code">
                <h4 className="card-station-name">{currentStation.name || currentStation.code}</h4>
                <span className="station-code-badge">{currentStation.code}</span>
              </div>
              <span className="card-sub-info">Last recorded telemetry stop</span>
            </div>
          </div>

          {/* Card C: Next Station */}
          <div className="dash-status-card next-station-card">
            <div className="card-top-caption">
              <span className="caption-label">Next Station</span>
              <span className="caption-horizon-tag">H1 Forecast</span>
            </div>
            <div className="card-content-body">
              <h4 className="card-station-name">{nextStationName}</h4>
              <span className="card-sub-info">{nextStationSub}</span>
            </div>
          </div>
        </div>

        {/* Journey Progress Bar Component */}
        <div className="dashboard-journey-progress-box">
          <div className="progress-metrics-bar">
            <div className="progress-labels-row">
              <span className="progress-title">
                Journey Progress
                {totalStops > 0 && currentIndex !== -1 && (
                  <span className="stops-counter-text">
                    (Station {currentIndex + 1} of {totalStops})
                  </span>
                )}
              </span>
              <span className="progress-percentage-text">{progressPercent}%</span>
            </div>
            <div className="progress-track">
              <div
                className="progress-fill"
                style={{ width: `${progressPercent}%` }}
                role="progressbar"
                aria-valuenow={progressPercent}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>
          </div>
        </div>
      </section>

      {/* =====================================================================
          3. ETA SUMMARY (Compact Multi-Horizon AI Forecasts)
          ===================================================================== */}
      <section className="dashboard-eta-summary-section" aria-label="AI Multi-Horizon ETA Summary">
        <div className="dashboard-section-header">
          <div className="section-title-with-icon">
            <Milestone size={18} className="section-icon" aria-hidden="true" />
            <div>
              <h3 className="section-title">ETA Summary</h3>
              <p className="section-subtitle">Compact multi-horizon AI arrival predictions powered by XGBoost</p>
            </div>
          </div>
          <div className="horizons-active-badge">
            <TrendingUp size={13} aria-hidden="true" />
            <span>
              {availablePredictions.length === 1
                ? '1 Horizon Available'
                : `${availablePredictions.length} Horizons Available`}
            </span>
          </div>
        </div>

        {availablePredictions.length === 0 ? (
          <div className="no-horizons-notice">
            <p>Train is approaching its final terminus. No further downstream station predictions available.</p>
          </div>
        ) : (
          <div className="dashboard-eta-summary-grid">
            {availablePredictions.map((pred) => {
              const delay = pred.predicted_delay_minutes ?? 0;
              const isEarly = delay < 0;
              const predDelayText = isEarly
                ? `${Math.abs(delay).toFixed(1)}m Early`
                : delay === 0
                ? 'On Time'
                : `+${delay.toFixed(1)}m Delay`;

              const delayTagVariant = delay <= 0 ? 'ontime' : delay <= 15 ? 'moderate' : 'severe';

              const horizonTitle =
                pred.horizon === 1
                  ? 'H1 — Next Station'
                  : pred.horizon === 2
                  ? 'H2 — Following Station'
                  : 'H3 — Third Station';

              return (
                <div key={pred.horizon} className={`compact-eta-card horizon-${pred.horizon}`}>
                  <div className="compact-card-top">
                    <span className={`compact-horizon-pill h${pred.horizon}`}>{horizonTitle}</span>
                    <span className={`compact-delay-pill ${delayTagVariant}`}>{predDelayText}</span>
                  </div>

                  <div className="compact-card-station">
                    <h4 className="compact-station-title">{pred.station}</h4>
                  </div>

                  <div className="compact-times-grid">
                    <div className="compact-time-col sched">
                      <span className="time-caption">
                        <Clock size={11} />
                        Scheduled
                      </span>
                      <span className="time-val">{formatTime(pred.scheduled_arrival)}</span>
                    </div>

                    <div className="compact-time-divider">
                      <ArrowRight size={14} />
                    </div>

                    <div className="compact-time-col pred">
                      <span className="time-caption highlight">
                        <Milestone size={11} />
                        Predicted ETA
                      </span>
                      <span className="time-val highlight">{formatTime(pred.predicted_eta)}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* =====================================================================
          4. ML MODEL EXPLANATION SECTION
          ===================================================================== */}
      <PredictionExplanation />
    </div>
  );
};
