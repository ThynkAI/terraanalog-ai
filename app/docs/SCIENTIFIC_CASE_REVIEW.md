# Scientific case review — 15 November 2026

## Scope and reproducibility

This is a targeted source review and a software/data integration improvement, not a systematic review, field campaign or claim of first discovery. No new observational measurements were collected. The three cases supplement the existing scoring contract; primary context sources do not silently upgrade tertiary scoring tags to measured data.

Narratives and source-to-claim links are stored in `data/research/supplementary/case_study_briefs.json`. `scripts/build_case_measurements.py` exports a deterministic subset of the committed root `outputs/analog_features.csv` and `outputs/planetary_features.csv`. Run `python app/scripts/build_case_measurements.py` from the repository root after changing the research outputs. The backend tests check this export against its inputs.

The `/api/case-studies` endpoint computes all four site scores and all four stressed scores with the existing scoring engine, one fixed reference and one objective. It retains full-catalog ranks and missing-data bounds. Bounds represent missing-feature extremes, not measurement-error confidence intervals. The Holuhraun–Elysium mobility comparison is explicitly exploratory because Elysium is outside that profile's published Jezero/Gale reference set.

Evidence-strict results are the existing published profile summary: remove hypothesized categorical tags and retain each site's best score over the profile's published references. Those results have a different reference scope from a fixed-reference case score. No per-site strict score or measured-only ranking is invented.

## Research findings in the current contract

| Case | Fixed target / profile | Baseline result | Stress test | Interpretation |
|---|---|---|---|---|
| Holuhraun | Elysium / Mars rover mobility | 53.4, rank 5; +5.5 points over the strongest challenge benchmark | Exclude slope and ruggedness: 46.4, rank 8 | Regional terrain contributes materially. Independent literature already establishes Holuhraun as an Elysium analog. |
| Undara | Tranquillitatis pit / Moon lava tube | 62.1, rank 2; +25.4 points over the strongest challenge benchmark | Exclude thermal: 57.8, rank 2 | Ranking persists without the questionable cave-temperature proxy, but actual cave measurements and permission are still required. |
| Bockfjorden / Svalbard | Shackleton / Moon ISRU ice | 42.1, rank 3; −4.2 points below Haughton | Exclude ice proxy: 22.7, rank 5 | A transparent non-winning case; regional permafrost agreement is not evidence of lunar extraction equivalence. |

Values above are rounded live-engine results on the committed research contract. The app computes them rather than hard-coding the figures into the interface. The stress test renormalizes remaining feature weights and is diagnostic, not a more accurate score.

## Sources and what they support

- Voigt et al. (2025), DOI **10.3847/PSJ/adb5f1**, [USGS publication record](https://pubs.usgs.gov/publication/70275623): Holuhraun–Elysium volcanic-process analogy and prior publication. [RAVEN's field-site page](https://raven.lpl.arizona.edu/field-site-holuhraun-iceland) supplies project context.
- [Queensland Parks resource information (2023)](https://parks.desi.qld.gov.au/__data/assets/pdf_file/0025/309931/Undara-Volcanic-National-Park-Resource-Information-2023.pdf): Undara cave geology and sediment-covered floors. It does not establish lunar robotics approval or novelty.
- Horvath, Hayne & Paige (2022), DOI **10.1029/2022GL099710**, and [NASA's explanation](https://www.nasa.gov/solar-system/nasas-lro-finds-lunar-pits-harbor-comfortable-temperatures/): separate orbital thermal observations from modeled pit/cave temperatures. This is why the case uses Tranquillitatis and explicitly labels the cave-temperature proxy.
- [NASA AMASE](https://science.gsfc.nasa.gov/sci/projects/247/), [ESA's Arctic summary](https://www.esa.int/Enabling_Support/Preparing_for_the_Future/Space_for_Earth/Arctic/Mars_in_the_Arctic), and the [2011 LPI analog-sites workshop](https://www.lpi.usra.edu/lpi/contribution_docs/LPI-001612.pdf): prior Svalbard analog operations and Bockfjord volcanic centers. They do not establish lunar resource qualification.

Searches included “Holuhraun Mars analogue NASA field study”, “Undara lava tubes Queensland official geology caves”, “AMASE Sverrefjellet Svalbard NASA”, and “Horvath Hayne Paige 2022 lunar pits 290”. Searches were targeted and cannot establish absence of prior work. Source review date: 15 November 2026.

## Presentation and submission corrections

The Impact page now describes the loaded research dataset rather than obsolete synthetic placeholders. The pitch distinguishes 10 specialized profiles plus general mode and 4,340 feature records including 378 missing values. Radar plots omit incomplete criteria for all selected sites rather than plotting missing measurements as zero. The revised demo shows a non-winning case and separates software consistency from scientific validation.

Field protocols are proposed research plans. Access, conservation review and scientific peer review remain necessary before any expedition or publication claiming validated analog performance. Raw observation retrieval and field work remain reproducible future work; this change does not claim either was performed.
