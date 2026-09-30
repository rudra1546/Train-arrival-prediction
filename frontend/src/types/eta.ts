/**
 * Type definitions for SIH 26028 Dynamic Train ETA API.
 * Exactly matches the FastAPI backend response payload schema.
 */

export interface CurrentStation {
  code: string;
  name: string;
  delay_minutes: number;
}

export interface HorizonPrediction {
  horizon: number;
  station: string;
  scheduled_arrival: string;
  predicted_delay_minutes: number;
  predicted_eta: string;
}

export interface TrainETAResponse {
  success: boolean;
  train_no: string;
  train_name: string;
  status: string;
  journey_date: string;
  current_station: CurrentStation;
  predictions: HorizonPrediction[];
}

export interface APIErrorState {
  title: string;
  message: string;
  statusCode?: number;
}
