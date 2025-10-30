Deliverables scaffold to reproduce the final v2 interactive HTML (zone‑focused dashboard) using a minimal, portable structure. This folder contains only placeholders and concise directions — no executable code.

Folder structure (simple)
- data/input/
  - telemetry.csv
  - usac.csv
  - corner_definitions.json
  - corner_labels.json (optional)
  - pit_lane.json (optional)
- data/output/
  - all_drivers.csv
  - brake_events.csv
  - driver_summary.csv
  - track_centerline.csv
  - dashboard.html
- src/
  - data_processing.py
  - visuals.py
- main.py
- requirements.txt

Inputs required per track (place under data/input/)
- data/input/telemetry.csv — Telemetry long CSV (same schema as Barber)
- data/input/usac.csv — USAC results CSV (semicolon‑delimited)
- data/input/corner_definitions.json — Manual zones (track‑level input; do not remove)
- Optional overlays (track‑level inputs):
  - data/input/corner_labels.json
  - data/input/pit_lane.json

Outputs (written under data/output/)
- all_drivers.csv
- brake_events.csv
- driver_summary.csv
- track_centerline.csv (auto‑created if missing)
- dashboard.html (final dashboard)

One-command flow (orchestrator outline)
1) Data processing (deliverables/src/data_processing.py):
   load_and_pivot_telemetry (from data/input/telemetry.csv) → compute_brake_threshold_p5 → detect_brake_onsets → filter_racing_laps → (call visuals.build_track_outline_figure once to create/reuse data/output/track_centerline.csv) → project_points_onto_centerline → assign_brake_events_to_zones → compute_zone_dispersion → summarize_driver_consistency → merge_usac_lap_times (from data/input/usac.csv)
2) Visuals (deliverables/src/visuals.py): render_zone_focus_dashboard → data/output/dashboard.html
3) Entry point: deliverables/main.py orchestrates steps and handles CLI args (defaults point to data/input/*; outputs under data/output)

Function mapping (original → deliverables/src/*)

src/data_processing.py
- load_and_pivot_telemetry ← src/data_loaders.py: load_telemetry
- convert_gps_to_meters ← src/data_loaders.py: _convert_gps_to_meters
- compute_brake_threshold_p5 ← src/data_loaders.py: calculate_brake_threshold
- load_usac_results ← src/data_loaders.py: load_usac_results
- detect_brake_onsets ← src/brake_detection.py: detect_brake_events
- filter_racing_laps (3500–4000 m) ← logic used in src/save_brake_events.py and src/generate_* scripts
- project_points_onto_centerline ← src/corner_detection.py: project_to_centerline
- assign_brake_events_to_zones ← src/corner_detection.py: assign_to_zones
- compute_zone_bounds ← src/corner_detection.py: calculate_zone_boundaries
- compute_zone_dispersion ← src/consistency_analysis.py: calculate_dispersion_by_zone
- summarize_driver_consistency ← src/consistency_analysis.py: calculate_driver_summary
- merge_usac_lap_times ← src/consistency_analysis.py: add_lap_times

src/visuals.py
- resample_centerline_by_distance ← src/track_rendering.py: resample_by_distance
- smooth_centerline_periodic ← src/track_rendering.py: smooth_periodic
- build_track_outline_figure ← src/track_rendering.py: generate_track_outline
- save_centerline_csv ← src/track_rendering.py: save_track_data
- render_zone_focus_dashboard ← src/visualization.py: create_zone_focused_dashboard

Notes
- Keep data/input/corner_definitions.json (manual zones). It is track‑specific and required to rebuild outputs.
- Optional overlays (corner labels, pit lane) improve visuals, but are not required.
- The centerline CSV is auto‑generated under data/output and reused to keep visuals consistent.
