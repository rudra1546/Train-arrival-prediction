import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { RouteSearchPage } from './components/RouteSearchPage';
import { LiveTrackingPage } from './components/LiveTrackingPage';
import { ETAPredictionPage } from './components/ETAPredictionPage';
import { DashboardOverview } from './components/DashboardOverview';
import { checkBackendHealth } from './services/api';
import {
  getLastSearchedTrain,
  saveLastSearchedTrain,
  clearLastSearchedTrain,
  type LastSearchedTrain
} from './services/persistence';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState<boolean>(false);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean | null>(null);

  // Load last searched train from browser localStorage (dynamic_eta_last_train)
  const [savedTrain, setSavedTrain] = useState<LastSearchedTrain | null>(() => getLastSearchedTrain());
  const [refreshCounter, setRefreshCounter] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Check API connectivity on load
  const verifyConnectivity = useCallback(async () => {
    const isHealthy = await checkBackendHealth();
    setIsBackendConnected(isHealthy);
  }, []);

  useEffect(() => {
    verifyConnectivity();
  }, [verifyConnectivity]);

  const handleRefresh = async () => {
    verifyConnectivity();
    setRefreshCounter((prev) => prev + 1);
  };

  const handleClearSelectedTrain = () => {
    clearLastSearchedTrain();
    setSavedTrain(null);
  };

  const handleSelectTrainFromSearch = (selected: LastSearchedTrain) => {
    saveLastSearchedTrain(selected);
    setSavedTrain(selected);
    setActiveTab('dashboard');
  };

  const handleViewLiveTracking = () => {
    setActiveTab('tracking');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleViewETAPrediction = () => {
    setActiveTab('prediction');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSelectNavTab = (tabId: string) => {
    setActiveTab(tabId);
    setIsMobileSidebarOpen(false);

    if (tabId === 'dashboard' || tabId === 'search' || tabId === 'tracking' || tabId === 'prediction') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else if (tabId === 'analytics') {
      setActiveTab('dashboard');
      setTimeout(() => {
        const mlEl =
          document.getElementById('ml-model-info-section') ||
          document.querySelector('.ml-model-info-section');
        if (mlEl) {
          mlEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 50);
    }
  };

  return (
    <div className="platform-layout">
      {/* 1. Left Sidebar (Fixed desktop + Mobile slide-out drawer) */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={handleSelectNavTab}
        isOpen={isMobileSidebarOpen}
        onClose={() => setIsMobileSidebarOpen(false)}
      />

      {/* Main Viewport Container */}
      <div className="platform-main-container">
        {/* 2. Top Header */}
        <Header
          onRefresh={handleRefresh}
          isLoading={isLoading}
          hasActiveTrain={Boolean(savedTrain?.train_no)}
          isBackendConnected={isBackendConnected}
          onToggleMobileMenu={() => setIsMobileSidebarOpen((prev) => !prev)}
        />

        {/* 3. Main Content: Route Search Page OR Live Tracking OR ETA Prediction OR Dashboard Overview */}
        {activeTab === 'search' ? (
          <main className="dashboard-content-area search-page-view">
            <RouteSearchPage
              onSelectTrain={handleSelectTrainFromSearch}
              lastSearchedTrain={savedTrain?.train_no || ''}
            />
          </main>
        ) : activeTab === 'tracking' ? (
          <main className="dashboard-content-area live-tracking-page-view">
            <LiveTrackingPage
              savedTrain={savedTrain}
              onNavigateToSearch={() => setActiveTab('search')}
              onNavigateToPrediction={handleViewETAPrediction}
            />
          </main>
        ) : activeTab === 'prediction' ? (
          <main className="dashboard-content-area eta-prediction-page-view">
            <ETAPredictionPage
              savedTrain={savedTrain}
              onNavigateToSearch={() => setActiveTab('search')}
              onNavigateToTracking={handleViewLiveTracking}
            />
          </main>
        ) : (
          <main className="dashboard-content-area dashboard-page-view">
            <DashboardOverview
              savedTrain={savedTrain}
              onNavigateToSearch={() => setActiveTab('search')}
              onNavigateToTracking={handleViewLiveTracking}
              onNavigateToPrediction={handleViewETAPrediction}
              onClearTrain={handleClearSelectedTrain}
              refreshTrigger={refreshCounter}
              onLoadingChange={setIsLoading}
            />
          </main>
        )}

        {/* Platform Footer */}
        <footer className="platform-footer">
          <div className="footer-left">
            <span>Dynamic Train ETA Platform • SIH 26028 Real-Time Operational Infrastructure</span>
          </div>
          <div className="footer-right">
            <span>Inference: <strong>XGBoost Regressors (H1, H2, H3)</strong></span>
            <span className="footer-sep">•</span>
            <span>Upstream: <strong>RailRadar Telemetry</strong></span>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default App;
