import React from 'react';
import {
  Train,
  LayoutDashboard,
  Search,
  Radio,
  Milestone,
  BarChart3,
  X
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  onSelectTab: (tab: string) => void;
  isOpen?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  isOpen = false,
  onClose
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'search', label: 'Search Train', icon: Search },
    { id: 'tracking', label: 'Live Tracking', icon: Radio },
    { id: 'prediction', label: 'ETA Prediction', icon: Milestone },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  ];

  const handleItemClick = (id: string) => {
    onSelectTab(id);
    if (onClose) {
      onClose();
    }
  };

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {isOpen && (
        <div
          className="sidebar-mobile-backdrop"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside className={`app-sidebar ${isOpen ? 'mobile-open' : ''}`} aria-label="Sidebar Navigation">
        {/* Brand & Railway Emblem Logo */}
        <div className="sidebar-brand">
          <div className="brand-logo-container" aria-hidden="true">
            <Train size={22} className="brand-train-icon" />
            <div className="brand-logo-glow" />
          </div>
          <div className="brand-text-block">
            <span className="brand-title">Dynamic Train ETA</span>
            <span className="brand-subtitle">Railway Operations Platform</span>
          </div>

          {/* Close button for mobile navigation */}
          {onClose && (
            <button
              type="button"
              className="sidebar-mobile-close-btn"
              onClick={onClose}
              aria-label="Close navigation sidebar"
            >
              <X size={18} />
            </button>
          )}
        </div>

        {/* Navigation List */}
        <nav className="sidebar-nav">
          <div className="nav-group-label">OPERATIONS & CONTROL</div>
          <ul className="nav-items-list">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    className={`nav-item-btn ${isActive ? 'active' : ''}`}
                    onClick={() => handleItemClick(item.id)}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <Icon size={18} className="nav-item-icon" />
                    <span className="nav-item-label">{item.label}</span>
                    {isActive && <span className="nav-active-pill" aria-hidden="true" />}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Sidebar System Telemetry Card */}
        <div className="sidebar-footer-card">
          <div className="system-status-indicator">
            <span className="status-dot-pulse" aria-hidden="true" />
            <span className="status-title">System Operational</span>
          </div>
          <div className="system-telemetry-meta">
            <div className="meta-row">
              <span className="meta-key">Inference Engine</span>
              <span className="meta-val">XGBoost H1/H2/H3</span>
            </div>
            <div className="meta-row">
              <span className="meta-key">Telemetry Stream</span>
              <span className="meta-val">RailRadar Live</span>
            </div>
            <div className="meta-row">
              <span className="meta-key">Model Protocol</span>
              <span className="meta-val">SIH 26028 v1.0</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
