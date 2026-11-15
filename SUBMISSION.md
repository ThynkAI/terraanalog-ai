# NASA Space Apps Challenge 2026 — submission checklist

**Project:** TerraAnalog AI — Earth as a Testbed for the Moon and Mars
**Team:** Deep Kanabar (lead), with AI assistants for the planetary-science and geospatial research pipeline and for the software platform

| Item | Link / status |
|---|---|
| Challenge review and latest change verification | [`app/docs/CHALLENGE_REVIEW.md`](app/docs/CHALLENGE_REVIEW.md) |
| Public repository | https://github.com/ThynkAI/terraanalog-ai |
| Live demo URL | https://terraanalog-web-cqgu.onrender.com (API health: https://terraanalog-api-cqgu.onrender.com/api/health) |
| Supplementary 3-minute walkthrough | [`app/docs/DEMO_SCRIPT.md`](app/docs/DEMO_SCRIPT.md) |
| Pitch (~150 words) | [`app/docs/PITCH.md`](app/docs/PITCH.md) |
| Presentation outline | [`app/docs/PRESENTATION_OUTLINE.md`](app/docs/PRESENTATION_OUTLINE.md) |
| Required short demonstration: seven-slide PDF | [`app/docs/TerraAnalog-AI-Space-Apps-Demo.pdf`](app/docs/TerraAnalog-AI-Space-Apps-Demo.pdf) |
| Screenshots | [`app/docs/screenshots/`](app/docs/screenshots/) (18 app views, including mobile, plus a PDF report page) |
| Sample generated report | [`app/docs/samples/site-comparison-report-sample.pdf`](app/docs/samples/site-comparison-report-sample.pdf) |
| How the AI works | [README → *How the AI works*](README.md#how-the-ai-works) (explainable scoring and a rule-based recommendation engine; no LLM invents facts) |
| Scientific cases and source review | Live: `/science` · [`app/docs/SCIENTIFIC_CASE_REVIEW.md`](app/docs/SCIENTIFIC_CASE_REVIEW.md) |
| Scientific methodology | [`scientific_methodology.md`](scientific_methodology.md) · app view: [`app/docs/DATA_INTEGRATION.md`](app/docs/DATA_INTEGRATION.md) |
| Data sources and references | [`source_references.md`](source_references.md) · [`outputs/dataset_catalog.csv`](outputs/dataset_catalog.csv) |
| Test evidence | [`app/docs/TEST_RESULTS.md`](app/docs/TEST_RESULTS.md) (backend, TypeScript, unit, end-to-end/accessibility, Docker Compose, 588-row published-score reproduction) |
| Licence | [MIT](LICENSE) for code; data keeps its upstream licences (README → *Licence and data terms*) |
| Run locally | README → *Quick start* (Windows `setup.ps1`, macOS/Linux `setup.sh`, Docker) |

## Development and use of AI

TerraAnalog AI was conceived, specified and directed by the team. Deep Kanabar wrote the project specification, set the scientific and data-integrity rules, and directed, reviewed and validated all output. AI coding assistants were used to help write code, documentation and data-processing scripts under that direction.

The deployed application uses no generative AI at runtime. Scores are produced by a deterministic, explainable engine, and every value traces to a cited source. Missing measurements are shown as missing; they are never invented.

## Final verification

The committed-data audit and score-reproduction reports are in `app/docs/test-results/submission-sanity.json` and `submission-score-reproduction.json`. The audit covers the committed contract, not an independent rerun of raw-raster extraction or field validation. The latest UI, mobile and accessibility checks are recorded in GitHub Actions.

See [`app/docs/SUBMISSION_READY.md`](app/docs/SUBMISSION_READY.md) for copy-ready project text and final links.

## Before submitting
- [x] Deploy (Render Blueprint) and add the demo URL above and in the README *Deploy* section. Live as of 15 November 2026, America/Toronto: https://terraanalog-web-cqgu.onrender.com
- [ ] Open the demo URL in a private window and walk through `DEMO_SCRIPT.md` once. Both Render services run on Starter instances and do not sleep when idle.
- [ ] Use the refreshed seven-slide PDF as the short demonstration, or supply a video of no more than 30 seconds if preferred. The three-minute walkthrough is supplementary.
- [ ] Paste the repo link, the demo link, the pitch and the team names into the Space Apps project page.
- [ ] Credit NASA data and imagery as listed in the README (*Data provenance*, *Licence and data terms*). NASA does not endorse the project.
