import React from 'react';
import { AlertCircle, RotateCcw, X, Search } from 'lucide-react';
import type { APIErrorState } from '../types/eta';

interface ErrorStateProps {
  error: APIErrorState;
  onRetry?: () => void;
  onClearTrain?: () => void;
  onNavigateToSearch?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  error,
  onRetry,
  onClearTrain,
  onNavigateToSearch
}) => {
  return (
    <div className="error-state-card" role="alert">
      <div className="error-icon-box" aria-hidden="true">
        <AlertCircle size={22} className="error-icon" />
      </div>

      <div className="error-details-box">
        <div className="error-title-row">
          <h4 className="error-title-text">{error.title}</h4>
          {error.statusCode ? (
            <span className="error-code-badge">HTTP {error.statusCode}</span>
          ) : null}
        </div>
        <p className="error-message-text">{error.message}</p>

        <div className="error-actions-row">
          {onRetry && (
            <button
              id="error-retry-btn"
              type="button"
              className="error-retry-btn"
              onClick={onRetry}
            >
              <RotateCcw size={14} aria-hidden="true" />
              <span>Retry Request</span>
            </button>
          )}

          {onNavigateToSearch && (
            <button
              id="error-search-btn"
              type="button"
              className="error-secondary-btn"
              onClick={onNavigateToSearch}
            >
              <Search size={14} aria-hidden="true" />
              <span>Search Another Train</span>
            </button>
          )}

          {onClearTrain && (
            <button
              id="error-clear-btn"
              type="button"
              className="error-clear-btn"
              onClick={onClearTrain}
              title="Clear selected train and return to empty dashboard"
            >
              <X size={14} aria-hidden="true" />
              <span>Clear Selected Train</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
