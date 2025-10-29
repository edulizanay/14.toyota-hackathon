# Brake Point Drift Detector

**One-liner**: Visualize braking point consistency across laps - tight clusters = fast/consistent, scattered = slow/inconsistent.

## Core Concept

Show drivers WHERE they're inconsistent and by HOW MUCH using GPS + brake pressure data overlaid on a track map.

## High-Level Architecture

### 1. Data Processing
- Extract GPS coordinates from telemetry data
- Identify brake events (brake pressure > threshold)
- Correlate brake points with GPS locations
- Group brake points by corner/sector

### 2. Track Visualization
- Generate track outline from GPS trace
- Render using Plotly (interactive, beautiful out-of-box)
- Dark theme with racing aesthetic
- Smooth GPS line for professional look

### 3. Consistency Analysis
- Calculate brake point scatter per corner (spatial variance)
- Calculate dispersion (std dev in meters) per corner
- Visualize driver's brake points against fastest driver's reference
- Identify which corners need work

### 4. Output
- Track map with colored dots (green=consistent, red=scattered)
- Dispersion values (meters) per corner
- Driver comparison view
- Simple, clean web interface

## Why This Wins

- **Beautiful**: Racing-style visualization, instantly impressive
- **Fundamental**: Consistency is THE skill differentiator between amateur and pro
- **Novel**: GPS brake scatter visualization hasn't been done this way
- **Actionable**: Shows repeatability—first step to improvement
- **Feasible**: We have all the data needed, proven libraries exist

## Tech Stack

- Python + Plotly for visualization
- Pandas for data processing
- Scipy for GPS smoothing
- Simple web interface for demo

## Data Requirements

- `VBOX_Long_Minutes` (GPS longitude)
- `VBOX_Lat_Min` (GPS latitude)
- `pbrake_f` / `pbrake_r` (brake pressure)
- `timestamp` (for correlation)
- `lap` (for grouping)

---

## Agreements

### Visualization Strategy
- Plotly with dark racing theme and smooth GPS curves (scipy)
- Color gradient: green (consistent) → red (scattered), prioritize aesthetic over colorblind safety
- Interactive zoom/hover with tooltips showing: corner name, dispersion (meters), lap number
- Layered visualization: gray transparent reference dots (fastest driver) underneath, vibrant colored scatter (target driver) on top
- Show full track (context matters)
- Numbered corner badges on track

### UX & Demo
- **Controls**: Driver selector dropdown only—use Plotly's built-in zoom/pan
- **Layout**: Driver dropdown top-left, track map center (zoomable), consistency score panel right showing per-corner breakdown
- **NO custom buttons/sliders/play animations** to avoid distraction
- **Target**: Judges grasp it in 10 seconds

### Data & Analysis
- **Baseline**: Single fastest driver (cleaner narrative, "best practice" reference)
- **Driver comparison**: Any driver vs the best (flexible selection)
- **Normalization**: Per-corner across all drivers for fairness
- **Brake threshold**: 5 bar (filters noise, catches intentional braking, tunable)
- **Corner detection**: Hybrid approach (speed minima + GPS DBSCAN clustering)
- **Corner naming**: C1, C2, C3... (auto-numbered sequentially by lap distance order)
- **Consistency metric**: Standard deviation in meters (raw values, no 0-100 scoring)
- **Display**: Show dispersion in meters for clarity
- **Demo dataset**: R1 only

### Track Rendering
- Use median GPS centerline from all laps (racing line IS the track)
- Soft glow to imply width (no edge-chasing needed)
- Brake points naturally cluster on racing line anyway

### Data Organization
- **Folder structure**: `data/telemetry-raw/`, `data/brake-analysis/`, `data/gps-tracks/`, `data/consistency-scores/`, `data/visualizations/`
- **Data tables**: `brake_events` (driver, lap, corner_id, x, y, lon, lat, time, pbrake) and `corner_summary` (driver, corner_id, dispersion, score, ref_dispersion)
- **Raw data docs**: Use existing data-structure.md; processed files get descriptive names

### Nice-to-Haves (Post-MVP)
- GPS sanity checks (drop >10m jumps)
- Decel proxy fallback if brake data missing
- Skip flagged laps
- Cap to best 5 laps/driver for performance
- Graceful error handling with warnings
- Convex hull area visualization
