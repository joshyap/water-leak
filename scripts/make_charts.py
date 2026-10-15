"""Leak analysis + README charts as standalone SVGs (no plotting deps needed).

Usage: python scripts/make_charts.py   -> prints the leak estimates, writes docs/charts/*.svg
"""
from pathlib import Path

import pandas as pd

OUT = Path("docs/charts")

# Known events
LANDSCAPING = pd.Timestamp("2026-01-15")  # new lawn installed sometime in January 2026
LEAK_FIXED = pd.Timestamp("2026-09-10")

# Analysis windows
BASELINE_WINDOW = ("2023-02-01", "2026-02-17")  # after the Jan 2023 spike, through the last normal read
SUMMER_WINDOW = ("2026-06-17", "2026-08-17")    # three full periods with the leak and lawn watering running

# Assumptions. Change these to match your utility and yard.
RATE_PER_KGAL = 6.00                   # $ per 1,000 gallons
IRRIGATION_SCENARIOS = [0, 200, 400]   # gal/day assumed for watering the new lawn

# Palette roles; dark values swap in via prefers-color-scheme inside each SVG.
STYLE = """
<style>
  svg { --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
        --grid:#e1e0d9; --axis:#c3c2b7; --s1:#2a78d6; --s2:#eb6834; --wash:rgba(235,104,52,0.10); }
  @media (prefers-color-scheme: dark) {
    svg { --surface:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --muted:#898781;
          --grid:#2c2c2a; --axis:#383835; --s1:#3987e5; --s2:#d95926; --wash:rgba(217,89,38,0.16); }
  }
  text { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; fill: var(--ink2); font-size: 12px; }
  .title { fill: var(--ink); font-size: 16px; font-weight: 600; }
  .tick { fill: var(--muted); font-size: 11px; font-variant-numeric: tabular-nums; }
  .val { fill: var(--ink); font-size: 11px; font-weight: 600; }
  .grid { stroke: var(--grid); stroke-width: 1; }
  .axis { stroke: var(--axis); stroke-width: 1; }
  .s1 { fill: var(--s1); } .s2 { fill: var(--s2); }
  .line2 { fill: none; stroke: var(--s2); stroke-width: 2; stroke-linejoin: round; }
  .ref { stroke: var(--ink2); stroke-width: 1; stroke-dasharray: 4 3; }
  .event { stroke: var(--ink); stroke-width: 1.5; }
  .wash { fill: var(--wash); }
</style>
"""


def load():
    df = pd.read_csv("data/usage_clean.csv", thousands=",", parse_dates=["Reading Date"])
    df = df.dropna(subset=["Customer GPD"]).sort_values("Reading Date").reset_index(drop=True)
    df["Start"] = df["Reading Date"] - pd.to_timedelta(df["Days in Read Period"], unit="D")
    base = df[df["Reading Date"].between(*BASELINE_WINDOW)]
    return df, float(base["Customer GPD"].median())


def estimate(df, baseline):
    """Bound the leak rate, start date and cost under each lawn-watering scenario.

    Monthly reads can't separate lawn watering from the leak, so each scenario
    assumes a watering rate and attributes the rest of the summer's excess to the leak.
    The start date assumes the leak ran at a constant rate and was the only extra use
    in the period ending Mar 17 (the first period above normal).
    """
    summer = df[df["Reading Date"].between(*SUMMER_WINDOW)]
    summer_gpd = summer["Gallons"].sum() / summer["Days in Read Period"].sum()
    first = df[df["Reading Date"] == "2026-03-17"].iloc[0]
    first_excess = first["Gallons"] - baseline * first["Days in Read Period"]
    rows = []
    for irrigation in IRRIGATION_SCENARIOS:
        leak_gpd = summer_gpd - baseline - irrigation
        start = first["Reading Date"] - pd.Timedelta(days=round(first_excess / leak_gpd))
        leak_gal = leak_gpd * (LEAK_FIXED - start).days
        rows.append({
            "irrigation_gpd": irrigation,
            "leak_gpd": leak_gpd,
            "start": start,
            "leak_gal": leak_gal,
            "leak_cost": leak_gal / 1000 * RATE_PER_KGAL,
            "saved_per_month": leak_gpd * 30 / 1000 * RATE_PER_KGAL,
            "saved_per_year": leak_gpd * 365 / 1000 * RATE_PER_KGAL,
        })
    return summer_gpd, pd.DataFrame(rows)


def bar(x, y, w, h, cls, title, top_round=True):
    """Bar anchored to the baseline with a 4px rounded data-end."""
    r = min(4, w / 2, h) if top_round else 0
    d = (f"M{x:.1f},{y + h:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} H{x + w - r:.1f} "
         f"Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} V{y + h:.1f} Z")
    return f'<path class="{cls}" d="{d}"><title>{title}</title></path>'


def svg(w, h, body, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{label}">{STYLE}'
            f'<rect width="{w}" height="{h}" rx="8" fill="var(--surface)"/>{body}</svg>')


def y_axis(x0, x1, y_of, ticks, fmt):
    out = []
    for t in ticks:
        y = y_of(t)
        out.append(f'<line class="{"axis" if t == 0 else "grid"}" x1="{x0}" x2="{x1}" y1="{y:.1f}" y2="{y:.1f}"/>')
        out.append(f'<text class="tick" x="{x0 - 8}" y="{y + 4:.1f}" text-anchor="end">{fmt(t)}</text>')
    return out


def time_scale(t0, t1, x0, x1):
    span = (t1 - t0).total_seconds()
    return lambda t: x0 + (t - t0).total_seconds() / span * (x1 - x0)


def event(x, top, bottom, label, anchor="end"):
    dx = -6 if anchor == "end" else 6
    return (f'<line class="event" x1="{x:.1f}" x2="{x:.1f}" y1="{top}" y2="{bottom}"/>'
            f'<text class="val" x="{x + dx:.1f}" y="{top + 12}" text-anchor="{anchor}">{label}</text>')


def timeline(df, baseline, leak_start):
    occ = df[df["Reading Date"] >= "2022-06-01"]
    W, H, L, R, T, B = 880, 400, 56, 24, 84, 40
    ph, ymax = H - T - B, 2000
    y_of = lambda v: T + ph - v / ymax * ph
    x_of = time_scale(occ["Start"].min(), occ["Reading Date"].max(), L, W - R)
    out = [f'<text class="title" x="{L}" y="30">Daily water use per billing period</text>',
           f'<text x="{L}" y="50">Gallons per day (GPD), Jun 2022 – Sep 2026. Bar width = billing period.</text>',
           f'<rect class="s1" x="{L}" y="60" width="10" height="10" rx="2"/>',
           f'<text x="{L + 16}" y="69">This home</text>',
           f'<line class="line2" x1="{L + 100}" x2="{L + 120}" y1="65" y2="65"/>',
           f'<text x="{L + 126}" y="69">Average household</text>',
           f'<line class="ref" x1="{L + 260}" x2="{L + 280}" y1="65" y2="65"/>',
           f'<text x="{L + 286}" y="69">This home\'s normal ({baseline:.0f} GPD)</text>']
    out.append(f'<rect class="wash" x="{x_of(leak_start):.1f}" y="{T}" '
               f'width="{x_of(LEAK_FIXED) - x_of(leak_start):.1f}" height="{ph}"/>')
    out += y_axis(L, W - R, y_of, range(0, ymax + 1, 500), lambda t: f"{t:,}")
    for _, r in occ.iterrows():
        v = r["Customer GPD"]
        x0, x1 = x_of(r["Start"]) + 1, x_of(r["Reading Date"]) - 1  # 2px gap between periods
        tip = f'{r["Start"]:%b %d} – {r["Reading Date"]:%b %d, %Y}: {v:,.0f} GPD ({r["Gallons"]:,.0f} gal)'
        out.append(bar(x0, y_of(v), x1 - x0, T + ph - y_of(v), "s1", tip))
    pts = " ".join(f'{(x_of(r["Start"]) + x_of(r["Reading Date"])) / 2:.1f},{y_of(r["Average Households GPD"]):.1f}'
                   for _, r in occ.iterrows())
    out.append(f'<polyline class="line2" points="{pts}"/>')
    out.append(f'<line class="ref" x1="{L}" x2="{W - R}" y1="{y_of(baseline):.1f}" y2="{y_of(baseline):.1f}"/>')
    jan23 = occ[occ["Reading Date"] == "2023-01-17"].iloc[0]
    out.append(f'<text class="val" x="{x_of(jan23["Reading Date"]) + 4:.1f}" y="{y_of(jan23["Customer GPD"]) + 10:.1f}">'
               f'Jan 2023: 1,837 GPD</text>')
    out.append(event(x_of(LANDSCAPING), T, T + ph, "Landscaping"))
    out.append(event(x_of(LEAK_FIXED), T, T + ph, "Leak fixed"))
    for y in range(2023, 2027):
        out.append(f'<text class="tick" x="{x_of(pd.Timestamp(f"{y}-01-01")):.1f}" y="{H - B + 18}" '
                   f'text-anchor="middle">{y}</text>')
    return svg(W, H, "".join(out), "Bar chart of daily water use per billing period, with landscaping and leak fix marked")


def zoom_2026(df, baseline, leak_start):
    z = df[df["Reading Date"] >= "2025-12-01"].copy()
    z["normal"] = (baseline * z["Days in Read Period"]).clip(upper=z["Gallons"])
    z["excess"] = z["Gallons"] - z["normal"]
    noise = z["excess"] < 300  # ignore rounding-level excess
    z.loc[noise, "normal"] = z.loc[noise, "Gallons"]
    z.loc[noise, "excess"] = 0
    W, H, L, R, T, B = 880, 380, 64, 24, 84, 40
    ph, ymax = H - T - B, 45000
    y_of = lambda v: T + ph - v / ymax * ph
    x_of = time_scale(z["Start"].min(), z["Reading Date"].max(), L, W - R)
    out = [f'<text class="title" x="{L}" y="30">2026: gallons per billing period, normal vs. above normal</text>',
           f'<text x="{L}" y="50">Normal = {baseline:.0f} GPD × days. Above normal = lawn watering + leak; '
           f'the meter can\'t tell them apart.</text>',
           f'<rect class="s1" x="{L}" y="60" width="10" height="10" rx="2"/><text x="{L + 16}" y="69">Normal use</text>',
           f'<rect class="s2" x="{L + 100}" y="60" width="10" height="10" rx="2"/>'
           f'<text x="{L + 116}" y="69">Above normal</text>',
           f'<rect class="wash" x="{L + 220}" y="60" width="10" height="10" rx="2"/>'
           f'<text x="{L + 236}" y="69">Estimated leak window</text>']
    out.append(f'<rect class="wash" x="{x_of(leak_start):.1f}" y="{T}" '
               f'width="{x_of(LEAK_FIXED) - x_of(leak_start):.1f}" height="{ph}"/>')
    out += y_axis(L, W - R, y_of, range(0, 40001, 10000), lambda t: f"{t // 1000}k" if t else "0")
    for _, r in z.iterrows():
        x0, x1 = x_of(r["Start"]) + 4, x_of(r["Reading Date"]) - 4
        w = x1 - x0
        yn, ye = y_of(r["normal"]), y_of(r["Gallons"])
        has_excess = r["excess"] > 0
        out.append(bar(x0, yn, w, T + ph - yn, "s1", f'Normal: {r["normal"]:,.0f} gal', top_round=not has_excess))
        if has_excess:
            out.append(bar(x0, ye, w, yn - ye - 2, "s2", f'Above normal: {r["excess"]:,.0f} gal'))
        out.append(f'<text class="val" x="{x0 + w / 2:.1f}" y="{ye - 6:.1f}" text-anchor="middle">'
                   f'{r["Gallons"] / 1000:.1f}k</text>')
        out.append(f'<text class="tick" x="{x1 + 4:.1f}" y="{H - B + 18}" text-anchor="middle">'
                   f'{r["Reading Date"]:%b %d}</text>')
    out.append(event(x_of(LANDSCAPING), T, T + ph, "Landscaping (Jan)", anchor="start"))
    out.append(event(x_of(LEAK_FIXED), T, T + ph, "Fixed Sep 10"))
    return svg(W, H, "".join(out), "Stacked bars of normal versus above-normal gallons per billing period in 2026")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    df, baseline = load()
    summer_gpd, est = estimate(df, baseline)
    leak_start = est["start"].min()  # earliest start across scenarios, used for the shaded window
    print(f"baseline {baseline:.0f} GPD; Jun–Aug 2026 average {summer_gpd:.0f} GPD; rate ${RATE_PER_KGAL}/kgal")
    print(est.to_string(index=False, float_format=lambda v: f"{v:,.0f}"))
    (OUT / "daily_usage.svg").write_text(timeline(df, baseline, leak_start))
    (OUT / "usage_2026.svg").write_text(zoom_2026(df, baseline, leak_start))
    print(f"wrote charts to {OUT}/")
