import React from 'react';
import { Info } from 'lucide-react';

export const PredictionExplanation: React.FC = () => {
  return (
    <div className="explanation-card">
      <Info size={18} className="explanation-icon" aria-hidden="true" />
      <p>
        <strong>Prediction Methodology:</strong> Predictions are generated using live train telemetry,
        historical delay patterns, timetable information, route progress, and an XGBoost machine-learning model.
      </p>
    </div>
  );
};
