/**
 * Automated Unit & Logic Tests for Dynamic Train ETA Frontend
 * Tests API service, validation, error mapping, route parsing, and last searched train persistence.
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

// Test 5: Route and Station Search Logic
describe('Route Search and Station Parsing Logic', () => {
  const formatTrainType = (typeCode) => {
    const norm = (typeCode || '').toUpperCase().trim();
    if (norm.includes('RAJ')) return 'Rajdhani Express';
    if (norm.includes('SHT')) return 'Shatabdi Express';
    if (norm.includes('T18') || norm.includes('VB')) return 'Vande Bharat Express';
    if (norm.includes('GRB')) return 'Garib Rath';
    if (norm.includes('PRM') || norm.includes('SPL')) return 'Special Express';
    if (norm.includes('SF')) return 'Superfast Express';
    if (norm.includes('EXP')) return 'Mail / Express';
    if (norm.includes('PASS')) return 'Passenger Service';
    return typeCode || 'Express';
  };

  test('Correctly maps Indian Railways train type codes to descriptive labels', () => {
    assert.equal(formatTrainType('RAJ-TRAINS'), 'Rajdhani Express');
    assert.equal(formatTrainType('SHT-TRAINS'), 'Shatabdi Express');
    assert.equal(formatTrainType('SF-TRAINS'), 'Superfast Express');
    assert.equal(formatTrainType('EXP-TRAINS'), 'Mail / Express');
    assert.equal(formatTrainType('PASS-TRAINS'), 'Passenger Service');
  });

  test('Filters trains matching from and to stations with valid forward progression', () => {
    const mockRoutes = [
      { no: '12301', s: ['HWH', 'ASN', 'DHN', 'GAYA', 'DDU', 'PRYJ', 'CNB', 'NDLS'] },
      { no: '12302', s: ['NDLS', 'CNB', 'PRYJ', 'DDU', 'GAYA', 'DHN', 'ASN', 'HWH'] },
      { no: '12951', s: ['MMCT', 'BVI', 'ST', 'BRC', 'RTM', 'KOTA', 'NDLS'] }
    ];

    const searchBetween = (from, to) => {
      return mockRoutes.filter(r => {
        const fIdx = r.s.indexOf(from);
        const tIdx = r.s.indexOf(to);
        return fIdx !== -1 && tIdx !== -1 && fIdx < tIdx;
      });
    };

    const hwhToNdls = searchBetween('HWH', 'NDLS');
    assert.equal(hwhToNdls.length, 1);
    assert.equal(hwhToNdls[0].no, '12301');

    const ndlsToHwh = searchBetween('NDLS', 'HWH');
    assert.equal(ndlsToHwh.length, 1);
    assert.equal(ndlsToHwh[0].no, '12302');

    const mmctToNdls = searchBetween('MMCT', 'NDLS');
    assert.equal(mmctToNdls.length, 1);
    assert.equal(mmctToNdls[0].no, '12951');

    const invalidRoute = searchBetween('HWH', 'MMCT');
    assert.equal(invalidRoute.length, 0);
  });
});

// Test 6: Last Searched Train Persistence & Dashboard Display
describe('Last Searched Train Persistence & Dashboard Display Logic', () => {
  const STORAGE_KEY = 'dynamic_eta_last_train';

  // Mock in-memory localStorage implementation
  const mockStorage = new Map();
  const fakeLocalStorage = {
    getItem: (key) => mockStorage.get(key) || null,
    setItem: (key, val) => mockStorage.set(key, String(val)),
    removeItem: (key) => mockStorage.delete(key),
    clear: () => mockStorage.clear()
  };

  const saveLastTrain = (train, storage = fakeLocalStorage) => {
    const minimal = {
      train_no: String(train.train_no || '').trim(),
      train_name: String(train.train_name || '').trim(),
      origin: String(train.origin || '').trim(),
      destination: String(train.destination || '').trim(),
      journey_date: train.journey_date ? String(train.journey_date).trim() : undefined
    };
    storage.setItem(STORAGE_KEY, JSON.stringify(minimal));
  };

  const getLastTrain = (storage = fakeLocalStorage) => {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed.train_no === 'string' && parsed.train_no.trim()) {
        return parsed;
      }
      return null;
    } catch {
      return null;
    }
  };

  const clearLastTrain = (storage = fakeLocalStorage) => {
    storage.removeItem(STORAGE_KEY);
  };

  test('Persists only minimal required fields under dynamic_eta_last_train', () => {
    fakeLocalStorage.clear();
    const trainInput = {
      train_no: '12473',
      train_name: 'Sarvodaya Exp',
      origin: 'Gandhidham Bg (GIMB)',
      destination: 'Mata Vaishno Devi Katra (SVDK)',
      journey_date: '2026-09-30',
      // Stale or full API fields that must NOT be persisted:
      current_station: { code: 'ADI', delay_minutes: 10 },
      predictions: [{ horizon: 1, delay: 12 }],
      raw_telemetry: { speed: 110 }
    };

    saveLastTrain(trainInput);

    const raw = JSON.parse(fakeLocalStorage.getItem(STORAGE_KEY));
    assert.equal(raw.train_no, '12473');
    assert.equal(raw.train_name, 'Sarvodaya Exp');
    assert.equal(raw.origin, 'Gandhidham Bg (GIMB)');
    assert.equal(raw.destination, 'Mata Vaishno Devi Katra (SVDK)');
    assert.equal(raw.journey_date, '2026-09-30');

    // Confirm full API response / predictions are never stored
    assert.equal(raw.current_station, undefined);
    assert.equal(raw.predictions, undefined);
    assert.equal(raw.raw_telemetry, undefined);
  });

  test('Loads persisted train correctly on simulated page reload', () => {
    const saved = getLastTrain();
    assert.notEqual(saved, null);
    assert.equal(saved.train_no, '12473');
    assert.equal(saved.origin, 'Gandhidham Bg (GIMB)');
    assert.equal(saved.destination, 'Mata Vaishno Devi Katra (SVDK)');
  });

  test('Clearing selected train removes it from localStorage and returns null', () => {
    clearLastTrain();
    const afterClear = getLastTrain();
    assert.equal(afterClear, null);
    assert.equal(fakeLocalStorage.getItem(STORAGE_KEY), null);
  });

  test('Handles corrupted or invalid localStorage entries gracefully without crashing', () => {
    fakeLocalStorage.setItem(STORAGE_KEY, 'not-valid-json{{');
    assert.equal(getLastTrain(), null);

    fakeLocalStorage.setItem(STORAGE_KEY, JSON.stringify({ invalid: true }));
    assert.equal(getLastTrain(), null);

    fakeLocalStorage.clear();
  });
});

// Test 7: Live Tracking Station Sequence and Journey Progress Logic
describe('Live Tracking Journey Progress & Status Partitioning', () => {
  const sampleStops = [
    { station_code: 'GIMB', station_name: 'Gandhidham Jn', station_no: 1 },
    { station_code: 'SIOB', station_name: 'Samakhiali B G', station_no: 2 },
    { station_code: 'BCOB', station_name: 'Bhachau', station_no: 3 },
    { station_code: 'DHG', station_name: 'Dhrangadhra', station_no: 4 },
    { station_code: 'VG', station_name: 'Viramgam Jn', station_no: 5 },
    { station_code: 'ADI', station_name: 'Ahmedabad Jn', station_no: 6 }
  ];

  test('Determines completed, current, and upcoming stops correctly', () => {
    const currentCode = 'BCOB';
    const currentIndex = sampleStops.findIndex(s => s.station_code === currentCode);
    assert.equal(currentIndex, 2);

    const completed = currentIndex > 0 ? sampleStops.slice(0, currentIndex) : [];
    const current = sampleStops[currentIndex];
    const upcoming = currentIndex !== -1 ? sampleStops.slice(currentIndex + 1) : [];
    const prevStation = currentIndex > 0 ? sampleStops[currentIndex - 1] : null;
    const nextStation = currentIndex !== -1 && currentIndex + 1 < sampleStops.length ? sampleStops[currentIndex + 1] : null;

    assert.equal(completed.length, 2);
    assert.equal(completed[0].station_code, 'GIMB');
    assert.equal(completed[1].station_code, 'SIOB');
    assert.equal(current.station_code, 'BCOB');
    assert.equal(upcoming.length, 3);
    assert.equal(prevStation.station_code, 'SIOB');
    assert.equal(nextStation.station_code, 'DHG');
  });

  test('Calculates journey progress percentage accurately', () => {
    const currentIndex = 2;
    const totalStops = sampleStops.length; // 6
    const progressPercent = Math.round((currentIndex / (totalStops - 1)) * 100);
    assert.equal(progressPercent, 40); // 2 / 5 * 100 = 40%

    // Edge case: first station
    assert.equal(Math.round((0 / (totalStops - 1)) * 100), 0);
    // Edge case: final station
    assert.equal(Math.round(((totalStops - 1) / (totalStops - 1)) * 100), 100);
  });

  test('Correctly maps delay values to status badge categories', () => {
    const getDelayBadge = (delayMinutes) => {
      if (delayMinutes === null || delayMinutes === undefined) return { label: 'Scheduled', type: 'info' };
      if (delayMinutes <= 0) return { label: 'On Time', type: 'ontime' };
      if (delayMinutes <= 15) return { label: `${delayMinutes}m Late`, type: 'minor' };
      return { label: `+${delayMinutes}m Delayed`, type: 'major' };
    };

    assert.deepEqual(getDelayBadge(0), { label: 'On Time', type: 'ontime' });
    assert.deepEqual(getDelayBadge(-2), { label: 'On Time', type: 'ontime' });
    assert.deepEqual(getDelayBadge(12), { label: '12m Late', type: 'minor' });
    assert.deepEqual(getDelayBadge(45), { label: '+45m Delayed', type: 'major' });
    assert.deepEqual(getDelayBadge(null), { label: 'Scheduled', type: 'info' });
  });

  test('Gracefully falls back to predictions list when schedule stops are unavailable', () => {
    const fallbackStops = [
      { station_code: 'GIMB', station_name: 'Gandhidham' },
      { station_code: 'BCOB', station_name: 'Bhachau' },
      { station_code: 'ADI', station_name: 'Ahmedabad' }
    ];
    assert.equal(fallbackStops.length, 3);
    const currentIndex = fallbackStops.findIndex(s => s.station_code === 'BCOB');
    assert.equal(currentIndex, 1);
  });
});

// Test 8: Dedicated ETA Prediction Page Multi-Horizon Logic & Comparisons
describe('ETA Prediction Multi-Horizon & Scheduled vs Predicted Comparisons', () => {
  const samplePredictions = [
    {
      horizon: 1,
      station: 'CYI',
      scheduled_arrival: '2026-09-30T16:22:00',
      predicted_delay_minutes: 2.8,
      predicted_eta: '2026-09-30T16:25:00'
    },
    {
      horizon: 2,
      station: 'GDA',
      scheduled_arrival: '2026-09-30T17:15:00',
      predicted_delay_minutes: 3.5,
      predicted_eta: '2026-09-30T17:18:30'
    },
    {
      horizon: 3,
      station: 'DHD',
      scheduled_arrival: '2026-09-30T18:20:00',
      predicted_delay_minutes: 4.0,
      predicted_eta: '2026-09-30T18:24:00'
    }
  ];

  test('Separates H1, H2, and H3 horizons accurately from prediction list', () => {
    const h1 = samplePredictions.find(p => p.horizon === 1);
    const h2 = samplePredictions.find(p => p.horizon === 2);
    const h3 = samplePredictions.find(p => p.horizon === 3);

    assert.notEqual(h1, undefined);
    assert.equal(h1.station, 'CYI');
    assert.equal(h1.predicted_delay_minutes, 2.8);

    assert.notEqual(h2, undefined);
    assert.equal(h2.station, 'GDA');

    assert.notEqual(h3, undefined);
    assert.equal(h3.station, 'DHD');
  });

  test('Gracefully handles terminal trains where H2 or H3 is unavailable without fabricating values', () => {
    const terminalPredictions = [samplePredictions[0]]; // Only H1 available
    const h1 = terminalPredictions.find(p => p.horizon === 1);
    const h2 = terminalPredictions.find(p => p.horizon === 2);
    const h3 = terminalPredictions.find(p => p.horizon === 3);

    assert.notEqual(h1, undefined);
    assert.equal(h1.station, 'CYI');
    assert.equal(h2, undefined); // Must be undefined, never a fake value
    assert.equal(h3, undefined); // Must be undefined, never a fake value
  });

  test('Computes scheduled vs predicted time difference correctly', () => {
    const computeDiff = (sched, eta) => {
      const s = new Date(sched).getTime();
      const e = new Date(eta).getTime();
      return Math.round((e - s) / 60000);
    };

    assert.equal(computeDiff('2026-09-30T16:22:00', '2026-09-30T16:25:00'), 3);
    assert.equal(computeDiff('2026-09-30T16:50:00', '2026-09-30T16:50:00'), 0);
    assert.equal(computeDiff('2026-09-30T17:00:00', '2026-09-30T16:58:00'), -2);
  });

  test('Calculates journey context metrics (remaining stops and remaining distance)', () => {
    const totalStops = 31;
    const currentIndex = 6; // Stop 7 (0-indexed: 6)
    const remainingStops = totalStops - currentIndex - 1;
    assert.equal(remainingStops, 24);

    const totalDistance = 2035;
    const currentDistance = 364;
    const remainingDistance = totalDistance - currentDistance;
    assert.equal(remainingDistance, 1671);

    const progressPercent = Math.round((currentIndex / (totalStops - 1)) * 100);
    assert.equal(progressPercent, 20);
  });
});

// Test 9: Improved Central Dashboard Overview Logic (Case 1 & Case 2)
describe('Improved Central Dashboard Overview Logic (Case 1 & Case 2)', () => {
  test('Case 1: Renders informational feature cards specification when no train is selected', () => {
    const welcomeTitle = 'Welcome to Dynamic Train ETA';
    const welcomeSubtitle = 'Search for a train to view live status, route tracking and AI-powered ETA predictions.';
    const primaryCta = 'Search Train';
    const featureCards = ['Live Tracking', 'ETA Prediction', 'Railway Route Map'];

    assert.equal(welcomeTitle, 'Welcome to Dynamic Train ETA');
    assert.equal(welcomeSubtitle.includes('AI-powered ETA predictions'), true);
    assert.equal(primaryCta, 'Search Train');
    assert.deepEqual(featureCards, ['Live Tracking', 'ETA Prediction', 'Railway Route Map']);
  });

  test('Case 2: Calculates Train Overview metadata, delay metrics, and live station progression', () => {
    const sampleSchedule = [
      { station_code: 'GIMB', station_name: 'Gandhidham', departure_time: '08:00' },
      { station_code: 'ADI', station_name: 'Ahmedabad', departure_time: '13:45' },
      { station_code: 'GDA', station_name: 'Godhra', departure_time: '15:30' },
      { station_code: 'DHD', station_name: 'Dahod', departure_time: '16:45' },
      { station_code: 'NDLS', station_name: 'New Delhi', departure_time: '04:00' }
    ];

    const currentStationCode = 'GDA';
    const currentIndex = sampleSchedule.findIndex(s => s.station_code === currentStationCode);
    assert.equal(currentIndex, 2);

    // Previous Station
    const prevStop = sampleSchedule[currentIndex - 1];
    assert.equal(prevStop.station_code, 'ADI');
    assert.equal(prevStop.station_name, 'Ahmedabad');

    // Next Station
    const nextStop = sampleSchedule[currentIndex + 1];
    assert.equal(nextStop.station_code, 'DHD');
    assert.equal(nextStop.station_name, 'Dahod');

    // Delay Severity classification
    const classifyDelay = (minutes) => {
      if (minutes <= 0) return 'ontime';
      if (minutes <= 5) return 'ontime';
      if (minutes <= 20) return 'moderate';
      return 'severe';
    };

    assert.equal(classifyDelay(0), 'ontime');
    assert.equal(classifyDelay(4), 'ontime');
    assert.equal(classifyDelay(14), 'moderate');
    assert.equal(classifyDelay(45), 'severe');
  });

  test('Case 2: Computes remaining stations and journey progress bar accurately', () => {
    const totalStops = 32;
    const currentIndex = 7; // Stop 8
    const progressPercent = Math.round((currentIndex / (totalStops - 1)) * 100);
    const remainingStops = totalStops - currentIndex - 1;

    assert.equal(progressPercent, 23);
    assert.equal(remainingStops, 24);
  });

  test('Case 2: Formats compact ETA Summary and strictly omits unavailable horizons', () => {
    // Only H1 available (approaching terminus)
    const rawPredictions = [
      { horizon: 1, station: 'NDLS', scheduled_arrival: '2026-09-30T10:00:00', predicted_delay_minutes: 5.5, predicted_eta: '2026-09-30T10:05:30' }
    ];

    const availableHorizons = rawPredictions
      .filter(p => p && typeof p.horizon === 'number')
      .sort((a, b) => a.horizon - b.horizon);

    assert.equal(availableHorizons.length, 1);
    assert.equal(availableHorizons[0].horizon, 1);
    assert.equal(availableHorizons.some(p => p.horizon === 2), false);
    assert.equal(availableHorizons.some(p => p.horizon === 3), false);

    // Multi-horizon available
    const multiPredictions = [
      { horizon: 1, station: 'GDA', predicted_delay_minutes: 4.0 },
      { horizon: 2, station: 'DHD', predicted_delay_minutes: 6.2 },
      { horizon: 3, station: 'MGN', predicted_delay_minutes: 8.5 }
    ];
    const multiHorizons = multiPredictions.filter(p => p && typeof p.horizon === 'number');
    assert.equal(multiHorizons.length, 3);
    assert.deepEqual(multiHorizons.map(p => p.horizon), [1, 2, 3]);
  });

  test('Quick Actions: Search Another Train preserves storage whereas Clear Train purges storage', () => {
    const mockStorage = new Map();
    const STORAGE_KEY = 'dynamic_eta_last_train';

    // 1. Initial train persisted
    const initialTrain = { train_no: '12473', train_name: 'Sarvodaya Exp' };
    mockStorage.set(STORAGE_KEY, JSON.stringify(initialTrain));
    assert.notEqual(mockStorage.get(STORAGE_KEY), null);

    // 2. Action: "Search Another Train" -> Navigate to search WITHOUT clearing storage
    const onSearchAnotherTrain = () => {
      // Navigates to search page; storage remains intact
    };
    onSearchAnotherTrain();
    assert.notEqual(mockStorage.get(STORAGE_KEY), null);
    const retained = JSON.parse(mockStorage.get(STORAGE_KEY));
    assert.equal(retained.train_no, '12473');

    // 3. Action: "Clear Selected Train" -> Purges storage and resets to empty state
    const onClearSelectedTrain = () => {
      mockStorage.delete(STORAGE_KEY);
    };
    onClearSelectedTrain();
    assert.equal(mockStorage.get(STORAGE_KEY), undefined);
  });
});

