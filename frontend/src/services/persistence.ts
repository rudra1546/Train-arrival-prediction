/**
 * Persistence service for Last Searched Train.
 * Stores only minimal required metadata in browser localStorage under 'dynamic_eta_last_train'.
 * Does NOT persist full API responses or stale telemetry.
 */

export const LAST_TRAIN_STORAGE_KEY = 'dynamic_eta_last_train';

export interface LastSearchedTrain {
  train_no: string;
  train_name: string;
  origin: string;
  destination: string;
  journey_date?: string;
  selected_at?: string;
}

/**
 * Retrieve the saved last searched train from browser localStorage.
 * Validates payload schema to guarantee safety against corrupted data.
 */
export function getLastSearchedTrain(): LastSearchedTrain | null {
  try {
    const raw = localStorage.getItem(LAST_TRAIN_STORAGE_KEY);
    if (!raw) return null;

    const parsed = JSON.parse(raw);
    if (
      parsed &&
      typeof parsed === 'object' &&
      typeof parsed.train_no === 'string' &&
      parsed.train_no.trim().length > 0
    ) {
      return {
        train_no: parsed.train_no.trim(),
        train_name: typeof parsed.train_name === 'string' ? parsed.train_name : `Train ${parsed.train_no}`,
        origin: typeof parsed.origin === 'string' ? parsed.origin : 'Origin',
        destination: typeof parsed.destination === 'string' ? parsed.destination : 'Destination',
        journey_date: typeof parsed.journey_date === 'string' ? parsed.journey_date : undefined,
        selected_at: typeof parsed.selected_at === 'string' ? parsed.selected_at : undefined
      };
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Save a selected train to browser localStorage.
 * Only stores necessary identity & route endpoints, never raw prediction responses.
 */
export function saveLastSearchedTrain(train: LastSearchedTrain): void {
  try {
    const minimal: LastSearchedTrain = {
      train_no: String(train.train_no || '').trim(),
      train_name: String(train.train_name || '').trim(),
      origin: String(train.origin || '').trim(),
      destination: String(train.destination || '').trim(),
      journey_date: train.journey_date ? String(train.journey_date).trim() : undefined,
      selected_at: new Date().toISOString()
    };
    localStorage.setItem(LAST_TRAIN_STORAGE_KEY, JSON.stringify(minimal));
  } catch {
    // Gracefully handle storage quota or privacy mode errors
  }
}

/**
 * Remove the last searched train from localStorage.
 */
export function clearLastSearchedTrain(): void {
  try {
    localStorage.removeItem(LAST_TRAIN_STORAGE_KEY);
  } catch {
    // ignore
  }
}
