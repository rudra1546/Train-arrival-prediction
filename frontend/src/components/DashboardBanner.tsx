import React from 'react';
import { Activity, ShieldCheck, Cpu } from 'lucide-react';
import trainBannerImg from '../assets/train-banner.jpeg';

export const DashboardBanner: React.FC = () => {
  return (
    <div
      className="dashboard-top-banner"
      style={{ backgroundImage: `url(${trainBannerImg})` }}
      role="banner"
      aria-label="Railway Operations Banner"
    >
      <div className="banner-dark-overlay">
        <div className="banner-inner-content">
          <div className="banner-pill-badge">
            <span className="banner-pulse-indicator" aria-hidden="true" />
            <Activity size={13} className="banner-badge-icon" aria-hidden="true" />
            <span className="banner-badge-text">Real-Time Railway Operations</span>
          </div>

          <h1 className="banner-headline">
            Dynamic Train Arrival &amp; ETA Platform
          </h1>

          <p className="banner-subtext">
            AI-driven multi-horizon delay forecasting and live tracking across Indian Railways corridors.
          </p>

          <div className="banner-features-row">
            <div className="banner-feature-tag">
              <Cpu size={12} aria-hidden="true" />
              <span>Multi-Horizon Inference</span>
            </div>
            <div className="banner-feature-tag">
              <ShieldCheck size={12} aria-hidden="true" />
              <span>Live Railway Telemetry</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
