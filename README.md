# Brake Point Drift Detector

**Hack the Track 2025 - Driver Training & Insights Category**

Brake Point Drift Detector analyzes GR Cup telemetry to measure driver consistency and identify where to focus practice time. Using GPS coordinates and brake pressure data, it visualizes brake point scatter across corners, helping drivers distinguish between systematic technique issues and random inconsistency.

> **Consistency separates fast drivers from champions—but how do you measure it?**

![Dashboard Screenshot](./docs/images/dashboard-screenshot.png)
*TODO: Add screenshot of the interactive dashboard showing track map and dispersion analysis*

## Demo & Submission

🎯 **[Try the Live Demo →](https://edulizanay.github.io/14.toyota-hackathon/)**

No installation required - opens directly in your browser with interactive features:
- Click drivers in the legend to compare brake point consistency
- Toggle between individual brake points and average centroids
- Explore zone-by-zone dispersion metrics

- **Demo Video**: [3-minute walkthrough on YouTube](https://www.youtube.com/watch?v=TODO)
- **Official Dataset**: `barber-motorsports-park.zip` from [trddev.com/hackathon-2025](https://trddev.com/hackathon-2025)
- **Supplemental Data**: USAC race timing data for lap time correlation

## Key Findings

Analysis of 16 drivers and 4,879 brake events from Barber Motorsports Park:

- **Zone-specific consistency wins races**: While overall dispersion is similar across the field, podium finishers show 7.1m consistency advantage in Zone 8 (final complex) and 5.3m advantage in Zone 5 (infield entry)—the two highest-priority braking zones

- **Strategic brake point placement**: Podium finishers brake 29m differently in Zone 1 and 28m differently in Zone 2, suggesting intentional racing line optimization beyond pure repeatability

- **Winner brakes 26m earlier on average**: In 7 of 8 zones, the winning driver initiates braking earlier than the field (up to 44m earlier in Zone 1), allowing more time to settle the car and carry higher corner speeds

- **Smoother braking technique**: Podium finishers average 7.1 bar brake pressure vs. 9.2 bar for the field (2.1 bar less), indicating more efficient threshold braking and better corner entry speed management

- **Winner (Car #13)** posted 1:37.428 fastest lap with 30.7m average dispersion—proving that strategic inconsistency in some zones enables speed in others

> 📊 **Detailed analysis**: See [analytics/README_KEY_FINDINGS.md](analytics/README_KEY_FINDINGS.md) for complete methodology, zone-by-zone breakdown, and coaching implications

## Quick Start

### Prerequisites
- Python 3.13+ (tested on 3.13)
- Virtual environment recommended

### Installation

```bash
# Navigate to deliverables directory
cd deliverables

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Usage

```bash
# Run the analysis pipeline (from deliverables/ directory)
python main.py

# Output: dashboard.html (open in any web browser)
```

The pipeline processes telemetry data and generates an interactive dashboard showing:
- Track map with brake points plotted by GPS coordinates
- Zone-by-zone dispersion analysis (in meters)
- Driver comparison against fastest lap reference
- Toggle between individual brake points and average centroids

### Input Data

The tool uses:
- **GR Cup Telemetry** (Barber Motorsports Park) from `barber-motorsports-park.zip` - brake pressure, GPS coordinates, speed, lap numbers
- **USAC Timing Data** - lap times and race results

Data files are located in `deliverables/data/input/`:
- `telemetry.csv` - Raw GR Cup telemetry
- `usac.csv` - Race timing data
- `corner_definitions.json` - Brake zone boundaries
- `corner_labels.json` - Corner naming (C1-C17)
- `pit_lane.json` - Pit lane geometry

## How It Works

### 1. Track Centerline Generation

The track centerline is computed from GPS telemetry using a multi-stage smoothing pipeline:

1. **Raw GPS Extraction**: Select one vehicle's most complete lap (highest GPS sample count)
2. **Distance-based Resampling**: Convert to uniform 2-meter spacing, removing GPS spikes (>10m jumps) and duplicates
3. **Periodic Smoothing**: Apply Savitzky-Golay filter (31-point window, 3rd-order polynomial) with periodic wrapping to eliminate start/finish kinks
4. **Caching**: Centerline saved to `data/output/track_centerline.csv` for reuse (use `--force` to regenerate)

**Why this matters**: A stable, smooth centerline ensures brake points are assigned to zones consistently across laps and drivers, enabling apples-to-apples comparison.

### 2. Brake Onset Detection

Brake events are detected using rising-edge logic:

1. **Threshold Calculation**: Compute P5 (5th percentile) of all positive brake pressures to filter noise
2. **Pressure Selection**: Use `max(pbrake_f, pbrake_r)` - whichever brake is pressed harder
3. **Brake Type Recording**: Tag each event as "front" or "rear" based on which pressure led
4. **Rising Edge Detection**: Detect transition from `pressure < threshold` → `pressure >= threshold` (brake onset)
5. **GPS Association**: Record GPS coordinates (x, y meters) at the moment of brake onset

**Output**: Each brake event has a GPS coordinate, timestamp, lap number, vehicle number, and brake type.

### 3. Zone Assignment & Dispersion

1. **Zone Mapping**: Assign each brake event to a predefined corner zone based on GPS distance from centerline
2. **Dispersion Calculation**: For each driver-zone pair, compute standard deviation of brake point GPS positions (in meters)
3. **Consistency Ranking**: Lower dispersion = more consistent braking

### 4. Interactive Dashboard

The dashboard provides:
- **Track visualization**: Overhead track map with brake points color-coded by driver
- **Zone analysis**: Bar chart showing dispersion (meters) for each corner
- **Driver comparison**: Compare any driver against the fastest lap reference
- **Dual modes**: Toggle between individual brake points (scatter) and average brake points (centroids)

## Technical Considerations

### Brake Detection Methodology

- **Brake onset vs. peak pressure**: This tool detects brake **onset** (the moment braking starts), not peak pressure. This measures where drivers initiate braking, which is the primary consistency metric for analyzing brake point placement.

- **Front vs. rear brake**: The tool uses the **maximum** of front or rear brake pressure and records which one led. In racing, drivers typically lead with front brake, but the system tracks both to capture technique variations.

### Known Limitations

- **GPS precision**: Consumer-grade GPS (~2-5m accuracy) limits the resolution of dispersion measurements. Sub-meter differences may not be meaningful.

- **Racing line variation**: Brake point scatter can result from intentional racing line adjustments (overtaking, defending, traffic) or unintentional inconsistency. The tool shows the symptom, not the root cause.

- **Pit lane filtering**: Events near pit entry/exit are currently included in analysis. For production use, these should be filtered to avoid skewing dispersion metrics.

### Training Applications

This methodology enables several coaching workflows:

- **Live session feedback**: "Braked 3 meters early, Corner 5" - real-time audio coaching during practice sessions
- **Multi-track analysis**: Expand beyond Barber to full GR Cup calendar for season-long consistency tracking
- **Apex/exit analysis**: Extend methodology to corner apex speed and throttle application points for complete corner profiling
- **Session-to-session tracking**: Measure improvement across practice/qualifying/race sessions to validate coaching interventions

## Project Structure

```
deliverables/
├── main.py                    # Entry point and pipeline orchestrator
├── dashboard.html             # Generated interactive dashboard
├── requirements.txt           # Python dependencies
├── data/
│   ├── input/                 # Source datasets (telemetry, USAC, zones)
│   └── output/                # Generated CSVs (brake_events, centroids, etc.)
└── src/
    ├── data_processing.py     # Brake detection, zone assignment, dispersion
    └── visuals/
        ├── geometry.py        # GPS smoothing and coordinate math
        ├── track_outline.py   # Centerline computation
        └── dashboards.py      # Plotly dashboard generation
```

## System Requirements

- **Python**: 3.13+ (may work on 3.10+, not tested)
- **Memory**: ~2GB RAM (processes large telemetry CSVs in chunks)
- **Storage**: ~500MB for telemetry data + outputs
- **Browser**: Modern browser with JavaScript (Chrome, Firefox, Safari, Edge)

## License

This project was created for the Hack the Track 2025 hackathon by Toyota Gazoo Racing. All telemetry data is provided by Toyota Racing Development and is subject to their licensing terms.

## Authors

Built by Eduardo Lizana for Hack the Track 2025.

## Acknowledgments

- Toyota Gazoo Racing for providing GR Cup telemetry datasets
- USAC for race timing data
- Barber Motorsports Park for the incredible racing venue
