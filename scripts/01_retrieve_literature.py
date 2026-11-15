"""Step 1 - literature retrieval.

* Wikipedia GeoData coordinates + plain-text extracts for every page cited in the
  site configs (tertiary source; used for coordinates and keyword evidence only).
* Crossref metadata for every DOI listed in config/doi_list.json (citation check).
* Archives the NASA / LROC web pages cited in planetary_references.json.

Outputs (data/raw/literature/): wikipedia_coordinates.json, wikipedia_extracts_index.json,
<Title>.txt extracts, crossref_dois.json, web/*.html
Run:  python scripts/01_retrieve_literature.py [--refresh]
"""
import sys, re, time, requests
from common import *

H = {"User-Agent": USER_AGENT}
REFRESH = "--refresh" in sys.argv
EXTRA_PAGES = ["Lunar water", "Lava tube", "Climate of Mars", "Moon", "Mars", "Lunar regolith",
               "LCROSS", "Octavia E. Butler Landing", "Bradbury Landing", "Tranquility Base", "Devon Island",
               "Flashline Mars Arctic Research Station", "Bockfjorden"]
WEB_PAGES = {
    "nasa_artemis3_regions_2024.html": "https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/",
    "lroc_pits_atlas_marius.html": "https://lroc.im-ldi.com/atlases/pits/1",
    "lroc_pits_atlas_list.html": "https://lroc.im-ldi.com/atlases/pits/list",
    "nasa_lro_pits_temperature_2022.html": "https://www.nasa.gov/solar-system/nasas-lro-finds-lunar-pits-harbor-comfortable-temperatures/",
    "nasa_science_malapert_region.html": "https://science.nasa.gov/image-detail/20100618/",
    "theregister_artemis3_2024.html": "https://www.theregister.com/offbeat/2024/10/29/nasa-narrows-artemis-iii-landing-target-list-to-nine/1205119",
}


def wiki_titles():
    t = set(EXTRA_PAGES)
    for s in earth_sites():
        t.update(s["wiki"])
    for r in planetary_refs():
        t.update(r["wiki"])
    return sorted(t)


def fetch_wikipedia():
    idx_p = LIT / "wikipedia_extracts_index.json"
    idx = load_json(idx_p) if idx_p.exists() and not REFRESH else {}
    coords = {}
    titles = wiki_titles()
    for i in range(0, len(titles), 20):
        r = requests.get("https://en.wikipedia.org/w/api.php", headers=H, timeout=60, params={
            "action": "query", "format": "json", "prop": "coordinates|info", "titles": "|".join(titles[i:i + 20]),
            "redirects": 1, "coprop": "globe|type|dim"}).json()
        for p in r["query"]["pages"].values():
            coords[p["title"]] = {"coords": p.get("coordinates"), "lastrevid": p.get("lastrevid"),
                                  "missing": "missing" in p, "retrieved": RETRIEVAL_DATE}
    save_json(coords, LIT / "wikipedia_coordinates.json")
    for t in titles:
        if t in idx and (LIT / idx[t]["file"]).exists():
            continue
        r = requests.get("https://en.wikipedia.org/w/api.php", headers=H, timeout=60, params={
            "action": "query", "prop": "extracts|info", "explaintext": 1, "titles": t, "format": "json", "redirects": 1}).json()
        pg = list(r["query"]["pages"].values())[0]
        fn = re.sub(r"[^A-Za-z0-9]+", "_", pg["title"]) + ".txt"
        (LIT / fn).write_text(pg.get("extract", ""), encoding="utf-8")
        idx[pg["title"]] = {"file": fn, "lastrevid": pg.get("lastrevid"),
                            "url": "https://en.wikipedia.org/wiki/" + pg["title"].replace(" ", "_"),
                            "retrieved": RETRIEVAL_DATE, "chars": len(pg.get("extract", ""))}
        time.sleep(0.3)
    save_json(idx, idx_p)
    print(f"wikipedia: {len(titles)} titles, {len(idx)} extracts")


def fetch_crossref():
    dois = load_json(CONFIG / "doi_list.json")["dois"]
    out_p = LIT / "crossref_dois.json"
    out = load_json(out_p) if out_p.exists() and not REFRESH else {}
    for d in dois:
        doi = d["doi"]
        if doi in out and out[doi].get("status") == 200:
            continue
        try:
            r = requests.get(f"https://api.crossref.org/works/{doi}", headers=H, timeout=60)
            rec = {"status": r.status_code, "retrieved": RETRIEVAL_DATE, "used_for": d.get("used_for")}
            if r.status_code == 200:
                m = r.json()["message"]
                rec.update({"title": (m.get("title") or [None])[0],
                            "container": (m.get("container-title") or [None])[0],
                            "year": (m.get("issued", {}).get("date-parts") or [[None]])[0][0],
                            "authors": [f"{a.get('family','')}, {a.get('given','')}".strip(", ") for a in m.get("author", [])[:6]],
                            "publisher": m.get("publisher"), "type": m.get("type")})
            else:
                # DataCite DOIs (e.g. Zenodo, PANGAEA) are not in Crossref: try doi.org content negotiation
                r2 = requests.get(f"https://doi.org/{doi}", headers={**H, "Accept": "application/vnd.citationstyles.csl+json"}, timeout=60)
                rec["doi_org_status"] = r2.status_code
                if r2.status_code == 200:
                    m = r2.json()
                    rec.update({"status": 200, "registry": "doi.org (non-Crossref)", "title": m.get("title"),
                                "container": m.get("container-title") or m.get("publisher"),
                                "year": (m.get("issued", {}).get("date-parts") or [[None]])[0][0],
                                "authors": [f"{a.get('family','')}, {a.get('given','')}".strip(", ") for a in m.get("author", [])[:6]],
                                "publisher": m.get("publisher"), "type": m.get("type")})
        except Exception as e:  # network error is recorded, not hidden
            rec = {"status": None, "error": str(e), "retrieved": RETRIEVAL_DATE}
        out[doi] = rec
        time.sleep(0.5)
    save_json(out, out_p)
    ok = sum(1 for k, v in out.items() if not k.startswith("_") and v.get("status") == 200)
    print(f"crossref/doi.org: {ok}/{len(out)} DOIs resolved")  # keys starting with _ are notes


def fetch_web():
    web = LIT / "web"
    web.mkdir(exist_ok=True)
    log = {}
    for fn, url in WEB_PAGES.items():
        p = web / fn
        if p.exists() and not REFRESH:
            log[fn] = {"url": url, "status": "cached"}
            continue
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 " + USER_AGENT}, timeout=60)
            p.write_bytes(r.content)
            log[fn] = {"url": url, "status": r.status_code, "bytes": len(r.content), "retrieved": RETRIEVAL_DATE}
        except Exception as e:
            log[fn] = {"url": url, "status": None, "error": str(e)}
    save_json(log, web / "web_fetch_log.json")


if __name__ == "__main__":
    fetch_wikipedia()
    fetch_crossref()
    fetch_web()
