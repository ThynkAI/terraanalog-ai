# 3-minute live demo script

Setup before going on stage: app running (`./scripts/dev.sh` or Docker), browser at `/`, zoom 100 %, second tab on `/compare`.

| Time | Screen | Say / do |
|---|---|---|
| 0:00–0:20 | **Mission Overview** `/` | "Every lunar and Martian system is tested on Earth first. TerraAnalog AI answers *where* — transparently." Point at the pink **Synthetic fixture data** badge: "We're honest about data status: scores are placeholders until our research dataset lands; planetary coordinates are real Gazetteer values." |
| 0:20–0:45 | Recommendation engine | Click the example *"Find Earth environments suitable for testing lunar polar rovers."* Show the interpretation chips (Moon · south polar region · Rover mobility · polar desert), the ranked results with **why** bullets, caveats, and **what Earth cannot replicate**. "No chatbot inventing facts — deterministic parsing into structured filters and a documented score." |
| 0:45–1:20 | **Moon Reference Explorer** `/moon` | Click **Shackleton crater vicinity**. Show LRO WAC imagery, coordinates −89.67°, 129.78°E, the polar stereographic inset on the 1737.4 km lunar sphere (≈10 km from the pole). Switch objective to **ISRU** — Analog Match Explorer re-ranks: McMurdo Dry Valleys, Axel Heiberg, Devon Island. |
| 1:20–1:55 | **Earth Analog Explorer** | Click *Open in Earth Explorer*. Rotate the globe, switch basemap to **Satellite (NASA Blue Marble)**, toggle 2D. Click Haughton marker → detail: score, completeness, confidence, transparent breakdown table; open **Evidence inspector** → value type + source + citation slot. Tick compare boxes on 3 sites. |
| 1:55–2:35 | **Comparison Lab** | Radar + side-by-side table (badges show provisional vs synthetic vs **missing**). Rio Tinto: "two criteria missing → completeness 78 %, the score shows a range, not false precision." Open **Custom Weight Lab**: drag *Operational testing* up → rankings move live with ▲▼. **Sensitivity** tab: rank-stability bars. |
| 2:35–2:50 | Export & share | Click **Download PDF report** (generated server-side), **Export CSV report** and **Copy deep link** — "every view is shareable." |
| 2:50–3:00 | Close | "Drop the research bot's files into one folder and the whole platform updates — no code changes. Earth as a testbed, with the evidence on the table." |

Backup if network/tiles fail: the Earth map falls back to the offline Natural Earth basemap; the planetary viewer shows its schematic
graticule; everything else is served locally.
