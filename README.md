# Pumpfun top-5 forecaster

Build a Python 3.13 program `main.py` (stdlib only, no network, deterministic) at the root of this repo.
It reads the house's pump.fun snapshots and writes one forecast. Read the task files first:
- `~/workspace/makefun/pumpfun-top5-forecast-01-kit/input/task.json`
- `~/workspace/makefun/pumpfun-top5-forecast-01-kit/input/history.ndjson` (practice data, 6 marks)
- `~/workspace/makefun/pumpfun-top5-forecast-01-kit/RULES.txt` (full rules; the output format and scoring are defined there)

## Input
- Input dir: env `MAKEFUN_INPUT_DIR` if set, else `/input/`. Read `history.ndjson` (one JSON object per line, one per mark, oldest first) and `task.json` from it.
- Each mark has `at` (ISO UTC), `rows`: up to 200 coins, each with `mint` (base58 string), `market_cap_lamports` (decimal integer string), `rank`, `venue`, `created_at`. Skip marks with zero rows.
- `task.json` has `reads` (7 answer-read instants, ISO UTC, ascending), `places` (5), `chart_size` (100), `size.edges` (81 floats, 2.00 to 6.00 step 0.05).

## Forecast logic (implement exactly this)
1. For each mint, collect (time, logcap) points over the marks, where logcap = log10(market_cap_lamports / 1e9). Use only rows present in a mark. Parse times with datetime.fromisoformat (replace trailing 'Z' with '+00:00').
2. For each mint with at least 1 point: L = last logcap, t_last = time of last point. Growth g per hour: if at least 2 points, g = (L - L_prev) / dt_hours where L_prev and dt_hours come from the previous point; else g = 0. Clip g into [-0.3, +0.5].
3. Horizon: H = (reads[3] - t_last) in hours (the middle answer read). Effective horizon Heff = min(H, 3.0). Predicted logcap P = L + g * Heff.
4. Rank all mints by P descending. Candidates = top 25. top5 = the top 5 mints in that order.
5. Probabilities: for each place k in 1..5, for each candidate at predicted rank r in 1..25: raw = exp(-((r - k) ** 2) / (2 * 2.0 ** 2)). Normalize the raw values for that place so they sum to 0.70. Round each p to 6 decimals. Keep only rows with p >= 0.005. (Each place then sums to <= 0.70, leaving 0.30 unnamed for coins born after the cut.)
6. Sizes: for each place k, center C = P of the mint predicted at rank k. sd = 0.35. For bin b in 0..81: bin 0 is (-inf, 2.00); bins 1..80 are [edges[b-1], edges[b]]; bin 81 is [6.00, +inf). Probability = normal CDF mass in that interval for N(C, sd) (use math.erf for the CDF). Normalize the 82 bin probabilities for that place so they sum to 0.85. Round each p to 6 decimals. Keep only rows with p >= 0.001.
7. Output JSON object with exactly three keys: `probabilities` (list of {"mint": str, "place": int, "p": float}), `top5` (list of exactly 5 mint strings), `sizes` (list of {"place": int, "bin": int, "p": float}).
8. Write to env `MAKEFUN_OUTPUT_DIR` if set else `/output/`, file `forecast.json`. Create the output dir if needed. Write with json.dump and sort_keys=True for determinism.
9. No randomness, no network, no third-party imports. Only stdlib (json, math, os, sys, datetime).

## Also write
- `LICENSE`: the MIT license text (Copyright (c) 2026 the make.fun team).

## Verify after writing
- Run it twice on the practice input and confirm the two forecast.json files are byte-identical.
- Confirm the output has exactly the keys probabilities/top5/sizes, top5 has 5 distinct mints, each place's probability sum is <= 1, and each place's size sum is <= 1.
- If a run fails or the output is invalid, fix main.py and re-run until it passes.
