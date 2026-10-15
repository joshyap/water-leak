# Finding a hidden water leak in utility billing data

In 2026 my water bills jumped to about 9× their normal level. A large landscaping project had just been finished in January, including a new lawn and a new [Rachio](https://rachio.com/) smart sprinkler system. The new lawn needed heavy watering, so at first the high numbers looked expected. This project uses five years of billing data to answer three questions:

1. **Was there really a leak, or was it just the new lawn?**
2. **When did it start?**
3. **What was it costing, and what did fixing it save?**

The analysis pointed to a leak. It was found and **fixed on September 10, 2026**. The fix saves an estimated **$70–$145 per month, or roughly $860–$1,740 a year**.

![Daily water use per billing period](docs/charts/daily_usage.svg)

## The data

The data is the utility's billing export, one row per billing period, from June 2021 to September 2026 ([data/usage_clean.csv](data/usage_clean.csv)). Account and meter numbers are removed by [scripts/sanitize.py](scripts/sanitize.py). The useful columns are:

- **Gallons** and **Days in Read Period**. **Customer GPD** (gallons per day) is `Gallons ÷ Days`, which puts periods of different lengths on the same scale.
- **Average Households GPD**: the utility's figure for comparable homes, which already includes their typical lawn watering.
- **Reading Date** marks the *end* of a period. The "Mar 17" row covers roughly Feb 17 – Mar 17.

The meter reads only once a month, which is the main limitation. There is no hourly data, so lawn watering and a leak can't be told apart directly. The analysis below works around that.

## 1. Was it a leak or the lawn?

The first step was to find what "normal" looks like for this home. From Feb 2023 to Feb 2026, median use was **96 gallons/day**, well below the average household (~132). Summers were barely higher than winters (76 GPD in summer 2025), so the home did little outdoor watering before 2026.

![2026 billing periods, normal vs above normal](docs/charts/usage_2026.svg)

Against that baseline, 2026 doesn't look like lawn watering alone:

- **The landscaping month itself was almost normal.** The period covering the landscaping (ending Feb 17) used 119 GPD. The jump came in the periods after it.
- **Usage never tapered off.** A new lawn needs the most water while it's establishing, then less. Instead, June was the *low point* at 680 GPD, and August was among the highest periods at 1,148 GPD, seven months after planting.
- **The scale is far too large.** From June to August, the home averaged **890 GPD**. That is about 6–7× the average household, *including that household's lawn watering*.

The steady, high floor is what a leak looks like: a leak runs 24 hours a day, whatever the weather or watering schedule.

## 2. When did it start?

- **Not before Feb 17.** That period was at a normal level.
- **Most likely in the first half of March.** The period ending Mar 17 was only about **4,800 gallons** above normal. At the leak rates implied by the summer data (below), the leak would produce that much in 6–12 days. That puts the start around **March 5–11, 2026**, about two months after the landscaping.

This estimate assumes the leak ran at a steady rate and that lawn watering added little in early March. If watering was already happening then, the leak started even later in that window.

## 3. What did it cost, and what did the fix save?

The summer's 890 GPD is three things together: the home's normal 96 GPD, lawn watering (unknown), and the leak. Because the meter can't separate the last two, I estimated the leak under three watering assumptions. The Rachio's watering logs could replace these assumptions with real numbers (see [What's next](#whats-next)).

| Assumed lawn watering | Implied leak rate | Estimated start | Leak cost (Mar → Sep 10) | **Saved per month by fixing** | **Saved per year** |
|---|---|---|---|---|---|
| 0 gal/day | 794 gal/day | Mar 11 | $872 (145k gal) | **$143** | **$1,739** |
| 200 gal/day | 594 gal/day | Mar 9 | $660 (110k gal) | **$107** | **$1,301** |
| 400 gal/day | 394 gal/day | Mar 5 | $447 (75k gal) | **$71** | **$863** |

Dollar figures use an assumed rate of **$6.00 per 1,000 gallons**, set in [scripts/make_charts.py](scripts/make_charts.py) as `RATE_PER_KGAL`. If your utility also charges sewer by the gallon, the savings are higher.

Even the most conservative case, which assumes 400 gal/day of watering (far above anything this home used before), comes out to **hundreds of dollars a year saved**. In that case the leak had already cost about $450 before it was found.

## Other findings

The same baseline approach also flags two earlier incidents:

| Period | GPD | Pattern |
|---|---|---|
| Jan 2023 | **1,837** | 58,800 gallons in one period, back to normal (64 GPD) by the next read. This looks like a one-time event such as a burst pipe. |
| Aug 2023 – Jan 2024 | 561, then 170–260 | One spike, then about 2× normal for five months before settling. This looks like a slow leak or a running fixture. |

The house reads zero from June 2021 to May 2022 because it was unoccupied. Those rows are left out of the charts and the baseline.

## What's next

The September period (Aug 17 – Sep 17) includes only 7 days after the fix. The **Oct 17, 2026 reading** will be the first full billing period without the leak. It will measure lawn watering directly and narrow the leak-rate range above to a single number.

Next I'll look into the **[Rachio API](https://rachio.readme.io/)**. The Rachio controller logs every watering run, which this analysis has so far had to guess at with scenarios. Pulling that history should allow:

- **More detailed analysis.** Run times per zone, combined with nozzle flow rates, give an estimate of the gallons used for watering in each billing period. Subtracting that from the bill isolates the leak directly instead of bounding it with assumed watering rates.
- **Automation going forward.** A scheduled job can compare each new meter reading against the home's baseline plus the logged watering, and raise an alert when unexplained use appears. That would catch the next leak in weeks instead of months.

## Reproduce

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/make_charts.py   # prints the estimates table, writes docs/charts/*.svg
```

The tools are pandas for the analysis and hand-built SVG for the charts, with no plotting library. The charts follow your system's light or dark mode, and each bar shows its exact value on hover when you open the SVG directly. The event dates, analysis windows, water rate and watering scenarios are all constants at the top of the script.
