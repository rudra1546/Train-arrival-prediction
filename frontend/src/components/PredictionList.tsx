import React from 'react';
import type { HorizonPrediction } from '../types/eta';
import { PredictionCard } from './PredictionCard';
import { Milestone, Layers } from 'lucide-react';

interface PredictionListProps {
  predictions: HorizonPrediction[];
}

export const PredictionList: React.FC<PredictionListProps> = ({ predictions }) => {
  if (!predictions || predictions.length === 0) {
    return null;
  }

  // Sort by horizon ascending
  const sorted = [...predictions].sort((a, b) => a.horizon - b.horizon);
  const count = sorted.length;
  const countLabel = count === 1 ? '1 Horizon Active' : `${count} Horizons Active`;

  return (
    <section className="predictions-section" id="upcoming-predictions-section" aria-label="Upcoming Multi-Horizon ETA Predictions">
      <div className="section-title-row">
        <div className="section-title-with-icon">
          <Milestone size={18} className="section-icon" aria-hidden="true" />
          <div>
            <h3 className="section-title">Upcoming Predictions</h3>
            <p className="section-subtitle">Simultaneous multi-horizon delay predictions powered by XGBoost</p>
          </div>
        </div>
        <div className="horizon-badge-wrapper">
          <Layers size={13} aria-hidden="true" />
          <span className="horizon-count-badge">{countLabel}</span>
        </div>
      </div>

      <div className="predictions-grid">
        {sorted.map((pred) => (
          <PredictionCard key={pred.horizon} prediction={pred} />
        ))}
      </div>
    </section>
  );
};
