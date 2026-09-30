import React from 'react';
import { Train } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="app-header">
      <div className="header-brand">
        <div className="brand-icon-wrapper" aria-hidden="true">
          <Train size={24} />
        </div>
        <div className="header-titles">
          <h1>Dynamic Train ETA</h1>
          <p>AI-powered real-time arrival prediction</p>
        </div>
      </div>
      <div className="header-status">
        <div className="live-status-pill" title="Connected to live inference service">
          <span className="pulsing-dot" aria-hidden="true"></span>
          <span>Live Prediction System</span>
        </div>
      </div>
    </header>
  );
};
