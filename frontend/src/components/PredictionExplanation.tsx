import React from 'react';
import { Cpu, ShieldCheck, Database, GitBranch } from 'lucide-react';

export const PredictionExplanation: React.FC = () => {
  return (
    <section className="ml-model-info-section" id="ml-model-info-section" aria-label="ML Model Information & Pipeline Architecture">
      <div className="section-title-row">
        <div className="section-title-with-icon">
          <Cpu size={18} className="section-icon" aria-hidden="true" />
          <div>
            <h3 className="section-title">ML Model & Prediction Information</h3>
            <p className="section-subtitle">Technical specifications for the SIH 26028 dynamic arrival forecasting system</p>
          </div>
        </div>
      </div>

      <div className="model-info-grid">
        {/* Card 1 */}
        <div className="model-info-card">
          <div className="info-card-header">
            <span className="info-icon-badge blue" aria-hidden="true">
              <GitBranch size={16} />
            </span>
            <h4 className="info-card-title">Multi-Horizon Gradient Boosting</h4>
          </div>
          <p className="info-card-body">
            Independent XGBoost Regressors dedicated to Horizon 1 (immediate next stop), Horizon 2 (two stops ahead),
            and Horizon 3 (three stops ahead) producing synchronized ETA forecasts.
          </p>
          <div className="info-meta-tag">Models: H1, H2, H3 Active</div>
        </div>

        {/* Card 2 */}
        <div className="model-info-card">
          <div className="info-card-header">
            <span className="info-icon-badge cyan" aria-hidden="true">
              <Database size={16} />
            </span>
            <h4 className="info-card-title">27 Leak-Free Engineered Features</h4>
          </div>
          <p className="info-card-body">
            Strictly validated feature set incorporating historical station delay velocities, schedule run durations,
            distance progression intervals, and day-of-week temporal encodings.
          </p>
          <div className="info-meta-tag">Leakage Audit: Verified Clean</div>
        </div>

        {/* Card 3 */}
        <div className="model-info-card">
          <div className="info-card-header">
            <span className="info-icon-badge navy" aria-hidden="true">
              <ShieldCheck size={16} />
            </span>
            <h4 className="info-card-title">Live Telemetry Synchronization</h4>
          </div>
          <p className="info-card-body">
            Real-time GPS/NTES telemetry ingested securely through the RailRadar upstream provider and mapped dynamically
            against official Indian Railways timetables.
          </p>
          <div className="info-meta-tag">Telemetry: Real-Time Stream</div>
        </div>
      </div>
    </section>
  );
};
