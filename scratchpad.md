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

### Track surface (rolled back to fixed-width buffer)
- Simplified to a meter-true Shapely buffer around a single centerline source of truth.
- Centerline saved/loaded at `data/gps-tracks/track_centerline.csv`.
- Fixed width set in `src/track_rendering.py` (`track_width_m`, default 12 m).
- All visualizations load the same centerline and render the same surface, so visuals match across pages.

### 2025-10-29 – Donut band + width tweak
- Restored donut-style band (hollow center) by constructing left/right edges from centerline normals and filling the ring.
- Kept single source of truth centerline (`data/gps-tracks/track_centerline.csv`).
- Increased band width: 12m → 14m → 16m total (constant `track_width_m` in `src/track_rendering.py`).
- To adjust: edit `track_width_m`, then run:
  - `venv/bin/python src/generate_brake_overlay.py`
  - `venv/bin/python src/generate_all_brakes_viz.py`
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
- **Brake histogram created**: Manual zone definition approach
  - Discovered brake points occur BEFORE corners, not at apex
  - Switched from auto-clustering to manual zone definition
  - Created brake_histogram.html: 4,892 brake events, 10m bins, max density 261 events/bin
  - Track length: 3662m, using vehicle #13 lap 18 as centerline reference
  - Next: Edu to manually define brake zone boundaries based on histogram peaks
- **Brake zones defined**: 8 significant brake zones identified from histogram
  - Saved to brake_zones.json with track distance ranges
  - Zones cover major braking areas before corners
- **Folder cleanup**: Reorganized to match implementation-plan.md structure
  - Removed data/track-layout/ folder
  - Moved brake_zones.json → data/brake-analysis/corner_definitions.json
  - Moved corner_labels.json, pit_lane.json → data/gps-tracks/
  - Created temp/ folder for helper files (histograms, diagnostics, track bands)
  - Updated path references in src/generate_all_brakes_viz.py and src/generate_brake_histogram.py
- **Step 5c completed**: Filtered brake visualization
  - Created step5c_filtered_brakes.html with only zone brake points
  - 4,501 points in zones (92%), removed 391 points outside zones (8%)
  - 8 zones colored distinctly: Zone 1=569pts, Z2=626, Z3=605, Z4=561, Z5=525, Z6=542, Z7=459, Z8=614
  - Track-distance projection working correctly
- **Step 6 completed**: Saved brake_events.csv
  - Created src/corner_detection.py with zone assignment utilities
  - Generated data/brake-analysis/brake_events.csv with 4,892 brake events
  - Columns: vehicle_number, lap, timestamp, zone_id, track_distance, x/y meters, lon/lat, brake pressures, brake_type
  - 92% of brake events assigned to zones, 8% outside (straights/other areas)
