"""Step 13 - export the TerraAnalog outputs into the web-app data contract
(terraanalog-ai/docs/DATA_INTEGRATION.md, 9 files).

    python scripts/13_export_app_contract.py --out /workspace/terraanalog-data

Nothing is recomputed scientifically: every number comes from outputs/ and data/processed/ of this package
(steps 04-06) or from fetched source files in data/raw/. See the "App data-contract export" section that this
script appends to scientific_methodology.md for the mapping rules.

Key mapping decision (documented as a contract mismatch):
  The app scores  100 * sum(w_c * x_c/5) / sum_present(w_c)  with ONE value x per (site, criterion), while
  TerraAnalog fidelity is a per-reference *similarity*. To make the app's live score reproduce the published
  fidelity exactly, criteria are reference-specific: '<REF_ID>.<feature>' (11 features x 14 references) with
  x = 5 * similarity(site, reference, feature). body_weights select the body, reference_multipliers set the other
  references' criteria to 0, and objective multipliers are the TerraAnalog mission-profile feature weights.
  'operational_suitability' is exported with weight 0 so it is displayed but never mixed into fidelity.
"""
import argparse, csv, json, re, shutil, subprocess
from collections import defaultdict
from pathlib import Path

from common import *

CRS = {"moon": "IAU_2015:30100", "mars": "IAU_2015:49900"}
COORD_SYS = {"moon": "IAU_2015:30100 - Moon 2015 sphere (R = 1737.4 km), planetocentric latitude, east-positive longitude",
             "mars": "IAU_2015:49900 - Mars 2015, planetocentric latitude, east-positive longitude (sphere R = 3396.19 km used by the MOLA mosaic)"}
# Body radii as read from the DEM products actually used (LOLA PDS label OFFSET text; MOLA mosaic GeoTIFF CRS spheroid).
BODY_RADIUS_KM = {"moon": 1737.4, "mars": 3396.19}
RADIUS_SOURCE = {"moon": "LOLA LDEM_80S_80M PDS label ('Map values are relative to a radius of 1737.4 km') and LOLA 118 m mosaic CRS (sphere 1737400 m)",
                 "mars": "USGS MOLA 463 m mosaic GeoTIFF CRS (sphere 3396190 m)"}

FEATURES = ["lithology", "process", "landform", "resource", "slope", "ruggedness", "thermal", "aridity", "ice",
            "abiotic_surface", "dust_sediment"]
FEATURE_LABEL = {"lithology": "Lithology match", "process": "Process match", "landform": "Landform match",
                 "resource": "Resource match", "slope": "Slope similarity", "ruggedness": "Ruggedness (TRI) similarity",
                 "thermal": "Thermal similarity", "aridity": "Aridity", "ice": "Ice / permafrost agreement",
                 "abiotic_surface": "Abiotic (unvegetated) surface", "dust_sediment": "Fine-sediment (dust) similarity"}
FEATURE_SOURCE = {"lithology": "DS-WIKI", "process": "DS-WIKI", "landform": "DS-WIKI", "resource": "DS-WIKI",
                  "slope": "DS-COP-DEM30", "ruggedness": "DS-COP-DEM30", "thermal": "DS-CHELSA21", "aridity": "DS-ERA5-OM",
                  "ice": "DS-OBU-PF", "abiotic_surface": "DS-ESA-WC2021", "dust_sediment": "DS-SOILGRIDS"}
FEATURE_FAMILIES = {"lithology": ["Wikipedia (fetched text)", "Macrostrat", "peer-reviewed literature (reference side)"],
                    "process": ["Wikipedia (fetched text)", "peer-reviewed literature"], "landform": ["Wikipedia (fetched text)"],
                    "resource": ["Wikipedia (fetched text)", "peer-reviewed literature"],
                    "slope": ["Copernicus DEM GLO-30", "LRO LOLA (target)", "MGS MOLA (target)"],
                    "ruggedness": ["Copernicus DEM GLO-30", "LRO LOLA (target)", "MGS MOLA (target)"],
                    "thermal": ["CHELSA V2.1", "ERA5", "Diviner / literature (target)"], "aridity": ["ERA5 (Open-Meteo)"],
                    "ice": ["Obu et al. 2019 permafrost", "ESA WorldCover", "literature ice evidence (target)"],
                    "abiotic_surface": ["ESA WorldCover 2021"], "dust_sediment": ["SoilGrids 2.0", "Lunar regolith literature (target)"]}

# Provenance class (this package) -> app value_type
VT_MAP = {"measured": "measured", "derived_from_measured": "measured", "derived_from_classification": "modeled",
          "modeled": "modeled", "own_simple_model": "provisional", "literature_tag": "provisional",
          "hypothesized": "provisional", "unavailable": "missing"}
FEATURE_CLASS = {"slope": "derived_from_measured", "ruggedness": "derived_from_measured", "thermal": "modeled",
                 "aridity": "modeled", "ice": "modeled", "abiotic_surface": "derived_from_classification",
                 "dust_sediment": "modeled"}  # tag features handled separately

ANALOG_TYPES = {"lava_tube_cave": "Lava tube / cave", "impact_crater": "Impact structure", "permafrost_ice": "Permafrost / ground ice",
                "polar_desert": "Polar desert", "basaltic_volcanic": "Basaltic / volcanic", "aqueous_alteration": "Aqueous / hydrothermal alteration",
                "evaporite_basin": "Evaporite / salt flat", "arid_desert": "Arid / hyper-arid desert", "high_altitude": "High altitude"}

REF_DOIS = {"MOON-REF-01": ["10.1126/science.1187726", "10.1029/2010GL043751"], "MOON-REF-02": ["10.1038/nature11216", "10.1126/science.1187726"],
            "MOON-REF-03": ["10.1016/j.asr.2018.08.032"], "MOON-REF-04": ["10.1126/science.1186986", "10.1126/science.1187726"],
            "MOON-REF-05": ["10.1029/2009GL040635", "10.1029/2022GL099710"], "MOON-REF-06": ["10.1016/j.pss.2012.05.008", "10.1029/2022GL099710"],
            "MARS-REF-01": ["10.1002/2014JE004782", "10.1126/science.abo2196"], "MARS-REF-02": ["10.1126/science.1242777"],
            "MARS-REF-03": ["10.1007/s11214-016-0321-9"], "MARS-REF-04": ["10.1126/science.1172339"], "MARS-REF-06": ["10.1029/2007GL030709"]}
SITE_DOIS = {"EA-001": ["10.1126/science.1089143"], "EA-004": ["10.1029/2001JD002045"], "EA-013": ["10.1038/ncomms15263"],
             "EA-018": ["10.1016/j.earscirev.2016.11.003"]}
LAVA_TUBE_REVIEW = "10.1016/j.earscirev.2020.103288"
# Diameters only where a fetched source states them; the quoted fragment is asserted against the fetched text.
DIAMETERS = {"MOON-REF-02": (21.0, "Shackleton (crater)", "21 km (13 miles) in diameter"),
             "MARS-REF-01": (45.0, "Jezero (crater)", "45.0 km"),
             "MARS-REF-02": (154.0, "Gale (crater)", "154 km (96 mi) in diameter"),
             "MARS-REF-06": (435.0, "Arsia Mons", "435 kilometres (270 mi) in diameter")}

TAG_CONF = {"literature": 0.75, "hypothesized": 0.3}


def fnum(x):
    try:
        v = float(x)
        return None if v != v else v
    except (TypeError, ValueError):
        return None


def rd(x, n=3):
    return None if x is None else round(x, n)


def doi_meta():
    d = load_json(LIT / "crossref_dois.json")
    return {k: v for k, v in d.items() if not k.startswith("_") and (v or {}).get("status") == 200}


def cite_doi(doi, meta):
    m = meta.get(doi)
    if not m:
        raise SystemExit(f"DOI {doi} not verified - refusing to cite")
    # Crossref sometimes returns author records without a family name (e.g. the ESA Copernicus DEM DOI returns one empty
    # author). Empty names are dropped; with no named author the registrant/publisher is used. Authors are never invented.
    au = [x for x in (m.get("authors") or []) if x and x.split(",")[0].strip()]
    a = (au[0].split(",")[0].strip() + (" et al." if len(au) > 1 else "")) if au else (m.get("publisher") or "Unknown author (no author in DOI metadata)")
    title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", re.sub(r"\s*<(sub|sup)>\s*(.*?)\s*</(sub|sup)>\s*", r"\2", m.get("title") or ""))).strip()
    return f"{a} ({m.get('year')}) {title}. {m.get('container') or ''}. doi:{doi}".replace(" . ", " ")


EMPTY_PAREN = re.compile(r"\s*\(\s*[;,]?\s*\)")


def clean_quote(q):
    """Remove empty '()' left where the MediaWiki plain-text extract dropped pronunciation/IPA markup; flag the edit."""
    q2 = EMPTY_PAREN.sub("", q)
    return (q2, True) if q2 != q else (q, False)


def cite_wiki(url, rev=None):
    title = url.rsplit("/", 1)[-1].replace("_", " ")
    return f"Wikipedia contributors, '{title}'" + (f" (revision {rev})" if rev else "") + f", retrieved 2026-11-15, {url}"


def read_csv(p):
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "app_contract_export"))
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or "unknown"
    cfg = scoring_config()
    meta = doi_meta()
    feats = {r["site_id"]: r for r in read_csv(OUTPUTS / "analog_features.csv")}
    pf = {r["ref_id"]: r for r in read_csv(OUTPUTS / "planetary_features.csv")}
    refcfg = {r["ref_id"]: r for r in load_json(CONFIG / "planetary_references.json")["references"]}
    ev = load_json(OUTPUTS / "site_evidence.json")
    rank_rows = read_csv(OUTPUTS / "analog_rankings.csv")
    pairs = read_csv(PROCESSED / "pair_scores.csv")
    opcomp = load_json(OUTPUTS / "sensitivity_summary.json")["operational_components"]
    catalog = read_csv(OUTPUTS / "dataset_catalog.csv")
    profiles = cfg["mission_profiles"]
    regions = load_json(RAW / "admin1" / "regions.json")
    imagery = load_json(RAW / "imagery" / "imagery.json")
    climcls = load_json(RAW / "era5_monthly" / "climate_classes.json")["classes"]
    gaz = load_json(RAW / "gazetteer" / "reference_matches.json")
    site_ids = sorted(feats)
    ref_ids = sorted(pf, key=lambda r: (r.startswith("MARS"), r))
    body_of = {r: pf[r]["body"].lower() for r in ref_ids}

    # ---- similarity per (site, ref) from pair_scores (identical across profiles; asserted) ------------------
    sim = {}
    for p in pairs:
        key = (p["site_id"], p["ref_id"])
        vals = {f: fnum(p.get(f"sim_{f}")) for f in FEATURES}
        if key in sim and sim[key] != vals:
            raise SystemExit(f"similarities differ across profiles for {key}")
        sim[key] = vals
    missing_pairs = [(s, r) for s in site_ids for r in ref_ids if (s, r) not in sim]
    if missing_pairs:
        raise SystemExit(f"pair_scores lacks {len(missing_pairs)} site/ref pairs")

    # ---- per-site convenience --------------------------------------------------------------------------------
    rk = defaultdict(dict)
    for r in rank_rows:
        rk[r["site_id"]][r["mission_profile"]] = r
    def tags(row, k):
        return [t for t in (row.get(f"{k}_tags") or "").split(";") if t]

    def site_analog_types(s):
        f = feats[s]
        T = {k: set(tags(f, k)) for k in ("lithology", "process", "landform", "resource")}
        maat, pr, ai, el, pp = (fnum(f["maat_for_scoring_c"]), fnum(f["era5_precip_mm_yr"]), fnum(f["era5_aridity_index"]),
                                fnum(f["elev_point_m"]), fnum(f["permafrost_prob"]))
        out = []
        if "lava_tube_cave" in T["landform"] or "pit_skylight" in T["landform"]: out.append("lava_tube_cave")
        if "impact" in T["process"] or "impact_crater" in T["landform"]: out.append("impact_crater")
        if "ground_ice" in T["lithology"] | T["resource"] or "periglacial" in T["process"] or (pp is not None and pp >= 0.5): out.append("permafrost_ice")
        if maat is not None and pr is not None and maat <= -10 and pr <= 250: out.append("polar_desert")
        if "basalt_mafic" in T["lithology"] or "volcanic_effusive" in T["process"]: out.append("basaltic_volcanic")
        if T["process"] & {"hydrothermal", "acidic_aqueous"} or T["lithology"] & {"clay_phyllosilicate", "sulfate"}: out.append("aqueous_alteration")
        if "evaporitic" in T["process"] or "playa_salt_flat" in T["landform"]: out.append("evaporite_basin")
        if ai is not None and ai < 0.2 and (maat is None or maat > -10): out.append("arid_desert")
        if el is not None and el >= 3000: out.append("high_altitude")
        return out

    def ref_analog_types(r):
        f = pf[r]
        T = {k: set(tags(f, k)) for k in ("lithology", "process", "landform", "resource")}
        out = []
        if T["landform"] & {"lava_tube_cave", "pit_skylight"}: out.append("lava_tube_cave")
        if "impact" in T["process"] or "impact_crater" in T["landform"]: out.append("impact_crater")
        if fnum(f["ice_indicator"]) == 1.0:
            out.append("permafrost_ice")
            if abs(float(f["lat"])) >= 60:
                out.append("polar_desert")
        if "basalt_mafic" in T["lithology"] or T["process"] & {"volcanic_effusive", "volcanic_explosive"}: out.append("basaltic_volcanic")
        if T["process"] & {"hydrothermal", "acidic_aqueous", "fluvial_lacustrine"} or T["lithology"] & {"clay_phyllosilicate", "sulfate"}: out.append("aqueous_alteration")
        if "evaporitic" in T["process"] or T["lithology"] & {"evaporite_salts", "perchlorate_salts"}: out.append("evaporite_basin")
        if r.startswith("MARS"): out.append("arid_desert")
        if r == "MARS-REF-06": out.append("high_altitude")
        return list(dict.fromkeys(out))

    # ======================================================================================================
    # 7. scoring_config.json
    crit = []
    for r in ref_ids:
        rname = pf[r]["name"]
        for f in FEATURES:
            fd = cfg["features"][f]
            crit.append({"id": f"{r}.{f}", "label": f"{FEATURE_LABEL[f]} - {rname} ({r})",
                         "description": f"5 x TerraAnalog similarity of the Earth site to {r} on '{f}' ({fd.get('similarity')}). {fd.get('note') or ''}".strip(),
                         "earth_proxy": FEATURE_FAMILIES[f][0], "source_families": FEATURE_FAMILIES[f],
                         "ref_id": r, "feature": f})
    crit.append({"id": "operational_suitability", "label": "Operational test suitability (separate; weight 0)",
                 "description": "TerraAnalog operational score / 20 (access 0.30, trafficability 0.20, climate workability 0.20, regulatory 0.15, infrastructure 0.15). Exported with body weight 0 so it is DISPLAYED but never mixed into fidelity.",
                 "earth_proxy": "Natural Earth roads (upper-bound distance), Copernicus DEM slope, ERA5 monthly temperature, regulatory/infrastructure classes",
                 "source_families": ["Natural Earth", "Copernicus DEM", "ERA5", "literature"], "ref_id": None, "feature": "operational"})
    crit_ids = [c["id"] for c in crit]
    body_weights = {b: {c["id"]: (1.0 if c["ref_id"] and body_of[c["ref_id"]] == b else 0.0) for c in crit} for b in ("moon", "mars")}
    ref_mult = {r: {c["id"]: 0.0 for c in crit if c["ref_id"] and c["ref_id"] != r and body_of[c["ref_id"]] == body_of[r]} for r in ref_ids}
    objectives = [{"id": "general", "label": "General (equal feature weights)",
                   "description": "All 11 TerraAnalog fidelity features weighted equally against the selected reference. Not a TerraAnalog mission profile; exploratory.",
                   "multipliers": {}}]
    for pname, prof in profiles.items():
        objectives.append({"id": pname, "label": pname.replace("_", " ").title().replace("Isru", "ISRU").replace("Eva", "EVA"),
                           "description": f"{prof.get('description', '')}. TerraAnalog mission profile ({prof['body']}); published references: {', '.join(prof['references'])}. Multipliers = profile feature weights, defined only for {prof['body']} criteria.",
                           # only this profile's own body: a Moon profile carries no multipliers for Mars criteria (and vice versa)
                           "multipliers": {c["id"]: float(prof["weights"].get(c["feature"], 0.0)) for c in crit
                                           if c["ref_id"] and body_of[c["ref_id"]] == prof["body"].lower()},
                           "body": prof["body"].lower(), "published_references": prof["references"]})
    scoring = {
        "meta": {"version": f"terraanalog-app-contract-1.0.0", "provenance": "mixed", "synthetic": False,
                 "generated": "2026-11-15", "source_package": "ThynkAI/terraanalog-ai", "source_commit": commit,
                 "notice": "Real TerraAnalog AI research outputs. Scores rank relative analog fidelity for one mission objective; they are not a measure of planetary equivalence.",
                 "criteria_design": "Criteria are reference-specific ('<REF_ID>.<feature>', value = 5 x similarity). body_weights pick the body, reference_multipliers zero the other references of the same body, objective multipliers are TerraAnalog mission-profile weights. With these, the app's live score equals TerraAnalog's published fidelity for that (reference, profile).",
                 "operational_separation": "operational_suitability has weight 0 in every body/objective, so it never enters fidelity.",
                 "value_type_mapping": "see scientific_methodology.md section 'App data-contract export'"},
        "scale_min": 0, "scale_max": 5,
        "min_completeness": 0.5,
        "criteria": crit, "body_weights": body_weights, "reference_multipliers": ref_mult, "objectives": objectives,
        "default_objective": "general", "default_reference": {"moon": "MOON-REF-01", "mars": "MARS-REF-01"},
        "value_type_confidence": {"measured": 0.85, "modeled": 0.7, "provisional": 0.5, "missing": 0.0},
        "non_replicable": {
            "moon": ["Lunar gravity (about one-sixth of Earth's; wiki:Moon) - affects mobility, dust settling, drilling reaction forces and locomotion.",
                     "Hard vacuum - no convective cooling; outgassing and vacuum-specific material behaviour.",
                     "Permanently shadowed regions far colder than any Earth surface (Diviner: Paige et al. 2010, doi:10.1126/science.1187726).",
                     "Unweathered, electrostatically charged regolith grains.",
                     "Surface radiation environment without atmosphere or global magnetic field.",
                     "Lunar day/night length and illumination geometry at the poles."],
            "mars": ["Martian gravity (lower than Earth's) - affects mobility, dust and locomotion.",
                     "Thin CO2 atmosphere - affects heat transfer, aerodynamics and dust lofting.",
                     "Surface radiation environment (no global magnetic field, thin atmosphere).",
                     "Global-scale oxidising, perchlorate-bearing regolith chemistry.",
                     "Global dust storms.",
                     "Earth sites are biologically active; planetary-protection conditions cannot be reproduced."]},
        "analog_types": ANALOG_TYPES,
        "terraanalog_mission_profiles": {k: {"body": v["body"], "references": v["references"], "weights": v["weights"]} for k, v in profiles.items()},
    }
    save_json(scoring, out / "scoring_config.json")

    # ======================================================================================================
    # 3. analog_features.csv (long) + 6. site_evidence.json
    pc = cfg["provenance_confidence"]
    eq = cfg["tag_equivalences"]
    evE = ev["earth_sites"]
    evR = ev["planetary_references"]
    frows, evidence = [], defaultdict(dict)
    vt_counts = defaultdict(int)

    def tag_info(lst):
        return {t["tag"]: t for t in lst}

    for s in site_ids:
        f = feats[s]
        e = evE[s]
        for r in ref_ids:
            pfr = pf[r]
            er = evR.get(r, {})
            for feat in FEATURES:
                cid = f"{r}.{feat}"
                v = sim[(s, r)][feat]
                items = []
                if feat in ("lithology", "process", "landform", "resource"):
                    st = tag_info(e.get(feat, [])); rt = tag_info(er.get(feat, []))
                    if not st or not rt:
                        vt, conf, note = "missing", None, ("site has no " if not st else "reference has no ") + f"{feat} tags"
                        why = (f"no {feat} tag for this site is supported by its fetched sources ({', '.join(sorted(set(t['source'] for k2 in ('lithology','process','landform') for t in e.get(k2, []) if t.get('source'))) or 'none')}); keyword search of the fetched text found no {feat} term in the tag vocabulary"
                               if not st else f"{r} has no {feat} tag supported by its fetched sources")
                        items.append({"statement": f"No evidence: value missing - {why}. Similarity not computed and not imputed.",
                                      "source_id": "TA-ENGINE", "value_type": "missing", "confidence": None,
                                      "citation": f"TerraAnalog AI scoring engine (ThynkAI/terraanalog-ai @ {commit}), scripts/04_build_features.py tags_with_evidence"})
                    else:
                        confs = [TAG_CONF.get(t["provenance"], 0.3) for t in list(st.values()) + list(rt.values())]
                        conf = round(sum(confs) / len(confs), 3)
                        vt = "provisional"
                        hyp = [k for k, t in st.items() if t["provenance"] == "hypothesized"] + [f"{k} (ref)" for k, t in rt.items() if t["provenance"] == "hypothesized"]
                        shared = sorted(set(st) & set(rt))
                        note = f"Jaccard (with documented tag equivalences) of site tags {sorted(st)} vs {r} tags {sorted(rt)}; exact shared: {shared or 'none'}" + (f"; hypothesized: {hyp}" if hyp else "")
                        items.append({"statement": f"Site {feat} tags: {', '.join(sorted(st))}. {r} {feat} tags: {', '.join(sorted(rt))}. Similarity {v if v is not None else 'n/a'} (Jaccard).",
                                      "source_id": "TA-ENGINE", "value_type": "provisional", "confidence": conf,
                                      "citation": f"TerraAnalog AI scoring engine (ThynkAI/terraanalog-ai @ {commit}), scripts/similarity.py"})
                        for k in shared[:2] or sorted(st)[:1]:
                            t = st[k]
                            if t.get("quote"):
                                q, edited = clean_quote(t["quote"])
                                items.append({"statement": f"'{k}' at site: \"{q}\"" + (" [empty parentheses left by the Wikipedia plain-text extract were removed]" if edited else ""), "source_id": "DS-WIKI", "value_type": "provisional",
                                              "confidence": TAG_CONF["literature"], "citation": cite_wiki(t["source"], t.get("source_revision"))})
                            else:
                                items.append({"statement": f"'{k}' at site is an expert (hypothesized) tag; no supporting sentence was found in the fetched sources.",
                                              "source_id": "TA-ENGINE", "value_type": "provisional", "confidence": TAG_CONF["hypothesized"],
                                              "citation": "TerraAnalog config/earth_sites_master.json (tag marked '?')"})
                    src = "DS-WIKI"
                else:
                    cls = FEATURE_CLASS[feat]
                    src = FEATURE_SOURCE[feat]
                    conf = None
                    if feat in ("slope", "ruggedness"):
                        base = "t90m_r5km" if body_of[r] == "moon" else "t450m_r15km"
                        if feat == "slope":
                            ev_txt = f"Earth median/p90 slope {rd(fnum(f[base + '_slope_median_deg']), 2)}/{rd(fnum(f[base + '_slope_p90_deg']), 2)} deg ({base}); {r} {rd(fnum(pfr['ref_slope_median_deg']), 2)}/{rd(fnum(pfr['ref_slope_p90_deg']), 2)} deg ({pfr['dem_product']}, {pfr['dem_grid_res_m']} m)"
                        else:
                            ev_txt = f"Earth median TRI {rd(fnum(f[base + '_tri_median_m']), 2)} m ({base}); {r} {rd(fnum(pfr['ref_tri_median_m']), 2)} m ({pfr['dem_product']})"
                        conf = pc["derived"]
                    elif feat == "thermal":
                        ev_txt = f"Earth {f['temperature_K']} K ({f['maat_source']}, modeled annual mean air temperature); {r} {pfr['temperature_K'] or 'null'} K ({pfr['temperature_provenance'] or 'unavailable'})"
                        src = "DS-CHELSA21" if "CHELSA" in (f["maat_source"] or "") else "DS-ERA5-OM"
                        rconf = pc.get((pfr["temperature_provenance"] or "unavailable").split()[0], 0.5)
                        conf = min(pc["modeled"], rconf)
                    elif feat == "aridity":
                        ev_txt = f"ERA5 1991-2020: P {rd(fnum(f['era5_precip_mm_yr']), 0)} mm/yr, P/ET0 {f['era5_aridity_index']}; references have no liquid precipitation (defined 0)"
                        conf = pc["modeled"]
                    elif feat == "ice":
                        ps = f["permafrost_source"] or ""
                        if "logistic" in ps.lower():
                            cls, src, conf = "own_simple_model", "TA-PF-LOGISTIC", 0.5
                        else:
                            conf = pc["modeled"]
                        ev_txt = f"Earth ice indicator {f['ice_indicator']} = max(permafrost probability {f['permafrost_prob']} [{ps}], WorldCover snow/ice {f['wc_frac_snow_ice_r5km']}); {r} ice indicator {pfr['ice_indicator']} (literature ice evidence: {pfr['ice_evidence'] or 'none'})"
                    elif feat == "abiotic_surface":
                        ev_txt = f"WorldCover 2021 bare/sparse + snow/ice fraction within 5 km = {f['abiotic_fraction_r5km']}; references are unvegetated (1.0)"
                        conf = pc["modeled"]
                    else:  # dust_sediment
                        near = f.get("soil_texture_source") == "SoilGrids2_nearest_valid_pixel"
                        ev_txt = (f"SoilGrids 0-5 cm silt+clay {f['fine_fraction'] or 'null'}"
                                  + (f" (nearest valid 250 m pixel, {f['soil_nearby_distance_km']} km from the point; point pixel masked; no interpolation)" if near else "")
                                  + f"; {r} fine fraction {pfr['fine_fraction'] or 'null (no sourced value)'}")
                        conf = min(pc["modeled"], pc["derived"]) - (0.1 if near else 0.0)
                    vt = VT_MAP[cls] if v is not None else "missing"
                    if v is None:
                        conf = None
                        why = missing_reason(feat, s, r, f, pfr)
                        ev_txt = f"No evidence: value missing - {why}. Inputs: {ev_txt}"
                        note = ev_txt
                    else:
                        note = ev_txt
                    items.append({"statement": ev_txt + (f". Similarity {v}." if v is not None else ". Similarity not computed and not imputed."),
                                  "source_id": src if v is not None else src, "value_type": vt, "confidence": conf,
                                  "citation": catalog_citation(src, catalog, meta)})
                val = "" if v is None else round(5 * v, 4)  # 4 dp; published scores are computed from these exported values
                if v is None:
                    vt, conf = "missing", None
                frows.append({"site_id": s, "criterion_id": cid, "value": val, "unit": "score_0_5", "value_type": vt,
                              "confidence": "" if conf is None else conf, "source_id": src, "notes": note})
                vt_counts[vt] += 1
                evidence[s][cid] = items
        # operational
        o = opcomp.get(s, {})
        osc = fnum(next(iter(rk[s].values()))["operational_score"]) if rk[s] else None
        ocomp = fnum(next(iter(rk[s].values()))["operational_completeness"]) if rk[s] else None
        oconf = operational_confidence(o, f, e, cfg, ocomp) if osc is not None else None
        frows.append({"site_id": s, "criterion_id": "operational_suitability", "value": "" if osc is None else round(osc / 20, 4),
                      "unit": "score_0_5", "value_type": "provisional" if osc is not None else "missing", "confidence": "" if oconf is None else oconf,
                      "source_id": "TA-ENGINE",
                      "notes": f"Operational score {osc}/100 (completeness {ocomp}); components {o}; access from Natural Earth major roads (upper bound). Weight 0: never part of fidelity."})
        vt_counts["provisional" if osc is not None else "missing"] += 1
        evidence[s]["operational_suitability"] = [{"statement": f"Operational components (0-1): {o}. Road distance {f['road_distance_m'] or ('> ' + f['road_distance_censored_gt_m'] + ' m (censored)')} m; regulatory class {f['regulatory_class']}; infrastructure {f['infrastructure_class']}.",
                                                   "source_id": "DS-NATEARTH", "value_type": "provisional", "confidence": oconf,
                                                   "citation": catalog_citation("DS-NATEARTH", catalog, meta)}]
    with open(out / "analog_features.csv", "w", newline="", encoding="utf-8") as fh:
        fh.write(f"# TerraAnalog AI real research outputs (source commit {commit}). value = 5 x similarity to the reference named in criterion_id; empty = missing (never imputed).\n")
        fh.write("# value_type mapping: measured = derived from instrument DEMs; modeled = CHELSA/ERA5/SoilGrids/Obu/WorldCover-based; provisional = literature-text tags, expert classes, simple in-house models; missing = no value.\n")
        w = csv.DictWriter(fh, fieldnames=["site_id", "criterion_id", "value", "unit", "value_type", "confidence", "source_id", "notes"])
        w.writeheader(); w.writerows(frows)
    save_json({"meta": {"generated": "2026-11-15", "source_commit": commit, "synthetic": False,
                        "note": "Evidence per (site, criterion). Tag quotes are verbatim sentences from Wikipedia revisions fetched 2026-11-15; numeric statements quote the package values and their datasets."},
               "evidence": evidence}, out / "site_evidence.json", indent=None)

    # ======================================================================================================
    # 1. earth_analog_sites.geojson
    feats_out = []
    for s in site_ids:
        f = feats[s]; e = evE[s]
        top = sorted(((p, r) for p, r in rk[s].items()), key=lambda x: int(x[1]["fidelity_rank"]))
        supported = [p for p, r in top if int(r["fidelity_rank"]) <= 7]
        best = {b: max((r for p, r in rk[s].items() if r["body"].lower() == b), key=lambda r: float(r["fidelity_score"])) for b in ("moon", "mars")}
        urls = []
        for k in ("lithology", "process", "landform", "resource"):
            for t in e.get(k, []):
                if t.get("source") and t["source"] not in [u[0] for u in urls]:
                    urls.append((t["source"], t.get("source_revision")))
        dois = SITE_DOIS.get(s, []) + ([LAVA_TUBE_REVIEW] if "lava_tube_cave" in tags(f, "landform") else [])
        cites = [cite_wiki(u, rv) for u, rv in urls] + [cite_doi(d, meta) for d in dois]
        maat, pr, ai = fnum(f["maat_for_scoring_c"]), fnum(f["era5_precip_mm_yr"]), fnum(f["era5_aridity_index"])
        env = {"Elevation at point (m, Copernicus DEM, measured)": rd(fnum(f["elev_point_m"]), 1),
               "MAAT (deg C, %s, modeled)" % f["maat_source"]: rd(maat, 1),
               "Annual precipitation (mm/yr, ERA5 1991-2020, modeled)": rd(pr, 0),
               "Aridity index P/ET0 (ERA5, modeled)": rd(ai, 3),
               "Freeze-thaw days per year (ERA5, modeled)": rd(fnum(f["era5_freeze_thaw_days_yr"]), 1),
               "Permafrost probability (%s, modeled)" % f["permafrost_source"]: rd(fnum(f["permafrost_prob"]), 2),
               "Unvegetated fraction within 5 km (WorldCover 2021)": rd(fnum(f["abiotic_fraction_r5km"]), 3),
               "Median slope 30 m within 2 km (deg, Copernicus DEM)": rd(fnum(f["t30m_r2km_slope_median_deg"]), 2),
               "Fine (silt+clay) fraction 0-5 cm (SoilGrids, modeled)": rd(fnum(f["fine_fraction"]), 3),
               "Distance to mapped major road (m, Natural Earth, upper bound)": rd(fnum(f["road_distance_m"]), 0),
               "Road distance censored beyond (m)": rd(fnum(f["road_distance_censored_gt_m"]), 0),
               "Operational score (0-100, separate from fidelity)": fnum(next(iter(rk[s].values()))["operational_score"]),
               "Group": f["group"], "Sampling point": f"{f['coord_kind']} ({f['coord_source']})",
               "Best Moon profile": f"{best['moon']['mission_profile']} {best['moon']['fidelity_score']} (completeness {best['moon']['evidence_completeness']}, vs {best['moon']['matched_reference_id']})",
               "Best Mars profile": f"{best['mars']['mission_profile']} {best['mars']['fidelity_score']} (completeness {best['mars']['evidence_completeness']}, vs {best['mars']['matched_reference_id']})"}
        rg = regions["regions"].get(s) or {}
        region = rg.get("admin1") or ""
        if rg.get("country") == "Antarctica":
            region = "Antarctica (no first-level administrative division)"
        cc = climcls[s]
        img = imagery.get(s)
        img_out = None
        if img:
            who = img.get("artist") or "author not recorded in Commons metadata"
            img_out = {"url": img["url"], "license": img["license"], "license_url": img.get("license_url"),
                       "credit": f"{who} / Wikimedia Commons ({img['license']})", "attribution_page": img["file_page"],
                       "source": f"Lead image of Wikipedia article '{img['from_article']}'", "url_checked": f"HTTP {img['url_status']} on {img['checked']}"}
        props = {"site_id": s, "name": f["name"], "country": f["country"], "region": region,
                 "region_source": f"Natural Earth 1:10m admin-1 ({rg.get('admin1_type') or 'n/a'}; {rg.get('iso_3166_2') or 'n/a'}), point-in-polygon" if rg.get("admin1") else None,
                 "analog_types": site_analog_types(s),
                 "climate_class": cc["climate_class"], "aridity_class": cc["aridity_class"],
                 "climate_class_source": "Koppen-Geiger per Peel et al. (2007) Table 1, from ERA5 1991-2020 monthly normals of the 0.25 deg grid cell (scripts/02d_climate_class.py); aridity class of ERA5 P/ET0 per the UNEP scheme in Zomer et al. (2022)",
                 "climate": f"Koppen {cc['climate_class']}, {cc['aridity_class']} (ERA5 grid cell). MAAT {rd(maat, 1)} deg C ({f['maat_source']}); precipitation {rd(pr, 0)} mm/yr and P/ET0 {rd(ai, 3)} (ERA5 1991-2020). Modeled values.",
                 "geology": f"Macrostrat map unit: {f['macrostrat_lith'] or 'n/a'} ({f['macrostrat_scale'] or 'n/a'} map). Lithology tags: {', '.join(tags(f, 'lithology')) or 'none'}; process tags: {', '.join(tags(f, 'process')) or 'none'}.",
                 "description": f"{f['group'].capitalize()} TerraAnalog site. Landforms: {', '.join(tags(f, 'landform')) or 'none'}. Top-quartile (rank <= 7 of 28) TerraAnalog profiles: {', '.join(supported) or 'none'}.",
                 "target_bodies": ["moon", "mars"], "mission_objectives": supported, "environment": env,
                 "elevation_m": rd(fnum(f["elev_point_m"]), 1),
                 "limitations": [x.strip() for x in (f["limitations"] or "").split("|") if x.strip()] +
                                ["Scores rank relative analog fidelity for one mission objective; not a measure of planetary equivalence."],
                 "imagery": img_out, "provenance": "mixed", "citations": cites + [cite_doi("10.5194/hess-11-1633-2007", meta), cite_doi("10.1038/s41597-022-01493-1", meta)],
                 "coordinate_note": f"WGS84 sampling point: {f['coord_kind']} ({f['coord_source']}).",
                 "group": f["group"], "data_confidence": fnum(f["data_confidence"]), "terraanalog_site_id": s}
        feats_out.append({"type": "Feature", "id": s, "geometry": {"type": "Point", "coordinates": [float(f["lon"]), float(f["lat"])]}, "properties": props})
    save_json({"type": "FeatureCollection", "name": "earth_analog_sites",
               "metadata": {"synthetic": False, "provenance": "mixed", "source_commit": commit, "generated": "2026-11-15", "crs": "EPSG:4326 (RFC 7946)"},
               "features": feats_out}, out / "earth_analog_sites.geojson")

    # ======================================================================================================
    # 2. planetary_reference_sites.geojson
    rfeats = []
    for r in ref_ids:
        p = pf[r]; c = refcfg[r]; b = body_of[r]
        lat, lon = float(c["lat"]), float(c["lon"])
        lon = ((lon + 180) % 360) - 180 if lon != 180 else 180.0
        lon360 = lon % 360
        d = DIAMETERS.get(r)
        wiki_diam = None
        if d:
            fp, _ = wiki_file(d[1])
            if fp and d[2] in fp.read_text(encoding="utf-8"):
                wiki_diam = d[0]
            else:
                raise SystemExit(f"diameter quote for {r} not found in fetched {d[1]}")
        g = gaz.get(r) or {}
        exact = g.get("match") == "exact"
        diam = g.get("diameter_km") if exact else None  # official IAU/USGS value, only when the named feature IS the reference
        diam_src = (f"USGS Gazetteer of Planetary Nomenclature feature {g['feature_id']} ({g['name']}), {g['url']}" if exact else None)
        cites = [cite_doi(x, meta) for x in REF_DOIS.get(r, [])]
        for w in c.get("wiki", []):
            fp, info = wiki_file(w)
            if info:
                cites.append(cite_wiki(info.get("url") or "https://en.wikipedia.org/wiki/" + w.replace(" ", "_"), info.get("lastrevid")))
        traits = [f"{k}: {t}" for k in ("lithology", "process", "landform", "resource") for t in tags(p, k)]
        props = {"ref_id": r, "body": b, "name": p["name"], "region_type": p["status_class"],
                 "lon_east_360": round(lon360, 6), "coordinate_system": COORD_SYS[b], "body_radius_km": BODY_RADIUS_KM[b],
                 "lon_east": round(lon, 6),
                 "diameter_km": diam, "gazetteer_feature_id": (str(g["feature_id"]) if g.get("feature_id") is not None else None),
                 "gazetteer_feature_name": g.get("name"), "gazetteer_match": g.get("match"), "gazetteer_url": g.get("url"),
                 "gazetteer_note": ({"exact": "Reference is this named feature.",
                                     "containing": "Reference lies inside this named feature; its diameter is not the reference's, so diameter_km is null.",
                                     "none": g.get("note")}.get(g.get("match"))),
                 "description": f"{c.get('status_note', '')} Illumination: {p['illumination_summary'] or 'n/a'}. Ice evidence: {p['ice_evidence'] or 'none'}. Hazards: {p['hazards'] or 'n/a'}. Objectives: {p['mission_objectives'] or 'n/a'}.",
                 "traits": traits, "analog_type_affinity": ref_analog_types(r),
                 "citation": " | ".join(cites) if cites else "No peer-reviewed citation attached; coordinates from " + c.get("coord_source", ""),
                 "provenance": "published", "status_class": p["status_class"], "not_an_approved_base_site": True,
                 "crs": CRS[b], "coord_source": c.get("coord_source"), "body_radius_source": RADIUS_SOURCE[b],
                 "diameter_source": diam_src,
                 "diameter_wiki_km": wiki_diam, "diameter_wiki_source": (f"wiki:{d[1]} ('{d[2]}')" if wiki_diam else None),
                 "terrain": {"dem_product": p["dem_product"], "grid_res_m": fnum(p["dem_grid_res_m"]), "elevation_m": rd(fnum(p["ref_elev_point_m"]), 1),
                             "slope_median_deg": rd(fnum(p["ref_slope_median_deg"]), 2), "tri_median_m": rd(fnum(p["ref_tri_median_m"]), 2)},
                 "temperature_K": fnum(p["temperature_K"]), "temperature_provenance": p["temperature_provenance"] or None}
        rfeats.append({"type": "Feature", "id": r, "geometry": {"type": "Point", "coordinates": [round(lon, 6), lat]}, "properties": props})
    save_json({"type": "FeatureCollection", "name": "planetary_reference_sites",
               "crs_note": "NOT WGS84: planetocentric body-fixed lon/lat (Moon IAU_2015:30100, Mars IAU_2015:49900). Render on Moon/Mars basemaps only.",
               "metadata": {"synthetic": False, "generated": "2026-11-15", "source_commit": commit}, "features": rfeats}, out / "planetary_reference_sites.geojson")

    # ======================================================================================================
    # 4. analog_rankings.csv  (exact TerraAnalog fidelity per (reference, profile, site))
    # Published scores are recomputed here from the EXPORTED (4 dp) values with the app's formula, in config criteria order,
    # so a consumer that recomputes from analog_features.csv gets the same number. Score is stored at 4 dp; completeness at 3 dp.
    # Ties: rank by (-score_4dp, -completeness_3dp, site_id) - the same deterministic key the app uses.
    xval = {(fr["site_id"], fr["criterion_id"]): (None if fr["value"] == "" else float(str(fr["value"]))) for fr in frows}
    objmult = {o["id"]: o["multipliers"] for o in objectives}
    grp = defaultdict(list)
    for p in pairs:
        grp[(p["ref_id"], p["mission_profile"])].append(p)
    rrows, max_dev = [], 0.0
    for (r, prof), lst in sorted(grp.items()):
        b = body_of[r]
        active = [c for c in crit if c["ref_id"] is None or c["ref_id"] == r]
        scored = []
        for p in lst:
            sid = p["site_id"]
            tot = pres = wsum = 0.0
            for c in active:
                w = body_weights[b].get(c["id"], 0.0) * ref_mult.get(r, {}).get(c["id"], 1.0) * objmult[prof].get(c["id"], 1.0) * 1.0
                tot += w
                x = xval.get((sid, c["id"]))
                if x is None:
                    continue
                pres += w; wsum += w * ((x - 0) / 5)
            sc, comp = 100.0 * wsum / pres, pres / tot
            max_dev = max(max_dev, abs(sc - float(p["fidelity_score"])))
            scored.append((round(sc, 4), round(comp, 3), sid))
        scored.sort(key=lambda t: (-t[0], -t[1], t[2]))
        for i, (sc, comp, sid) in enumerate(scored, 1):
            rrows.append({"ref_id": r, "objective": prof, "site_id": sid, "score": sc, "rank": i,
                          "completeness": comp, "method_version": f"terraanalog-mcda-1.0.0@{commit}", "provenance": "mixed"})
    if max_dev > 0.01:
        raise SystemExit(f"recomputed score deviates from package fidelity by {max_dev}")
    with open(out / "analog_rankings.csv", "w", newline="", encoding="utf-8") as fh:
        fh.write(f"# TerraAnalog AI published fidelity per (reference, mission profile), recomputed from the exported 4 dp values (max |diff| vs package fidelity {max_dev:.5f}); score 4 dp; ties broken by (-score, -completeness, site_id). Profile-level ranking in the package = max over the profile's references.\n")
        w = csv.DictWriter(fh, fieldnames=list(rrows[0])); w.writeheader(); w.writerows(rrows)

    # ======================================================================================================
    # 5. dataset_catalog.csv
    PROV = {"DS-COP-DEM30": "measured", "DS-LOLA-80S": "measured", "DS-LOLA-118": "measured", "DS-MOLA-463": "measured",
            "DS-ESA-WC2021": "modeled", "DS-CHELSA21": "modeled", "DS-ERA5": "modeled", "DS-ERA5-OM": "modeled", "DS-OBU-PF": "modeled",
            "DS-SOILGRIDS": "modeled", "DS-MACROSTRAT": "published", "DS-NATEARTH": "published", "DS-WIKI": "published", "DS-OSM": "published",
            "DS-WORLDCLIM": "modeled", "DS-MODIS-LST": "measured", "DS-DIVINER": "measured", "DS-LCROSS": "measured"}
    STATUS = {"yes": "used", "yes_literature": "used (literature values only)", "no_catalog_only": "catalogued, not used", "blocked": "not used (blocked or credentials required)"}
    crow = []
    for c in catalog:
        crow.append({"source_id": c["dataset_id"], "name": c["name"], "provider": c["agency"], "url": c["official_url"], "license": c["license_access"],
                     "data_type": f"{c['variables']} | resolution {c['spatial_resolution']} | {c['crs']}", "usage": (c["variables"] if c["used_in_package"].startswith("yes") else
                               ("Not used: access blocked from the build host - " if c["used_in_package"] == "blocked" else "Not used: catalogued for reference only - ") + c["limitations"]),
                     "status": STATUS.get(c["used_in_package"], c["used_in_package"]), "provenance": PROV.get(c["dataset_id"], "published"),
                     "notes": "; ".join(x for x in (c["limitations"], ("doi:" + c["citation_doi"]) if c["citation_doi"] else "", f"retrieved {c['retrieval_date']}") if x)})
    crow.append({"source_id": "TA-ENGINE", "name": "TerraAnalog AI scoring engine (similarities, operational score)", "provider": "ThynkAI / TerraAnalog AI",
                 "url": "https://github.com/ThynkAI/terraanalog-ai", "license": "MIT (code, see LICENSE); derived values CC BY 4.0", "data_type": "derived values",
                 "usage": "Similarity functions, MCDA fidelity, operational score", "status": "used", "provenance": "mixed",
                 "notes": f"scripts/similarity.py, scripts/05_score.py at commit {commit}"})
    crow.append({"source_id": "TA-PF-LOGISTIC", "name": "TerraAnalog MAAT-logistic permafrost fallback", "provider": "ThynkAI / TerraAnalog AI",
                 "url": "https://github.com/ThynkAI/terraanalog-ai", "license": "MIT (code, see LICENSE); derived values CC BY 4.0", "data_type": "simple model output (probability 0-1)",
                 "usage": "Permafrost probability where Obu et al. 2019 has no coverage (Southern Hemisphere, <25N, nodata)", "status": "used", "provenance": "provisional",
                 "notes": "Documented in config/scoring_config.json permafrost_model; low confidence (0.5)"})
    with open(out / "dataset_catalog.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(crow[0])); w.writeheader(); w.writerows(crow)
    cat_ids = {c["source_id"] for c in crow}
    used = {r["source_id"] for r in frows} | {i["source_id"] for d in evidence.values() for L in d.values() for i in L}
    if used - cat_ids:
        raise SystemExit(f"uncatalogued source_ids: {sorted(used - cat_ids)}")

    # ======================================================================================================
    # 8-9. markdown
    shutil.copy(ROOT / "source_references.md", out / "source_references.md")
    with open(out / "source_references.md", "a", encoding="utf-8") as fh:
        fh.write("\n\n## App-contract source IDs\n\nEvery `source_id` in `analog_features.csv` and `site_evidence.json` is a row of `dataset_catalog.csv` "
                 "(TerraAnalog `dataset_id`s, plus `TA-ENGINE` for engine-derived values and `TA-PF-LOGISTIC` for the in-house permafrost fallback).\n"
                 "Body radii come from the DEM products themselves (LOLA PDS label; MOLA mosaic GeoTIFF CRS). Reference diameters are the official USGS Gazetteer of Planetary Nomenclature values where the reference is the named feature itself (exact match); references inside a larger named feature, and the lunar south-pole region, have null diameters.\n"
                 "New sources in this export: Natural Earth admin-1 (DS-NE-ADMIN1), USGS Gazetteer (DS-USGS-GAZ), Wikimedia Commons imagery (DS-COMMONS), "
                 "Clifford et al. (2000) Icarus doi:10.1006/icar.1999.6290 (Planum Boreum 155 K mean annual surface temperature), Peel et al. (2007) doi:10.5194/hess-11-1633-2007 (Koppen-Geiger criteria), "
                 "Zomer et al. (2022) doi:10.1038/s41597-022-01493-1 (aridity classes).\n")
    meth = (ROOT / "scientific_methodology.md").read_text(encoding="utf-8")
    meth += f"""

## App data-contract export (scripts/13_export_app_contract.py, source commit {commit})

**Criteria.** The app's score is `100 * sum(w_c * x_c/5) / sum_present(w_c)` with one value per (site, criterion). TerraAnalog fidelity is a similarity to a specific reference, so the export uses **reference-specific criteria** `<REF_ID>.<feature>` (11 features x 14 references = 154) with `x = 5 x similarity`. `body_weights` = 1 for criteria of that body's references, `reference_multipliers[ref]` = 0 for the other references of the same body, and each objective's multipliers are the TerraAnalog mission-profile feature weights, **listed only for that profile's own body** (a Moon profile has no multipliers for Mars criteria, so applying it to a Mars reference falls back to equal weights; the app flags that combination). `general` = equal weights; it is not a TerraAnalog profile.

**Published scores and ties.** `analog_rankings.csv` scores are recomputed by this script from the exported values (4 dp) with the app's formula, in config criteria order, and stored at 4 dp (completeness at 3 dp). Recomputing from `analog_features.csv` therefore reproduces them to within 0.00005 (rounding of the 4th decimal). They differ from the package's own fidelity (computed from unrounded similarities) by at most the amount stated in the CSV banner (< 0.001). Ranks use the deterministic key (-score, -completeness, site_id), the same key as the app. `min_completeness` = 0.5 (the lowest TerraAnalog pair completeness is 0.70, so no published score is suppressed).
**Operational separation.** `operational_suitability` (= operational score / 20) has weight 0 everywhere. It is displayed and is never part of fidelity.

**value_type mapping** (TerraAnalog provenance -> app):

| TerraAnalog class / input | app value_type | default confidence |
|---|---|---|
| derived from instrument DEMs (slope, TRI: Copernicus DEM vs LOLA/MOLA) | measured | 0.85 |
| modeled (CHELSA, ERA5, SoilGrids, Obu et al. permafrost) | modeled | 0.70 (min with reference-side confidence) |
| derived from a classified product (WorldCover unvegetated fraction) | modeled | 0.70 |
| in-house simple model (MAAT-logistic permafrost fallback) | provisional | 0.50 |
| literature-text categorical tags (Wikipedia sentences found) | provisional | 0.75 per tag, averaged with hypothesized tags |
| hypothesized tags (no supporting sentence) | provisional | 0.30 per tag |
| unavailable | missing (empty value, never imputed) | - |

Thermal values are always `modeled`, even where the reference temperature is a published measurement (Diviner), because the Earth side is a modeled air-temperature normal. Literature numbers are not exported as `measured` unless the underlying instrument data were read by this package.

**Analog types** (`analog_types`) are derived from tags and data using fixed rules in the export script:
* lava tube/pit landform -> lava_tube_cave
* impact process or crater -> impact_crater
* ground-ice tag, periglacial process or permafrost probability >= 0.5 -> permafrost_ice
* MAAT <= -10 deg C and P <= 250 mm/yr -> polar_desert
* basalt or effusive volcanism -> basaltic_volcanic
* references: literature ice evidence -> permafrost_ice, plus polar_desert if |lat| >= 60; every Mars reference -> arid_desert; Arsia Mons -> high_altitude
* hydrothermal/acidic process, clay or sulfate -> aqueous_alteration
* evaporitic process or salt flat -> evaporite_basin
* P/ET0 < 0.2 (and not polar) -> arid_desert
* elevation >= 3000 m -> high_altitude

`mission_objectives` lists the TerraAnalog profiles where the site ranks in the top quartile (rank <= 7 of 28).

**Evidence.** Every (site, criterion) has at least one evidence item. Where the value is missing the item starts with "No evidence: value missing -" and states why. Wikipedia quotes whose plain-text extract contained empty parentheses (where pronunciation markup was dropped) have them removed and are flagged in the statement. Citations with no named author in the DOI metadata use the registrant/publisher (e.g. "European Space Agency (2022) Copernicus DEM"); authors are never invented.

**Operational confidence.** `confidence` of `operational_suitability` = weighted mean of component confidences over the components present (same weights as the operational score: access 0.30, trafficability 0.20, climate workability 0.20, regulatory 0.15, infrastructure 0.15), multiplied by operational completeness. Component confidences: access 0.5 (Natural Earth major roads, an upper bound) or 0.3 when the distance is censored; trafficability 0.85 (DEM-derived); climate workability 0.70 (ERA5, modeled); regulatory/infrastructure 0.75 when a supporting sentence was found in the fetched source, else 0.30 (hypothesized).

**Fine sediment fallback.** Where the SoilGrids point pixel is masked, the nearest valid 250 m pixel within 10 km is used (scripts/02b_soilgrids_nearby.py). It is not interpolated, the distance is reported in the evidence, and confidence drops by 0.1 (to 0.60).

**Region, imagery, gazetteer, climate classes.**
* `region`: Natural Earth 1:10m admin-1 unit containing the sampling point (scripts/02c_admin_region.py). Antarctica has no admin-1 units.
* `imagery`: the lead image of the site's Wikipedia article, kept only if its Wikimedia Commons licence is public domain, CC0, CC BY, CC BY-SA or the Free Art License. Licence, author, file page and an HTTP 200 check are recorded (scripts/01b_imagery.py); sites without such an image stay null.
* `gazetteer_feature_id`: the USGS/IAU Gazetteer of Planetary Nomenclature ID (scripts/03b_gazetteer.py). The match is either "exact" (the reference is the named feature) or "containing" (the reference lies inside a named mare or planitia). For exact matches `diameter_km` is the official Gazetteer diameter, and the Wikipedia diameter is kept as `diameter_wiki_km`. Containing matches have a null diameter.
* `climate_class`: Koppen-Geiger type per Peel et al. (2007), doi:10.5194/hess-11-1633-2007, Table 1 (B tested first; Cs/Cw and Ds/Dw ties broken by half-year precipitation). It is computed from ERA5 1991-2020 monthly normals of the 0.25 deg grid cell, so it describes the grid cell (with its own elevation), not necessarily the exact point.
* `aridity_class`: ERA5 P/ET0 classed with the UNEP scheme as tabulated by Zomer et al. (2022), doi:10.1038/s41597-022-01493-1: <0.03 hyper-arid, 0.03-0.2 arid, 0.2-0.5 semi-arid, 0.5-0.65 dry sub-humid, >0.65 humid. Cold polar sites can class as "humid" because ET0 is very small; read it together with `climate_class`.

**Values that remain missing (not imputed; see supplementary/data_gaps.csv).**
* `dust_sediment`: no Mars reference has a sourced silt+clay fraction, and EA-004 (McMurdo Dry Valleys) has no valid SoilGrids pixel within 10 km.
* `resource`: seven sites have no resource tag supported by their fetched text, and MARS-REF-06 (Arsia Mons) has none either.
* `thermal`: MOON-REF-07 (Apollo 11 site). Only a temperature range was found in the sources read, not a mean.
* `abiotic_surface`: EA-004, because ESA WorldCover does not cover Antarctica.
* `ruggedness`: EA-011 (Salar de Uyuni). The DEM has zero relief over the window, so the log ratio is undefined.

**Known contract notes.**
1. There are 155 criteria instead of a handful. This keeps the app's live score identical to the TerraAnalog fidelity, at the cost of long criterion lists in the UI; the app groups criteria by the extra `ref_id` and `feature` keys.
2. `target_bodies` lists both bodies for every site, because every site is scored against both.
3. Supplementary research files (not part of the 9-file contract) are in `supplementary/`: `data_gaps.csv`, `radar_chart_data.json`, `sensitivity_summary.json`, `analog_profile_rankings.csv` (profile-level ranking with the Monte Carlo `mc_*` columns) and `earth_analog_site_bounds.geojson` (approximate site extents, with `boundary_status`).
"""
    (out / "scientific_methodology.md").write_text(meth, encoding="utf-8")
    # supplementary research files (outside the 9-file contract; same bytes as outputs/)
    sup = out / "supplementary"
    sup.mkdir(exist_ok=True)
    for src, dst in (("data_gaps.csv", "data_gaps.csv"), ("radar_chart_data.json", "radar_chart_data.json"),
                     ("sensitivity_summary.json", "sensitivity_summary.json"), ("analog_rankings.csv", "analog_profile_rankings.csv"),
                     ("earth_analog_site_bounds.geojson", "earth_analog_site_bounds.geojson")):
        shutil.copy(OUTPUTS / src, sup / dst)
    (sup / "README.md").write_text(
        "# Supplementary TerraAnalog research files (not part of the 9-file app contract)\n\n"
        f"Copied unchanged from `outputs/` of ThynkAI/terraanalog-ai @ {commit} by scripts/13_export_app_contract.py.\n\n"
        "| file | content |\n|---|---|\n"
        "| data_gaps.csv | per-site list of missing inputs and why |\n"
        "| radar_chart_data.json | per-profile top-5 sites with per-feature similarities |\n"
        "| sensitivity_summary.json | Monte Carlo weight-sensitivity results, operational components, strict-evidence variant |\n"
        "| analog_profile_rankings.csv | package ranking per (site, mission profile) = max over the profile's references, with mc_score_p05/p95, mc_rank_p05/p95, mc_top5_probability |\n"
        "| earth_analog_site_bounds.geojson | approximate site extents (Polygon, EPSG:4326) with boundary_status |\n", encoding="utf-8")
    print(f"exported to {out}: {len(feats_out)} sites, {len(rfeats)} references, {len(frows)} feature rows {dict(vt_counts)}, "
          f"{len(rrows)} ranking rows, {len(crow)} catalog rows, {len(crit)} criteria")


def missing_reason(feat, s, r, f, pfr):
    """Plain-language reason a similarity is missing (written into the value notes and evidence)."""
    if feat == "dust_sediment":
        if fnum(pfr.get("fine_fraction")) is None:
            return (f"{r} has no sourced silt+clay (fine) fraction: no Mars regolith source read by this package reports a fine fraction "
                    "comparable with SoilGrids 0-5 cm silt+clay (texts checked report clay-size or dust-particle sizes only)")
        return ("SoilGrids 2.0 returned no texture at the point and there is no valid 250 m pixel within 10 km "
                "(bare rock / ice areas are masked in SoilGrids)")
    if feat == "thermal":
        if fnum(pfr.get("temperature_K")) is None:
            return f"no primary published mean annual surface temperature for {r} was found (the sources read give only a temperature range, e.g. 'lunar equator where temperatures span from −150 °C to 100 °C', not a mean)"
        return "no modeled mean annual temperature at the site"
    if feat == "abiotic_surface":
        return "ESA WorldCover 2021 has no coverage of Antarctica (the tile request returned HTTP 404), so the unvegetated fraction is unknown"
    if feat == "ruggedness":
        if fnum(f.get("t90m_r5km_tri_median_m")) == 0.0:
            return ("Copernicus DEM GLO-30 has zero relief across the whole sampling window (TRI = 0 at 30, 90 and 450 m), so the log-ratio "
                    "similarity is undefined; a constant DEM surface over a salt flat is consistent with DEM flat-area editing, so no TRI floor was substituted")
        return "terrain index unavailable"
    return "input unavailable"


def operational_confidence(o, f, e, cfg, ocomp):
    """Documented confidence for operational_suitability: weighted mean of per-component confidences over the components
    present (same weights as the operational score), multiplied by operational completeness."""
    pc = cfg["provenance_confidence"]
    W = cfg["operational"]["weights"]
    c = {"access": 0.5 if fnum(f.get("road_distance_m")) is not None else 0.3,  # Natural Earth major roads = upper bound; censored = weaker
         "trafficability": pc["derived"], "climate_workability": pc["modeled"],
         "regulatory": pc.get((e.get("regulatory") or {}).get("provenance"), pc["hypothesized"]),
         "infrastructure": pc.get((e.get("infrastructure") or {}).get("provenance"), pc["hypothesized"])}
    num = den = 0.0
    for k, w in W.items():
        if o.get(k) is not None:
            num += w * c[k]; den += w
    if not den:
        return None
    return round(num / den * (ocomp if ocomp is not None else den), 3)


def catalog_citation(src, catalog, meta):
    for c in catalog:
        if c["dataset_id"] == src:
            if c["citation_doi"] and c["citation_doi"] in meta:
                return f"{c['name']} - " + cite_doi(c["citation_doi"], meta)
            return f"{c['name']} ({c['agency']}), {c['official_url']}, retrieved {c['retrieval_date']}"
    if src == "TA-PF-LOGISTIC":
        return "TerraAnalog AI MAAT-logistic permafrost fallback (config/scoring_config.json permafrost_model)"
    return "TerraAnalog AI scoring engine (ThynkAI/terraanalog-ai)"


if __name__ == "__main__":
    main()
