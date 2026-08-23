"""Generate architecture diagrams for the technical exercise document."""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ASSETS = Path(__file__).parent
DPI = 240


def box(ax, x, y, w, h, text, fc="#E8F0FE", ec="#1A73E8", fontsize=10):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.05,rounding_size=0.1",
        linewidth=1.4, edgecolor=ec, facecolor=fc, clip_on=False,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2, y + h / 2, text,
        ha="center", va="center", fontsize=fontsize,
        multialignment="center", linespacing=1.35, clip_on=False,
    )


def harrow(ax, x1, x2, y, color="#333", linestyle="-", lw=1.4):
    ax.add_patch(
        FancyArrowPatch(
            (x1, y), (x2, y),
            arrowstyle="-|>", mutation_scale=13, linewidth=lw,
            color=color, linestyle=linestyle, clip_on=False,
        )
    )


def varrow(ax, x, y1, y2, color="#333", linestyle="-", lw=1.4):
    ax.add_patch(
        FancyArrowPatch(
            (x, y1), (x, y2),
            arrowstyle="-|>", mutation_scale=13, linewidth=lw,
            color=color, linestyle=linestyle, clip_on=False,
        )
    )


def edge_text(ax, x, y, text, fontsize=8, color="#333"):
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize, color=color)


def save(fig, name):
    path = ASSETS / name
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white", pad_inches=0.25)
    plt.close(fig)
    return path


def problem1_diagram():
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.5)
    ax.axis("off")
    ax.set_title("Problem 1: Usage & Cost Data Flow", fontsize=12, fontweight="bold", pad=12)

    box(ax, 0.2, 2.8, 1.6, 0.9, "Background\nWorkers", fc="#FCE8E6", ec="#D93025", fontsize=9)
    box(ax, 2.3, 2.8, 1.8, 0.9, "llm_usage_events\n(Postgres)", fc="#E6F4EA", ec="#137333", fontsize=9)
    box(ax, 4.6, 2.8, 2.0, 0.9, "Materialized Views\n(daily + workflow rollups)", fc="#E6F4EA", ec="#137333", fontsize=9)
    box(ax, 7.1, 2.8, 1.7, 0.9, "UsageAnalytics\nService", fc="#FFF8E1", ec="#F9AB00", fontsize=9)
    box(ax, 9.0, 2.8, 0.8, 0.9, "FastAPI", fc="#FFF8E1", ec="#F9AB00", fontsize=9)
    box(ax, 0.5, 1.0, 2.0, 0.8, "Provider Billing\n(reconciliation)", fc="#F3E8FD", ec="#9334E6", fontsize=9)
    box(ax, 3.2, 1.0, 2.2, 0.8, "Auth Middleware\n(workspace / org)", fc="#FCE8E6", ec="#D93025", fontsize=9)
    box(ax, 6.2, 1.0, 2.8, 0.8, "React Admin Dashboard\n(shadcn + TanStack Query)", fc="#E8F0FE", ec="#1A73E8", fontsize=9)

    harrow(ax, 1.8, 2.3, 3.25)
    harrow(ax, 4.1, 4.6, 3.25)
    harrow(ax, 6.6, 7.1, 3.25)
    harrow(ax, 8.8, 9.0, 3.25)
    varrow(ax, 9.4, 2.8, 1.8)
    harrow(ax, 7.6, 9.4, 1.4)
    varrow(ax, 2.5, 2.8, 1.8)
    harrow(ax, 1.5, 2.5, 1.4)
    ax.text(5.0, 0.35, "Phase 1: shadow logging  →  Phase 2: rollups + API  →  Phase 3: UI behind feature flag",
            ha="center", fontsize=8, color="#555")
    return save(fig, "problem1_data_flow.png")


def problem3_state_machine():
    """
    Clear layout:
      - Happy path on one horizontal row (left → right)
      - Error branch stacked vertically under 'processing'
      - Recovery paths kept separate with minimal crossing
    """
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")
    ax.set_title("Problem 3: Job Status State Machine", fontsize=13, fontweight="bold", pad=16)

    bw, bh = 1.75, 1.05

    # --- Happy path (top row) ---
    qx, py, cx = 0.6, 5.0, 5.0
    px = (qx + bw + cx) / 2 - bw / 2
    cy = py + bh / 2

    box(ax, qx, py, bw, bh, "queued", fc="#E8F0FE", ec="#1A73E8")
    box(ax, px, py, bw + 0.35, bh, "processing\n(lease)", fc="#FFF8E1", ec="#F9AB00", fontsize=9)
    box(ax, cx, py, bw, bh, "completed", fc="#E6F4EA", ec="#137333")

    harrow(ax, qx + bw, px, cy)
    harrow(ax, px + bw + 0.35, cx, cy)
    edge_text(ax, (qx + bw + px) / 2, cy + 0.42, "claim (Postgres)")
    edge_text(ax, (px + bw + 0.35 + cx) / 2, cy + 0.42, "blob write + Postgres update")

    # --- Error branch (below processing) ---
    pcx = px + (bw + 0.35) / 2
    fx, fy = pcx - bw / 2, 3.15
    dx, dy = pcx - bw / 2, 1.55

    box(ax, fx, fy, bw, bh, "failed", fc="#FCE8E6", ec="#D93025")
    box(ax, dx, dy, bw + 0.2, bh, "DLQ\n(max retries)", fc="#F3E8FD", ec="#9334E6", fontsize=9)

    varrow(ax, pcx, py, fy + bh)
    edge_text(ax, pcx + 0.55, (py + fy + bh) / 2, "transient error")

    varrow(ax, pcx, fy, dy + bh)
    edge_text(ax, pcx + 0.55, (fy + dy + bh) / 2, "max retries")

    # --- Reconcile: failed → completed (dashed, arcs above happy path) ---
    ax.add_patch(
        FancyArrowPatch(
            (fx + bw, fy + bh * 0.65), (cx + bw * 0.5, py),
            arrowstyle="-|>", mutation_scale=13, linewidth=1.3,
            color="#137333", linestyle="--",
            connectionstyle="arc3,rad=-0.25", clip_on=False,
        )
    )
    edge_text(ax, 6.55, 4.55, "reconcile if\nblob exists", color="#137333")

    # --- Retry: failed → queued (simple left-side path, no crossing) ---
    left_x = 0.25
    retry_y = 2.35
    ax.plot([fx, left_x, left_x, qx + bw * 0.5], [fy + bh * 0.35, fy + bh * 0.35, retry_y, retry_y],
            color="#666", linewidth=1.3, clip_on=False)
    ax.add_patch(
        FancyArrowPatch(
            (qx + bw * 0.5, retry_y), (qx + bw * 0.5, py),
            arrowstyle="-|>", mutation_scale=13, linewidth=1.3, color="#666", clip_on=False,
        )
    )
    edge_text(ax, 1.55, retry_y - 0.28, "retry / Check Again", color="#555")

    # --- Legend strip ---
    ax.text(
        0.5, 0.95,
        "Postgres = source of truth   ·   Redis = UI cache   ·   Blob keyed by job_id",
        fontsize=8.5, color="#444",
    )
    ax.text(
        0.5, 0.55,
        "UI: Retry + Check Again   ·   /retry returns existing result if job already completed",
        fontsize=8.5, color="#444",
    )

    return save(fig, "problem3_state_machine.png")


def local_demo_architecture():
    """Architecture from the local demo MVP plan (Plan mode)."""
    fig, ax = plt.subplots(figsize=(10.5, 4.2))
    ax.set_xlim(0, 10.5)
    ax.set_ylim(0, 4.2)
    ax.axis("off")
    ax.set_title("Local OmniView demo architecture (from Plan)", fontsize=13, fontweight="bold", pad=14)

    box(ax, 0.25, 2.55, 2.1, 1.0, "frontend\nVite + React", fc="#E8F0FE", ec="#1A73E8")
    box(ax, 3.0, 2.55, 2.2, 1.0, "backend\nFastAPI", fc="#FFF8E1", ec="#F9AB00")
    box(ax, 5.9, 2.85, 1.9, 0.7, "Postgres", fc="#E6F4EA", ec="#137333", fontsize=9)
    box(ax, 8.3, 2.85, 1.9, 0.7, "Redis\ncache + queue", fc="#FCE8E6", ec="#D93025", fontsize=9)

    box(ax, 3.0, 0.85, 2.2, 1.0, "worker\nPython", fc="#F3E8FD", ec="#9334E6")
    box(ax, 5.9, 0.85, 1.9, 0.8, "local blobs\n{job_id}.json", fc="#E8F0FE", ec="#1A73E8", fontsize=9)
    box(ax, 8.3, 0.85, 1.9, 0.8, "llm_usage_events", fc="#E6F4EA", ec="#137333", fontsize=9)

    harrow(ax, 2.35, 3.0, 3.05)
    harrow(ax, 5.2, 5.9, 3.2)
    harrow(ax, 5.2, 8.3, 2.95)
    varrow(ax, 4.1, 2.55, 1.85)
    harrow(ax, 5.2, 5.9, 1.35)
    harrow(ax, 5.2, 8.3, 1.15)

    ax.text(5.25, 0.25, "Postgres = source of truth   ·   Redis = UI cache + queue   ·   no Azure credentials in this demo",
            ha="center", fontsize=8, color="#555")
    return save(fig, "local_demo_architecture.png")


if __name__ == "__main__":
    print(problem1_diagram())
    print(problem3_state_machine())
    print(local_demo_architecture())
