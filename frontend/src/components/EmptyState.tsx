import React from 'react';
import { Search, Train, ArrowRight, Navigation, Milestone, MapPin } from 'lucide-react';

interface EmptyStateProps {
  onNavigateToSearch: () => void;
  isLoading?: boolean;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  onNavigateToSearch,
  isLoading = false
}) => {
  return (
    <div className="dashboard-welcome-container" aria-label="Welcome to Dynamic Train ETA">
      {/* Central Welcome Card */}
      <div className="empty-state-card dashboard-hero-card">
        {/* Railway Icon illustration */}
        <div className="empty-state-icon-wrapper" aria-hidden="true">
          <Train size={38} className="empty-train-icon" />
        </div>

        {/* Primary Empty State Messaging */}
        <div className="empty-state-text-block">
          <h2 className="empty-state-title">Welcome to Dynamic Train ETA</h2>
          <p className="empty-state-description">
            Search for a train to view live status, route tracking and AI-powered ETA predictions.
          </p>
        </div>

        {/* Primary CTA: Button -> Search Train */}
        <div className="empty-state-primary-action">
          <button
            id="empty-state-search-train-btn"
            type="button"
            className="empty-search-primary-btn"
            onClick={onNavigateToSearch}
            disabled={isLoading}
          >
            <Search size={16} aria-hidden="true" />
            <span>Search Train</span>
            <ArrowRight size={15} aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Three Small Informational Feature Cards */}
      <div className="dashboard-feature-cards-grid" aria-label="Platform Feature Overview">
        {/* Card 1: Live Tracking */}
        <div className="dashboard-feature-card" id="feature-card-live-tracking">
          <div className="feature-card-header">
            <div className="feature-icon-box blue" aria-hidden="true">
              <Navigation size={20} />
            </div>
            <h3 className="feature-card-title">Live Tracking</h3>
          </div>
          <p className="feature-card-desc">
            Monitor real-time station progression, GPS telemetry, delay classification, and live schedule status across Indian Railways.
          </p>
        </div>

        {/* Card 2: ETA Prediction */}
        <div className="dashboard-feature-card" id="feature-card-eta-prediction">
          <div className="feature-card-header">
            <div className="feature-icon-box cyan" aria-hidden="true">
              <Milestone size={20} />
            </div>
            <h3 className="feature-card-title">ETA Prediction</h3>
          </div>
          <p className="feature-card-desc">
            Multi-horizon arrival forecasting (H1, H2, H3) powered by trained XGBoost regressors and topological route features.
          </p>
        </div>

        {/* Card 3: Railway Route Map */}
        <div className="dashboard-feature-card" id="feature-card-route-map">
          <div className="feature-card-header">
            <div className="feature-icon-box indigo" aria-hidden="true">
              <MapPin size={20} />
            </div>
            <h3 className="feature-card-title">Railway Route Map</h3>
          </div>
          <p className="feature-card-desc">
            Interactive geographic visualization displaying railway corridors, passed halts, and live train positions along the track.
          </p>
        </div>
      </div>
    </div>
  );
};
