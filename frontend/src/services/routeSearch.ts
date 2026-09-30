/**
 * Route and Station Search Service
 * Connects directly to FastAPI backend endpoints:
 * - GET /api/stations/search?q=...
 * - GET /api/trains/search?from=...&to=...&date=...
 */

import type { StationMeta, RouteSearchResult, TrainSearchApiResponse, RecentTrainSearch } from '../types/route';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');
const RECENT_SEARCHES_STORAGE_KEY = 'sih26028_recent_train_searches';

// In-memory cache for resolved stations to avoid redundant network round-trips
const stationCache = new Map<string, StationMeta>();

/**
 * Filter stations for autocomplete suggestions from real railway station master data
 */
export async function searchStations(query: string, limit = 8): Promise<StationMeta[]> {
  const clean = (query || '').trim();

  try {
    const url = `${API_BASE_URL}/api/stations/search?q=${encodeURIComponent(clean)}&limit=${limit}`;
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json'
      }
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData?.detail || `Failed to search stations (HTTP ${response.status})`);
    }

    const stations: StationMeta[] = await response.json();
    for (const st of stations) {
      if (st.code) {
        stationCache.set(st.code.toUpperCase(), st);
      }
    }
    return stations;
  } catch (err: any) {
    if (err.name === 'TypeError' || err.message?.includes('Failed to fetch')) {
      console.warn('Backend API unavailable for station search:', err.message);
      // Fallback to cached stations if network is offline
      if (stationCache.size > 0 && clean) {
        const needle = clean.toUpperCase();
        return Array.from(stationCache.values())
          .filter((s) => s.code.startsWith(needle) || s.name.toUpperCase().includes(needle))
          .slice(0, limit);
      }
      throw new Error('Railway API backend service is unavailable. Please ensure the backend is running.');
    }
    throw err;
  }
}

/**
 * Look up a station record by its exact code
 */
export async function getStationByCode(code: string): Promise<StationMeta | null> {
  const clean = (code || '').trim().toUpperCase();
  if (!clean) return null;

  if (stationCache.has(clean)) {
    return stationCache.get(clean)!;
  }

  try {
    const results = await searchStations(clean, 1);
    const match = results.find((s) => s.code.toUpperCase() === clean);
    if (match) {
      stationCache.set(clean, match);
      return match;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Get popular initial stations for default dropdown list
 */
export async function getStations(): Promise<StationMeta[]> {
  try {
    return await searchStations('', 15);
  } catch {
    return Array.from(stationCache.values());
  }
}

/**
 * Search trains between two stations from the real project schedule dataset via backend
 */
export async function searchTrainsBetweenStations(
  fromCode: string,
  toCode: string,
  journeyDate?: string
): Promise<RouteSearchResult[]> {
  const cleanFrom = (fromCode || '').trim();
  const cleanTo = (toCode || '').trim();

  if (!cleanFrom || !cleanTo) {
    throw new Error('Please select both Origin and Destination stations.');
  }

  if (cleanFrom.toUpperCase() === cleanTo.toUpperCase()) {
    throw new Error('Origin and Destination stations cannot be identical.');
  }

  const queryParams = new URLSearchParams({
    from: cleanFrom,
    to: cleanTo
  });

  if (journeyDate && journeyDate.trim()) {
    queryParams.append('date', journeyDate.trim());
  }

  const url = `${API_BASE_URL}/api/trains/search?${queryParams.toString()}`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        Accept: 'application/json'
      }
    });

    const contentType = response.headers.get('content-type') || '';
    let data: any = null;
    if (contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = { detail: await response.text() };
    }

    if (!response.ok) {
      const detail = data?.detail || `Search failed with status ${response.status}`;
      throw new Error(detail);
    }

    const payload = data as TrainSearchApiResponse;
    const trains = payload.trains || [];

    // Also populate station cache from response metadata
    if (payload.from_station?.code) {
      stationCache.set(payload.from_station.code, payload.from_station);
    }
    if (payload.to_station?.code) {
      stationCache.set(payload.to_station.code, payload.to_station);
    }

    return trains;
  } catch (err: any) {
    if (err.name === 'TypeError' || err.message?.includes('Failed to fetch')) {
      throw new Error('Railway API backend service is unavailable. Please ensure the backend server is running on http://127.0.0.1:8000.');
    }
    throw err;
  }
}

/**
 * LocalStorage utilities for recently searched trains
 */
export function getRecentSearches(): RecentTrainSearch[] {
  try {
    const saved = localStorage.getItem(RECENT_SEARCHES_STORAGE_KEY);
    if (!saved) return [];
    return JSON.parse(saved);
  } catch {
    return [];
  }
}

export function saveRecentSearch(item: RecentTrainSearch): void {
  try {
    const current = getRecentSearches().filter((x) => x.train_no !== item.train_no);
    const updated = [item, ...current].slice(0, 6);
    localStorage.setItem(RECENT_SEARCHES_STORAGE_KEY, JSON.stringify(updated));
  } catch {
    // ignore
  }
}
