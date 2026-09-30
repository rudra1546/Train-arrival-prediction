import React, { useState } from 'react';
import { Header } from './components/Header';
import { TrainSearch } from './components/TrainSearch';
import { TrainSummary } from './components/TrainSummary';
import { CurrentStationCard } from './components/CurrentStationCard';
import { PredictionList } from './components/PredictionList';
import { PredictionExplanation } from './components/PredictionExplanation';
import { EmptyState } from './components/EmptyState';
import { ErrorState } from './components/ErrorState';
import { LoadingSkeleton } from './components/LoadingSkeleton';
import { fetchTrainETA } from './services/api';
import type { TrainETAResponse, APIErrorState } from './types/eta';

export const App: React.FC = () => {
  const [currentTrain, setCurrentTrain] = useState<string>('');
  const [trainData, setTrainData] = useState<TrainETAResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<APIErrorState | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadTrainETA = async (trainNo: string) => {
    setIsLoading(true);
    setError(null);
    setCurrentTrain(trainNo);

    try {
      const data = await fetchTrainETA(trainNo);
      setTrainData(data);
      setLastUpdated(new Date());
    } catch (err: any) {
      setTrainData(null);
      setError(err as APIErrorState);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = () => {
    if (currentTrain) {
      loadTrainETA(currentTrain);
    }
  };

  const formatLastUpdated = (date: Date): string => {
    const diffSec = Math.floor((Date.now() - date.getTime()) / 1000);
    if (diffSec < 20) {
      return 'Updated just now';
    }
    return `Updated ${date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true })}`;
  };

  return (
    <div className="app-container">
      {/* 1. Header */}
      <Header />

      {/* 2. Train Search */}
      <TrainSearch
        onSearch={loadTrainETA}
        isLoading={isLoading}
        initialValue={currentTrain}
      />

      {/* 3. Loading State */}
      {isLoading && <LoadingSkeleton />}

      {/* 4. Error State */}
      {!isLoading && error && (
        <ErrorState
          error={error}
          onRetry={currentTrain ? () => loadTrainETA(currentTrain) : undefined}
        />
      )}

      {/* 5. Successful Data Display */}
      {!isLoading && !error && trainData && (
        <>
          <TrainSummary
            trainNo={trainData.train_no}
            trainName={trainData.train_name}
            status={trainData.status}
            journeyDate={trainData.journey_date}
            lastUpdatedText={lastUpdated ? formatLastUpdated(lastUpdated) : undefined}
            onRefresh={handleRefresh}
            isLoading={isLoading}
          />

          <CurrentStationCard currentStation={trainData.current_station} />

          <PredictionList predictions={trainData.predictions} />

          <PredictionExplanation />
        </>
      )}

      {/* 6. Empty State */}
      {!isLoading && !error && !trainData && (
        <EmptyState onSelectTrain={loadTrainETA} />
      )}

      {/* 7. Footer / Metadata */}
      <footer className="app-footer">
        <div>
          {lastUpdated ? (
            <span>Last fetched: <strong>{formatLastUpdated(lastUpdated)}</strong></span>
          ) : (
            <span>Ready for query</span>
          )}
        </div>
        <div className="footer-model-info">
          <span>Multi-Horizon Inference Engine: <strong>XGBoost H1/H2/H3</strong></span>
        </div>
      </footer>
    </div>
  );
};

export default App;
