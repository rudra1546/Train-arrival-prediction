import React from 'react';
import { RotateCw, Menu, AlertCircle } from 'lucide-react';

interface HeaderProps {
  onRefresh?: () => void;
  isLoading?: boolean;
  hasActiveTrain?: boolean;
  isBackendConnected?: boolean | null;
  onToggleMobileMenu?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onRefresh,
  isLoading = false,
  hasActiveTrain = false,
  isBackendConnected = null,
  onToggleMobileMenu
}) => {
  return (
    <header className="app-top-header">
      <div className="top-header-left">
        {/* Mobile menu toggle hamburger */}
        {onToggleMobileMenu && (
          <button
            type="button"
            className="mobile-menu-toggle-btn"
            onClick={onToggleMobileMenu}
            aria-label="Open navigation sidebar"
          >
            <Menu size={20} />
          </button>
        )}

        <div className="top-header-titles">
          <h1 className="top-header-title">Train ETA Dashboard</h1>
          <p className="top-header-subtitle">Dynamic, data-driven railway arrival predictions</p>
        </div>
      </div>

      <div className="top-header-actions">
        {/* Live system status indicator based on actual API availability */}
        <div
          className={`system-live-badge ${isBackendConnected === false ? 'offline' : 'online'}`}
          title={
            isBackendConnected === false
              ? 'FastAPI prediction backend is unreachable'
              : 'FastAPI prediction service and ML models online'
          }
        >
          {isBackendConnected === false ? (
            <>
              <AlertCircle size={13} className="live-status-icon offline" aria-hidden="true" />
              <span className="live-status-text">Backend Offline</span>
            </>
          ) : (
            <>
              <span className="live-pulse-dot" aria-hidden="true" />
              <span className="live-status-text">System Connected</span>
            </>
          )}
        </div>

        {/* Refresh button */}
        <button
          id="header-refresh-btn"
          type="button"
          className="header-refresh-btn"
          onClick={onRefresh}
          disabled={isLoading || !hasActiveTrain}
          title={
            hasActiveTrain
              ? 'Refresh live train telemetry & ETA predictions'
              : 'Search a train to enable live refresh'
          }
        >
          <RotateCw size={14} className={isLoading ? 'spinning' : ''} aria-hidden="true" />
          <span>Refresh</span>
        </button>
      </div>
    </header>
  );
};
