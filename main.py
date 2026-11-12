# Momentum log-cap forecaster (pumpfun top-5, 24h out).
# Design: per-mint log10 market cap in SOL; growth g from the LAST two
# points clipped to [-0.3, +0.5] per hour; forecast to the middle answer
# read (reads[3]) with horizon capped at 3.0 h; rank by predicted log-cap;
# place probabilities are a Gaussian in rank distance (sigma 2.0) scaled
# to 0.70 per place; size bins are a discrete Gaussian (sigma 7 bins)
# scaled to 0.85 per place. Deterministic, stdlib only, offline.
import os, json, math
from datetime import datetime

def main():
    input_dir = os.getenv('MAKEFUN_INPUT_DIR', '/input/')
    output_dir = os.getenv('MAKEFUN_OUTPUT_DIR', '/output/')
    if not os.path.exists(output_dir): os.makedirs(output_dir)

    history = []
    with open(os.path.join(input_dir, 'history.ndjson')) as f:
        for line in f:
            line = line.strip()
            if line:
                mark = json.loads(line)
                if mark['rows']:
                    history.append(mark)
    with open(os.path.join(input_dir, 'task.json')) as f:
        task = json.load(f)

    series = {}
    for mark in history:
        t = datetime.fromisoformat(mark['at'].replace('Z', '+00:00'))
        for row in mark['rows']:
            mint = row['mint']
            logcap = math.log10(int(row['market_cap_lamports']) / 1e9)
            if mint not in series:
                series[mint] = []
            series[mint].append([t, logcap])

    P = {}
    reads3 = datetime.fromisoformat(task['reads'][3].replace('Z', '+00:00'))
    for mint, pts in series.items():
        L = pts[-1][1]
        t_last = pts[-1][0]
        if len(pts) >= 2:
            L_prev = pts[-2][1]
            t_prev = pts[-2][0]
            dt = (t_last - t_prev).total_seconds() / 3600.0
            g = (L - L_prev) / dt if dt > 0 else 0.0
        else:
            g = 0.0
        if g > 0.5: g = 0.5
        if g < -0.3: g = -0.3
        H = (reads3 - t_last).total_seconds() / 3600.0
        Heff = H if H < 3.0 else 3.0
        P[mint] = L + g * Heff

    ranked = sorted(series.keys(), key=lambda m: P[m], reverse=True)
    candidates = ranked[:25]
    top5 = ranked[:5]

    probabilities = []
    for k in range(1, 6):
        raws = []
        for r in range(1, 26):
            raws.append(math.exp(-((r - k) ** 2) / (2 * 2.0 ** 2)))
        s = sum(raws)
        for r in range(1, 26):
            p = round(raws[r - 1] / s * 0.70, 6)
            if p >= 0.005:
                probabilities.append({"mint": candidates[r - 1], "place": k, "p": p})

    sizes = []
    for k in range(1, 6):
        C = P[candidates[k - 1]]
        center_bin = round((C - 2.00) / 0.05)
        if center_bin < 0: center_bin = 0
        if center_bin > 81: center_bin = 81
        raws = []
        for b in range(82):
            raws.append(math.exp(-((b - center_bin) ** 2) / (2 * 7.0 ** 2)))
        s = sum(raws)
        for b in range(82):
            p = round(raws[b] / s * 0.85, 6)
            if p >= 0.001:
                sizes.append({"place": k, "bin": b, "p": p})

    out = {"probabilities": probabilities, "top5": top5, "sizes": sizes}
    with open(os.path.join(output_dir, 'forecast.json'), 'w') as f:
        json.dump(out, f, sort_keys=True)

if __name__ == '__main__':
    main()
