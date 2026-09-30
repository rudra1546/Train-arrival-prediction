import React, { useState, useEffect, useCallback } from 'react';
import {
  Train,
  Radio,
  MapPin,
  Clock,
  Milestone,
  Navigation,
  RefreshCw,
  Search,
  AlertCircle,
  Calendar,
  ArrowRight,
  CheckCircle2,
  CircleDot,
  Compass
} from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { LiveRouteMap } from './LiveRouteMap';
import { fetchTrainETA, fetchTrainRouteSchedule } from '../services/api';
import type { TrainETAResponse, APIErrorState } from '../types/eta';
import type { LastSearchedTrain } from '../services/persistence';
import type { TrainRouteSchedule, RouteStop } from '../types/route';

interface LiveTrackingPageProps {
  savedTrain: LastSearchedTrain | null;
  onNavigateToSearch: () => void;
  onNavigateToPrediction?: () => void;
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

export const LiveTrackingPage: React.FC<LiveTrackingPageProps> = ({
  savedTrain,
  onNavigateToSearch,
  onNavigateToPrediction
}) => {
  const [trainData, setTrainData] = useState<TrainETAResponse | null>(null);
  const [routeSchedule, setRouteSchedule] = useState<TrainRouteSchedule | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<APIErrorState | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const trainNo = savedTrain?.train_no || '';

  const loadLiveData = useCallback(async (isRefreshAction = false) => {
    if (!trainNo) {
      setIsLoading(false);
      return;
    }

    if (isRefreshAction) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      // 1. Fetch real live telemetry & ETA predictions
      const liveEtaPromise = fetchTrainETA(trainNo, savedTrain?.journey_date);
      // 2. Fetch full real route schedule stops
      const routePromise = fetchTrainRouteSchedule(trainNo);

      const [liveData, routeData] = await Promise.all([liveEtaPromise, routePromise]);

      setTrainData(liveData);
      setRouteSchedule(routeData);
      setLastUpdated(new Date());
    } catch (err: any) {
      setError(err as APIErrorState);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [trainNo, savedTrain?.journey_date]);

  // Load on mount or when saved train changes
  useEffect(() => {
    loadLiveData(false);
  }, [loadLiveData]);

  const handleRefresh = () => {
    loadLiveData(true);
  };

  const formatLastUpdatedText = (date: Date | null): string => {
    if (!date) return 'Awaiting telemetry';
    const diffSec = Math.floor((Date.now() - date.getTime()) / 1000);
    if (diffSec < 20) return 'Updated just now';
    return `Updated ${date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true })}`;
  };

  // ---------------------------------------------------------------------------
  // 1. EMPTY STATE: When no train is selected
  // ---------------------------------------------------------------------------
  if (!savedTrain && !trainNo) {
    return (
      <div className="live-tracking-page empty-view" aria-label="Live Tracking Empty State">
        <section className="live-tracking-hero">
          <div className="tracking-hero-badge">
            <Radio size={14} className="tag-live-dot" />
            <span>Real-Time Railway Operations</span>
          </div>
          <h2 className="tracking-hero-title">Live Train Tracking</h2>
          <p className="tracking-hero-subtitle">
            Inspect real-time GPS telemetry, station progression, and operational delay tracking.
          </p>
        </section>

        <div className="empty-state-card" aria-label="No Train Selected">
          <div className="empty-state-icon-wrapper" aria-hidden="true">
            <Train size={36} className="empty-train-icon" />
          </div>
          <div className="empty-state-text-block">
            <h3 className="empty-state-title">No train selected</h3>
            <p className="empty-state-description">
              Search for a train to get started and monitor real-time railway telemetry, live delay
              updates, and station progress.
            </p>
          </div>
          <div className="empty-state-primary-action">
            <button
              id="live-tracking-search-train-btn"
              type="button"
              className="empty-search-primary-btn"
              onClick={onNavigateToSearch}
            >
              <Search size={16} aria-hidden="true" />
              <span>Search Train</span>
              <ArrowRight size={15} aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // 2. ERROR STATE (when API fails but train info remains visible)
  // ---------------------------------------------------------------------------
  if (!isLoading && error && !trainData) {
    return (
      <div className="live-tracking-page error-view" aria-label="Live Tracking Error State">
        {/* Selected Train Header Banner */}
        <section className="live-tracking-train-header">
          <div className="train-header-identity">
            <span className="tracking-train-no-badge">{trainNo}</span>
            <div className="train-header-text">
              <h2 className="tracking-train-name">{savedTrain?.train_name || `Train ${trainNo}`}</h2>
              {savedTrain?.origin && savedTrain?.destination && (
                <div className="tracking-route-strip">
                  <MapPin size={13} className="route-pin" />
                  <span>{savedTrain.origin} &rarr; {savedTrain.destination}</span>
                </div>
              )}
            </div>
          </div>
          <div className="train-header-actions">
            <button
              type="button"
              className="tracking-refresh-btn"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw size={14} className={isRefreshing ? 'spinning' : ''} />
              <span>Retry</span>
            </button>
            <button
              type="button"
              className="tracking-secondary-btn"
              onClick={onNavigateToSearch}
            >
              <Search size={14} />
              <span>Change Train</span>
            </button>
          </div>
        </section>

        {/* Clean Error Card */}
        <div className="error-state-card" role="alert">
          <div className="error-icon-box" aria-hidden="true">
            <AlertCircle size={22} className="error-icon" />
          </div>
          <div className="error-details-box">
            <div className="error-title-row">
              <h4 className="error-title-text">{error.title}</h4>
              {error.statusCode && (
                <span className="error-code-badge">HTTP {error.statusCode}</span>
              )}
            </div>
            <p className="error-message-text">{error.message}</p>
            <div className="error-actions-row">
              <button
                type="button"
                className="error-retry-btn"
                onClick={() => loadLiveData(false)}
              >
                <RefreshCw size={14} />
                <span>Retry Request</span>
              </button>
              <button
                type="button"
                className="error-secondary-btn"
                onClick={onNavigateToSearch}
              >
                <Search size={14} />
                <span>Search Another Train</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // 3. RESOLVE ROUTE STATIONS & CURRENT / PREVIOUS / NEXT POSITIONS
  // ---------------------------------------------------------------------------
  const currentStation = trainData?.current_station || {
    code: '',
    name: 'Locating...',
    delay_minutes: 0
  };

  const delayMinutes = currentStation.delay_minutes ?? 0;
  let delayVariant = 'ontime';
  let delayText = delayMinutes <= 0 ? 'On Time (0m)' : `+${delayMinutes.toFixed(0)} min`;
  if (delayMinutes > 20) {
    delayVariant = 'severe';
  } else if (delayMinutes > 5) {
    delayVariant = 'moderate';
  }

  // Determine stops list from real schedule
  const allStops: RouteStop[] = routeSchedule?.stops || [];
  const currentStnCode = (currentStation.code || '').toUpperCase();

  // Find index of current station in schedule
  const currentIndex = allStops.findIndex(
    (s) => s.station_code.toUpperCase() === currentStnCode
  );

  // Compute Previous Station
  let prevStationName = 'Origin Terminal';
  let prevStationSub = 'Starting Point';
  if (currentIndex > 0) {
    const prevStop = allStops[currentIndex - 1];
    prevStationName = `${prevStop.station_name} (${prevStop.station_code})`;
    prevStationSub = prevStop.departure_time ? `Departed: ${prevStop.departure_time}` : 'Passed';
  } else if (savedTrain?.origin && currentStnCode !== (routeSchedule?.origin_code || '')) {
    prevStationName = savedTrain.origin;
    prevStationSub = 'Starting Terminal';
  }

  // Compute Next Station (from H1 prediction or schedule)
  let nextStationName = 'Destination Reached';
  let nextStationSub = 'Journey Completed';
  const h1Pred = trainData?.predictions?.[0];

  if (h1Pred) {
    nextStationName = h1Pred.station;
    nextStationSub = `Sched: ${formatTime(h1Pred.scheduled_arrival)} • ETA: ${formatTime(h1Pred.predicted_eta)}`;
  } else if (currentIndex !== -1 && currentIndex < allStops.length - 1) {
    const nextStop = allStops[currentIndex + 1];
    nextStationName = `${nextStop.station_name} (${nextStop.station_code})`;
    nextStationSub = nextStop.arrival_time ? `Sched: ${nextStop.arrival_time}` : 'Upcoming Stop';
  }

  // Origin & Destination Terminals
  const originText =
    savedTrain?.origin ||
    (routeSchedule?.origin_name ? `${routeSchedule.origin_name} (${routeSchedule.origin_code})` : 'Origin');
  const destText =
    savedTrain?.destination ||
    (routeSchedule?.dest_name ? `${routeSchedule.dest_name} (${routeSchedule.dest_code})` : 'Destination');

  // Completed / Current / Upcoming breakdown for visual journey diagram
  const completedStops = currentIndex > 0 ? allStops.slice(0, currentIndex) : [];
  const upcomingStops = currentIndex !== -1 ? allStops.slice(currentIndex + 1) : [];

  const progressPercent =
    allStops.length > 1 && currentIndex !== -1
      ? Math.round((currentIndex / (allStops.length - 1)) * 100)
      : currentIndex === -1 && h1Pred
      ? 50
      : 0;

  return (
    <div className="live-tracking-page" aria-label="Live Train Tracking Dashboard">
      {/* 1. TRAIN HEADER */}
      <section className="live-tracking-train-header" id="live-tracking-header">
        <div className="train-header-identity">
          <div className="tracking-train-no-badge">
            <span className="train-no-text">{trainData?.train_no || trainNo}</span>
          </div>
          <div className="train-header-text">
            <div className="train-header-super">
              <span className="telemetry-pill">
                <Radio size={12} className="tag-live-dot" />
                RailRadar Live Telemetry
              </span>
              <span className="header-date-pill">
                <Calendar size={12} />
                {trainData?.journey_date || savedTrain?.journey_date || 'Today'}
              </span>
            </div>
            <h2 className="tracking-train-name">
              {trainData?.train_name || savedTrain?.train_name || `Train ${trainNo}`}
            </h2>
            <div className="tracking-route-strip">
              <Compass size={13} className="route-pin" aria-hidden="true" />
              <span className="route-text">{originText} &rarr; {destText}</span>
            </div>
          </div>
        </div>

        <div className="train-header-actions">
          <StatusBadge status={trainData?.status || 'running'} />
          {onNavigateToPrediction && (
            <button
              id="live-tracking-prediction-btn"
              type="button"
              className="tracking-refresh-btn secondary"
              onClick={onNavigateToPrediction}
              title="View multi-horizon AI arrival predictions"
            >
              <Milestone size={14} aria-hidden="true" />
              <span>ETA Forecasts</span>
            </button>
          )}
          <button
            id="live-tracking-refresh-btn"
            type="button"
            className="tracking-refresh-btn"
            onClick={handleRefresh}
            disabled={isRefreshing || isLoading}
            title="Refresh live telemetry and recompute position"
          >
            <RefreshCw size={14} className={isRefreshing ? 'spinning' : ''} aria-hidden="true" />
            <span>{isRefreshing ? 'Refreshing...' : 'Refresh Status'}</span>
          </button>
        </div>
      </section>

      {/* 2. CURRENT STATUS CARDS */}
      <section className="live-status-cards-section" aria-label="Current Telemetry Metrics">
        <div className="status-cards-grid">
          {/* Card 1: Current Location */}
          <div className="status-metric-card" id="tracking-card-current-location">
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

          {/* Card 2: Current Delay */}
          <div className="status-metric-card" id="tracking-card-current-delay">
            <div className="card-top-strip">
              <span className="metric-caption">Current Delay</span>
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

          {/* Card 3: Previous Station */}
          <div className="status-metric-card" id="tracking-card-previous-station">
            <div className="card-top-strip">
              <span className="metric-caption">Previous Station</span>
              <span className="metric-icon-wrap navy" aria-hidden="true">
                <CheckCircle2 size={17} />
              </span>
            </div>
            <div className="metric-body">
              <div className="metric-primary-row">
                <h3 className="metric-station-name">{prevStationName}</h3>
              </div>
              <span className="metric-subtext">{prevStationSub}</span>
            </div>
          </div>

          {/* Card 4: Next Station */}
          <div className="status-metric-card" id="tracking-card-next-station">
            <div className="card-top-strip">
              <span className="metric-caption">Next Station</span>
              <span className="metric-icon-wrap cyan" aria-hidden="true">
                <Navigation size={17} />
              </span>
            </div>
            <div className="metric-body">
              <div className="metric-primary-row">
                <h3 className="metric-station-name">{nextStationName}</h3>
                {h1Pred && <span className="station-code-badge cyan">H1</span>}
              </div>
              <span className="metric-subtext">{nextStationSub}</span>
            </div>
          </div>

          {/* Card 5: Last Updated Time */}
          <div className="status-metric-card" id="tracking-card-last-updated">
            <div className="card-top-strip">
              <span className="metric-caption">Telemetry Stream</span>
              <span className="metric-icon-wrap blue" aria-hidden="true">
                <Radio size={17} />
              </span>
            </div>
            <div className="metric-body">
              <div className="metric-primary-row">
                <span className="metric-update-time">{formatLastUpdatedText(lastUpdated)}</span>
              </div>
              <span className="metric-subtext">NTES / RailRadar synchronization</span>
            </div>
          </div>
        </div>
      </section>

      {/* 3. JOURNEY PROGRESS (Visual Railway Track Component) */}
      <section className="live-journey-track-section" aria-label="Railway Journey Progress">
        <div className="section-header-block">
          <div className="section-title-with-icon">
            <Milestone size={18} className="section-icon" aria-hidden="true" />
            <h3 className="section-title">Journey Progress</h3>
          </div>
          <div className="route-stats-pill">
            <span>{progressPercent}% Journey Completed</span>
            {allStops.length > 0 && <span>&bull; Stop {currentIndex !== -1 ? currentIndex + 1 : 1} of {allStops.length}</span>}
          </div>
        </div>

        {/* Visual Track Diagram */}
        {/* Origin ──────●──────────────●────────────── Destination */}
        {/*        Previous       Current (🚆) */}
        <div className="railway-visual-track-card" aria-label="Visual Railway Track">
          <div className="track-terminals-labels">
            <div className="terminal-marker origin">
              <span className="terminal-tag">Origin</span>
              <strong className="terminal-name">{originText}</strong>
            </div>
            <div className="terminal-marker destination">
              <span className="terminal-tag">Destination</span>
              <strong className="terminal-name">{destText}</strong>
            </div>
          </div>

          <div className="railway-line-wrapper">
            {/* Background Rail Line */}
            <div className="railway-track-bg" />

            {/* Filled / Completed Track Progress */}
            <div
              className="railway-track-fill"
              style={{ width: `${Math.max(5, Math.min(progressPercent, 100))}%` }}
            />

            {/* Stations Key Points on Track */}
            <div className="track-nodes-row">
              {/* Origin Node */}
              <div className="track-key-node origin-node completed" title={`Origin: ${originText}`}>
                <div className="node-dot" />
                <span className="node-caption">Origin</span>
              </div>

              {/* Previous Station Node (if intermediate) */}
              {currentIndex > 0 && (
                <div
                  className="track-key-node prev-node completed"
                  style={{ left: `${Math.max(15, progressPercent - 20)}%` }}
                  title={`Previous: ${prevStationName}`}
                >
                  <div className="node-dot" />
                  <span className="node-caption">Previous: {allStops[currentIndex - 1]?.station_code}</span>
                </div>
              )}

              {/* Current Station Position with Train Icon */}
              <div
                className="track-key-node current-node active"
                style={{ left: `${Math.max(10, Math.min(progressPercent, 90))}%` }}
                title={`Current Position: ${currentStation.name} (${currentStation.code})`}
              >
                <div className="train-icon-halo">
                  <Train size={18} className="live-train-sprite" />
                  <span className="train-pulse-ring" />
                </div>
                <div className="current-node-bubble">
                  <span className="bubble-label">Current</span>
                  <span className="bubble-stn">{currentStation.code}</span>
                </div>
              </div>

              {/* Next Station Node (if upcoming) */}
              {h1Pred && (
                <div
                  className="track-key-node next-node upcoming"
                  style={{ left: `${Math.min(85, progressPercent + 20)}%` }}
                  title={`Next: ${h1Pred.station}`}
                >
                  <div className="node-dot" />
                  <span className="node-caption">Next: {h1Pred.station}</span>
                </div>
              )}

              {/* Destination Node */}
              <div className="track-key-node dest-node upcoming" title={`Terminus: ${destText}`}>
                <div className="node-dot" />
                <span className="node-caption">Terminus</span>
              </div>
            </div>
          </div>
        </div>

        {/* 4. GEOGRAPHIC RAILWAY MAP */}
        <LiveRouteMap
          trainData={trainData}
          routeSchedule={routeSchedule}
          currentIndex={currentIndex}
        />

        {/* Detailed Real Station Progress Flow */}
        <div className="route-stations-breakdown-card">
          <div className="breakdown-header">
            <h4 className="breakdown-title">Scheduled Timetable Sequence</h4>
            <span className="breakdown-count-tag">
              {currentIndex !== -1
                ? `${completedStops.length} Completed • 1 Current • ${upcomingStops.length} Upcoming`
                : allStops.length > 0
                ? `${allStops.length} Total Route Halts`
                : 'Live Forecast Halts'}
            </span>
          </div>

          <div className="route-timeline-flow">
            {/* If full route stops available from railway_search.db */}
            {allStops.length > 0 ? (
              allStops.map((stop, sIdx) => {
                const isPassed = currentIndex !== -1 && sIdx < currentIndex;
                const isCurrent = currentIndex !== -1 && sIdx === currentIndex;
                const isNext = currentIndex !== -1 && sIdx === currentIndex + 1;
                const isUpcoming = currentIndex !== -1 && sIdx > currentIndex;

                // Match with prediction if available
                const matchPred = trainData?.predictions?.find(
                  (p) => p.station.toUpperCase() === stop.station_code.toUpperCase()
                );

                return (
                  <div
                    key={`${stop.station_code}-${stop.station_no}`}
                    className={`timeline-station-row ${
                      isCurrent
                        ? 'is-current'
                        : isPassed
                        ? 'is-completed'
                        : isNext
                        ? 'is-next'
                        : isUpcoming
                        ? 'is-upcoming'
                        : 'is-scheduled'
                    }`}
                  >
                    <div className="station-node-col">
                      <div className="node-icon-box">
                        {isPassed && <CheckCircle2 size={16} className="node-icon completed" />}
                        {isCurrent && <Train size={16} className="node-icon current" />}
                        {isNext && <Navigation size={15} className="node-icon next" />}
                        {!isPassed && !isCurrent && !isNext && (
                          <CircleDot size={14} className="node-icon upcoming" />
                        )}
                      </div>
                      {sIdx < allStops.length - 1 && <div className="node-track-connector" />}
                    </div>

                    <div className="station-info-col">
                      <div className="station-name-row">
                        <span className="station-seq">#{stop.station_no}</span>
                        <h5 className="station-name">{stop.station_name}</h5>
                        <span className="station-code-pill">{stop.station_code}</span>

                        {isCurrent && <span className="status-tag current">Current Location</span>}
                        {isPassed && <span className="status-tag completed">Completed</span>}
                        {isNext && <span className="status-tag next">Next Stop (H1)</span>}
                        {matchPred && matchPred.horizon > 1 && (
                          <span className="status-tag future">H{matchPred.horizon} Prediction</span>
                        )}
                      </div>

                      <div className="station-timings-row">
                        {stop.arrival_time && stop.arrival_time !== '--:--' && (
                          <span className="timing-item">Arr: {stop.arrival_time}</span>
                        )}
                        {stop.departure_time && stop.departure_time !== '--:--' && (
                          <span className="timing-item">Dep: {stop.departure_time}</span>
                        )}
                        {matchPred && (
                          <span className="timing-item predicted-eta">
                            Predicted ETA: <strong>{formatTime(matchPred.predicted_eta)}</strong> (
                            {matchPred.predicted_delay_minutes <= 0
                              ? 'On Time'
                              : `+${matchPred.predicted_delay_minutes.toFixed(0)}m delay`}
                            )
                          </span>
                        )}
                        {stop.distance !== undefined && stop.distance > 0 && (
                          <span className="timing-item distance">{stop.distance} km</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              /* Fallback to predictions stops if route database was not loaded */
              <div className="fallback-predictions-list">
                <div className="timeline-station-row is-current">
                  <div className="station-node-col">
                    <Train size={16} className="node-icon current" />
                    <div className="node-track-connector" />
                  </div>
                  <div className="station-info-col">
                    <div className="station-name-row">
                      <h5 className="station-name">{currentStation.name}</h5>
                      <span className="station-code-pill">{currentStation.code}</span>
                      <span className="status-tag current">Current Location</span>
                    </div>
                    <div className="station-timings-row">
                      <span className="timing-item">
                        Live Delay: {currentStation.delay_minutes <= 0 ? 'On Time' : `+${currentStation.delay_minutes} min`}
                      </span>
                    </div>
                  </div>
                </div>

                {trainData?.predictions?.map((pred, pIdx) => (
                  <div key={pred.horizon} className={`timeline-station-row ${pIdx === 0 ? 'is-next' : 'is-upcoming'}`}>
                    <div className="station-node-col">
                      <Navigation size={15} className={`node-icon ${pIdx === 0 ? 'next' : 'upcoming'}`} />
                      {pIdx < (trainData?.predictions?.length || 0) - 1 && <div className="node-track-connector" />}
                    </div>
                    <div className="station-info-col">
                      <div className="station-name-row">
                        <h5 className="station-name">{pred.station}</h5>
                        <span className="station-code-pill">{pred.station}</span>
                        <span className="status-tag next">Horizon {pred.horizon}</span>
                      </div>
                      <div className="station-timings-row">
                        <span className="timing-item">Sched: {formatTime(pred.scheduled_arrival)}</span>
                        <span className="timing-item predicted-eta">
                          ETA: <strong>{formatTime(pred.predicted_eta)}</strong> (+{pred.predicted_delay_minutes.toFixed(0)}m)
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
};
