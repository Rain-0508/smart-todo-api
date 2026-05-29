import http from 'k6/http';
import { check, sleep } from 'k6';
import { fail } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:5000';
// Reuse a small pool of realistic tasks so the API sees mixed priority inputs.
const TASKS = [
  'Fix production bug',
  'Prepare quarterly report',
  'Book team lunch',
  'Review release blocker tickets',
  'Read newsletter',
  'Resolve API timeout errors',
  'Update customer success playbook',
  'Watch tutorial video',
];

export const options = {
  // Increase traffic gradually to spot the first point where latency or failures rise.
  stages: [
    { duration: '30s', target: 1 },
    { duration: '1m', target: 10 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<1500'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'max'],
};

function parseJsonSafe(response) {
  try {
    return response.json();
  } catch (error) {
    return null;
  }
}

export function setup() {
  // Preflight check gives a clear error when API is not started in another terminal.
  const health = http.get(`${BASE_URL}/health`, {
    timeout: '3s',
    tags: {
      test_type: 'ramp_up',
      endpoint: 'health',
    },
  });

  if (health.status !== 200) {
    fail(
      `Preflight failed: ${BASE_URL}/health returned status ${health.status}. Start API with: python3 src/app.py`
    );
  }
}

function pickTask() {
  return TASKS[Math.floor(Math.random() * TASKS.length)];
}

export default function () {
  const payload = JSON.stringify({ task: pickTask() });

  // Every virtual user repeatedly exercises the prediction endpoint with JSON input.
  const response = http.post(`${BASE_URL}/predict`, payload, {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: {
      test_type: 'ramp_up',
      endpoint: 'predict',
    },
  });

  // Validate both transport-level success and the core response shape.
  check(response, {
    'predict status is 200': (res) => res.status === 200,
    'predict returns priority': (res) => {
      const body = parseJsonSafe(res);
      return body && typeof body.priority === 'string' && body.priority.length > 0;
    },
    'predict returns confidence': (res) => {
      const body = parseJsonSafe(res);
      return body && typeof body.confidence === 'number';
    },
  });

  // Add a short pause so the test shape reflects controlled user traffic.
  sleep(1);
}