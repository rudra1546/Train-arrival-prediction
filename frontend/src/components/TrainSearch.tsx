import React, { useState, useEffect } from 'react';
import { Search, Train, ArrowRight } from 'lucide-react';

interface TrainSearchProps {
  onSearch: (trainNo: string) => void;
  isLoading: boolean;
  initialValue?: string;
}

export const TrainSearch: React.FC<TrainSearchProps> = ({
  onSearch,
  isLoading,
  initialValue = ''
}) => {
  const [trainInput, setTrainInput] = useState(initialValue);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    setTrainInput(initialValue);
  }, [initialValue]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanNo = trainInput.trim();

    if (!cleanNo) {
      setValidationError('Please enter a valid 4 or 5-digit Indian Railways train number.');
      return;
    }

    if (!/^\d{4,5}$/.test(cleanNo)) {
      setValidationError('Train number must contain 4 or 5 numeric digits (e.g. 12301).');
      return;
    }

    setValidationError(null);
    onSearch(cleanNo);
  };

  const handleChipClick = (no: string) => {
    setTrainInput(no);
    setValidationError(null);
    onSearch(no);
  };

  return (
    <section className="train-search-card" aria-label="Train Search">
      <div className="search-card-header">
        <div className="search-header-titles">
          <h2 className="search-card-title">Live Train Telemetry & ETA Search</h2>
          <p className="search-card-subtitle">
            Enter an Indian Railways train number to generate dynamic arrival predictions
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="train-search-form">
        <div className="search-input-group">
          <Search size={18} className="search-field-icon" aria-hidden="true" />
          <input
            id="train-search-input"
            type="text"
            className="search-field-input"
            placeholder="Enter 4 or 5-digit train number (e.g. 12301, 12951, 12002)"
            value={trainInput}
            onChange={(e) => {
              setTrainInput(e.target.value);
              if (validationError) setValidationError(null);
            }}
            disabled={isLoading}
            autoComplete="off"
            maxLength={6}
            aria-label="Train number input"
          />
        </div>

        <button
          id="train-search-submit"
          type="submit"
          className="search-action-btn"
          disabled={isLoading}
        >
          {isLoading ? (
            <span className="btn-loading-state">
              <span className="search-spinner" aria-hidden="true" />
              Tracking...
            </span>
          ) : (
            <span className="btn-normal-state">
              <span>Track Train</span>
              <ArrowRight size={16} aria-hidden="true" />
            </span>
          )}
        </button>
      </form>

      {validationError && (
        <div className="search-validation-alert" role="alert">
          {validationError}
        </div>
      )}

      <div className="search-quick-recommendations">
        <span className="recommendations-label">
          <Train size={13} aria-hidden="true" />
          Quick Trains:
        </span>
        <div className="quick-chips-group">
          <button
            type="button"
            className="search-quick-chip"
            onClick={() => handleChipClick('12301')}
            disabled={isLoading}
          >
            <span className="chip-no">12301</span>
            <span className="chip-name">Howrah Rajdhani</span>
          </button>
          <button
            type="button"
            className="search-quick-chip"
            onClick={() => handleChipClick('12951')}
            disabled={isLoading}
          >
            <span className="chip-no">12951</span>
            <span className="chip-name">Mumbai Rajdhani</span>
          </button>
          <button
            type="button"
            className="search-quick-chip"
            onClick={() => handleChipClick('12002')}
            disabled={isLoading}
          >
            <span className="chip-no">12002</span>
            <span className="chip-name">Bhopal Shatabdi</span>
          </button>
        </div>
      </div>
    </section>
  );
};
