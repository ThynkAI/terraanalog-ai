# TerraAnalog AI — copy-ready submission

## Project name
TerraAnalog AI — Earth as a Testbed for the Moon and Mars

## Challenge
Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars

## Short summary
TerraAnalog AI compares Earth field sites with Moon and Mars reference regions for a stated mission test. Interactive maps, traceable data, benchmark comparisons and assumption stress tests help users build a defensible shortlist and identify what still needs field measurement.

## Project description
Mission teams need Earth environments in which to test equipment and procedures before exploring the Moon or Mars. Selecting a useful analog requires a comparison of specific physical processes and evidence, rather than visual resemblance alone.

TerraAnalog AI provides a working open-source research platform with 28 Earth sites, 14 lunar/Martian reference regions, 10 specialized mission profiles and a general comparison mode. Users explore a globe, choose a target and test objective, inspect source-labelled features, adjust weights, compare sites and export evidence. The research contract contains 4,340 feature records, including 378 missing values. Missing values stay missing.

Three scientific cases connect the scoring to practical research decisions. Holuhraun illustrates a published volcanic analogy and its dependence on regional terrain. Undara motivates a cave-robotics investigation while exposing the limitations of a cave-temperature proxy. Bockfjorden shows a polar case that scores below Haughton and depends strongly on an ice/permafrost proxy. Each compares the same three challenge benchmarks against one fixed planetary target, documents prior work and proposes field measurements.

The contribution is a reproducible shortlist and research workflow. Candidate labels do not establish new discovery, site permissions or validated hardware performance. The tool explicitly separates analog fidelity from operational suitability and preserves those limits in the interface and exports.

## NASA and other data use
NASA LRO LOLA and MGS MOLA terrain products support regional lunar and Martian topographic comparisons. NASA Moon Trek and Mars Trek provide orbital imagery, and NASA GIBS supplies optional Earth basemaps. Earth measurements and proxies also draw on Copernicus DEM, ESA WorldCover, CHELSA, ERA5 via Open-Meteo, SoilGrids, permafrost models and published literature. The app's Data & Provenance page distinguishes data actually processed, literature-only sources and catalogued sources not ingested. Spatial resolution and sampling support appear in the scientific cases.

## Technology and AI assistance
The application uses Next.js/TypeScript, MapLibre, deck.gl and Recharts with a FastAPI scoring service and PDF/CSV/JSON exports. Runtime scoring is deterministic and explainable. Plain-language recommendations use keyword parsing, not a generative model.

AI coding assistants supported research synthesis, software implementation, documentation and verification under the project lead's direction. The project lead reviewed and directed the work. The team should ensure its portal disclosure names every assistant it actually used. OpenAI ChatGPT/Codex assistance is documented in this development session. AI assistants are tools, not human team members.

## Project links
- Live application: https://terraanalog-web-cqgu.onrender.com
- Scientific case studies: https://terraanalog-web-cqgu.onrender.com/science
- Public repository: https://github.com/ThynkAI/terraanalog-ai
- Seven-slide short demonstration: https://github.com/ThynkAI/terraanalog-ai/blob/main/app/docs/TerraAnalog-AI-Space-Apps-Demo.pdf
- Data and licenses: https://terraanalog-web-cqgu.onrender.com/data
- Current automated checks: https://github.com/ThynkAI/terraanalog-ai/actions

## Verification summary
The committed-data audit passes 17 checks, including 2,352 compatible site scores. All 588 published rankings reproduce with no rank mismatches and maximum unrounded score difference below 0.00005 points. Automated backend, frontend, mobile, keyboard and accessibility checks appear in the linked CI runs. These checks establish implementation/data consistency and do not constitute independent scientific validation.

## Remaining portal-specific details
Use the actual registered team and member names. The repository credits Deep Kanabar as project lead. The team owner, Local Event, eligibility declarations and any other AI tools used must match the registered team's real details. Those facts cannot be inferred from source code.

The official 2026 overview says project submission occurs through the Project tab on the team's page. A short demonstration may be a video no longer than 30 seconds or a presentation of at most seven slides; the longer repository walkthrough is supplementary. Review the live form before clicking Submit for Judging. Do not mark the project submitted without a portal confirmation.

Reference links: https://www.spaceappschallenge.org/2026/ ; https://www.spaceappschallenge.org/resources/project-submission-guide/ ; https://github.com/nasa/spaceapps/discussions/1973
