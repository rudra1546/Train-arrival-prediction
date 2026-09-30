import React from 'react';
import { Calendar, RefreshCw } from 'lucide-react';
import { StatusBadge } from './StatusBadge';

interface TrainSummaryProps {
  trainNo: string;
  trainName: string;
  status: string;
  journeyDate: string;
  lastUpdatedText?: string;
  onRefresh: () => void;
  isLoading: boolean;
}

export const TrainSummary: React.FC<TrainSummaryProps> = ({
  trainNo,
  trainName,
  status,
  journeyDate,
  lastUpdatedText,
  onRefresh,
  isLoading
}) => {
  return (
    <div className="train-summary-card">
      <div className="summary-header-row">
        <div className="train-title-block">
          <span className="train-badge-no">{trainNo}</span>
          <h2 className="train-name-text">{trainName}</h2>
        </div>
        <div className="summary-actions-block">
          {lastUpdatedText && (
            <span className="last-updated-text" style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
              {lastUpdatedText}
            </span>
          )}
          <StatusBadge status={status} />
          <button
            id="refresh-eta-btn"
            type="button"
            className="refresh-button"
            onClick={onRefresh}
            disabled={isLoading}
            title="Refresh live prediction"
          >
            <RefreshCw size={14} className={isLoading ? 'spinner' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <div className="summary-meta-grid">
        <div className="meta-item">
          <span className="meta-item-label">Operational Status</span>
          <span className="meta-item-value">{status || 'Running'}</span>
        </div>
        <div className="meta-item">
          <span className="meta-item-label">Journey Start Date</span>
          <span className="meta-item-value">
            <Calendar size={15} style={{ color: 'var(--text-muted)' }} />
            {journeyDate || 'Today'}
          </span>
        </div>
      </div>
    </div>
  );
};
