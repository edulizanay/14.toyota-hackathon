# Scratchpad - Brake Point Drift Detector

## Issues & Out-of-Scope Notes

### 2025-10-29 Session
- Phase 1 Step 1: System uses externally-managed Python environment, created venv at `/venv/` (activate with `source venv/bin/activate`)
- Phase 1 Step 2: Smooth. P95=42.84 bar (WRONG - corrected later), fastest driver=#13, 20 vehicles, 1M+ rows processed
- Phase 2 Step 3: Smooth. Track outline generated from car #13 lap #4. Added 12m track surface width using shapely buffer
- **P95→P5 correction caught before Step 4**: Changed from P95 (42.84 bar, top 5% only) to P5 of positive pressures (3.81 bar) for brake onset detection. Rising-edge detection: 5,309 events, rear brake leads 85.2%
