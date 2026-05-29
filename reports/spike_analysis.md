# Spike Test Analysis

## Test setup

- Script: `spike_test.js`
- API target: `POST /predict`
- Traffic pattern: `5 -> 100` virtual users with a sudden jump, then reduced back to `5` before ramping down to `0`
- Test duration: about `2 minutes`

## Performance report summary

- Total requests: `5786`
- Request failure rate: `0.00%`
- Average response time: `3.15 ms`
- Median response time: `2.93 ms`
- P90 response time: `5.01 ms`
- P95 response time: `5.87 ms`
- Maximum response time: `16.39 ms`
- Average throughput: `47.99 requests/second`
- Max concurrent virtual users reached: `100`

## Analysis

The API stayed stable during the sudden traffic jump from `5` to `100` users. There were no failed requests, all response checks passed, and response times remained low throughout the burst period.

The server also recovered correctly after the spike. Once the test reduced traffic back to `5` users, requests continued completing normally and the test ended with `0` interrupted iterations.

## Questions answered

- Does the server crash?

  No. The server did not crash during the spike test. The failure rate stayed at `0.00%`.

- Does it recover afterward?

  Yes. After the burst phase, the API continued serving requests normally during the lower-traffic recovery stage, which shows that it recovered cleanly.

## Conclusion

For this local Flask setup and current ML model, the API handled a sudden spike to `100` virtual users without visible instability. To push the system harder, the next step would be to repeat the spike test at higher burst levels such as `200` or `300` users, or remove the `sleep(1)` pacing to increase request pressure.