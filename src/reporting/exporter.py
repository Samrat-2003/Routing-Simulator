import csv
import os
import tempfile
from datetime import datetime

os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "routing-simulator-mpl"))
os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


def _ensure_output_dir(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def _write_csv(path, network_state, simulation_state, recommendations):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["section", "key", "value"])

        for key, value in (network_state or {}).items():
            if key in {"import_data"}:
                continue
            writer.writerow(["scenario", key, value])

        if simulation_state.get("mode") == "all":
            for algorithm, metrics in simulation_state.get("comparison", {}).items():
                writer.writerow(["comparison", algorithm, metrics["packet_delivery_ratio"]])
        else:
            results = simulation_state.get("results", {})
            for key in [
                "algorithm",
                "execution_time",
                "successful_routes",
                "dropped_flows",
                "total_flows",
                "packet_delivery_ratio",
                "average_latency",
                "average_throughput",
                "average_hop_count",
                "average_utilization",
                "max_utilization",
                "congested_edges",
            ]:
                writer.writerow(["metrics", key, results.get(key)])

            for edge in results.get("edge_loads", {}).values():
                writer.writerow(
                    [
                        "edge_load",
                        f"{edge['u']}-{edge['v']}",
                        f"load={edge['load']}, bandwidth={edge['bandwidth']}, ratio={edge['load_ratio']}",
                    ]
                )

        for recommendation in recommendations:
            writer.writerow(["recommendation", recommendation["title"], recommendation["detail"]])


def _pdf_page(pdf, title, lines):
    figure = plt.figure(figsize=(8.27, 11.69))
    figure.patch.set_facecolor("white")
    plt.axis("off")
    plt.text(0.05, 0.96, title, fontsize=18, fontweight="bold", va="top")
    y = 0.90
    for line in lines:
        plt.text(0.05, y, line, fontsize=11, va="top", wrap=True)
        y -= 0.045
        if y <= 0.08:
            pdf.savefig(figure, bbox_inches="tight")
            plt.close(figure)
            figure = plt.figure(figsize=(8.27, 11.69))
            figure.patch.set_facecolor("white")
            plt.axis("off")
            y = 0.95
    pdf.savefig(figure, bbox_inches="tight")
    plt.close(figure)


def _write_pdf(path, network_state, simulation_state, recommendations):
    lines = [
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Network source: {(network_state or {}).get('source_label', 'generated')}",
        f"Scenario failures: {(network_state or {}).get('failure_profile', {})}",
    ]

    if simulation_state.get("mode") == "all":
        lines.append("Comparison mode:")
        for algorithm, metrics in simulation_state.get("comparison", {}).items():
            lines.append(
                f"- {algorithm}: PDR {metrics['packet_delivery_ratio']:.0%}, latency {metrics['average_latency']:.2f}, throughput {metrics['average_throughput']:.2f}"
            )
    else:
        results = simulation_state.get("results", {})
        lines.extend(
            [
                f"Algorithm: {results.get('algorithm', 'N/A')}",
                f"Packet delivery ratio: {results.get('packet_delivery_ratio', 0):.0%}",
                f"Average latency: {results.get('average_latency', 0):.2f}",
                f"Average throughput: {results.get('average_throughput', 0):.2f}",
                f"Average utilization: {results.get('average_utilization', 0):.2f}",
                f"Max utilization: {results.get('max_utilization', 0):.2f}",
            ]
        )
        for edge in sorted(results.get("edge_loads", {}).values(), key=lambda item: item["load_ratio"], reverse=True)[:5]:
            lines.append(
                f"- Edge {edge['u']}-{edge['v']}: load {edge['load']:.2f}, bandwidth {edge['bandwidth']:.0f}, ratio {edge['load_ratio']:.2f}"
            )

    lines.append("Recommendations:")
    for recommendation in recommendations:
        lines.append(f"- [{recommendation['priority'].upper()}] {recommendation['title']}: {recommendation['detail']}")

    with PdfPages(path) as pdf:
        _pdf_page(pdf, "Routing Scenario Report", lines)


def export_simulation_bundle(network_state, simulation_state, recommendations, output_dir="reports"):
    if not simulation_state:
        return None

    output_dir = _ensure_output_dir(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.abspath(os.path.join(output_dir, f"routing_report_{timestamp}.csv"))
    pdf_path = os.path.abspath(os.path.join(output_dir, f"routing_report_{timestamp}.pdf"))

    _write_csv(csv_path, network_state, simulation_state, recommendations)
    _write_pdf(pdf_path, network_state, simulation_state, recommendations)

    return {"csv_path": csv_path, "pdf_path": pdf_path}
