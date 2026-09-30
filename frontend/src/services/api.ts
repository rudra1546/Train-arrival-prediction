/**
 * API Service for communicating exclusively with the FastAPI backend.
 * Never connects directly to external railway providers or creates credentials.
 */

import type { TrainETAResponse, APIErrorState } from '../types/eta';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');

export async function fetchTrainETA(trainNo: string, date?: string): Promise<TrainETAResponse> {
  const cleanNo = trainNo.trim();

  // Client-side numeric validation
  if (!/^\d{4,5}$/.test(cleanNo)) {
    const error: APIErrorState = {
      title: 'Invalid Train Number',
      message: 'Please enter a valid 4 or 5 digit numeric Indian Railways train number (e.g. 12301).',
      statusCode: 400
    };
    throw error;
  }

  const queryParams = new URLSearchParams();
  if (date) {
    queryParams.append('date', date);
  }
  const queryString = queryParams.toString() ? `?${queryParams.toString()}` : '';
  const url = `${API_BASE_URL}/api/train/${cleanNo}/eta${queryString}`;

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
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
      const statusCode = response.status;
      let title = 'Error';
      let message = 'An unexpected error occurred.';

      if (statusCode === 400) {
        title = 'Invalid Request';
        message = data?.detail || 'Invalid train number or parameter provided.';
      } else if (statusCode === 404) {
        title = 'Train Not Found';
        message = `Train '${cleanNo}' could not be found in active railway schedules or live tracking systems.`;
      } else if (statusCode === 422) {
        title = 'Route or Journey Limitation';
        message = data?.detail || 'The train has either completed its run or is not running on this journey date.';
      } else if (statusCode === 502) {
        title = 'Live Tracking Service Unavailable';
        message = 'The upstream railway tracking provider returned an error or authentication issue.';
      } else if (statusCode === 504) {
        title = 'Request Timeout';
        message = 'The railway tracking service did not respond in time. Please try again.';
      } else if (statusCode >= 500) {
        title = 'Server Error';
        message = 'The ETA prediction service encountered an internal error processing the forecast.';
      }

      const error: APIErrorState = {
        title,
        message,
        statusCode
      };
      throw error;
    }

    // Backend returned 200 with live_api_not_configured gate notice
    if (data?.status === 'live_api_not_configured') {
      const error: APIErrorState = {
        title: 'Backend Configuration Notice',
        message: 'The RailRadar API key is not configured in the backend environment.',
        statusCode: 503
      };
      throw error;
    }

    return data as TrainETAResponse;

  } catch (err: any) {
    if (err && err.title && err.message) {
      throw err;
    }
    // Network connectivity failure
    const error: APIErrorState = {
      title: 'Backend Offline',
      message: `Unable to connect to the prediction backend at ${API_BASE_URL}. Ensure the FastAPI server is running with 'python -m uvicorn app.live.app:app --port 8000' inside backend/.`,
      statusCode: 0
    };
    throw error;
  }
}
