#!/usr/bin/env python3
"""
Generate every graph used in the report from the recorded measurements.

The experiment: php-apache with a CPU *request* (100m) but NO CPU limit, idle vs under load.

Inputs  (relative to the repo root):
    data/results.csv               idle vs. load summary (kubectl top)
    data/readings_under_load.csv   successive kubectl top readings under load

Outputs:
    graphs/*.png                   one file per graph + graphs/00_summary.png

Usage:
    pip install -r analysis/requirements.txt
    python analysis/plot_results.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "graphs"
OUT.mkdir(exist_ok=True)

# Resource settings from manifests/php-apache.yaml (there is no CPU limit)
CPU_REQUEST_M = 100
MEM_REQUEST_MI, MEM_LIMIT_MI = 64, 128

# Palette
C_IDLE = "#1F9D6B"
C_LOAD = "#D98E04"
C_REQ = "#6B7280"
C_LIMIT = "#D93A40"
C_NODE_CPU = "#7C5CE0"
C_NODE_MEM = "#0E7490"
C_LOADGEN = "#9CA3AF"

plt.rcParams.update({
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.axisbelow": True,
    "figure.facecolor": "white",
})

results = pd.read_csv(DATA / "results.csv")
readings = pd.read_csv(DATA / "readings_under_load.csv")


def val(stage, col):
    row = results[results.stage == stage]
    return float(row[col].iloc[0])


def label_bars(ax, bars, fmt="{:g}"):
    for b in bars:
        ax.annotate(fmt.format(b.get_height()), (b.get_x() + b.get_width() / 2, b.get_height()),
                    ha="center", va="bottom", fontsize=10, xytext=(0, 3), textcoords="offset points")


def idle_load_bars(ax, idle, load, fmt="{:g}"):
    bars = ax.bar(["Idle", "Under load"], [idle, load], width=0.5, color=[C_IDLE, C_LOAD])
    label_bars(ax, bars, fmt)


# ---------------------------------------------------------------- graph 1
def g_pod_cpu(ax):
    idle_load_bars(ax, val("idle", "pod_cpu_m"), val("load", "pod_cpu_m"), "{:g}m")
    ax.axhline(CPU_REQUEST_M, color=C_REQ, ls=":", lw=1.4)
    ax.text(-0.45, CPU_REQUEST_M + 18, f"CPU request {CPU_REQUEST_M}m (no CPU limit set)", color=C_REQ, fontsize=10)
    ax.set_ylim(0, 1150)
    ax.set_ylabel("CPU (millicores)")
    ax.set_title("Pod CPU: idle vs under load (php-apache)")


# ---------------------------------------------------------------- graph 2
def g_pod_mem(ax):
    idle_load_bars(ax, val("idle", "pod_mem_mi"), val("load", "pod_mem_mi"), "{:g}Mi")
    ax.axhline(MEM_LIMIT_MI, color=C_LIMIT, ls="--", lw=1.4)
    ax.axhline(MEM_REQUEST_MI, color=C_REQ, ls=":", lw=1.4)
    ax.text(-0.45, MEM_LIMIT_MI + 3, f"memory limit {MEM_LIMIT_MI}Mi", color=C_LIMIT, fontsize=10)
    ax.text(-0.45, MEM_REQUEST_MI + 3, f"memory request {MEM_REQUEST_MI}Mi", color=C_REQ, fontsize=10)
    ax.set_ylim(0, 150)
    ax.set_ylabel("Memory (MiB)")
    ax.set_title("Pod memory: idle vs under load (php-apache)")


# ---------------------------------------------------------------- graph 3
def g_node(ax):
    labels = ["Idle", "Under load"]
    cpu = [val("idle", "node_cpu_pct"), val("load", "node_cpu_pct")]
    mem = [val("idle", "node_mem_pct"), val("load", "node_mem_pct")]
    cpu_m = [val("idle", "node_cpu_m"), val("load", "node_cpu_m")]
    x = range(2)
    w = 0.36
    b1 = ax.bar([i - w / 2 for i in x], cpu, w, color=C_NODE_CPU, label="Node CPU %")
    b2 = ax.bar([i + w / 2 for i in x], mem, w, color=C_NODE_MEM, label="Node memory %")
    for b, m in zip(b1, cpu_m):
        ax.annotate(f"{b.get_height():g}%\n({m:g}m)", (b.get_x() + b.get_width() / 2, b.get_height()),
                    ha="center", va="bottom", fontsize=10, xytext=(0, 3), textcoords="offset points")
    label_bars(ax, b2, "{:g}%")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 30)
    ax.set_ylabel("Utilisation (%)")
    ax.set_title("Node: CPU rises with the load, memory stays flat")
    ax.legend(loc="upper left", frameon=False)


# ---------------------------------------------------------------- graph 4
def g_readings(ax):
    x = readings["label"]
    ax.plot(x, readings["pod_cpu_m"], marker="o", lw=2.2, color=C_LOAD, label="php-apache (kubectl top)")
    ax.plot(x, readings["loadgen_cpu_m"], marker="s", lw=1.8, color=C_LOADGEN, label="load-generator (kubectl top)")
    ax.axhline(CPU_REQUEST_M, color=C_REQ, ls=":", lw=1.4)
    ax.text(0.02, CPU_REQUEST_M + 18, f"CPU request {CPU_REQUEST_M}m", color=C_REQ, fontsize=10)
    for xi, yi in zip(x, readings["pod_cpu_m"]):
        ax.annotate(f"{yi:g}m", (xi, yi), ha="center", va="bottom", fontsize=10, xytext=(0, 6), textcoords="offset points")
    ax.set_ylim(0, 1150)
    ax.set_ylabel("CPU (millicores)")
    ax.set_title("Pod CPU climbs, then holds steady near one core")
    ax.legend(loc="center right", frameon=False)
    ax.text(0.5, -0.22, "Successive manual readings, not evenly spaced in time",
            transform=ax.transAxes, ha="center", fontsize=9, color="#555")


# ---------------------------------------------------------------- graph 5
def g_req(ax):
    names = ["Usage, idle", "CPU request", "Usage, under load"]
    vals = [val("idle", "pod_cpu_m"), CPU_REQUEST_M, val("load", "pod_cpu_m")]
    colors = [C_IDLE, C_REQ, C_LOAD]
    bars = ax.barh(names, vals, color=colors, height=0.55)
    for b, v in zip(bars, vals):
        ax.annotate(f"{v:g}m", (v, b.get_y() + b.get_height() / 2), va="center", xytext=(6, 0), textcoords="offset points")
    ax.invert_yaxis()
    ax.set_xlim(0, 1150)
    ax.set_xlabel("CPU (millicores)")
    ax.set_title("Observed CPU vs the configured request (no CPU limit)")
    ax.grid(axis="y", visible=False)
    ratio = val("load", "pod_cpu_m") / CPU_REQUEST_M
    ax.text(0.5, -0.2, f"Usage under load is about {ratio:.1f}x the CPU request",
            transform=ax.transAxes, ha="center", fontsize=9, color="#555")


# ---------------------------------------------------------------- graph 6
def g_node_accounting(ax):
    """Where did the node's extra CPU come from? (idle -> steady load)"""
    steady = readings.iloc[-1]
    node_delta = val("load", "node_cpu_m") - val("idle", "node_cpu_m")
    pod_delta = val("load", "pod_cpu_m") - val("idle", "pod_cpu_m")
    lg = float(steady["loadgen_cpu_m"])
    gap = node_delta - pod_delta - lg
    parts = [("php-apache", pod_delta, C_LOAD), ("load-generator", lg, C_LOADGEN)]
    bottom = 0
    for name, v, c in parts:
        ax.bar(["Sum of\npod changes"], [v], bottom=bottom, color=c, width=0.45, label=f"{name}: +{v:g}m")
        bottom += v
    ax.bar(["Node CPU\nincrease"], [node_delta], color=C_NODE_CPU, width=0.45)
    ax.annotate(f"+{node_delta:g}m", (1, node_delta), ha="center", va="bottom", fontsize=10, xytext=(0, 3), textcoords="offset points")
    ax.annotate(f"+{pod_delta + lg:g}m", (0, bottom), ha="center", va="bottom", fontsize=10, xytext=(0, 3), textcoords="offset points")
    ax.text(0.5, -0.2, f"Unexplained difference: {gap:g}m (other node processes, sampling time, rounding)",
            transform=ax.transAxes, ha="center", fontsize=9, color="#555")
    ax.set_ylim(0, 1600)
    ax.set_ylabel("Change in CPU, idle to steady load (millicores)")
    ax.set_title("The node's extra CPU is almost all the two pods")
    ax.legend(loc="upper left", frameon=False)


GRAPHS = [
    ("01_pod_cpu_idle_vs_load.png", g_pod_cpu),
    ("02_pod_memory_idle_vs_load.png", g_pod_mem),
    ("03_node_utilisation.png", g_node),
    ("04_pod_cpu_readings.png", g_readings),
    ("05_cpu_usage_vs_request.png", g_req),
    ("06_node_cpu_accounting.png", g_node_accounting),
]

for fname, fn in GRAPHS:
    fig, ax = plt.subplots(figsize=(8, 5))
    fn(ax)
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=200)
    plt.close(fig)
    print("wrote", OUT / fname)

# Combined overview sheet
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
for ax, (_, fn) in zip(axes.flat, GRAPHS):
    fn(ax)
fig.suptitle("Cluster monitoring with Metrics Server - php-apache with no CPU limit: summary of results",
             fontsize=16, y=0.995)
fig.tight_layout()
fig.savefig(OUT / "00_summary.png", dpi=150)
plt.close(fig)
print("wrote", OUT / "00_summary.png")
