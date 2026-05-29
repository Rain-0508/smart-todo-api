# Ramp-Up Test Analysis

## Test setup

- Script: `ramp_up_test.js`
- API target: `POST /predict`
- Traffic pattern: `1 -> 10 -> 50` virtual users, then ramp down to `0`
- Test duration: about `3 minutes`

## Performance report summary

- Total requests: `2876`
- Request failure rate: `0.00%`
- Average response time: `3.39 ms`
- Median response time: `2.80 ms`
- P90 response time: `5.50 ms`
- P95 response time: `6.79 ms`
- Maximum response time: `73.84 ms`
- Average throughput: `15.95 requests/second`
- Max concurrent virtual users reached: `50`

## Analysis

The API stayed stable for the full ramp-up test. There were no failed requests, all response body checks passed, and the `p95` response time remained very low at `6.79 ms`.

Within the tested range up to `50` virtual users, there is no clear sign that the server became slow. The maximum latency spike was only `73.84 ms`, which is still far below the threshold of `1500 ms` used in the script.

## Questions answered

- At what point does response time increase?

  Based on this run, there is no obvious performance degradation point between `1`, `10`, and `50` users. The API handled the full ramp without noticeable slowdown.

- Does the server start failing?

  No. The server did not fail during this test. Request failure rate stayed at `0.00%`.

## Conclusion

For this local Flask setup and current ML model, the API comfortably handled the tested ramp-up load. To find the actual breaking point, the next step would be to repeat the test with a higher upper bound such as `100`, `200`, or more virtual users.