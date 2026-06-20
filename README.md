# Routing Simulator

A Python-based network routing simulator for generating topologies, routing traffic flows, comparing routing algorithms, visualizing congestion, and exporting simulation reports.

The project is designed for final-year experimentation and demos. It includes an interactive command-line workflow, a Dash web dashboard, reproducible seeded runs, scenario import, failure modeling, congestion-aware metrics, and PDF/CSV reporting.

## Features

- Generate random, mesh, ring, and star network topologies.
- Compare Dijkstra, Bellman-Ford, PCA-MR, Ant Colony Optimization (ACO), and Genetic Algorithm (GA) routing.
- Simulate low, medium, high, or custom traffic loads.
- Use random seeds for repeatable topology, traffic, and stochastic algorithm behavior.
- Model congestion using link bandwidth and packet size.
- Apply scenario failures, including down nodes, down links, packet-loss zones, and maintenance cost multipliers.
- Import network and traffic scenarios from JSON or CSV files in the dashboard.
- Export CLI results to JSON or CSV.
- Export dashboard reports to PDF and CSV.
- Generate practical recommendations from simulation metrics.

## Project Structure

```text
.
|-- main.py                       # CLI entry point and dashboard launcher
|-- requirements.txt              # Python dependencies
|-- config/
|   `-- config.json               # Default topology, traffic, and simulation settings
|-- backend/                       # Flask backend connecting Dashboard to backend server
|   |--server.py
|-- src/
|   |-- algorithms/routing.py      # Dijkstra, Bellman-Ford, PCA-MR, ACO, and GA implementations
|   |-- dashboard                  # Dash web dashboard
|   |   |--app.py
|   |   |--config.py
|   |   |--api_client.py           # Helper file handling  REST APIs
|   |-- metrics/analyzer.py        # Latency, throughput, PDR, congestion, and load metrics
|   |-- network/topology.py        # Topology generation, import, and failure profiles
|   |-- planning/recommendations.py# Capacity and resilience recommendations
|   |-- reporting/exporter.py      # Dashboard PDF/CSV report export
|   `-- traffic/generator.py       # Random and imported traffic flows
|-- reports/                       # Generated dashboard reports
`-- tests/                         # Unit tests
`--test.http                       #APis Testing
```

## Requirements

- Python 3.10 or newer
- pip

Python packages are listed in `requirements.txt`:

- networkx
- pandas
- numpy
- dash
- plotly
- pytest
- matplotlib

## Installation

From the project root:

```powershell
python -m pip install -r requirements.txt
```

On Windows, if your Python launcher is `py`, use:

```powershell
py -3 -m pip install -r requirements.txt
```

Optional virtual environment setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Running the CLI

Start the interactive simulator:

```powershell
python main.py
```

The CLI prompts for:

- topology type
- number of nodes
- edge probability for random topologies
- routing algorithm
- traffic intensity

Use a seed for reproducible runs:

```powershell
python main.py --seed 42
```

Export CLI results to JSON:

```powershell
python main.py --seed 42 --export outputs/results.json
```

Export CLI results to CSV:

```powershell
python main.py --seed 42 --export outputs/results.csv
```

To compare all algorithms from the CLI, choose `ALL` when prompted for the routing algorithm.

## Running the backend server

Launch the server:
```powershell
python backend/server.py
```

The server runs on:
```test
http://localhost:5000
```

The backend server handles:

- Network topology generation
- Routing simulations
- Algorithm comparison
- Recommendation generation
- Report generation
- REST API endpoints for dashboard communication

Note: Keep the backend server running before starting the dashboard.

## Running the Dashboard

Launch the Dash dashboard:

```powershell
python main.py --mode dashboard
```

Then open:

```text
http://localhost:8050
```

The dashboard provides:

- topology generation with seed control
- JSON/CSV scenario import
- manual and random failure profiles
- congestion simulation toggle
- single-algorithm analysis
- all-algorithm comparison and ranking
- link-stress visualization
- flow-level delivery details
- capacity and resilience recommendations
- PDF and CSV report export into `reports/`

## Scenario Import

The dashboard can import JSON or CSV files.

JSON scenarios may include:

```json
{
  "nodes": [{"id": 0}, {"id": 1}],
  "edges": [{"source": 0, "target": 1, "weight": 2, "bandwidth": 100}],
  "flows": [{"source": 0, "destination": 1, "size": 250, "count": 5}]
}
```

CSV imports are detected by their columns:

- node files: `id` or `node_id`
- edge files: `source,target`
- traffic files: `source,destination`

Traffic records can include `size`, `packet_size`, `count`, or `demand`.

## Metrics Reported

Each simulation can report:

- execution time
- successful routes and dropped flows
- packet delivery ratio
- average latency
- average throughput
- average hop count
- average and maximum utilization
- congested edge count
- per-edge load, bandwidth, load ratio, and packet-loss value
- per-flow route and delivery details

## Algorithms

| Algorithm | Purpose |
| --- | --- |
| Dijkstra | Deterministic shortest-path routing using edge weights. |
| Bellman-Ford | Shortest-path routing with repeated edge relaxation. |
| PCA-MR | Proposed Predictive Congestion-Aware Multipath Routing using normalized cost, logarithmic loss penalty, and link load ratio. |
| ACO | Stochastic path optimization using pheromone trails and edge-cost heuristics. |
| GA | Stochastic route search using population selection, crossover, mutation, and repair. |

## Proposed Algorithm: PCA-MR

PCA-MR, or Predictive Congestion-Aware Multipath Routing, is the proposed algorithm in this project. Instead of selecting a route only by shortest distance, it computes a dynamic link score:

```text
psi(u,v,t) = alpha * normalized_weight(u,v)
           + beta  * [-ln(1 - loss(u,v,t))]
           + gamma * load_ratio(u,v,t)
```

Where:

- `normalized_weight` represents the base delay or distance of the link.
- `loss` represents current packet-loss probability on the link or adjacent nodes.
- `load_ratio` represents projected traffic load divided by available bandwidth.
- `alpha`, `beta`, and `gamma` control the importance of distance, reliability, and congestion.

The logarithmic loss term sharply penalizes unreliable links as packet loss rises. PCA-MR also remembers previously routed demand and smooths link scores over time, so later flows are pushed away from congested or lossy links. This makes it strongest in scenarios with high traffic, packet-loss zones, bandwidth limits, or maintenance-degraded links.

## Configuration

Default values live in `config/config.json`.

Current configuration groups:

- `network`: default topology, node count, and random edge probability
- `traffic`: default traffic intensity and flow counts
- `simulation`: default algorithm and iteration settings

The interactive CLI asks for most runtime values directly. The dashboard exposes its own controls for topology, traffic, seed, failures, and algorithm selection.

## Reports and Outputs

CLI exports are written to the path supplied through `--export`. The path must end in `.json` or `.csv`.

Dashboard report exports are generated in `reports/` as timestamped files:

```text
routing_report_YYYYMMDD_HHMMSS.csv
routing_report_YYYYMMDD_HHMMSS.pdf
```

## Running Tests

Run the unit test suite with:

```powershell
python -m unittest discover -s tests -v
```

If you prefer pytest:

```powershell
python -m pytest
```

## Example Workflows

Run a reproducible CLI comparison:

```powershell
python main.py --seed 42 --export outputs/comparison.json
```

Then choose a topology and select `ALL` for the algorithm.

Run a visual dashboard demo:

```powershell
python main.py --mode dashboard
```

Generate a network, enable congestion, run `ALL`, inspect the ranking, and export the report.

## Notes

- Random topologies fall back to a connected graph if the initial Erdos-Renyi graph is disconnected.
- ACO and GA are stochastic; use `--seed` or the dashboard seed field for repeatable experiments.
- Congestion simulation increases effective link cost as load approaches or exceeds bandwidth.
- Dashboard reports include recommendations based on utilization, delivery ratio, comparison scores, and failure profile data.
