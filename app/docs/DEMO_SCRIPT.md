# 3-minute live demo script

Setup before going on stage: app running (`./scripts/dev.sh` or Docker), browser at `/`, zoom 100 %, second tab on `/compare`.

| Time | Screen | Say / do |
|---|---|---|
| 0:00–0:20 | **Mission Overview** `/` | "Every lunar and Martian system is tested on Earth first. TerraAnalog AI answers *where* — transparently." Point at the green **Research dataset** badge and notice: "28 Earth sites, 14 Moon/Mars references, 4,340 research values — each one measured, modeled or provisional, and missing values stay missing." |
| 0:20–0:45 | Recommendation engine | Click the example *"Find Earth environments suitable for testing lunar polar rovers."* Show the interpretation (Moon · Lunar south polar highlands · Moon Rover Mobility · polar desert), the ranked results (McMurdo Dry Valleys, Haughton) with **why** bullets, caveats, and **what Earth cannot replicate**. "No chatbot inventing facts — deterministic parsing into structured filters and a documented score." |
| 0:45–1:20 | **Moon Reference Explorer** `/moon` | Click **Shackleton crater and rim vicinity**. Show the *representative region* status badge (never a "base"), LRO WAC imagery and the polar stereographic inset on the 1737.4 km lunar sphere. Switch objective to **Moon ISRU Ice** — Analog Match Explorer re-ranks: Haughton (46.3), McMurdo Dry Valleys (42.6), Bockfjorden (42.1). |
| 1:20–1:55 | **Earth Analog Explorer** | Click *Open in Earth Explorer*. Rotate the globe, switch basemap to **Satellite (NASA Blue Marble)**, toggle 2D. Click Haughton marker → detail: score, completeness, confidence, feature breakdown with Measured/Modeled/Provisional badges, the published research score next to the live one; open **Evidence inspector** → source + citation per feature. Tick compare boxes on 3 sites. |
| 1:55–2:35 | **Comparison Lab** | Radar of the 11 features + side-by-side table (badges show measured / modeled / provisional / **missing**). McMurdo (Moon Rover Mobility vs the south polar highlands): "abiotic surface and fine-sediment are missing → completeness 75 %, the score shows a range (26.9–51.9), not false precision." Operational suitability is shown separately, never mixed into the score. Open **Custom Weight Lab**: drag *Ice / permafrost agreement* up → rankings move live with ▲▼. **Sensitivity** tab: rank-stability bars. |
| 2:35–2:50 | Export & share | Click **Download PDF report** (generated server-side), **Export CSV report** and **Copy deep link** — "every view is shareable." |
| 2:50–3:00 | Close | "Drop the research bot's files into one folder and the whole platform updates — no code changes. Earth as a testbed, with the evidence on the table." |

Backup if network/tiles fail: the Earth map falls back to the offline Natural Earth basemap; the planetary viewer shows its schematic
graticule; everything else is served locally.
