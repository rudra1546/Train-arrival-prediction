/**
 * Type definitions for Indian Railways Station and Route Search
 * Powered by FastAPI backend /api/trains/search, /api/stations/search, and /api/train/{train_no}/route
 */

export interface StationMeta {
  code: string;
  name: string;
  zone?: string;
}

export interface RouteSearchResult {
  train_no: string;
  train_name: string;
  type_code: string;
  type_label: string;
  train_type?: string;
  origin: string;
  destination: string;
  origin_station?: string;
  destination_station?: string;
  from_station: string;
  from_station_name?: string;
  to_station: string;
  to_station_name?: string;
  departure_time: string;
  arrival_time: string;
  duration?: string;
  stops: number;
  distance_km?: number;
  total_stops?: number;
}

export interface TrainSearchApiResponse {
  success: boolean;
  count: number;
  from_station: StationMeta;
  to_station: StationMeta;
  journey_date?: string;
  trains: RouteSearchResult[];
}

export interface RouteStop {
  station_no: number;
  station_code: string;
  station_name: string;
  arrival_time: string;
  departure_time: string;
  distance: number;
  latitude?: number | null;
  longitude?: number | null;
}

export interface StationCoordinates {
  code: string;
  name: string;
  latitude: number;
  longitude: number;
}

export interface TrainRouteSchedule {
  train_no: string;
  train_name: string;
  origin_code?: string;
  origin_name?: string;
  dest_code?: string;
  dest_name?: string;
  total_stops: number;
  stops: RouteStop[];
}

export interface RecentTrainSearch {
  train_no: string;
  train_name: string;
  searched_at: string;
  from_station?: string;
  to_station?: string;
}
