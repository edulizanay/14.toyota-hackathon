# Scratchpad - Brake Point Drift Detector

## Issues & Out-of-Scope Notes

### 2025-10-29 Session
- Phase 1 Step 1: System uses externally-managed Python environment, created venv at `/venv/` (activate with `source venv/bin/activate`)
- Phase 1 Step 2: Smooth. P95=42.84 bar (WRONG - corrected later), fastest driver=#13, 20 vehicles, 1M+ rows processed
- Phase 2 Step 3: Track surface issues - multiple failed approaches:
  - Square joins (cap_style=2, join_style=2) → spiky/serrated edges
  - Changed to round joins (cap_style=1, join_style=1) + simplify(1.0) → smoother but still issues
  - Thick centerline ribbon (width=16px) → looked awful, rolled back
  - Parallel offsets donut polygon approach → rendering issues with hollow holes
  - **FINAL SOLUTION**: Layered strokes (18px dark gray base + 12px lighter gray + 2px cyan centerline) → clean ribbon, no polygons
- Smoothing increased from s=0.001 to s=0.01 for smoother centerline per Edu's request
- **P95→P5 correction caught before Step 4**: Changed from P95 (42.84 bar, top 5% only) to P5 of positive pressures (3.81 bar) for brake onset detection. Rising-edge detection: 5,309 events, rear brake leads 85.2%

### Track surface update (donut band)
- Replaced pixel-width strokes and fixed-width buffer with data-driven donut band (annulus) built from all telemetry positions.
- Method: project points to centerline, compute signed offsets; per-station half-widths from q90, smoothed; build left/right edges and fill between.
- Validations (console): area, implied mean width, width p05/p50/p95, sample count. Temp check script: `temp/check_annulus_coverage.py` prints % of brake events inside band.
- Current stats: implied mean width ~6.4m (p50=6.0m), coverage ~93% on sampled brake points. Tune by raising quantile or min_width if we want a thicker ribbon.
- **Step 3 refinement**: Replaced UnivariateSpline with distance-based resampling + Savitzky-Golay smoothing:
  - Resample to uniform 2m spacing (removes GPS jitter)
  - Remove spikes >10m and duplicate points
  - Periodic wrapping (25 points) to eliminate closure kink
  - Result: Perfectly smooth track outline with crisp corners
- **Step 4 completed**: Brake overlay visualization
  - Vehicle #13, lap 18: 20 brake events detected
  - Colorbar resized to 2/3 height to avoid legend collision
  - Investigation confirmed detection logic is correct (20 segments = 20 events)
  - Brake point visualization shows some alignment issues (coordinate system mismatch between smoothed track and raw brake GPS - resolved with ChatGPT)
- **Step 5a completed**: All brake points visualization
  - 4,892 brake events from racing laps (all drivers, 3500-4000m laps only)
  - Semi-transparent red overlay shows brake density at each corner
  - Ready for manual corner polygon definition
- **Corner labeling added**: Auto-clustering found 13 corner clusters
  - DBSCAN clustering (eps=25m, min_samples=10)
  - Corner numbers displayed as white circles with black text
  - Pit lane extracted from lap 2 (1038m) and displayed as dashed yellow line
  - Data stored in: corner_labels.json, pit_lane.json
  - Applied pixel-based position adjustments
- **Interactive label editor created**: temp/label_editor.html
  - Click-to-place interface for repositioning all 17 corner labels
  - Edit mode for individual corner adjustments
  - Downloads updated corner_labels.json
  - Self-contained HTML (no server needed)
- **Git commit created**: Steps 3-5a completed and committed to main branch
