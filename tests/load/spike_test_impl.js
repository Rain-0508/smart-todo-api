import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:5000';
// Use varied requests so the burst does not hammer a single repeated task string.
const TASKS = [
  'Fix production bug',
  'Prepare quarterly report',
  'Book team lunch',
  'Review release blocker tickets',
  'Read newsletter',
  'Resolve API timeout errors',
  'Update customer success playbook',
  'Watch tutorial video',
  'Patch security vulnerability',
  'Document release process',
];

export const options = {
  // Jump quickly from light traffic to a large burst, then watch recovery afterward.
  stages: [
    { duration: '20s', target: 5 },
    { duration: '10s', target: 100 },
    { duration: '40s', target: 100 },
    { duration: '20s', target: 5 },
    { duration: '20s', target: 5 },
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.10'],
    http_req_duration: ['p(95)<2000'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'max'],
};

function pickTask() {
  return TASKS[Math.floor(Math.random() * TASKS.length)];
}

export default function () {
  const payload = JSON.stringify({ task: pickTask() });

  // The spike test still targets the same API contract as the ramp-up test.
  const response = http.post(`${BASE_URL}/predict`, payload, {
    headers: {
      'Content-Type': 'application/json',
    },
    tags: {
      test_type: 'spike',
      endpoint: 'predict',
    },
  });

  // Keep the checks identical so the two test reports are directly comparable.
  check(response, {
    'predict status is 200': (res) => res.status === 200,
    'predict returns priority': (res) => {
      const body = res.json();
      return body && typeof body.priority === 'string' && body.priority.length > 0;
    },
    'predict returns confidence': (res) => {
      const body = res.json();
      return body && typeof body.confidence === 'number';
    },
  });

  // Preserve simple per-user pacing while the stage configuration drives concurrency.
  sleep(1);
}