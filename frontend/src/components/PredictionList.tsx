import React from 'react';
import type { HorizonPrediction } from '../types/eta';
import { PredictionCard } from './PredictionCard';

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
  const countLabel = count === 1 ? '1 Horizon Available' : `${count} Horizons Available`;

  return (
    <section className="predictions-section">
      <div className="section-title-row">
        <h2>Expected Time of Arrival (ETA) Forecasts</h2>
        <span className="horizon-count-badge">{countLabel}</span>
      </div>

      <div className="predictions-grid">
        {sorted.map((pred) => (
          <PredictionCard key={pred.horizon} prediction={pred} />
        ))}
      </div>
    </section>
  );
};
