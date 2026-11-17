"""Comparison charts and their table: speed and robustness against measured S:N.

Inputs per campaign folder (all written by hfbench itself):
  runsheet.csv  - modem, version, profile, payload set, IONOS setting per run
  runs.csv      - `hfbench results`: outcome, delivered/attempted, bytes, session time
  messages.csv  - `hfbench results`: per-message batch transfer rate (and the older goodput)
  snr.csv       - `hfbench audio listen-report --runs` (or scripts/*_snr.py): measured data S:N per run
  crest.csv     - optional, scripts/crest_report.py: the sender's transmitted PAPR per run

A *point* is one modem x profile x payload set x IONOS setting, pooled over its
replicates. Its x value is the median measured data S:N of those runs.

Charts (one per metric and profile; one y axis each). Reporting set by the operator,
17 Nov 2026: net throughput is the headline (what an operator sees), the transfer rate
and the time to connect are shown beside it.
  net         - net throughput: delivered bytes x 8 / total session time (headline)
  rate        - transfer rate per proposal batch (results.py): median, min-max range
  success     - delivered / attempted messages (cut-by-time-box excluded)
  connect     - time to connect (caller's "Calling" to connected), median

Two views of the S:N axis:
  equal average power (D5, as tested): x = measured data S:N
  equal peak power (a peak-limited transmitter): x = measured S:N - (PAPR - 3.0 dB),
    PAPR = the sender's transmitted peak-to-average ratio at 0.01 % (crest.csv), so a
    modem is placed where it would sit if driven to the same peak as a constant-
    envelope (sine-like, 3.0 dB) signal. Charts *-peak-*; only points with a PAPR.

Encoding (dataviz method): one fixed categorical slot per modem (never cycled),
2 px lines, 8 px markers, filled = Text_50KB and open = Text_5KB (secondary
encoding, explained in the legend), direct labels at each line's end, a recessive
grid, and the bench ceiling marked. points.csv is the table view of every chart.
"""

from __future__ import annotations

import csv
import statistics as stats
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Validated categorical palette (dataviz reference, light mode), in fixed slot order.
# Modems keep their slot in every chart, whatever subset is plotted.
MODEM_SLOTS = ["ARDOP 1.0.2.9", "VARA HF", "Data2G", "Mercury", "ARDOP 1.0.3", "Modem73", "Aether HF", "ULTRA"]
SLOT_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"

# Fewer data bursts than this in a run's S:N reading and the run gives no x value
# (e.g. sweep-ardop-5k-0012: 5 bursts, recorder ended 27 min into the run).
MIN_SNR_BURSTS = 30


def modem_color(label: str) -> str:
    for i, name in enumerate(MODEM_SLOTS):
        if label.startswith(name):
            return SLOT_COLORS[i]
    raise ValueError(f"{label!r} has no fixed color slot; add it to MODEM_SLOTS (never cycle colors)")


@dataclass
class Point:
    modem: str
    profile: str
    payload: str
    setting_db: float
    snr_db: float | None = None          # median measured data S:N
    snr_runs: int = 0
    runs: int = 0
    attempted: int = 0
    delivered: int = 0
    success: float | None = None
    goodput_median: float | None = None  # older receiver window: table only, not charted
    rate_median: float | None = None
    rate_min: float | None = None
    rate_max: float | None = None
    connect_s: float | None = None
    papr_db: float | None = None          # sender's transmitted PAPR at 0.01 % (median over runs)
    snr_peak_db: float | None = None      # x at equal peak power: snr_db - (papr_db - 3.0)
    net_bps: float | None = None
    session_min: float = 0.0
    outcomes: str = ""
    run_ids: list[str] = field(default_factory=list)


def _read(p: Path) -> list[dict]:
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_points(campaign_dirs: list[str | Path]) -> list[Point]:
    groups: dict[tuple, dict] = {}
    for d in map(Path, campaign_dirs):
        sheet = {r["run_id"]: r for r in _read(d / "runsheet.csv")}
        runs = _read(d / "runs.csv")
        if not runs:
            raise FileNotFoundError(f"{d / 'runs.csv'} missing: run `hfbench results -d {d}` first")
        snr = {r["run_id"]: r for r in _read(d / "snr.csv")}
        crest = {r["run_id"]: r for r in _read(d / "crest.csv")}
        msgs: dict[str, list[dict]] = {}
        for m in _read(d / "messages.csv"):
            msgs.setdefault(m["run_id"], []).append(m)
        for r in runs:
            s = sheet[r["run_id"]]
            key = (f"{s['modem']} {s['modem_version']}", s["profile"], s["payload_file"], float(s["snr_db"]))
            g = groups.setdefault(key, {"runs": [], "snr": [], "good": [], "rate": [], "conn": [], "papr": [],
                                        "outcomes": []})
            g["runs"].append(r)
            g["outcomes"].append(r["outcome"])
            sr = snr.get(r["run_id"], {})
            # a run only partly inside a recording gives too few bursts to trust
            if sr.get("data_snr_db") and int(sr.get("data_n") or 0) >= MIN_SNR_BURSTS:
                g["snr"].append(float(sr["data_snr_db"]))
            g["good"] += [float(m["goodput_bps"]) for m in msgs.get(r["run_id"], [])
                          if m["status"] == "delivered" and m.get("goodput_bps")]
            g["rate"] += [float(m["rate_bps"]) for m in msgs.get(r["run_id"], [])
                          if m["status"] == "delivered" and m.get("rate_bps")]
            if r.get("connect_s"):
                g["conn"].append(float(r["connect_s"]))
            c = crest.get(r["run_id"], {})
            if c.get("st2_papr_0.01pct_db"):
                g["papr"].append(float(c["st2_papr_0.01pct_db"]))
    points = []
    for (modem, prof, payload, setting), g in sorted(groups.items()):
        att = sum(int(r["attempted"]) for r in g["runs"])
        dl = sum(int(r["delivered"]) for r in g["runs"])
        secs = sum(int(r["session_s"]) for r in g["runs"] if r["session_s"])
        byt = sum(int(r["delivered_bytes"]) for r in g["runs"])
        points.append(Point(
            modem, prof, payload, setting,
            snr_db=stats.median(g["snr"]) if g["snr"] else None, snr_runs=len(g["snr"]),
            runs=len(g["runs"]), attempted=att, delivered=dl,
            success=dl / att if att else None,
            goodput_median=stats.median(g["good"]) if g["good"] else None,
            rate_median=stats.median(g["rate"]) if g["rate"] else None,
            rate_min=min(g["rate"]) if g["rate"] else None,
            rate_max=max(g["rate"]) if g["rate"] else None,
            connect_s=stats.median(g["conn"]) if g["conn"] else None,
            papr_db=stats.median(g["papr"]) if g["papr"] else None,
            net_bps=byt * 8 / secs if secs else None, session_min=round(secs / 60, 1),
            outcomes=" ".join(g["outcomes"]), run_ids=[r["run_id"] for r in g["runs"]]))
    for p in points:
        if p.snr_db is not None and p.papr_db is not None:
            p.snr_peak_db = round(p.snr_db - (p.papr_db - 3.0), 2)
    return points


def write_table(points: list[Point], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        fields = [k for k in Point.__dataclass_fields__]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for p in points:
            row = asdict(p)
            row["run_ids"] = " ".join(p.run_ids)
            w.writerow(row)
    return path


METRICS = {
    "net": ("Net throughput", "bit/s (delivered bytes x 8 / total session time)"),
    "rate": ("Transfer rate per message batch", "bit/s (receiver's FS to last message received; median and range)"),
    "success": ("Messages delivered", "% of messages attempted"),
    "connect": ("Time to connect", "seconds (Calling to connected, median)"),
}
VIEWS = {
    "": ("snr_db", "Measured data-frame S:N (dB, 3 kHz), equal average power"),
    "peak-": ("snr_peak_db", "S:N at equal PEAK power (dB): measured S:N minus PAPR above a sine's 3 dB"),
}


def plot(points: list[Point], out_dir: str | Path, *, ceiling_db: float | None = None,
         subtitle: str = "") -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = []
    for view, (xattr, xlabel) in VIEWS.items():
      plotted = [p for p in points if getattr(p, xattr) is not None]
      for prof in sorted({p.profile for p in plotted}):
        for metric, (title, ylabel) in METRICS.items():
            fig, ax = plt.subplots(figsize=(8, 4.8), dpi=150)
            fig.patch.set_facecolor(SURFACE)
            ax.set_facecolor(SURFACE)
            modems = [m for m in MODEM_SLOTS if any(p.modem.startswith(m) for p in plotted if p.profile == prof)]
            ymax = 0.0
            for name in modems:
                pts = sorted((p for p in plotted if p.profile == prof and p.modem.startswith(name)),
                             key=lambda p: getattr(p, xattr))
                col = modem_color(name)
                xs, ys = [], []
                for p in pts:
                    y = {"rate": p.rate_median, "net": p.net_bps, "connect": p.connect_s,
                         "success": None if p.success is None else 100 * p.success}[metric]
                    if y is None:
                        continue
                    x = getattr(p, xattr)
                    xs.append(x)
                    ys.append(y)
                    if metric == "rate" and p.rate_min is not None:
                        ax.plot([x, x], [p.rate_min, p.rate_max], color=col, lw=1.2,
                                solid_capstyle="round", zorder=2)
                        ymax = max(ymax, p.rate_max)
                    small = p.payload.endswith("5KB")
                    ax.plot([x], [y], marker="o", ms=7, mew=2, color=col,
                            mfc=SURFACE if small else col, mec=col, zorder=4)
                    ymax = max(ymax, y)
                if xs:
                    ax.plot(xs, ys, color=col, lw=2, zorder=3, solid_joinstyle="round")
                    ax.annotate(pts[0].modem if len({p.modem for p in pts}) == 1 else name,
                                (xs[-1], ys[-1]), xytext=(6, 0), textcoords="offset points",
                                va="center", fontsize=9, color=INK)
            if ceiling_db is not None and not view:
                ax.axvline(ceiling_db, color=INK2, lw=1, ls=(0, (4, 3)), zorder=1)
                # at the foot of the line: the top is where the best points sit
                ax.annotate(f"bench ceiling ~{ceiling_db:.0f} dB", (ceiling_db, 0), xycoords=("data", "axes fraction"),
                            xytext=(-4, 4), textcoords="offset points", ha="right", va="bottom", fontsize=8, color=INK2)
            ax.set_ylim(0, 105 if metric == "success" else max(ymax * 1.12, 1))
            ax.set_xlabel(xlabel, color=INK2, fontsize=9)
            ax.set_ylabel(ylabel, color=INK2, fontsize=9)
            ax.set_title(f"{title}, {prof}" + (", equal peak power" if view else "")
                         + (f"\n{subtitle}" if subtitle else ""), loc="left", fontsize=11,
                         color=INK)
            ax.grid(True, color=GRID, lw=0.8)
            ax.set_axisbelow(True)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            for side in ("left", "bottom"):
                ax.spines[side].set_color(GRID)
            ax.tick_params(colors=INK2, labelsize=8)
            # Legend below the plot so it never sits on data. One modem: the title and
            # the direct label name it, so only the payload key is needed.
            handles = []
            if len(modems) > 1:
                handles += [Line2D([], [], color=modem_color(m), lw=2, marker="o", ms=7,
                                   label=next(p.modem for p in plotted if p.modem.startswith(m))) for m in modems]
            present = {p.payload for p in plotted if p.profile == prof}
            if "Text_50KB" in present:
                handles.append(Line2D([], [], ls="", marker="o", ms=7, color=INK2, label="Text_50KB (10 x 50 KB)"))
            if "Text_5KB" in present:
                handles.append(Line2D([], [], ls="", marker="o", ms=7, mew=2, mfc=SURFACE, color=INK2,
                                      label="Text_5KB (10 x 5 KB)"))
            if handles:
                fig.legend(handles=handles, loc="lower center", ncol=min(len(handles), 4), fontsize=8,
                           frameon=False, labelcolor=INK, bbox_to_anchor=(0.5, 0.0))
            fig.tight_layout(rect=(0, 0.07 if handles else 0, 1, 1))
            for ext in ("png", "svg"):
                f = out / f"{view}{metric}-{prof.lower()}.{ext}"
                fig.savefig(f, facecolor=SURFACE)
                files.append(f)
            plt.close(fig)
    return files
