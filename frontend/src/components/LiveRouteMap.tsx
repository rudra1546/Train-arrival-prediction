import React, { useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Train, Navigation, MapPin, Clock, AlertCircle, Compass } from 'lucide-react';
import type { TrainETAResponse, HorizonPrediction } from '../types/eta';
import type { TrainRouteSchedule, RouteStop } from '../types/route';

interface LiveRouteMapProps {
  trainData: TrainETAResponse | null;
  routeSchedule: TrainRouteSchedule | null;
  currentIndex: number;
}

// Subcomponent to automatically fit map bounds whenever route coordinates change
function FitRouteBounds({ bounds }: { bounds: L.LatLngBoundsExpression | null }) {
  const map = useMap();

  useEffect(() => {
    if (bounds) {
      try {
        map.fitBounds(bounds, {
          padding: [45, 45],
          maxZoom: 13,
          animate: true,
        });
      } catch (e) {
        console.warn('Map fitBounds error:', e);
      }
    }
  }, [bounds, map]);

  return null;
}

// Subcomponent providing a "Recenter / Fit Route" button inside map
function RecenterControl({ bounds }: { bounds: L.LatLngBoundsExpression | null }) {
  const map = useMap();

  if (!bounds) return null;

  return (
    <div className="leaflet-top leaflet-right" style={{ pointerEvents: 'auto', margin: '12px' }}>
      <button
        type="button"
        className="map-recenter-btn"
        onClick={() => {
          map.fitBounds(bounds, { padding: [45, 45], maxZoom: 13, animate: true });
        }}
        title="Fit route to screen"
        aria-label="Fit route to screen"
      >
        <Compass size={16} />
        <span>Fit Route</span>
      </button>
    </div>
  );
}

// Create custom DOM DivIcon for the Train locomotive marker
function createTrainIcon() {
  return L.divIcon({
    className: 'custom-train-marker-wrapper',
    html: `
      <div class="train-geo-marker">
        <div class="train-pulse-ring"></div>
        <div class="train-marker-core">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <rect width="16" height="16" x="4" y="3" rx="2"></rect>
            <path d="M4 11h16"></path>
            <path d="M12 3v8"></path>
            <path d="m8 19-2 3"></path>
            <path d="m18 22-2-3"></path>
            <circle cx="8" cy="15" r="1"></circle>
            <circle cx="16" cy="15" r="1"></circle>
          </svg>
        </div>
      </div>
    `,
    iconSize: [38, 38],
    iconAnchor: [19, 19],
    popupAnchor: [0, -20],
  });
}

// Create custom DOM DivIcon for Station nodes
function createStationIcon(type: 'completed' | 'current' | 'upcoming' | 'terminal', code: string) {
  let cls = 'station-marker-upcoming';
  if (type === 'current') cls = 'station-marker-current';
  else if (type === 'completed') cls = 'station-marker-completed';
  else if (type === 'terminal') cls = 'station-marker-terminal';

  return L.divIcon({
    className: 'custom-station-marker-wrapper',
    html: `
      <div class="station-geo-marker ${cls}" title="${code}">
        <span class="station-geo-dot"></span>
      </div>
    `,
    iconSize: type === 'terminal' || type === 'current' ? [20, 20] : [14, 14],
    iconAnchor: type === 'terminal' || type === 'current' ? [10, 10] : [7, 7],
    popupAnchor: [0, -10],
  });
}

export const LiveRouteMap: React.FC<LiveRouteMapProps> = ({
  trainData,
  routeSchedule,
  currentIndex,
}) => {
  // 1. Collect valid route stops that have actual coordinates
  const stopsWithCoords = useMemo(() => {
    if (!routeSchedule?.stops || routeSchedule.stops.length === 0) {
      return [];
    }

    return routeSchedule.stops
      .map((stop, originalIndex) => ({
        ...stop,
        originalIndex,
      }))
      .filter((stop): stop is RouteStop & { originalIndex: number; latitude: number; longitude: number } => {
        return (
          typeof stop.latitude === 'number' &&
          typeof stop.longitude === 'number' &&
          !isNaN(stop.latitude) &&
          !isNaN(stop.longitude) &&
          stop.latitude !== 0 &&
          stop.longitude !== 0
        );
      });
  }, [routeSchedule]);

  // 2. Resolve Current Train Marker Coordinates
  // CURRENT TRAIN POSITION RULE:
  // "If the live API gives coordinates, use them.
  // If it only provides a station/current-location code:
  // Resolve that station using the real station coordinate lookup.
  // Place the train marker at that station.
  // Do not pretend to have GPS-level precision when the API only provides station-level location."
  const trainPositionInfo = useMemo<{
    position: [number, number];
    isGps: boolean;
    stationName: string;
    stationCode: string;
  } | null>(() => {
    // A: Check if real GPS coords exist directly on trainData
    const lat = (trainData as any)?.latitude;
    const lon = (trainData as any)?.longitude;
    if (
      typeof lat === 'number' &&
      typeof lon === 'number' &&
      !isNaN(lat) &&
      !isNaN(lon) &&
      lat !== 0 &&
      lon !== 0
    ) {
      return {
        position: [lat, lon],
        isGps: true,
        stationName: trainData?.current_station?.name || 'Current GPS Location',
        stationCode: trainData?.current_station?.code || 'GPS',
      };
    }

    // B: Resolve current station coordinate from routeSchedule stops
    const currentCode = trainData?.current_station?.code?.toUpperCase();
    if (currentCode && stopsWithCoords.length > 0) {
      const matchStop = stopsWithCoords.find(
        (s) => s.station_code.toUpperCase() === currentCode
      );
      if (matchStop) {
        return {
          position: [matchStop.latitude, matchStop.longitude],
          isGps: false,
          stationName: matchStop.station_name,
          stationCode: matchStop.station_code,
        };
      }
    }

    // C: If currentIndex is valid and pointing to a stop with coordinates
    if (currentIndex >= 0 && routeSchedule?.stops && routeSchedule.stops[currentIndex]) {
      const currStop = routeSchedule.stops[currentIndex];
      if (
        typeof currStop.latitude === 'number' &&
        typeof currStop.longitude === 'number' &&
        currStop.latitude !== 0
      ) {
        return {
          position: [currStop.latitude, currStop.longitude],
          isGps: false,
          stationName: currStop.station_name,
          stationCode: currStop.station_code,
        };
      }
    }

    return null;
  }, [trainData, stopsWithCoords, currentIndex, routeSchedule]);

  // 3. Compute Polyline Coordinates (Completed segment & Upcoming segment)
  const { completedPolyline, upcomingPolyline, bounds } = useMemo(() => {
    if (stopsWithCoords.length === 0) {
      return { completedPolyline: [], upcomingPolyline: [], bounds: null };
    }

    const allCoords: [number, number][] = stopsWithCoords.map((s) => [s.latitude, s.longitude]);
    const b = L.latLngBounds(allCoords);

    // If train position is available, expand bounds to include it
    if (trainPositionInfo) {
      b.extend(trainPositionInfo.position);
    }

    // Split polyline at currentIndex
    const completed: [number, number][] = [];
    const upcoming: [number, number][] = [];

    stopsWithCoords.forEach((s) => {
      if (currentIndex !== -1 && s.originalIndex <= currentIndex) {
        completed.push([s.latitude, s.longitude]);
      } else {
        upcoming.push([s.latitude, s.longitude]);
      }
    });

    // Bridge completed and upcoming so line is contiguous
    if (completed.length > 0 && upcoming.length > 0) {
      const lastCompleted = completed[completed.length - 1];
      upcoming.unshift(lastCompleted);
    }

    return {
      completedPolyline: completed,
      upcomingPolyline: upcoming.length > 0 ? upcoming : allCoords,
      bounds: b,
    };
  }, [stopsWithCoords, currentIndex, trainPositionInfo]);

  // Next station information for popup
  const h1Pred = trainData?.predictions?.find((p: HorizonPrediction) => p.horizon === 1);
  const nextStationName =
    h1Pred?.station ||
    (currentIndex !== -1 && routeSchedule?.stops[currentIndex + 1]?.station_name) ||
    'Terminus';

  const delayMinutes = trainData?.current_station?.delay_minutes ?? 0;
  const delayLabel =
    delayMinutes <= 0
      ? 'On Time (0 min)'
      : `+${delayMinutes}m Delayed`;

  // 4. Handle Empty / Coordinate Unavailable State
  if (stopsWithCoords.length === 0 && !trainPositionInfo) {
    return (
      <div className="map-unavailable-container" role="region" aria-label="Geographic Railway Map">
        <div className="map-unavailable-card">
          <div className="map-unavailable-icon">
            <AlertCircle size={28} className="text-amber-500" />
          </div>
          <h4 className="map-unavailable-title">Map location data is currently unavailable.</h4>
          <p className="map-unavailable-desc">
            Geographic railway coordinates could not be resolved for train route halts.
            The complete timetable schedule and textual live telemetry remain fully operational below.
          </p>
        </div>
      </div>
    );
  }

  // Initial center fallback (Central India if bounds not ready)
  const initialCenter: [number, number] =
    trainPositionInfo?.position ||
    (stopsWithCoords[0] ? [stopsWithCoords[0].latitude, stopsWithCoords[0].longitude] : [22.9734, 78.6569]);

  return (
    <section className="live-route-map-section" aria-label="Interactive Geographic Railway Map">
      <div className="map-section-header">
        <div className="map-header-left">
          <div className="map-header-icon-box">
            <Navigation size={18} className="map-header-icon" />
          </div>
          <div>
            <h3 className="map-header-title">Live Railway Route Map</h3>
            <p className="map-header-subtitle">
              Interactive track progression with OpenStreetMap railway telemetry
            </p>
          </div>
        </div>

        <div className="map-legend-pills">
          <span className="map-legend-item">
            <span className="legend-dot legend-dot-traversed"></span>
            <span>Traversed ({currentIndex !== -1 ? currentIndex + 1 : 0})</span>
          </span>
          <span className="map-legend-item">
            <span className="legend-dot legend-dot-upcoming"></span>
            <span>Upcoming ({routeSchedule?.total_stops ? routeSchedule.total_stops - Math.max(0, currentIndex + 1) : stopsWithCoords.length})</span>
          </span>
          <span className="map-legend-item">
            <span className="legend-train-badge">🚆</span>
            <span>Current Train</span>
          </span>
        </div>
      </div>

      <div className="map-render-wrapper">
        <MapContainer
          center={initialCenter}
          zoom={6}
          scrollWheelZoom={true}
          className="leaflet-railway-map"
          style={{ width: '100%', height: '100%' }}
        >
          {/* Base OpenStreetMap Tiles */}
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={18}
          />

          {/* Automatic Bounds Fitting */}
          <FitRouteBounds bounds={bounds} />
          <RecenterControl bounds={bounds} />

          {/* Traversed / Completed Route Line */}
          {completedPolyline.length > 1 && (
            <Polyline
              positions={completedPolyline}
              pathOptions={{
                color: '#059669', // Emerald/Green for traversed section
                weight: 4.5,
                opacity: 0.85,
                lineCap: 'round',
                lineJoin: 'round',
              }}
            />
          )}

          {/* Upcoming Route Line */}
          {upcomingPolyline.length > 1 && (
            <Polyline
              positions={upcomingPolyline}
              pathOptions={{
                color: '#0284c7', // Railway Blue for upcoming route
                weight: 4,
                opacity: 0.8,
                dashArray: completedPolyline.length > 1 ? '7, 7' : undefined,
                lineCap: 'round',
                lineJoin: 'round',
              }}
            />
          )}

          {/* Route Stations Markers */}
          {stopsWithCoords.map((stop) => {
            const isCompleted = currentIndex !== -1 && stop.originalIndex < currentIndex;
            const isCurrent = currentIndex !== -1 && stop.originalIndex === currentIndex;
            const isTerminal =
              stop.originalIndex === 0 ||
              stop.originalIndex === (routeSchedule?.stops.length ? routeSchedule.stops.length - 1 : 0);

            let markerType: 'completed' | 'current' | 'upcoming' | 'terminal' = 'upcoming';
            if (isCurrent) markerType = 'current';
            else if (isTerminal) markerType = 'terminal';
            else if (isCompleted) markerType = 'completed';

            // Match prediction if available
            const pred = trainData?.predictions?.find(
              (p: HorizonPrediction) => p.station.toUpperCase() === stop.station_code.toUpperCase()
            );

            return (
              <Marker
                key={`map-stn-${stop.station_code}-${stop.station_no}`}
                position={[stop.latitude, stop.longitude]}
                icon={createStationIcon(markerType, stop.station_code)}
              >
                <Popup className="railway-map-station-popup">
                  <div className="map-popup-card">
                    <div className="map-popup-header">
                      <div className="popup-code-badge">{stop.station_code}</div>
                      <div className="popup-name-box">
                        <h4 className="popup-station-name">{stop.station_name}</h4>
                        <span className="popup-stop-number">Halt #{stop.station_no} • {stop.distance} km</span>
                      </div>
                    </div>

                    <div className="map-popup-details">
                      <div className="popup-detail-row">
                        <span className="detail-label">Schedule Arrival:</span>
                        <span className="detail-value">{stop.arrival_time}</span>
                      </div>
                      <div className="popup-detail-row">
                        <span className="detail-label">Schedule Departure:</span>
                        <span className="detail-value">{stop.departure_time}</span>
                      </div>
                      {pred && (
                        <div className="popup-detail-row pred-highlight">
                          <span className="detail-label">AI Forecast ETA:</span>
                          <span className="detail-value eta-val">{pred.predicted_eta} ({pred.predicted_delay_minutes > 0 ? `+${pred.predicted_delay_minutes}m` : 'On Time'})</span>
                        </div>
                      )}
                      <div className="popup-status-badge-row">
                        <span className={`popup-status-pill ${markerType}`}>
                          {isCurrent
                            ? '🚆 Current Train Halt'
                            : isCompleted
                            ? '✓ Passed Station'
                            : isTerminal && stop.originalIndex === 0
                            ? '🚩 Origin Terminal'
                            : isTerminal
                            ? '🏁 Destination Terminal'
                            : 'Upcoming Halt'}
                        </span>
                      </div>
                    </div>
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {/* 1. TRAIN POSITION MARKER */}
          {trainPositionInfo && (
            <Marker
              position={trainPositionInfo.position}
              icon={createTrainIcon()}
              zIndexOffset={1000} // Keeps train marker above station markers
            >
              <Popup className="railway-map-train-popup" autoPan={true}>
                <div className="map-train-popup-card">
                  <div className="train-popup-header">
                    <div className="train-badge-pill">
                      <Train size={14} />
                      <span>{trainData?.train_no || 'Train'}</span>
                    </div>
                    <span className="train-popup-status-tag">
                      {trainData?.status || 'RUNNING'}
                    </span>
                  </div>

                  <h4 className="train-popup-name">
                    {trainData?.train_name || 'Express Service'}
                  </h4>

                  <div className="train-popup-telemetry">
                    <div className="telemetry-item">
                      <MapPin size={14} className="telemetry-icon text-sky-600" />
                      <div className="telemetry-text">
                        <span className="telemetry-label">Current Location</span>
                        <span className="telemetry-val">
                          {trainPositionInfo.stationName} ({trainPositionInfo.stationCode})
                        </span>
                      </div>
                    </div>

                    <div className="telemetry-item">
                      <Clock size={14} className="telemetry-icon text-amber-500" />
                      <div className="telemetry-text">
                        <span className="telemetry-label">Current Delay</span>
                        <span className={`telemetry-val ${delayMinutes > 15 ? 'text-rose-600' : 'text-emerald-700'}`}>
                          {delayLabel}
                        </span>
                      </div>
                    </div>

                    <div className="telemetry-item">
                      <Navigation size={14} className="telemetry-icon text-indigo-600" />
                      <div className="telemetry-text">
                        <span className="telemetry-label">Next Station</span>
                        <span className="telemetry-val">{nextStationName}</span>
                      </div>
                    </div>
                  </div>

                  <div className="train-popup-precision-note">
                    {trainPositionInfo.isGps ? (
                      <span>📡 Live GPS Unit Telemetry</span>
                    ) : (
                      <span>📍 Station-Resolved Location ({trainPositionInfo.stationCode})</span>
                    )}
                  </div>
                </div>
              </Popup>
            </Marker>
          )}
        </MapContainer>
      </div>

      <div className="map-footer-caption">
        <span>
          Showing {stopsWithCoords.length} of {routeSchedule?.total_stops || stopsWithCoords.length} verified track halts with geospatial coordinates.
        </span>
        <span className="map-interactive-hint">Click any station or train marker for real-time telemetry.</span>
      </div>
    </section>
  );
};
