# NASA Space Apps Challenge 2026 — submission checklist

**Project:** TerraAnalog AI — Earth as a Testbed for the Moon and Mars
**Team:** Deep Kanabar (lead), with AI assistants for the planetary-science and geospatial research pipeline and for the software platform

| Item | Link / status |
|---|---|
| Challenge review and latest change verification | [`app/docs/CHALLENGE_REVIEW.md`](app/docs/CHALLENGE_REVIEW.md) |
| Public repository | https://github.com/ThynkAI/terraanalog-ai |
| Live demo URL | https://terraanalog-web-cqgu.onrender.com (API: https://terraanalog-api-cqgu.onrender.com) |
| 3-minute demo script | [`app/docs/DEMO_SCRIPT.md`](app/docs/DEMO_SCRIPT.md) |
| Pitch (~150 words) | [`app/docs/PITCH.md`](app/docs/PITCH.md) |
| Presentation outline (6–8 slides) | [`app/docs/PRESENTATION_OUTLINE.md`](app/docs/PRESENTATION_OUTLINE.md) |
| Demo deck | [`app/docs/TerraAnalog-AI-Space-Apps-Demo.pdf`](app/docs/TerraAnalog-AI-Space-Apps-Demo.pdf) |
| Screenshots | [`app/docs/screenshots/`](app/docs/screenshots/) (17 app views, including mobile, plus a PDF report page) |
| Sample generated report | [`app/docs/samples/site-comparison-report-sample.pdf`](app/docs/samples/site-comparison-report-sample.pdf) |
| How the AI works | [README → *How the AI works*](README.md#how-the-ai-works) (explainable scoring and a rule-based recommendation engine; no LLM invents facts) |
| Scientific methodology | [`scientific_methodology.md`](scientific_methodology.md) · app view: [`app/docs/DATA_INTEGRATION.md`](app/docs/DATA_INTEGRATION.md) |
| Data sources and references | [`source_references.md`](source_references.md) · [`outputs/dataset_catalog.csv`](outputs/dataset_catalog.csv) |
| Test evidence | [`app/docs/TEST_RESULTS.md`](app/docs/TEST_RESULTS.md) (backend, TypeScript, unit, end-to-end/accessibility, Docker Compose, 588-row published-score reproduction) |
| Licence | [MIT](LICENSE) for code; data keeps its upstream licences (README → *Licence and data terms*) |
| Run locally | README → *Quick start* (Windows `setup.ps1`, macOS/Linux `setup.sh`, Docker) |

## Development and use of AI

TerraAnalog AI was conceived, specified and directed by the team. Deep Kanabar wrote the project specification, set the scientific and data-integrity rules, and directed, reviewed and validated all output. AI coding assistants were used to help write code, documentation and data-processing scripts under that direction.

The deployed application uses no generative AI at runtime. Scores are produced by a deterministic, explainable engine, and every value traces to a cited source. Missing measurements are shown as missing; they are never invented.

## Before submitting
- [x] Deploy (Render Blueprint) and replace the **TBD** demo URL above, and in the README *Deploy* section. Live as of 15 November 2026, America/Toronto: https://terraanalog-web-cqgu.onrender.com
- [ ] Open the demo URL in a private window and walk through `DEMO_SCRIPT.md` once (allow ~1 min for free-tier services to wake).
- [ ] Record the 3-minute demo video if the challenge form asks for one, and add its link here: **TBD**.
- [ ] Paste the repo link, the demo link, the pitch and the team names into the Space Apps project page.
- [ ] Credit NASA data and imagery as listed in the README (*Data provenance*, *Licence and data terms*). NASA does not endorse the project.
