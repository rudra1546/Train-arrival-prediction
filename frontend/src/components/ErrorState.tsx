import React from 'react';
import { AlertCircle, RotateCcw } from 'lucide-react';
import type { APIErrorState } from '../types/eta';

interface ErrorStateProps {
  error: APIErrorState;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({ error, onRetry }) => {
  return (
    <div className="error-state-card" role="alert">
      <AlertCircle size={22} className="error-icon" aria-hidden="true" />
      <div className="error-content" style={{ flex: 1 }}>
        <h4>{error.title}</h4>
        <p>{error.message}</p>
        {onRetry && (
          <div style={{ marginTop: '0.75rem' }}>
            <button
              type="button"
              className="quick-chip"
              onClick={onRetry}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', background: '#ffffff' }}
            >
              <RotateCcw size={13} />
              <span>Retry Search</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
