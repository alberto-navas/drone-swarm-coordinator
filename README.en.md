# Drone Swarm Coordinator

**English** · [Español](README.md)

[![Tests](https://github.com/alberto-navas/drone-swarm-coordinator/actions/workflows/tests.yml/badge.svg)](https://github.com/alberto-navas/drone-swarm-coordinator/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Mission allocation, formation flying and collision avoidance for a swarm
of your own drones — simulated and visualized on a real map, with
explainable methods at every step, no black-box machine learning.

<p align="center">
  <img src="docs/screenshots/panel_web.png" alt="Web panel: real animated map (Gibraltar) with ten drones covering a port area, next to the simulation summary (drones, ticks, separation conflicts) and the ES/EN/DE language switcher" width="800">
</p>

*Web panel (`python -m src.web`) — ten drones covering a port area in the
Strait of Gibraltar region, a real animated Leaflet map, not a static
capture.*

## Motivation

Coordinating a swarm of your own drones to fulfill a mission — cover an
area, watch several points, reach several destinations — is an
allocation and distributed-control problem: which drone does what, how
to keep them from getting too close to each other while flying
concurrently, and how to hold a formation when needed. It's the flip
side of the sibling project
[C-UAS Threat Triage](https://github.com/alberto-navas/cuas-threat-triage):
there the goal is deciding which outside threat to respond to first;
here it's coordinating your own fleet so it completes its mission
without colliding. This project solves the three pieces with explainable
methods — greedy allocation, formation geometry, a reactive separation
rule — on a purpose-built simulator, and visualizes it on a web panel
with a real animated map (same approach as
[Maritime Domain Awareness](https://github.com/alberto-navas/maritime-domain-awareness)).

## Capabilities

Four independent, separately auditable modules, `src/`:

- **Mission allocation** (`allocation.py`): for point/destination tasks, a
  greedy distance-based pairing — out of every possible (free drone,
  unassigned task) pair, the closest one still available is picked,
  repeatedly. Deliberately not optimal (no Hungarian algorithm), the same
  simplicity/explainability trade-off as the nearest-neighbor associator
  in C-UAS Threat Triage's tracker. For area-coverage tasks, the zone's
  rectangle is split into as many cells as there are drones (as square a
  grid as possible), each cell is assigned via the same greedy pairing,
  and every drone gets a "lawnmower" (boustrophedon) sweep route that
  fully covers its cell.
- **Formation** (`formation.py`): three shapes — line, V, grid — relative
  to a designated leader or the group's centroid (with its mean heading
  computed as a circular mean, not an arithmetic one). Each drone's slot
  is assigned by reusing the same greedy pairing from `allocation.py`, so
  the "who goes where" logic isn't duplicated.
- **Separation conflicts** (`conflict.py`): detection — the distance
  between every pair of drones checked each simulation tick against a
  minimum safety threshold — and reactive correction — a repulsion
  vector in the style of *separation steering* (Reynolds, 1987), added to
  the drone's vector toward its task or formation slot. Not a trajectory
  optimizer and no mathematical guarantee of avoiding every collision
  (see "Known limitations" below); a simple reactive rule, documented as
  such.
- **Simulation** (`simulation.py`): a discrete-tick loop (1 tick = 1
  mission second) that ties the three modules above together over
  minimal kinematics (constant cruise speed toward the target point) and
  simple battery drain.

**Web panel** (`src/web/`, optional): pick one of the two demo scenarios
and see an animated map (a real Leaflet map, with real streets and
coastlines) with every drone's trail and its separation conflicts marked
at the exact tick they were detected, alongside the final fleet-status
table and a conflicts table grouped by drone pair. A thin layer over the
same `src/simulation.py` the CLI uses — no engine logic is reimplemented.

**Spanish / English / German**: the CLI (`--lang`) and the web panel
(language switcher on the page) show the whole interface — drone
statuses, headings, scenario names — in any of the three languages.
`src/i18n.py` is the only module that knows the concept of language
exists; the simulation engine (`allocation.py`, `formation.py`,
`conflict.py`, `simulation.py`) never imports it.

## Architecture

```
Scenario (src/scenarios.py)
  -> Drone[] + Mission (tasks + optional formation)
        │
        ▼
src/simulation.py  build_initial_state()
  └── src/allocation.py   (task allocation, once at startup)
        │
        ▼
src/simulation.py  step()  — repeats once per mission second
  ├── src/formation.py    (formation slot, if the mission asks for one;
  │                         recomputed every tick since its origin moves)
  ├── src/conflict.py     (separation detection + correction)
  └── src/geo.py          (distances, local offsets, bearings)
        │
        ▼
SimulationState[]  (full simulation history)
        │
        ├──────────────────────────────┬─────────────────────
        ▼                              ▼
src/cli.py                     src/web/app.py (FastAPI)
  (text report,                  ├── animated_map.py (Leaflet + TimestampedGeoJson)
   --lang es/en/de)              └── groups conflicts by pair for the table
```

`src/model.py` is the shared vocabulary (`Drone`, `Task`, `Mission`,
`SimulationState`, `ConflictEvent`) every module uses: the allocation
engine doesn't know how a scenario was built, and the web panel doesn't
reimplement any allocation or formation rule.

`src/geo.py` solves short-range geometry (drone separation, formation
offsets) with a local tangent-plane approximation, not a full geodesic
projection — valid at swarm operating scale (formations and separations
of tens/hundreds of meters), documented as such, not meant for long
distances where Earth's curvature matters.

## Usage

```bash
# Run a demo scenario and print the fleet's final status
python -m src.cli cobertura
python -m src.cli formacion --ticks 45 --lang en

# Custom minimum safety separation (default: 15 m)
python -m src.cli cobertura --min-separation 20
```

**Web panel**:

```bash
python -m src.web
# -> http://127.0.0.1:8000
```

Pick a scenario and a duration (in ticks) and press "Run" to see the
animated map, the fleet's final status, and the separation conflicts
detected. The ES/EN/DE switcher in the top right changes the whole
page's language — the URL (`?lang=en`) is self-contained, no cookies or
session state, and switching language on a report re-runs the same
scenario with the same duration.

## Demo scenarios

100% synthetic, generated deterministically by `src/scenarios.py` (no
random numbers): no public dataset of real swarm flights exists with the
level of detail needed here (position + task + status of every drone at
every instant), and this way the demo cases are exactly controlled. Both
are set in the Strait of Gibraltar/Alboran area — the same region the
Maritime Domain Awareness demo uses — because a real port facility is a
believable surveillance/area-coverage target for this kind of fleet:

- **Coverage with a forced conflict** (`cobertura`): ten drones launch
  together from the same point of a port facility to fully cover a
  rectangular zone around it. Since they all start at the same position,
  the first ticks generate real separation conflicts that the reactive
  correction has to resolve while each drone heads to its assigned cell.
- **Formation transit** (`formacion`): ten drones start already
  reasonably spread out and form a V wedge to transit together,
  demonstrating a clean formation without the noise of a collision
  correction starting from scratch.

## Tests

```bash
pytest -v
```

79 tests covering the engine's nine modules and the web panel (model,
geometry, allocation, formation, conflicts, simulation, scenarios, i18n,
CLI, animated map, web panel), 99% coverage (`pytest --cov=src`, with an
85% CI threshold as a safety net against a major drop, not a line-by-line
target to chase). Run automatically on every `push` via GitHub Actions
(`.github/workflows/tests.yml`), on Ubuntu and Windows.

## Code quality

```bash
ruff check .        # lint
ruff format .       # formatting
mypy src/           # static type checking
```

Configured in `pyproject.toml`. Checked automatically on every `push` (a
`lint` job separate from the test job).

## Known limitations

- Task allocation is greedy, not globally optimal (no Hungarian
  algorithm): a drone can end up with a task that isn't the closest to
  it specifically, if an even closer drone already claimed it in an
  earlier iteration. A deliberate limitation, documented in
  `allocation.py`.
- Collision correction is a simple reactive rule, not a mathematical
  guarantee. This was found during the panel's visual verification: in
  the coverage scenario, two drones launched from the same point toward
  neighboring cells on near-parallel bearings settle into an equilibrium
  a few meters below the safety threshold instead of fully separating —
  the separation force and the pull toward the task cancel each other
  out instead of one winning. The system correctly detects and reports
  this for the whole simulation (hence the scenario's name, "with a
  forced conflict"), but doesn't fully resolve it; that's the expected
  behavior of a simple rule, not a detector bug. The panel's conflicts
  table groups these cases by drone pair (from/until which tick, how many
  times, minimum distance) so they read as what they are — one sustained
  conflict, not hundreds of loose events.
- 2D geometry (latitude/longitude); altitude is a state field with no
  effect yet on separation or formation geometry.

## What this project deliberately does NOT do

This is a **simulation, planning and visualization** tool for your own
fleet on a legitimate mission (surveillance, area coverage, logistics) —
unlike the sibling non-lethal interception project, this has nothing to
do with weapons or neutralizing anything:

- **Does not control real drones or connect to any flight hardware** —
  no autopilot (MAVLink, ArduPilot, PX4), no manufacturer SDK, no radio.
  All the state you see (position, battery, task) is generated by the
  simulator, not a physical drone.
- **Not a certified command-and-control system**: it does not meet, and
  does not aim to meet, any uncrewed-aviation regulation. Using this code
  to operate real drones without the testing, certification and
  authorization the law requires would be irresponsible and, in most
  jurisdictions, illegal.
- **No real perception**: every drone "knows" its exact position because
  the simulator hands it to it, not because it perceives it with its own
  sensors. No cameras, no obstacle detection, no avoidance of anything
  beyond another drone in the same swarm.
- **Not a surveillance tool aimed at third parties**: tasks are abstract
  points, areas and formations defined by whoever runs the simulator,
  with no recognition or identification of real people or objects.
- Task allocation and collision avoidance are simple, deliberately
  explainable heuristics — see "Known limitations" above for what that
  means in practice.

## Possible extensions

- **Globally optimal allocation** (Hungarian algorithm) as a documented
  alternative to the current greedy pairing, to compare total swarm
  travel distance between both methods.
- **Altitude/3D** in separation and formation geometry (purely 2D today).
- **Mixed-task missions** (area + points + destinations at once) — each
  scenario currently uses a single task type, though the data model
  doesn't forbid mixing.
- **More formations** (echelon, diamond) reusing the same slot mechanism
  from `formation.py`.
- **Live web panel deployment** (like the sibling projects, via Render):
  for now it's only meant to run locally (`python -m src.web`).
