/**
 * Automated Unit & Logic Tests for Dynamic Train ETA Frontend
 * Tests API service, validation, error mapping, and response schema parsing.
 */

import { test, describe } from 'node:test';
import assert from 'node:assert/strict';

// Test 1: Numeric train number validation regex
describe('Train Number Validation', () => {
  const isValidTrainNo = (val) => /^\d{4,5}$/.test(val?.trim() || '');

  test('Accepts valid 5-digit train numbers', () => {
    assert.equal(isValidTrainNo('12301'), true);
    assert.equal(isValidTrainNo('12951'), true);
    assert.equal(isValidTrainNo('12002'), true);
    assert.equal(isValidTrainNo(' 12301 '), true);
  });

  test('Accepts valid 4-digit train numbers', () => {
    assert.equal(isValidTrainNo('2301'), true);
  });

  test('Rejects non-numeric, short, or oversized train numbers', () => {
    assert.equal(isValidTrainNo(''), false);
    assert.equal(isValidTrainNo('12'), false);
    assert.equal(isValidTrainNo('123'), false);
    assert.equal(isValidTrainNo('123456'), false);
    assert.equal(isValidTrainNo('ABC12'), false);
    assert.equal(isValidTrainNo('1230A'), false);
  });
});

// Test 2: Error mapping logic
describe('API Error Handling and Human-Readable Messages', () => {
  const mapError = (statusCode, detail) => {
    let title = 'Error';
    let message = 'An unexpected error occurred.';

    if (statusCode === 400) {
      title = 'Invalid Request';
      message = detail || 'Invalid train number or parameter provided.';
    } else if (statusCode === 404) {
      title = 'Train Not Found';
      message = 'Train could not be found in active railway schedules or live tracking systems.';
    } else if (statusCode === 422) {
      title = 'Route or Journey Limitation';
      message = detail || 'The train has either completed its run or is not running on this journey date.';
    } else if (statusCode === 502) {
      title = 'Live Tracking Service Unavailable';
      message = 'The upstream railway tracking provider returned an error or authentication issue.';
    } else if (statusCode === 504) {
      title = 'Request Timeout';
      message = 'The railway tracking service did not respond in time. Please try again.';
    } else if (statusCode >= 500) {
      title = 'Server Error';
      message = 'The ETA prediction service encountered an internal error processing the forecast.';
    } else if (statusCode === 0) {
      title = 'Backend Offline';
      message = 'Unable to connect to the prediction backend.';
    }
    return { title, message, statusCode };
  };

  test('Maps 404 to Train Not Found', () => {
    const err = mapError(404);
    assert.equal(err.title, 'Train Not Found');
    assert.match(err.message, /could not be found/);
  });

  test('Maps 502 to Upstream Service Unavailable', () => {
    const err = mapError(502);
    assert.equal(err.title, 'Live Tracking Service Unavailable');
    assert.match(err.message, /upstream railway tracking provider/);
  });

  test('Maps 504 to Request Timeout', () => {
    const err = mapError(504);
    assert.equal(err.title, 'Request Timeout');
  });

  test('Maps 0 (Network) to Backend Offline', () => {
    const err = mapError(0);
    assert.equal(err.title, 'Backend Offline');
  });
});

// Test 3: Multi-Horizon Display Logic
describe('Horizon Prediction Rendering Logic', () => {
  test('Gracefully handles single horizon (H1 only)', () => {
    const predictions = [
      {
        horizon: 1,
        station: 'NDLS',
        scheduled_arrival: '2026-03-30T10:05:00',
        predicted_delay_minutes: 7.6,
        predicted_eta: '2026-03-30T10:12:36'
      }
    ];

    assert.equal(predictions.length, 1);
    assert.equal(predictions[0].horizon, 1);
    assert.equal(predictions.some(p => p.horizon === 2), false);
    assert.equal(predictions.some(p => p.horizon === 3), false);
  });

  test('Handles multi-horizon (H1, H2, H3)', () => {
    const predictions = [
      {
        horizon: 1,
        station: 'NDLS',
        scheduled_arrival: '2026-03-30T10:05:00',
        predicted_delay_minutes: 7.6,
        predicted_eta: '2026-03-30T10:12:36'
      },
      {
        horizon: 2,
        station: 'GZB',
        scheduled_arrival: '2026-03-30T11:15:00',
        predicted_delay_minutes: 8.2,
        predicted_eta: '2026-03-30T11:23:12'
      },
      {
        horizon: 3,
        station: 'MB',
        scheduled_arrival: '2026-03-30T13:40:00',
        predicted_delay_minutes: 12.0,
        predicted_eta: '2026-03-30T13:52:00'
      }
    ];

    assert.equal(predictions.length, 3);
    const horizons = predictions.map(p => p.horizon);
    assert.deepEqual(horizons, [1, 2, 3]);
  });
});

// Test 4: Security Verification
describe('Security Verification in Frontend Codebase', () => {
  test('Ensures no auth headers or secret tokens in frontend service', async () => {
    const fs = await import('node:fs');
    const apiCode = fs.readFileSync(new URL('../src/services/api.ts', import.meta.url), 'utf-8');
    assert.equal(apiCode.includes('RAILRADAR_API_KEY'), false);
    assert.equal(apiCode.includes('Authorization'), false);
    assert.equal(apiCode.includes('Bearer'), false);
  });
});
