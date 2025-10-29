# Hack the Track 2025 - Toyota Gazoo Racing

## Objective

Participate in the Hack the Track 2025 hackathon by Toyota Gazoo Racing and Devpost. Goal: build a data-driven, innovative, and easy-to-understand project using the provided GR Cup telemetry datasets.

## Rules (Key Points)

- Must use at least one provided dataset from [trddev.com/hackathon-2025](https://trddev.com/hackathon-2025)

## Categories

- **Driver Training / Insights**
- **Pre-event Prediction**
- **Post-event Analysis**
- **Real-time Analytics**
- **Wildcard** (anything impactful for GR Cup)

## Deliverables

- Working prototype or app
- 3-minute demo video (must show it running)
- Description of how it works + dataset use

## Judging Criteria

Each entry is scored equally across these four points:

1. **Application of the Dataset** — how effectively and creatively it uses the telemetry
2. **Design** — clarity, usability, and how well the idea is presented visually or interactively
3. **Quality of the Idea** — originality and technical cleverness; not just another dashboard
4. **Potential Impact** — how valuable it could be to Toyota GR or GR Cup racing (driver performance, fan engagement, or engineering insight)

## Data Available

### Telemetry

- Speed, gear, RPM (nmot)
- Throttle (ath/aps)
- Brake pressure (pbrake_f/r)
- Steering angle
- Longitudinal/lateral acceleration (accx_can, accy_can)
- GPS position
- Lap distance

### Structure

- Split by track (Barber, COTA, Indy, etc.)
- Each with multiple laps and sectors (S1a–S3b)

**Note:** All data is anonymized, ECU-synced, and usable for analytics, prediction, or comparison.

## Additional Data Sources

### USAC Timing Site
- URL: [http://usac.alkamelna.com/?series=06_SRO&season=25_2025](http://usac.alkamelna.com/?series=06_SRO&season=25_2025)
- Series: **SRO**
- 2025 season: Look for **TGRNA GR CUP NORTH AMERICA**
- 2024 season: Look for **Toyota GR Cup**

### Available Data Per Race Weekend

Each race weekend includes detailed downloadable CSV/PDF datasets for every session (Test, Practice, Qualifying, Race):

- **Results**: Finishing positions, lap times, gaps, and averages per driver
- **Results by Class**: Separated by class (Pro/Am, etc.)
- **Fastest Lap by Driver**: Best individual laps across the field
- **Best Sector Times**: Breakdown of sector performance for all drivers
- **Fastest Lap Sequence**: Sequence and evolution of each driver's best laps
- **Pit Stop Time Cards**: Timing and duration of pit stops
- **Analysis With Sections**: Detailed lap timing split by track sectors (S1a–S3b)
- **Weather Reports**: Conditions for the session (temp, humidity, etc.)
- **Best 10 Laps by Driver**: Average and consistency analysis

**Available Tracks (2025 Toyota GR Cup North America):**
Sonoma, COTA, Sebring, VIR, Road America, Barber, Indianapolis

## Technical Notes

### Known Issues with Telemetry Data

#### Time Fields
- **meta_time**: The time the message was received
- **timestamp**: The time on the electronic control unit (ECU) of the vehicle (may not be accurate)

#### Vehicle Identification
Example: For `GR86-004-78`:
- Chassis number: `004`
- Car number: `78` (sticker on the side of the car)
- If car number is `000`, it hasn't been assigned to the ECU yet
- Vehicles can be uniquely identified by chassis number
- Car numbers may be updated in later races

#### Lap Count Issues
- Lap count is sometimes lost or erroneously reported (often as lap #32768)
- Time values should still be accurate
- Lap number can be determined from time values

## Vehicle Telemetry Parameters

### Speed & Drivetrain

| Parameter | Description |
|-----------|-------------|
| `Speed` | Actual vehicle speed (km/h) |
| `Gear` | Current gear selection |
| `nmot` | Engine RPM |

### Throttle & Braking

| Parameter | Description |
|-----------|-------------|
| `ath` | Throttle blade position (0% = fully closed, 100% = wide open) |
| `aps` | Accelerator pedal position (0% = no acceleration, 100% = fully pressed) |
| `pbrake_f` | Front brake pressure (bar) |
| `pbrake_r` | Rear brake pressure (bar) |

### Acceleration & Steering

| Parameter | Description |
|-----------|-------------|
| `accx_can` | Forward/backward acceleration in G's (positive = accelerating, negative = braking) |
| `accy_can` | Lateral acceleration in G's (positive = left turn, negative = right turn) |
| `Steering_Angle` | Steering wheel angle in degrees (0 = straight, negative = counterclockwise, positive = clockwise) |

### Position & Lap Data

| Parameter | Description |
|-----------|-------------|
| `VBOX_Long_Minutes` | GPS longitude (degrees) |
| `VBOX_Lat_Min` | GPS latitude (degrees) |
| `Laptrigger_lapdist_dls` | Distance from start/finish line (meters) |

---

## Track Context: Barber Motorsports Park

### Track Characteristics
- **Corner count**: 17 corners, clockwise direction
- **Lap length**: 2.30 miles (~3.7 km)
- **Expected corner labels**: C1–C17 (validation check for auto-detection)

### Key Track Features
- **Pit locations**: Pit Out near C1–C4; Pit In by C15–C16
- **Priority brake zones**: End of front straight (C1–C2), entry to infield (C5), lower hairpin (C8–C9), tight hairpin by pit (C16)
- **Overlap caution**: Infield C6–C7 visually lies under the front straight—cluster by lap-distance first, then by GPS, to prevent merges
- **Close corner pairs**: C6/C7 and C15/C16 are adjacent; may need special handling

### Implementation Notes
- Filter pit-lane events for corner analysis (ignore braking near pit merge/split)
- Show pit lanes on track map visualization
- Use lap length for quick QA/sanity checks on corner spacing
- Do not use PNG/images for geometry—telemetry drives all quantitative logic
- Target priority brake zones for demo narrative ("where to practice first")
