"""Step 01b - openly licensed imagery for Earth sites from Wikimedia Commons.

For each site's Wikipedia article (config 'wiki' list) the article's lead image (MediaWiki pageimages API) is taken,
its Commons metadata (license, artist, credit) is read via imageinfo/extmetadata, and it is kept ONLY if the licence
is public domain, CC0, CC BY, CC BY-SA or the Free Art License. The thumbnail URL (1280 px) and the file description page are both checked
with an HTTP request; anything that does not return 200 is dropped.
Output: data/raw/imagery/imagery.json
"""
import re, time, requests
from common import *

H = {"User-Agent": "TerraAnalogAI/1.0 (research package; https://github.com/ThynkAI)"}
OK = re.compile(r"^(public domain|pd|cc0|cc by(-sa)?( \d\.\d)?|fal)", re.I)  # FAL = Free Art License (free, copyleft)


def clean_html(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def main():
    sites = load_json(CONFIG / "earth_sites_master.json")
    sites = sites["sites"] if isinstance(sites, dict) else sites
    out = {}
    for s in sites:
        rec = None
        for title in s.get("wiki", []):
            r = requests.get("https://en.wikipedia.org/w/api.php", headers=H, timeout=60, params={
                "action": "query", "format": "json", "prop": "pageimages", "piprop": "original|name", "titles": title, "redirects": 1}).json()
            page = next(iter(r["query"]["pages"].values()))
            fname = page.get("pageimage")
            if not fname:
                continue
            ii = requests.get("https://commons.wikimedia.org/w/api.php", headers=H, timeout=60, params={
                "action": "query", "format": "json", "titles": f"File:{fname}", "prop": "imageinfo",
                "iiprop": "url|extmetadata|mime", "iiurlwidth": 1280}).json()
            p = next(iter(ii["query"]["pages"].values()))
            if "imageinfo" not in p:
                continue  # file hosted on en.wikipedia only (often non-free) -> skip
            info = p["imageinfo"][0]; md = info.get("extmetadata", {})
            lic = clean_html(md.get("LicenseShortName", {}).get("value"))
            if not OK.match(lic):
                print(s["site_id"], "skip licence", lic); continue
            url = (info.get("thumburl") or info.get("url")).split("?")[0]
            st1 = requests.head(url, headers=H, timeout=60, allow_redirects=True).status_code
            st2 = requests.head(info["descriptionurl"], headers=H, timeout=60, allow_redirects=True).status_code
            if st1 != 200 or st2 != 200:
                print(s["site_id"], "skip status", st1, st2); continue
            rec = {"url": url, "original_url": (info.get("url") or "").split("?")[0], "file_page": info["descriptionurl"], "license": lic,
                   "license_url": clean_html(md.get("LicenseUrl", {}).get("value")) or None,
                   "artist": clean_html(md.get("Artist", {}).get("value")) or None, "credit": clean_html(md.get("Credit", {}).get("value")) or None,
                   "from_article": title, "url_status": st1, "file_page_status": st2, "checked": "2026-11-15"}
            break
        out[s["site_id"]] = rec
        print(s["site_id"], (rec or {}).get("license"), (rec or {}).get("url", "")[:90])
        time.sleep(0.5)
    save_json(out, RAW / "imagery" / "imagery.json")


if __name__ == "__main__":
    main()
