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
