import React, { useState } from 'react';
import { Search } from 'lucide-react';

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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanNo = trainInput.trim();

    if (!cleanNo) {
      setValidationError('Please enter a train number.');
      return;
    }

    if (!/^\d{4,5}$/.test(cleanNo)) {
      setValidationError('Train number must be 4 or 5 digits.');
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
    <div className="search-card">
      <form onSubmit={handleSubmit} className="search-form">
        <div className="search-input-wrapper">
          <Search size={18} className="search-icon-prefix" />
          <input
            id="train-search-input"
            type="text"
            className="search-input"
            placeholder="Enter train number"
            value={trainInput}
            onChange={(e) => {
              setTrainInput(e.target.value);
              if (validationError) setValidationError(null);
            }}
            disabled={isLoading}
            autoComplete="off"
            maxLength={6}
          />
        </div>
        <button
          id="train-search-submit"
          type="submit"
          className="search-button"
          disabled={isLoading}
        >
          {isLoading ? 'Tracking...' : 'Track Train'}
        </button>
      </form>

      {validationError && (
        <div style={{ color: 'var(--color-severe)', fontSize: '0.8125rem', fontWeight: 500 }}>
          {validationError}
        </div>
      )}

      <div className="search-quick-chips">
        <span className="chip-label">Popular Trains:</span>
        <button
          type="button"
          className="quick-chip"
          onClick={() => handleChipClick('12301')}
          disabled={isLoading}
        >
          12301 (Howrah Rajdhani)
        </button>
        <button
          type="button"
          className="quick-chip"
          onClick={() => handleChipClick('12951')}
          disabled={isLoading}
        >
          12951 (Mumbai Rajdhani)
        </button>
        <button
          type="button"
          className="quick-chip"
          onClick={() => handleChipClick('12002')}
          disabled={isLoading}
        >
          12002 (Bhopal Shatabdi)
        </button>
      </div>
    </div>
  );
};
