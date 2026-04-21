# Network Routing Simulation Project

## Overview
This project simulates and compares multiple routing algorithms on different network topologies under configurable traffic loads. It includes:

- Interactive CLI mode
- Dash web dashboard
- Multiple topology types: random, mesh, ring, star
- Routing algorithms: Dijkstra, Bellman-Ford, ACO, and GA
- Seeded runs for reproducible experiments
- JSON and CSV result export

## Project Structure
```text
main.py                  Entry point for CLI and dashboard
config/                  Default configuration values
src/network/             Topology creation and graph utilities
src/algorithms/          Routing algorithm implementations
src/traffic/             Traffic flow generation
src/metrics/             Performance analysis and congestion model
src/dashboard/           Dash dashboard
tests/                   Unit tests
```

## Requirements
- Python 3.10+ recommended
- `pip`

## Installation
From the project root:

```powershell
python -m pip install -r requirements.txt
```

If your system uses `py` instead of `python`, use:

```powershell
py -3.12 -m pip install -r requirements.txt
```

## Running the Project

### Interactive CLI
```powershell
python main.py
```

The CLI will ask you to choose:
- topology type
- number of nodes
- edge probability for random topology
- routing algorithm
- traffic intensity

### CLI with Reproducible Seed
```powershell
python main.py --seed 42
```

Using the same seed gives the same topology, traffic flows, and stochastic algorithm behavior.

### CLI with Result Export
Export single-run or comparison results to JSON:

```powershell
python main.py --seed 42 --export outputs/results.json
```

Export results to CSV:

```powershell
python main.py --seed 42 --export outputs/results.csv
```

### Web Dashboard
```powershell
python main.py --mode dashboard
```

Then open:

```text
http://localhost:8050
```

The dashboard supports:
- random, mesh, ring, and star topologies
- congestion toggle
- single algorithm analysis
- all-algorithm comparison
- seed-controlled network generation

## Running Tests
Run the unit test suite with:

```powershell
python -m unittest discover -s tests -v
```

## Example Workflows

### Compare all algorithms with reproducible settings
```powershell
python main.py --seed 42 --export outputs/comparison.json
```

In the CLI:
- choose `Random` or another topology
- choose `ALL` for algorithm selection

### Launch the dashboard for visual demos
```powershell
python main.py --mode dashboard
```

## Metrics Reported
The simulator reports:
- execution time
- successful routes
- packet delivery ratio
- average latency
- average throughput
- average hop count

## Notes
- CSV and JSON export are available from CLI runs only.
- Dashboard import requires the Dash dependencies from `requirements.txt`.
- If `pytest` is not installed in your active environment, the built-in `unittest` command above is enough to verify the project.
