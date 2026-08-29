#!/usr/bin/env bash
#
# Quick self-check: build two test tracks with KNOWN tempo (one steady at
# 127.96 BPM, one deliberately drifting), run beatgrid on them, and confirm it
# recovers the right answers. Prints RESULT: PASSED when all good.
#
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
PY="$VENV/bin/python3"
[ -x "$PY" ] || PY="python3"

"$PY" - "$SCRIPT_DIR" <<'PY'
import os, sys, tempfile, numpy as np
sys.path.insert(0, sys.argv[1])
import beatgrid as bg

SR = 22050
def clicks(times, dur):
    n=int(dur*SR); y=np.zeros(n,dtype=np.float32)
    L=int(0.03*SR); env=np.exp(-np.linspace(0,8,L)).astype(np.float32)
    tone=np.sin(2*np.pi*1500*np.arange(L)/SR).astype(np.float32)
    noise=np.random.RandomState(0).randn(L).astype(np.float32)
    c=env*(0.6*tone+0.4*noise)
    for t in times:
        i=int(round(t*SR))
        if 0<=i<n-L: y[i:i+L]+=c
    return y

def const(bpm, first, count):
    return first + (60.0/bpm)*np.arange(count)
def drift(b0,b1,first,count):
    t=[first]
    for k in range(1,count):
        t.append(t[-1]+60.0/(b0+(b1-b0)*k/(count-1)))
    return np.array(t)

import soundfile as sf
ok=True

with tempfile.TemporaryDirectory() as d:
    cpath=os.path.join(d,"const.wav"); dpath=os.path.join(d,"drift.wav")
    sf.write(cpath, clicks(const(127.96,0.5,300), 145), SR)
    sf.write(dpath, clicks(drift(128,125,0.3,320), 155), SR)

    r=bg.analyze_file(cpath)
    print(f"  steady track : detected {r['bpm']:.3f} BPM, verdict={r['verdict']}")
    if abs(r['bpm']-127.96)>0.1: print("    FAIL: BPM off"); ok=False
    if r['verdict']!="constant": print("    FAIL: should be constant"); ok=False

    r=bg.analyze_file(dpath)
    print(f"  drifting track: avg {r['bpm']:.3f} BPM, verdict={r['verdict']}, "
          f"{len(r['drift']['cues'])} cues, range "
          f"{r['drift']['local_bpm_min']}-{r['drift']['local_bpm_max']}")
    if r['verdict']!="drifting": print("    FAIL: should be drifting"); ok=False
    if len(r['drift']['cues'])<2: print("    FAIL: expected cue points"); ok=False

print()
print("RESULT: PASSED" if ok else "RESULT: FAILED")
sys.exit(0 if ok else 1)
PY
