#!/usr/bin/env python3
"""Generate the SYNTHETIC fixture versions of the 9 data-contract files in data/fixtures/.

!!! SYNTHETIC — NOT REAL DATA !!!
These fixtures exist so the platform can be built and demonstrated before the research bot
("NASA SPACE APP CHALLENGE 1", a.k.a. Bot 1) delivers its authoritative files. Replace them by pointing
TERRA_DATA_DIR at Bot 1's output directory — no UI or API changes are needed.

What is (and is not) real in here:
  * Planetary reference coordinates: copied from the IAU/USGS Gazetteer of Planetary Nomenclature
    (queried 2026-11-15; feature IDs recorded per record). Body radii: IAU mean radii.
  * Earth site names/locations: well-known analog field areas; coordinates are approximate AOI centroids.
    Twelve of them (and six of their criterion scores) come from the team's AnalogSite prep pack
    (/workspace/AnalogSite, PREP_DRAFT expert judgement, value_type = "provisional").
  * Every other score is SYNTHETIC (value_type = "synthetic"). Nothing here is a measurement.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "fixtures"
OUT.mkdir(parents=True, exist_ok=True)
GENERATED = "2026-11-15"
PENDING = "citation pending from research dataset"
BANNER = "SYNTHETIC FIXTURE — NOT REAL DATA. Replace with Bot 1 research outputs (see docs/DATA_INTEGRATION.md)."

CRITERIA = [
    ("terrain", "Terrain similarity", "Slope, roughness and trafficability relative to the reference terrain.", "SRTM / Copernicus DEM slope & roughness in AOI", ["Copernicus DEM", "SRTM", "LOLA (target)", "MOLA (target)"]),
    ("geology", "Geological similarity", "Lithology / process match (basaltic, impact, aqueous alteration, glacial...).", "USGS planetary analog resources + peer-reviewed literature", ["USGS", "literature"]),
    ("thermal", "Thermal / environmental similarity", "Thermal extremes and diurnal/seasonal swing.", "MODIS / VIIRS land-surface temperature", ["MODIS LST", "Diviner (target)", "THEMIS (target)"]),
    ("dust_aridity", "Dust & aridity", "Dryness, fine-grained dust, abrasion relevance.", "Precipitation climatology, aridity index, SMAP", ["Worldview", "SMAP"]),
    ("illumination", "Illumination contrast", "Polar night / low sun angle / long shadow proxy (Moon-weighted).", "Latitude + DEM hillshade / insolation models", ["solar geometry", "DEM"]),
    ("ice_permafrost", "Ice / permafrost relevance", "Presence of ground ice, permafrost or glacial ice as a process analog.", "Permafrost maps, field reports", ["permafrost maps", "literature"]),
    ("subsurface_access", "Subsurface / cave access", "Accessible lava tubes, caves or skylights for subsurface robotics.", "Cave surveys, park inventories", ["cave surveys"]),
    ("operational", "Operational testing suitability", "Access, permits, logistics and safety for hardware/crew field tests.", "OpenStreetMap + published field logistics", ["OpenStreetMap", "literature"]),
]

# ---------------------------------------------------------------------------------------------------------
# Earth sites. AS = values from the AnalogSite prep pack (PREP_DRAFT expert judgement -> "provisional").
# order of AS tuple: terrain(slope_topo), thermal, dust_aridity, illumination(illum_contrast), operational(access_logistics), geology(geology_analog)
# SYN = synthetic values for the remaining criteria (None = intentionally missing to exercise missing-data handling)
# ---------------------------------------------------------------------------------------------------------
SITES = [
    dict(site_id="CA-HAU", name="Haughton Impact Structure, Devon Island", country="Canada", region="Nunavut", lat=75.37, lon=-89.68,
         analog_types=["impact_crater", "polar_desert", "permafrost_ice"], climate="Polar desert / tundra", geology="Impact breccias in sedimentary target rocks; periglacial terrain",
         target_bodies=["moon", "mars"], mission_objectives=["rover_mobility", "astronaut_field_ops", "habitat", "drilling", "general"],
         AS=(4, 4, 3, 5, 3, 5), SYN=dict(ice_permafrost=4, subsurface_access=1),
         J=dict(terrain="Impact ejecta and crater rim topography; traversable but rough in places.", thermal="High-Arctic cold extremes; strong seasonal swing.",
                dust_aridity="Cold desert fines; not hyper-arid Atacama-class.", illumination="Polar night / low sun angle; strongest lunar south-pole illumination proxy in set.",
                operational="Seasonal airlift; established analog camp logistics, still remote.", geology="Impact structure + published CSA/NASA analog campaigns."),
         description="High-Arctic impact structure used for long-running Mars/Moon analog field campaigns."),
    dict(site_id="AQ-MDV", name="McMurdo Dry Valleys", country="Antarctica", region="Victoria Land", lat=-77.5, lon=162.9,
         analog_types=["polar_desert", "permafrost_ice"], climate="Polar desert (ice-free valleys)", geology="Glacial tills, patterned ground, crystalline bedrock",
         target_bodies=["mars", "moon"], mission_objectives=["drilling", "isru", "rover_mobility", "general"],
         AS=(3, 5, 5, 4, 2, 5), SYN=dict(ice_permafrost=5, subsurface_access=1),
         J=dict(terrain="Valley floors often gentle; valley walls steep — AOI-dependent.", thermal="Extreme cold desert thermal environment.",
                dust_aridity="Classic cold hyper-arid Mars proxy.", illumination="Polar night seasons; secondary lunar value.",
                operational="USAP/national program logistics; hard for indie hardware tests.", geology="Extensive Mars cold-desert literature."),
         description="Ice-free polar desert valleys; a classic cold, dry Mars analog."),
    dict(site_id="CL-ATA", name="Atacama Desert (Yungay transect)", country="Chile", region="Antofagasta", lat=-24.08, lon=-69.92,
         analog_types=["hyperarid_desert"], climate="Hyper-arid desert", geology="Saline, oxidised hyper-arid soils; alluvial fans",
         target_bodies=["mars"], mission_objectives=["drilling", "rover_mobility", "astronaut_field_ops", "general"],
         AS=(3, 4, 5, 1, 4, 5), SYN=dict(ice_permafrost=0, subsurface_access=1),
         J=dict(terrain="Mostly low-relief basins; local alluvial fans.", thermal="Hot diurnal swing; not polar cold.",
                dust_aridity="Hyper-arid; primary Mars dust/soil proxy.", illumination="Low-latitude; weak PSR/polar-night proxy.",
                operational="Road-accessible research sites; permits required.", geology="Canonical Mars soil/microbial-limit analog literature."),
         description="One of the driest places on Earth; widely used for Mars soil and life-detection instrument tests."),
    dict(site_id="US-MOJ", name="Mojave Desert (volcanic/playa AOIs)", country="USA", region="California", lat=35.0, lon=-116.0,
         analog_types=["hyperarid_desert", "basaltic_volcanic"], climate="Arid desert", geology="Basaltic flows, cinder cones and playas",
         target_bodies=["mars"], mission_objectives=["rover_mobility", "astronaut_field_ops", "habitat", "general"],
         AS=(3, 4, 4, 1, 5, 4), SYN=dict(ice_permafrost=0, subsurface_access=2),
         J=dict(terrain="Playas flat; volcanic fields locally rough.", thermal="Strong desert diurnal swing.", dust_aridity="Dusty arid; good ops dust testing.",
                illumination="Not polar.", operational="Excellent road access for hardware shakedown.", geology="Basaltic/playa Mars-ops analog; training heritage."),
         description="Accessible desert with basaltic and playa terrains for rover and operations shakedowns."),
    dict(site_id="US-SFV", name="San Francisco Volcanic Field / Flagstaff", country="USA", region="Arizona", lat=35.35, lon=-111.65,
         analog_types=["basaltic_volcanic"], climate="Semi-arid plateau", geology="Basaltic cinder cones and lava flows",
         target_bodies=["moon"], mission_objectives=["astronaut_field_ops", "rover_mobility", "general"],
         AS=(4, 3, 3, 1, 5, 5), SYN=dict(ice_permafrost=0, subsurface_access=2),
         J=dict(terrain="Cinder cones, lava fields — lunar trafficability practice.", thermal="Elevated plateau; moderate desert swing.", dust_aridity="Semi-arid volcanic fines.",
                illumination="Not polar.", operational="Near Flagstaff; strong logistics for field tests.", geology="Lunar volcanic/crater training heritage (USGS/NASA region)."),
         description="Volcanic field with a long history of astronaut geology training."),
    dict(site_id="IS-ASK", name="Iceland basaltic highlands (Askja/Krafla-class AOI)", country="Iceland", region="Highlands", lat=65.03, lon=-16.75,
         analog_types=["basaltic_volcanic", "permafrost_ice"], climate="Subarctic highland", geology="Basaltic lava fields, hyaloclastite, glacio-volcanic deposits",
         target_bodies=["mars", "moon"], mission_objectives=["rover_mobility", "astronaut_field_ops", "drilling", "general"],
         AS=(4, 3, 3, 2, 3, 5), SYN=dict(ice_permafrost=2, subsurface_access=3),
         J=dict(terrain="Lava fields and hyaloclastite — rough trafficability.", thermal="Subarctic; milder than polar deserts.", dust_aridity="Volcanic dust; not hyper-arid.",
                illumination="High-latitude winters; partial illumination interest.", operational="Seasonal highland access; research-camp precedent.", geology="Basaltic Mars volcanic analog literature."),
         description="Young basaltic terrains with glacio-volcanic features."),
    dict(site_id="ES-RIO", name="Rio Tinto", country="Spain", region="Andalusia", lat=37.7, lon=-6.6,
         analog_types=["acidic_aqueous"], climate="Mediterranean", geology="Acidic, iron- and sulfate-rich river system in a mining district",
         target_bodies=["mars"], mission_objectives=["drilling", "general"],
         AS=(2, 3, 3, 1, 4, 5), SYN=dict(ice_permafrost=None, subsurface_access=None),
         J=dict(terrain="River valley / mine terrain; low regional relief.", thermal="Mediterranean; limited Mars thermal match.", dust_aridity="Seasonally dry; not a dust analog.",
                illumination="Not polar.", operational="Road access; mining-district permits.", geology="Acidic aqueous geochemistry analog literature."),
         description="Acidic, iron-rich river system studied as an aqueous-alteration Mars analog."),
    dict(site_id="CA-AXE", name="Axel Heiberg Island cold/evaporite AOIs", country="Canada", region="Nunavut", lat=79.45, lon=-90.5,
         analog_types=["polar_desert", "permafrost_ice"], climate="High-Arctic polar desert", geology="Permafrost, perennial cold springs, evaporites",
         target_bodies=["moon", "mars"], mission_objectives=["drilling", "isru", "general"],
         AS=(3, 5, 3, 5, 2, 4), SYN=dict(ice_permafrost=5, subsurface_access=1),
         J=dict(terrain="Local relief variable; glacier-proximal hazards.", thermal="High-Arctic extreme cold.", dust_aridity="Polar desert; moderate dust.",
                illumination="Polar night; strong low-sun proxy.", operational="Remote; seasonal research station logistics.", geology="Cold-spring/permafrost analog literature."),
         description="High-Arctic permafrost terrain with perennial cold springs."),
    dict(site_id="US-LBN", name="Lava Beds National Monument (tube/cave AOI)", country="USA", region="California", lat=41.71, lon=-121.51,
         analog_types=["lava_tube_cave", "basaltic_volcanic"], climate="Semi-arid steppe", geology="Basaltic lava tubes, collapse pits",
         target_bodies=["moon", "mars"], mission_objectives=["cave_exploration", "rover_mobility", "astronaut_field_ops", "general"],
         AS=(4, 3, 3, 4, 4, 5), SYN=dict(ice_permafrost=3, subsurface_access=5),
         J=dict(terrain="Tube floors/roofs and collapse pits — subsurface trafficability practice.", thermal="Stable cave microclimate vs surface desert swing (document both).",
                dust_aridity="Semi-arid surface fines.", illumination="Cave darkness provides a PSR-like low-light proxy.", operational="Park access with permits.",
                geology="Lava-tube analog for lunar/Martian caves."),
         description="Dense concentration of accessible basaltic lava tubes."),
    dict(site_id="US-DV", name="Death Valley (selected basins)", country="USA", region="California", lat=36.5, lon=-117.0,
         analog_types=["hyperarid_desert"], climate="Hot desert", geology="Evaporite basins, alluvial fans",
         target_bodies=["mars"], mission_objectives=["rover_mobility", "habitat", "general"],
         AS=(2, 5, 4, 1, 4, 3), SYN=dict(ice_permafrost=0, subsurface_access=None),
         J=dict(terrain="Basin floors gentle.", thermal="Extreme heat / diurnal swing.", dust_aridity="Very dry basin fines.", illumination="Not polar.",
                operational="National park access.", geology="Evaporite/alluvial; partial Mars analog."),
         description="Extreme-heat desert basins."),
    dict(site_id="US-HMK", name="Mauna Kea high-elevation volcanic terrain", country="USA", region="Hawaii", lat=19.82, lon=-155.47,
         analog_types=["basaltic_volcanic", "high_altitude"], climate="Alpine (high-elevation)", geology="Basaltic tephra and lava",
         target_bodies=["moon"], mission_objectives=["rover_mobility", "isru", "general"],
         AS=(4, 3, 2, 1, 3, 4), SYN=dict(ice_permafrost=1, subsurface_access=2),
         J=dict(terrain="Volcanic slopes; rover-scale roughness.", thermal="High-elevation cold nights.", dust_aridity="Volcanic tephra; moderate.",
                illumination="Not polar.", operational="Access constrained; cultural and permit considerations.", geology="Basaltic tephra regolith simulant heritage."),
         description="High-elevation basaltic terrain."),
    dict(site_id="AU-PIL", name="Pilbara ancient terrains (selected)", country="Australia", region="Western Australia", lat=-21.0, lon=119.0,
         analog_types=["hyperarid_desert", "acidic_aqueous"], climate="Hot arid", geology="Archean volcanic-sedimentary sequences",
         target_bodies=["mars"], mission_objectives=["drilling", "general"],
         AS=(3, 4, 4, 1, 3, 4), SYN=dict(ice_permafrost=None, subsurface_access=None),
         J=dict(terrain="Moderate relief outback.", thermal="Hot arid swing.", dust_aridity="Arid, dusty.", illumination="Not polar.",
                operational="Remote; long road logistics.", geology="Ancient terrains relevant to early-Mars habitability studies."),
         description="Ancient terrains used in early-life and early-Mars analog studies."),
    dict(site_id="US-MDR", name="Mars Desert Research Station area", country="USA", region="Utah", lat=38.4064, lon=-110.7919,
         analog_types=["hyperarid_desert"], climate="Cold desert", geology="Sedimentary badlands (shales, sandstones)",
         target_bodies=["mars"], mission_objectives=["habitat", "astronaut_field_ops", "rover_mobility", "general"],
         SYN=dict(terrain=3, geology=4, thermal=3, dust_aridity=4, illumination=1, ice_permafrost=0, subsurface_access=1, operational=5),
         description="Desert badlands hosting a long-running crewed Mars habitat simulation station."),
    dict(site_id="US-MET", name="Meteor Crater (Barringer)", country="USA", region="Arizona", lat=35.0274, lon=-111.0228,
         analog_types=["impact_crater"], climate="Semi-arid plateau", geology="Simple impact crater in sedimentary rocks",
         target_bodies=["moon", "mars"], mission_objectives=["astronaut_field_ops", "rover_mobility", "general"],
         SYN=dict(terrain=4, geology=4, thermal=3, dust_aridity=3, illumination=1, ice_permafrost=0, subsurface_access=0, operational=5),
         description="Well-preserved simple impact crater."),
    dict(site_id="ES-LAN", name="Lanzarote lava tubes (La Corona system)", country="Spain", region="Canary Islands", lat=29.16, lon=-13.44,
         analog_types=["lava_tube_cave", "basaltic_volcanic"], climate="Arid subtropical", geology="Basaltic lava tube and young lava fields",
         target_bodies=["moon", "mars"], mission_objectives=["cave_exploration", "astronaut_field_ops", "general"],
         SYN=dict(terrain=4, geology=4, thermal=None, dust_aridity=3, illumination=3, ice_permafrost=0, subsurface_access=5, operational=4),
         description="Long basaltic lava tube system used for cave-exploration training."),
]

ORDER_AS = ["terrain", "thermal", "dust_aridity", "illumination", "operational", "geology"]

LIMITS = {
    "moon": ["1 g gravity vs 1/6 g", "Dense atmosphere vs hard vacuum", "No cryogenic permanently-shadowed-region temperatures"],
    "mars": ["1 g gravity vs 0.38 g", "Thick N2/O2 atmosphere vs thin CO2 atmosphere", "Biologically active environment (contamination)"],
}

REFS = [
    # ref_id, body, name, region_type, lat, lon_east(-180..180), gazetteer_fid, diameter_km, coordinate_system, traits, affinity, description
    ("moon-south-pole-region", "moon", "Lunar south polar region", "polar region", -90.0, 0.0, None, None,
     "IAU lunar body-fixed frame; the south pole is -90° latitude by definition", ["polar", "low sun angle", "permanently shadowed regions", "cold traps"],
     ["polar_desert", "permafrost_ice", "impact_crater"], "Region surrounding the lunar south pole: extreme illumination contrast and permanently shadowed crater floors."),
    ("moon-shackleton", "moon", "Shackleton crater vicinity", "crater", -89.67, 129.78, "5450", 20.92, "Planetographic, +East, -180 - 180 (Gazetteer)",
     ["polar", "permanently shadowed interior", "impact crater", "cold trap"], ["impact_crater", "polar_desert", "permafrost_ice"],
     "Crater located almost at the lunar south pole; its floor lies in permanent shadow."),
    ("moon-malapert", "moon", "Malapert crater & massif vicinity", "crater / massif", -85.0, 11.4, "3603", 72.38, "Planetographic, +East, -180 - 180 (Gazetteer)",
     ["polar", "high-relief massif", "low sun angle"], ["impact_crater", "polar_desert"],
     "South-polar crater; the neighbouring Malapert massif region was among NASA's 2022 Artemis III candidate landing regions."),
    ("moon-de-gerlache", "moon", "de Gerlache crater rim", "crater", -88.48, -88.34, "1439", 32.71, "Planetographic, +East, -180 - 180 (Gazetteer)",
     ["polar", "crater rim", "illumination extremes"], ["impact_crater", "polar_desert", "permafrost_ice"],
     "South-polar crater near Shackleton; its rim was among NASA's 2022 Artemis III candidate regions."),
    ("moon-mare-tranquillitatis", "moon", "Mare Tranquillitatis (mare basalt plains)", "mare", 8.35, 30.83, "3691", 875.75, "Planetographic, +East, -180 - 180 (Gazetteer)",
     ["basaltic plains", "volcanic", "equatorial"], ["basaltic_volcanic"],
     "Basaltic mare plain; Apollo 11 landing region. Representative lunar mare/volcanic environment."),
    ("moon-marius-hills", "moon", "Marius Hills volcanic complex (anchored at Marius crater)", "volcanic domes", 11.9, -50.84, "3715", 40.09, "Planetographic, +East, -180 - 180 (Gazetteer, Marius crater)",
     ["volcanic domes", "lava tubes", "skylight / pit"], ["basaltic_volcanic", "lava_tube_cave"],
     "Volcanic dome field in Oceanus Procellarum near Marius crater; a pit/skylight was reported there from Kaguya imagery. Coordinates are those of Marius crater (anchor), not the pit."),
    ("moon-rima-hadley", "moon", "Rima Hadley (Hadley Rille)", "sinuous rille", 25.72, 3.15, "5064", 116.09, "Planetographic, +East, -180 - 180 (Gazetteer)",
     ["volcanic channel", "basaltic", "mare edge"], ["basaltic_volcanic", "lava_tube_cave"],
     "Sinuous volcanic rille at the edge of Mare Imbrium; Apollo 15 landing region."),
    ("mars-jezero", "mars", "Jezero crater", "crater / paleolake delta", 18.41, 77.69, "14300", 47.52, "Planetocentric, +East, 0 - 360 (Gazetteer)",
     ["paleolake", "delta deposits", "aqueous alteration", "impact crater"], ["acidic_aqueous", "impact_crater", "hyperarid_desert"],
     "Crater hosting an ancient river delta; Mars 2020 Perseverance landing site."),
    ("mars-gale", "mars", "Gale crater", "crater / layered mound", -5.37, 137.81, "2071", 154.08, "Planetocentric, +East, 0 - 360 (Gazetteer)",
     ["layered sediments", "impact crater", "aqueous history", "dust"], ["impact_crater", "hyperarid_desert", "acidic_aqueous"],
     "Large crater with a central layered mound (Aeolis Mons); Curiosity rover landing site."),
    ("mars-elysium-planitia", "mars", "Elysium Planitia", "volcanic plains", 2.98, 154.74, "1784", 3000.79, "Planetocentric, +East, 0 - 360 (Gazetteer)",
     ["volcanic plains", "smooth terrain", "basaltic"], ["basaltic_volcanic", "hyperarid_desert"],
     "Broad volcanic plain; InSight landed in western Elysium Planitia."),
    ("mars-utopia-planitia", "mars", "Utopia Planitia", "plains / ground ice", 46.74, 117.52, "6260", 3560.45, "Planetocentric, +East, 0 - 360 (Gazetteer)",
     ["ground ice", "periglacial", "plains"], ["permafrost_ice", "polar_desert"],
     "Northern plains with radar-detected subsurface ice in western Utopia; Viking 2 landing region."),
    ("mars-arsia-mons", "mars", "Arsia Mons (cave-skylight candidates)", "shield volcano", -8.26, -120.09, "394", 470.0, "Planetocentric, +East, 0 - 360 (Gazetteer: 239.91°E)",
     ["shield volcano", "lava tubes", "skylights"], ["basaltic_volcanic", "lava_tube_cave"],
     "Tharsis shield volcano whose flanks host candidate cave skylights."),
    ("mars-planum-australe", "mars", "Planum Australe (south polar layered deposits)", "polar plateau", -83.35, 157.70, "4753", 1429.87, "Planetocentric, +East, 0 - 360 (Gazetteer)",
     ["polar ice", "layered deposits", "extreme cold"], ["polar_desert", "permafrost_ice"],
     "South polar plateau of layered ice-rich deposits."),
    ("mars-meridiani-planum", "mars", "Meridiani Planum", "plains / sulfate-hematite", -0.04, -3.14, "3854", 1058.53, "Planetocentric, +East, 0 - 360 (Gazetteer: 356.86°E)",
     ["sulfates", "hematite", "aqueous alteration"], ["acidic_aqueous", "hyperarid_desert"],
     "Plain with hematite and sulfate-bearing rocks; Opportunity rover landing site."),
]
RADIUS = {"moon": 1737.4, "mars": 3389.5}

REF_MULT = {
    "moon-south-pole-region": dict(illumination=1.4, ice_permafrost=1.5, thermal=1.2),
    "moon-shackleton": dict(illumination=1.5, ice_permafrost=1.6, terrain=1.2),
    "moon-malapert": dict(terrain=1.3, illumination=1.3, operational=1.2),
    "moon-de-gerlache": dict(illumination=1.4, ice_permafrost=1.4, terrain=1.2),
    "moon-mare-tranquillitatis": dict(geology=1.5, terrain=1.1, illumination=0.5, ice_permafrost=0.3),
    "moon-marius-hills": dict(geology=1.5, subsurface_access=1.8, illumination=0.5, ice_permafrost=0.3),
    "moon-rima-hadley": dict(geology=1.4, terrain=1.3, subsurface_access=1.3, illumination=0.5, ice_permafrost=0.3),
    "mars-jezero": dict(geology=1.6, dust_aridity=1.1, terrain=1.1),
    "mars-gale": dict(geology=1.4, terrain=1.3),
    "mars-elysium-planitia": dict(geology=1.3, terrain=1.2, operational=1.1),
    "mars-utopia-planitia": dict(ice_permafrost=2.0, thermal=1.2),
    "mars-arsia-mons": dict(subsurface_access=2.0, geology=1.3),
    "mars-planum-australe": dict(ice_permafrost=2.0, thermal=1.5, illumination=1.5),
    "mars-meridiani-planum": dict(geology=1.4, dust_aridity=1.1),
}

OBJECTIVES = [
    ("general", "General analog fidelity", "Balanced weights from the body profile.", {}),
    ("rover_mobility", "Rover mobility", "Trafficability, slopes, dust and logistics for rover testing.", dict(terrain=1.6, dust_aridity=1.2, operational=1.2)),
    ("drilling", "Drilling", "Subsurface sampling and drill hardware.", dict(geology=1.5, ice_permafrost=1.4, terrain=0.8)),
    ("isru", "ISRU / resource prospecting", "Ice and resource prospecting, extraction tests.", dict(ice_permafrost=1.8, geology=1.3)),
    ("habitat", "Habitat testing", "Long-duration habitation, thermal stress and isolation logistics.", dict(thermal=1.5, operational=1.4, illumination=1.1)),
    ("cave_exploration", "Cave exploration", "Subsurface robotics in lava tubes and caves.", dict(subsurface_access=2.5, terrain=1.2, geology=1.2, illumination=0.8)),
    ("astronaut_field_ops", "Astronaut field operations", "EVA procedures, field geology training and crew logistics.", dict(operational=1.5, terrain=1.2, geology=1.2)),
]

ANALOG_TYPES = {
    "polar_desert": "Polar desert", "permafrost_ice": "Permafrost / ground ice", "basaltic_volcanic": "Basaltic / volcanic",
    "impact_crater": "Impact crater", "lava_tube_cave": "Lava tube / cave", "hyperarid_desert": "Arid / hyper-arid desert",
    "acidic_aqueous": "Aqueous alteration", "high_altitude": "High altitude",
}


def write(name: str, text: str) -> None:
    (OUT / name).write_text(text, encoding="utf-8")
    print("wrote", OUT / name)


def main() -> None:
    # scoring_config.json
    cfg = {
        "meta": {"version": "fixture-1.0", "provenance": "synthetic", "notice": BANNER,
                 "basis": "Body weights for terrain/thermal/dust_aridity/illumination/operational/geology follow the AnalogSite prep pack v0 weights (person_a/SCORING_METHOD.md). ice_permafrost, subsurface_access, reference multipliers and objective multipliers are TerraAnalog fixture choices pending Bot 1's scoring_config.json.",
                 "generated": GENERATED},
        "scale_min": 0, "scale_max": 5, "min_completeness": 0.7,
        "criteria": [dict(id=c[0], label=c[1], description=c[2], earth_proxy=c[3], source_families=c[4]) for c in CRITERIA],
        "body_weights": {
            "moon": dict(terrain=1.0, thermal=1.0, dust_aridity=0.7, illumination=1.3, operational=0.9, geology=1.1, ice_permafrost=1.2, subsurface_access=0.6),
            "mars": dict(terrain=1.0, thermal=1.1, dust_aridity=1.2, illumination=0.4, operational=0.9, geology=1.1, ice_permafrost=0.9, subsurface_access=0.6),
        },
        "reference_multipliers": REF_MULT,
        "objectives": [dict(id=o[0], label=o[1], description=o[2], multipliers=o[3]) for o in OBJECTIVES],
        "default_objective": "general",
        "default_reference": {"moon": "moon-south-pole-region", "mars": "mars-jezero"},
        "value_type_confidence": {"measured": 0.9, "modeled": 0.7, "provisional": 0.5, "synthetic": 0.25, "missing": 0.0},
        "non_replicable": {
            "moon": ["Lunar gravity (1/6 g) — affects mobility, dust settling, drilling reaction forces and human locomotion.",
                     "Hard vacuum — no convective cooling, outgassing, cold welding and vacuum-specific lubrication behaviour.",
                     "Cryogenic permanently shadowed regions far colder than any Earth environment.",
                     "Unweathered, sharp, electrostatically charged regolith grains.",
                     "Space radiation (solar particle events, galactic cosmic rays) without a magnetosphere or atmosphere.",
                     "~29.5-Earth-day synodic day/night cycle and extreme thermal cycling."],
            "mars": ["Martian gravity (~0.38 g).",
                     "Thin CO2 atmosphere (~0.6 kPa mean surface pressure) — affects heat transfer, aerodynamics, dust lofting.",
                     "Surface radiation environment (no global magnetic field, thin atmosphere).",
                     "Planet-wide oxidising/perchlorate-bearing regolith chemistry at Martian scale.",
                     "Global dust storms and their duration.",
                     "Earth sites are biologically active; planetary-protection contamination conditions cannot be reproduced."],
        },
        "analog_types": ANALOG_TYPES,
    }
    write("scoring_config.json", json.dumps(cfg, indent=2) + "\n")

    # earth_analog_sites.geojson + features + evidence
    features, feat_rows, evidence = [], [], {}
    for s in SITES:
        from_pack = "AS" in s
        props = {k: v for k, v in s.items() if k not in ("AS", "SYN", "J", "lat", "lon")}
        props.update({
            "provenance": "synthetic",
            "score_status": "PREP_DRAFT (AnalogSite pack) + SYNTHETIC" if from_pack else "SYNTHETIC",
            "coordinate_note": "Approximate AOI centroid (WGS84). " + ("From AnalogSite prep pack sites.csv." if from_pack else "Fixture placement of a well-known site; verify before use."),
            "elevation_m": None,
            "environment": {"climate_class": s["climate"], "elevation": "pending Copernicus DEM extract", "land_surface_temperature": "pending MODIS LST extract",
                            "precipitation": "pending climatology extract"},
            "limitations": LIMITS[s["target_bodies"][0]] + ["All scores for this site are synthetic or provisional placeholders."],
            "imagery": None,
            "citations": [PENDING],
        })
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]}, "properties": props})
        vals: dict[str, tuple] = {}
        if from_pack:
            for cid, v in zip(ORDER_AS, s["AS"]):
                vals[cid] = (v, "provisional", "AS-PREP", s["J"][cid])
        for cid, v in s["SYN"].items():
            vals[cid] = (v, "synthetic", "SYN-FIXTURE", "Synthetic placeholder value generated for UI development.")
        ev = {}
        for c in CRITERIA:
            cid = c[0]
            if cid not in vals:
                continue
            v, vt, src, note = vals[cid]
            if v is None:
                feat_rows.append([s["site_id"], cid, "", "score_0_5", "missing", "", "", "Intentionally missing in fixture to exercise missing-data handling."])
                ev[cid] = [{"statement": "No evidence available — value missing (not imputed).", "source_id": "", "value_type": "missing", "confidence": 0.0, "citation": PENDING}]
                continue
            conf = 0.5 if vt == "provisional" else 0.25
            feat_rows.append([s["site_id"], cid, v, "score_0_5", vt, conf, src, note])
            ev[cid] = [{"statement": note, "source_id": src, "value_type": vt, "confidence": conf, "citation": PENDING}]
        evidence[s["site_id"]] = ev
    write("earth_analog_sites.geojson", json.dumps({
        "type": "FeatureCollection",
        "metadata": {"synthetic": True, "notice": BANNER, "crs": "WGS84 (EPSG:4326), [lon, lat] per RFC 7946", "generated": GENERATED,
                     "sources": "Site list partly from the team AnalogSite prep pack (PREP_DRAFT); all scores synthetic/provisional."},
        "features": features}, indent=2) + "\n")

    with (OUT / "analog_features.csv").open("w", newline="", encoding="utf-8") as fh:
        fh.write(f"# {BANNER}\n# value_type: provisional = AnalogSite PREP_DRAFT expert judgement; synthetic = generated placeholder; missing = no value (never imputed)\n")
        w = csv.writer(fh)
        w.writerow(["site_id", "criterion_id", "value", "unit", "value_type", "confidence", "source_id", "notes"])
        w.writerows(feat_rows)
    print("wrote", OUT / "analog_features.csv")

    write("site_evidence.json", json.dumps({"meta": {"synthetic": True, "notice": BANNER, "generated": GENERATED}, "evidence": evidence}, indent=2) + "\n")

    # planetary_reference_sites.geojson (real Gazetteer coordinates)
    pf = []
    for (rid, body, name, rtype, lat, lon, fid, diam, cs, traits, aff, desc) in REFS:
        cit = (f"Gazetteer of Planetary Nomenclature (IAU WGPSN / USGS Astrogeology), feature {fid}, https://planetarynames.wr.usgs.gov/Feature/{fid} (queried {GENERATED})"
               if fid else "Pole position by definition of the IAU lunar body-fixed frame.")
        pf.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": {
            "ref_id": rid, "body": body, "name": name, "region_type": rtype, "lon_east_360": round(lon % 360, 2),
            "coordinate_system": cs, "body_radius_km": RADIUS[body], "diameter_km": diam, "gazetteer_feature_id": fid,
            "description": desc, "traits": traits, "analog_type_affinity": aff, "citation": cit, "provenance": "published",
            "description_citation": PENDING}})
    write("planetary_reference_sites.geojson", json.dumps({
        "type": "FeatureCollection",
        "metadata": {"synthetic": False, "notice": "Coordinates are IAU/USGS Gazetteer values (planetocentric/IAU body-fixed, east-positive). NOT Earth WGS84. Geometry uses [lon_east, lat] for convenience only.",
                     "body_radii_km": {"moon": "1737.4 (IAU mean radius)", "mars": "3389.5 (IAU mean radius)"}, "generated": GENERATED},
        "features": pf}, indent=2) + "\n")

    # dataset_catalog.csv (real portals; status says whether values were actually used)
    cat = [
        ["AS-PREP", "AnalogSite prep pack (Person A) sites.csv", "Team (Doubler Aerospace / Space Apps team)", "", "Team-internal", "expert-judgement table", "Provisional factor scores for 12 sites", "used (PREP_DRAFT)", "provisional", "Expert judgement pending AppEEARS/DEM extracts"],
        ["SYN-FIXTURE", "TerraAnalog synthetic fixture generator", "TerraAnalog AI", "scripts/build_fixtures.py", "MIT (project)", "synthetic", "Placeholder values for UI development", "used (SYNTHETIC)", "synthetic", "NOT REAL DATA"],
        ["USGS-GAZ", "Gazetteer of Planetary Nomenclature", "IAU WGPSN / USGS Astrogeology", "https://planetarynames.wr.usgs.gov/", "Public domain (USGS)", "reference coordinates", "Moon/Mars reference coordinates", "used", "published", "Queried 2026-11-15"],
        ["TREK-MOON-WAC", "LRO WAC Global Mosaic 303ppd v02 (WMTS)", "NASA Moon Trek / LROC", "https://trek.nasa.gov/tiles/Moon/EQ/LRO_WAC_Mosaic_Global_303ppd_v02/1.0.0/WMTSCapabilities.xml", "NASA imagery (no copyright; credit NASA/GSFC/ASU)", "imagery tiles", "Moon reference viewer basemap", "used (display)", "published", "Equirectangular tile matrix, verified 200 OK 2026-11-15"],
        ["TREK-MARS-MDIM", "Viking MDIM 2.1 Colorized Global Mosaic 232m (WMTS)", "NASA Mars Trek / USGS", "https://trek.nasa.gov/tiles/Mars/EQ/Mars_Viking_MDIM21_ClrMosaic_global_232m/1.0.0/WMTSCapabilities.xml", "NASA/USGS imagery (no copyright; credit NASA/JPL/USGS)", "imagery tiles", "Mars reference viewer basemap", "used (display)", "published", "Equirectangular tile matrix, verified 200 OK 2026-11-15"],
        ["GIBS-BLUEMARBLE", "Blue Marble Shaded Relief + Bathymetry (WMTS EPSG:3857)", "NASA GIBS", "https://gibs.earthdata.nasa.gov/", "NASA (no restrictions; attribution requested)", "imagery tiles", "Earth 'satellite' basemap layer", "used (display)", "published", "Verified 200 OK 2026-11-15"],
        ["GIBS-ASTER-RELIEF", "ASTER GDEM Greyscale Shaded Relief (WMTS EPSG:3857)", "NASA GIBS / NASA-METI", "https://gibs.earthdata.nasa.gov/", "NASA (attribution requested)", "imagery tiles", "Earth terrain basemap layer", "used (display)", "published", "Verified 200 OK 2026-11-15"],
        ["NE-110M", "Natural Earth 110m land (via world-atlas npm)", "Natural Earth", "https://www.naturalearthdata.com/", "Public domain", "vector", "Offline Earth land base layer", "used (display)", "published", "Bundled; no network needed"],
        ["COP-DEM", "Copernicus DEM GLO-30", "ESA / Copernicus", "https://spacedata.copernicus.eu/collections/copernicus-digital-elevation-model", "Copernicus licence", "raster DEM", "Planned: slope/roughness extracts", "referenced (not yet extracted)", "", "Pending Bot 1"],
        ["SRTM", "SRTM GL1 v003", "NASA LP DAAC", "https://lpdaac.usgs.gov/products/srtmgl1v003/", "Public domain", "raster DEM", "Planned: slope/roughness extracts", "referenced (not yet extracted)", "", "Pending Bot 1"],
        ["MODIS-LST", "MODIS Land Surface Temperature (MOD11)", "NASA LP DAAC", "https://modis.gsfc.nasa.gov/data/dataprod/mod11.php", "Public domain", "raster", "Planned: thermal extremes", "referenced (not yet extracted)", "", "Pending Bot 1"],
        ["APPEEARS", "AppEEARS", "NASA Earthdata / LP DAAC", "https://appeears.earthdatacloud.nasa.gov/", "Public domain (product-dependent)", "extraction service", "Planned: AOI extracts", "referenced (not yet extracted)", "", "Pending Bot 1"],
        ["OSM", "OpenStreetMap", "OpenStreetMap contributors", "https://www.openstreetmap.org/copyright", "ODbL", "vector", "Planned: access/logistics", "referenced (not yet extracted)", "", "Attribution required if used"],
    ]
    with (OUT / "dataset_catalog.csv").open("w", newline="", encoding="utf-8") as fh:
        fh.write(f"# Dataset catalog for the fixture build. Portals are real; 'status' states whether values were actually used.\n")
        w = csv.writer(fh)
        w.writerow(["source_id", "name", "provider", "url", "license", "data_type", "usage", "status", "provenance", "notes"])
        w.writerows(cat)
    print("wrote", OUT / "dataset_catalog.csv")

    write("scientific_methodology.md", METHODOLOGY)
    write("source_references.md", REFERENCES)

    # analog_rankings.csv — produced by the documented scoring engine itself (fixture of Bot 1's "published" rankings)
    sys.path.insert(0, str(ROOT / "backend"))
    from app.loader import load_store
    from app.scoring import rank_sites
    st = load_store(OUT)
    with (OUT / "analog_rankings.csv").open("w", newline="", encoding="utf-8") as fh:
        fh.write(f"# {BANNER}\n# Generated by the TerraAnalog scoring engine from the fixture inputs; stands in for Bot 1's published rankings.\n")
        w = csv.writer(fh)
        w.writerow(["ref_id", "objective", "site_id", "score", "rank", "completeness", "method_version", "provenance"])
        for rid, ref in st.references.items():
            for o in OBJECTIVES:
                for r in rank_sites(st, ref, o[0]):
                    w.writerow([rid, o[0], r.site_id, "" if r.score is None else r.score, "" if r.rank is None else r.rank, r.completeness, "fixture-1.0", "synthetic"])
    print("wrote", OUT / "analog_rankings.csv")


METHODOLOGY = f"""> **{BANNER}**
> This methodology describes the TerraAnalog scoring engine as implemented. Bot 1's `scientific_methodology.md` will replace this file.

# Scientific methodology (fixture edition)

## 1. Question being answered
For a chosen **planetary reference region** (Moon or Mars) and a chosen **mission objective**, which Earth field sites are the most useful
*operational and environmental proxies* for testing hardware, procedures and crews?

Analog scores are **not** landing-site selections, do not certify flight hardware, and never claim that Earth reproduces the planetary environment.

## 2. Criteria (0–5 scale)
| Criterion | Earth proxy (planned source) |
|---|---|
| Terrain similarity | Copernicus DEM / SRTM slope & roughness |
| Geological similarity | USGS planetary analog resources + literature |
| Thermal / environmental similarity | MODIS / VIIRS land-surface temperature |
| Dust & aridity | Precipitation climatology, aridity index, SMAP |
| Illumination contrast | Latitude + DEM hillshade / insolation |
| Ice / permafrost relevance | Permafrost maps, field reports |
| Subsurface / cave access | Cave surveys |
| Operational testing suitability | OpenStreetMap + published field logistics |

## 3. Weighting
`w_c = body_weight[body][c] × reference_multiplier[ref][c] × objective_multiplier[objective][c] × user_multiplier[c]`

Body weights for six criteria follow the team's AnalogSite v0 method (Moon emphasises illumination contrast; Mars emphasises dust/aridity and thermal).
Reference and objective multipliers are listed in `scoring_config.json` and shown in the UI.

## 4. Score, completeness and confidence
* **Score** (0–100) = `100 × Σ w_c·x̂_c / Σ_present w_c`, with `x̂ = (x − min)/(max − min)`.
* **Evidence completeness** = `Σ_present w_c / Σ_all w_c`.
* **Missing values are never imputed.** If completeness < **0.70** the site is shown as *insufficient evidence* with no point score.
* Every score carries a **plausible range**: missing criteria set to the scale minimum (low) and maximum (high).
* **Confidence** = completeness × weighted mean of per-value confidence (measured 0.9, modeled 0.7, provisional 0.5, synthetic 0.25 unless a value states its own).

## 5. Sensitivity
Each criterion's weight is swept from 0× to 2× and the resulting scores and ranks are reported; rank shifts under ±50 % perturbation indicate robustness.

## 6. Clustering
Mask-aware k-means on criterion vectors (distance over shared, present criteria only) groups candidate environments without imputation.

## 7. What Earth cannot replicate
Gravity (1/6 g Moon, ~0.38 g Mars), vacuum / thin CO₂ atmosphere, space radiation, cryogenic PSR temperatures, lunar regolith electrostatics,
Martian global dust storms and planetary-protection conditions. These are listed with every recommendation.

## 8. Planetary coordinates
Reference coordinates come from the IAU/USGS Gazetteer of Planetary Nomenclature (planetocentric/IAU body-fixed, east-positive longitude).
They are displayed in body-specific viewers (equirectangular and south-polar stereographic on a sphere of the body's IAU mean radius). No Earth
geodetic (WGS84) assumptions are applied to Moon or Mars geometry.
"""

REFERENCES = f"""> **{BANNER}**

# Source references (fixture edition)

## Used in this build
1. Gazetteer of Planetary Nomenclature. IAU Working Group for Planetary System Nomenclature / USGS Astrogeology Science Center. https://planetarynames.wr.usgs.gov/ (queried 2026-11-15). Feature IDs: Shackleton 5450, Malapert 3603, de Gerlache 1439, Mare Tranquillitatis 3691, Marius 3715, Rima Hadley 5064, Jezero 14300, Gale 2071, Elysium Planitia 1784, Utopia Planitia 6260, Arsia Mons 394, Planum Australe 4753, Meridiani Planum 3854.
2. NASA Moon Trek — LRO WAC Global Mosaic 303ppd v02 WMTS. https://trek.nasa.gov/moon/
3. NASA Mars Trek — Viking MDIM 2.1 Colorized Global Mosaic 232m WMTS. https://trek.nasa.gov/mars/
4. NASA GIBS — Blue Marble Shaded Relief & Bathymetry; ASTER GDEM Greyscale Shaded Relief. https://gibs.earthdata.nasa.gov/
5. Natural Earth 110m land (public domain), packaged by the `world-atlas` npm module.
6. AnalogSite prep pack (team-internal): site longlist, PREP_DRAFT factor scores and v0 weights.

## Planned (values not yet extracted)
Copernicus DEM GLO-30; SRTM GL1; MODIS LST (MOD11); AppEEARS; OpenStreetMap; LOLA, Diviner, LROC (Moon targets); MOLA, THEMIS (Mars targets).

## Literature
Site-specific peer-reviewed citations: **{PENDING}** (Bot 1).
"""

if __name__ == "__main__":
    main()
