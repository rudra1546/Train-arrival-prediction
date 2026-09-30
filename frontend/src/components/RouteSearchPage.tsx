import React, { useState, useEffect } from 'react';
import {
  Search,
  ArrowRightLeft,
  Calendar,
  Train,
  MapPin,
  ArrowRight,
  AlertCircle,
  History,
  RotateCcw,
  Sparkles
} from 'lucide-react';
import { StationAutocomplete } from './StationAutocomplete';
import {
  searchTrainsBetweenStations,
  getRecentSearches,
  saveRecentSearch
} from '../services/routeSearch';
import { saveLastSearchedTrain, type LastSearchedTrain } from '../services/persistence';
import type { RouteSearchResult, RecentTrainSearch } from '../types/route';

interface RouteSearchPageProps {
  onSelectTrain: (train: LastSearchedTrain) => void;
  lastSearchedTrain?: string;
}

export const RouteSearchPage: React.FC<RouteSearchPageProps> = ({
  onSelectTrain,
  lastSearchedTrain
}) => {
  const [fromStation, setFromStation] = useState<string>('ADI');
  const [toStation, setToStation] = useState<string>('NDLS');
  const [journeyDate, setJourneyDate] = useState<string>(() => {
    return new Date().toISOString().split('T')[0];
  });

  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [results, setResults] = useState<RouteSearchResult[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [recentSearches, setRecentSearches] = useState<RecentTrainSearch[]>([]);

  // Load recent searches on mount
  useEffect(() => {
    setRecentSearches(getRecentSearches());
  }, []);

  const handleSwapStations = () => {
    const temp = fromStation;
    setFromStation(toStation);
    setToStation(temp);
  };

  const executeSearch = async (from: string, to: string, date: string) => {
    if (!from || !to) {
      setSearchError('Please select both Origin and Destination stations.');
      return;
    }
    if (from.toUpperCase() === to.toUpperCase()) {
      setSearchError('Origin and Destination stations cannot be the same.');
      return;
    }

    setSearchError(null);
    setIsSearching(true);
    setHasSearched(true);

    try {
      const data = await searchTrainsBetweenStations(from, to, date);
      setResults(data);
    } catch (err: any) {
      setSearchError(err?.message || 'Failed to search trains. Please try again.');
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeSearch(fromStation, toStation, journeyDate);
  };

  const handleQuickRoute = (from: string, to: string) => {
    setFromStation(from);
    setToStation(to);
    executeSearch(from, to, journeyDate);
  };

  const handleViewTrain = (train: RouteSearchResult) => {
    // 1. Save to recents list
    saveRecentSearch({
      train_no: train.train_no,
      train_name: train.train_name,
      searched_at: new Date().toISOString(),
      from_station: train.from_station,
      to_station: train.to_station
    });
    setRecentSearches(getRecentSearches());

    // 2. Persist as dynamic_eta_last_train (required fields only)
    const selectedTrain: LastSearchedTrain = {
      train_no: train.train_no,
      train_name: train.train_name,
      origin: train.origin,
      destination: train.destination,
      journey_date: journeyDate
    };
    saveLastSearchedTrain(selectedTrain);

    // 3. Trigger dashboard navigation & live ETA load
    onSelectTrain(selectedTrain);
  };

  const handleTrackRecent = (item: RecentTrainSearch) => {
    const selectedTrain: LastSearchedTrain = {
      train_no: item.train_no,
      train_name: item.train_name,
      origin: item.from_station || 'Origin',
      destination: item.to_station || 'Destination',
      journey_date: journeyDate
    };
    saveLastSearchedTrain(selectedTrain);
    onSelectTrain(selectedTrain);
  };

  return (
    <div className="route-search-page" aria-label="Railway Route & Train Search">
      {/* Search Header Banner */}
      <section className="route-search-hero">
        <div className="search-hero-content">
          <div className="hero-icon-pill" aria-hidden="true">
            <Train size={18} />
            <span>Timetable Route Search</span>
          </div>
          <h2 className="search-hero-title">Find Trains Between Stations</h2>
          <p className="search-hero-subtitle">
            Search scheduled coaching trains across Indian Railways and track live ETA predictions
          </p>
        </div>
      </section>

      {/* Main Route Search Form Card */}
      <section className="route-search-card" aria-label="Train Search Controls">
        <form onSubmit={handleSearchSubmit} className="route-form">
          <div className="route-inputs-strip">
            {/* From Station */}
            <div className="route-input-col from-col">
              <StationAutocomplete
                id="from-station-input"
                label="From Station"
                value={fromStation}
                onChange={(code) => {
                  setFromStation(code);
                  if (searchError) setSearchError(null);
                }}
                placeholder="Origin station (e.g. NDLS)..."
                disabled={isSearching}
              />
            </div>

            {/* Swap Button */}
            <div className="route-swap-col">
              <button
                type="button"
                className="route-swap-btn"
                onClick={handleSwapStations}
                disabled={isSearching}
                title="Swap Origin and Destination"
                aria-label="Swap Origin and Destination Stations"
              >
                <ArrowRightLeft size={16} />
              </button>
            </div>

            {/* To Station */}
            <div className="route-input-col to-col">
              <StationAutocomplete
                id="to-station-input"
                label="To Station"
                value={toStation}
                onChange={(code) => {
                  setToStation(code);
                  if (searchError) setSearchError(null);
                }}
                placeholder="Destination station (e.g. CNB)..."
                disabled={isSearching}
              />
            </div>

            {/* Journey Date */}
            <div className="route-input-col date-col">
              <label htmlFor="journey-date-input" className="autocomplete-field-label">
                <Calendar size={14} className="label-pin-icon" aria-hidden="true" />
                <span>Journey Date</span>
              </label>
              <div className="date-input-wrapper">
                <input
                  id="journey-date-input"
                  type="date"
                  className="route-date-input"
                  value={journeyDate}
                  onChange={(e) => setJourneyDate(e.target.value)}
                  disabled={isSearching}
                />
              </div>
            </div>

            {/* Search Trains Button */}
            <div className="route-submit-col">
              <button
                id="search-trains-submit-btn"
                type="submit"
                className="route-search-submit-btn"
                disabled={isSearching}
              >
                {isSearching ? (
                  <>
                    <span className="search-spinner" aria-hidden="true" />
                    <span>Searching...</span>
                  </>
                ) : (
                  <>
                    <Search size={16} aria-hidden="true" />
                    <span>Search Trains</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>

        {searchError && (
          <div className="route-search-error-alert" role="alert">
            <AlertCircle size={16} aria-hidden="true" />
            <span>{searchError}</span>
          </div>
        )}
      </section>

      {/* Recent / Previously Searched Trains Section */}
      {recentSearches.length > 0 && (
        <section className="recent-searches-section" aria-label="Recently Viewed Trains">
          <div className="recent-header-row">
            <div className="recent-title-group">
              <History size={16} className="recent-icon" aria-hidden="true" />
              <h3 className="recent-title">Recently Viewed Trains</h3>
            </div>
            {lastSearchedTrain && (
              <span className="last-viewed-pill">
                Active in Dashboard: <strong>{lastSearchedTrain}</strong>
              </span>
            )}
          </div>

          <div className="recent-chips-grid">
            {recentSearches.map((item) => (
              <div key={item.train_no} className="recent-train-chip">
                <div className="recent-chip-left">
                  <span className="recent-badge-no">{item.train_no}</span>
                  <div className="recent-names">
                    <span className="recent-name">{item.train_name}</span>
                    {item.from_station && item.to_station && (
                      <span className="recent-route-sub">
                        {item.from_station} &rarr; {item.to_station}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  className="recent-track-btn"
                  onClick={() => handleTrackRecent(item)}
                  title={`Track ${item.train_no} on Dashboard`}
                >
                  <span>Track ETA</span>
                  <ArrowRight size={13} aria-hidden="true" />
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Search Results Area */}
      <section className="search-results-area" aria-label="Train Search Results">
        {/* State 1: Loading */}
        {isSearching && (
          <div className="results-loading-state" aria-busy="true">
            <div className="results-loading-banner">
              <RotateCcw size={16} className="spinning" aria-hidden="true" />
              <span>Querying Indian Railways schedule database for direct routes...</span>
            </div>
            <div className="results-skeleton-grid">
              {[1, 2, 3].map((n) => (
                <div key={n} className="result-card-skeleton">
                  <div className="skel-bone skel-header-line" />
                  <div className="skel-bone skel-body-box" />
                  <div className="skel-bone skel-footer-line" />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* State 2: Results Display */}
        {!isSearching && hasSearched && results.length > 0 && (
          <div className="results-container">
            <div className="results-summary-bar">
              <div className="summary-text-block">
                <h3 className="results-count-title">
                  {results.length} Scheduled {results.length === 1 ? 'Train' : 'Trains'} Found
                </h3>
                <span className="results-route-tag">
                  {fromStation} &rarr; {toStation} &bull; Journey Date: {journeyDate}
                </span>
              </div>
            </div>

            <div className="train-results-list">
              {results.map((train) => (
                <article key={train.train_no} className="train-result-card">
                  {/* Left Identity Column */}
                  <div className="result-identity-col">
                    <div className="result-train-no-box">
                      <span className="result-train-no">{train.train_no}</span>
                    </div>
                    <div className="result-train-name-box">
                      <h4 className="result-train-name">{train.train_name}</h4>
                      <span className="result-type-badge">{train.type_label}</span>
                    </div>
                  </div>

                  {/* Middle Timing & Route Column */}
                  <div className="result-timing-col">
                    <div className="timing-box departure">
                      <span className="timing-label">Departs {train.from_station}</span>
                      <span className="timing-val">{train.departure_time}</span>
                    </div>

                    <div className="timing-route-diagram">
                      {train.duration && <span className="duration-tag">{train.duration}</span>}
                      <div className="route-arrow-track">
                        <span className="track-line" />
                        <span className="stops-count-pill">{train.stops} stops</span>
                        <span className="track-arrow">&rarr;</span>
                      </div>
                      <span className="route-terminals-sub">
                        {train.origin} &rarr; {train.destination}
                      </span>
                    </div>

                    <div className="timing-box arrival">
                      <span className="timing-label">Arrives {train.to_station}</span>
                      <span className="timing-val">{train.arrival_time}</span>
                    </div>
                  </div>

                  {/* Right Action Column */}
                  <div className="result-action-col">
                    <button
                      type="button"
                      className="view-train-btn"
                      onClick={() => handleViewTrain(train)}
                      title={`View live ETA details for Train ${train.train_no}`}
                    >
                      <span>View Train</span>
                      <ArrowRight size={14} aria-hidden="true" />
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </div>
        )}

        {/* State 3: No Results */}
        {!isSearching && hasSearched && results.length === 0 && (
          <div className="results-empty-state">
            <div className="no-results-icon-wrap" aria-hidden="true">
              <AlertCircle size={32} />
            </div>
            <h3 className="no-results-title">No Direct Trains Found</h3>
            <p className="no-results-desc">
              No direct scheduled trains were found running between <strong>{fromStation}</strong> and{' '}
              <strong>{toStation}</strong> in the timetable records. Try major railway junction hubs
              such as <strong>NDLS</strong>, <strong>HWH</strong>, <strong>MMCT</strong>, <strong>CNB</strong>, or <strong>BPL</strong>.
            </p>
          </div>
        )}

        {/* State 4: Initial Empty State (No search performed yet) */}
        {!isSearching && !hasSearched && (
          <div className="search-initial-empty-card">
            <div className="empty-prompt-icon" aria-hidden="true">
              <Sparkles size={28} />
            </div>
            <h3 className="empty-prompt-title">Select Stations to View Scheduled Trains</h3>
            <p className="empty-prompt-desc">
              Select an origin and destination station from the search bar above or choose a popular
              route shortcut below to query the railway database and track live ETA forecasts.
            </p>

            <div className="popular-routes-block">
              <span className="popular-routes-label">Popular Routes:</span>
              <div className="popular-routes-chips">
                <button
                  type="button"
                  className="route-shortcut-chip"
                  onClick={() => handleQuickRoute('ADI', 'NDLS')}
                >
                  <MapPin size={13} aria-hidden="true" />
                  <span>Ahmedabad (ADI) &rarr; New Delhi (NDLS)</span>
                </button>
                <button
                  type="button"
                  className="route-shortcut-chip"
                  onClick={() => handleQuickRoute('NDLS', 'CNB')}
                >
                  <MapPin size={13} aria-hidden="true" />
                  <span>New Delhi (NDLS) &rarr; Kanpur (CNB)</span>
                </button>
                <button
                  type="button"
                  className="route-shortcut-chip"
                  onClick={() => handleQuickRoute('HWH', 'NDLS')}
                >
                  <MapPin size={13} aria-hidden="true" />
                  <span>Howrah (HWH) &rarr; New Delhi (NDLS)</span>
                </button>
                <button
                  type="button"
                  className="route-shortcut-chip"
                  onClick={() => handleQuickRoute('MMCT', 'NDLS')}
                >
                  <MapPin size={13} aria-hidden="true" />
                  <span>Mumbai (MMCT) &rarr; New Delhi (NDLS)</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
};
