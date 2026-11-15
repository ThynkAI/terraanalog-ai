# Three-minute submission demo

Open the deployed app in a private window first. Confirm the Science Cases navigation entry and research badge are present. Wake both Render services before recording. Prepare `/science?case=undara-cave-robotics` in a second tab. Record the current UI; earlier screenshots describe the previous revision.

| Time | Screen | Demonstration |
|---|---|---|
| 0:00–0:20 | Overview | “Where can we test a specific Moon or Mars mission on Earth?” Show 28 sites, 14 references and mission shortcuts. “We compare surface and process proxies; Earth cannot reproduce another world's environment.” |
| 0:20–0:45 | Mission shortcut → Earth Explorer | Choose Mars rover mobility. Inspect a site, its evidence completeness and measured/modeled/provisional labels. Missing measurements stay missing. |
| 0:45–1:20 | Science Cases → Undara | Show the source-reviewed novelty assessment. “This is a research lead, not a claimed discovery.” Show the regional measurement table, units, DEM comparison scale and sampling radius. “Regional terrain is not a cave survey; the Earth temperature is annual air temperature, not an in-cave measurement.” |
| 1:20–1:45 | Benchmark table / proxy stress test | Compare Undara with Atacama, Haughton and Death Valley against the same Tranquillitatis reference. Remove the thermal proxy. “The score changes, but the case remains second in our fixed-reference catalog ranking. That is assumption sensitivity, not proof of field suitability.” |
| 1:45–2:10 | Evidence-strict summary | Show the original and evidence-strict top five. “The published pipeline removes hypothesized tags. This is a profile summary across its published references, distinct from the fixed-reference score above. Strict does not mean measured-only.” |
| 2:10–2:35 | Svalbard case | Show the ice-proxy stress test and benchmark result. “We show non-winning cases too. Permafrost probability is not mineable lunar ice; the tool makes that dependence visible.” Show source links and proposed field validation. |
| 2:35–3:00 | Exports / close | Download the evidence JSON and measurement CSV; show the case's Comparison Lab link. “Our contribution is a traceable shortlist and a research workflow. The next step is targeted literature assessment and permitted field measurements, not a declaration of a new validated analog.” |

Fallback: the measurement tables, benchmark scores and evidence exports do not depend on external image tiles. The Earth Explorer's Natural Earth basemap works without a remote tile service. Run locally using the repository instructions if Render is unavailable.

Do not describe reproduction of the 588 published internal scores as scientific validation or predictive accuracy. It is a computational regression check.
