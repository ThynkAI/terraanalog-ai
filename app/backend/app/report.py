"""Server-side PDF "Site Comparison Report" (ReportLab). Content mirrors /api/compare exactly — no extra claims."""
from __future__ import annotations

import io
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .scoring import effective_weights

INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#4b5563")
ACCENT = colors.HexColor("#b4451c")
WARN_BG = colors.HexColor("#fde7f0")
WARN_FG = colors.HexColor("#9d174d")
GRID = colors.HexColor("#d1d5db")
HEAD_BG = colors.HexColor("#f3f4f6")

# Built-in Type-1 fonts only cover WinAnsi (cp1252); map the few symbols we use.
_TR = str.maketrans({"≥": ">=", "≤": "<=", "→": "->", "±": "+/-", "−": "-", "…": "...", "✓": "yes", "✗": "no"})


def _t(s) -> str:
    return escape(str(s if s is not None else "").translate(_TR)).encode("cp1252", "replace").decode("cp1252")


def _val(v, dash="—"):
    """Criterion value exactly as exported (up to 3 decimals, no rounding to 1 dp)."""
    if v is None:
        return dash
    return f"{v:.3f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


def _fmt(v, nd=1, dash="—"):
    if v is None:
        return dash
    return f"{v:.{nd}f}" if isinstance(v, float) else str(v)


def _lat(v):
    return f"{abs(v):.2f}°{'N' if v >= 0 else 'S'}"


def _lon(v):
    return f"{abs(v):.2f}°{'E' if v >= 0 else 'W'}"


def build_compare_pdf(st, sids, ref, obj, ranked, user_weights) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title=f"TerraAnalog AI — Site Comparison Report ({ref.name})", author="TerraAnalog AI",
                            subject="Earth analog site comparison", creator="TerraAnalog AI API (ReportLab)")
    ss = getSampleStyleSheet()
    H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=18, textColor=INK, spaceAfter=2, alignment=0)
    H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12, textColor=ACCENT, spaceBefore=8, spaceAfter=4)
    P = ParagraphStyle("P", parent=ss["BodyText"], fontSize=8.5, leading=11, textColor=INK)
    S = ParagraphStyle("S", parent=P, fontSize=7.5, leading=9.5, textColor=MUTED)
    C = ParagraphStyle("C", parent=P, fontSize=7.5, leading=9)
    BANNER = ParagraphStyle("B", parent=P, textColor=WARN_FG, backColor=WARN_BG, borderPadding=4, alignment=TA_CENTER, fontName="Helvetica-Bold")

    cfg = st.scoring
    crit = cfg.active_criteria(ref.ref_id)  # per-reference configs: only this reference's criteria (+ shared ones)
    obj_label = next((o.label for o in cfg.objectives if o.id == obj), obj)
    eff = effective_weights(cfg, ref, obj, user_weights)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    story = []

    story.append(Paragraph("TerraAnalog AI — Site Comparison Report", H1))
    story.append(Paragraph(_t(f"Generated {now} · reference: {ref.name} ({ref.body.title()}) · objective: {obj_label}"
                              + (" · custom weight multipliers applied" if user_weights else " · documented weights")), S))
    story.append(Spacer(1, 4))
    if st.is_synthetic:
        story.append(Paragraph("SYNTHETIC FIXTURE DATA — scores and criterion values in this report are placeholders or provisional expert "
                               "judgements, NOT measurements. Planetary reference coordinates are real (IAU/USGS Gazetteer).", BANNER))
        story.append(Spacer(1, 6))
    else:
        meta = cfg.meta if isinstance(cfg.meta, dict) else {}
        notice = meta.get("notice") or "Research dataset."
        src = f" Source: {meta.get('source_package')} @ {meta.get('source_commit')}." if meta.get("source_commit") else ""
        story.append(Paragraph(_t(notice + src), ParagraphStyle("N", parent=P, textColor=INK, backColor=HEAD_BG, borderPadding=4)))
        story.append(Spacer(1, 6))

    # Reference
    story.append(Paragraph("Planetary reference", H2))
    lon360 = f" ({ref.lon_east_360:.2f}°E, 0–360)" if ref.lon_east_360 is not None else ""
    story.append(Paragraph(_t(f"{ref.name} — {(ref.region_type or 'region').replace('_', ' ')} on the {ref.body.title()}"
                              f"{' (not an approved base site)' if getattr(ref, 'not_an_approved_base_site', False) else ''}. "
                              f"Coordinates {_lat(ref.lat)}, {_lon(ref.lon_east)}{lon360} ({ref.coordinate_system or 'IAU body-fixed'}); "
                              f"body radius {ref.body_radius_km} km (not WGS84)."), P))
    if ref.description:
        story.append(Paragraph(_t(ref.description), P))
    story.append(Paragraph(_t(f"Citation: {ref.citation}" + (f" (Gazetteer feature {ref.gazetteer_feature_id})" if ref.gazetteer_feature_id else "")), S))

    # Summary
    story.append(Paragraph("Overall analog scores", H2))
    published = {p.site_id: p for p in st.published_rankings if p.ref_id == ref.ref_id and p.objective == obj}
    rows = [["Site", "Country", "Coordinates (WGS84)", "Rank", "Score /100", "Published", "Plausible range", "Completeness", "Confidence", "Status"]]
    for sid in sids:
        s, r = st.sites[sid], ranked[sid]
        pub = published.get(sid)
        rows.append([Paragraph(_t(f"{s.name} ({sid})"), C), Paragraph(_t(s.country), C), f"{_lat(s.lat)} {_lon(s.lon)}", _fmt(r.rank),
                     _fmt(r.score), _fmt(pub.score, 2) if pub and pub.score is not None and not user_weights else "—",
                     f"{r.score_low:.1f}–{r.score_high:.1f}", f"{r.completeness * 100:.0f}%", f"{r.confidence * 100:.0f}%",
                     _t(r.status.replace("_", " "))])
    story.append(_table(rows, [64 * mm, 26 * mm, 36 * mm, 11 * mm, 18 * mm, 18 * mm, 24 * mm, 22 * mm, 20 * mm, 30 * mm]))
    if published and not user_weights:
        story.append(Paragraph("Published = the research package's own score for this (reference, objective); live scores reproduce it "
                               "(see docs/TEST_RESULTS.md).", S))
    story.append(Paragraph(_t(f"Scores use only criteria with data; sites below {cfg.min_completeness * 100:.0f}% weighted completeness are "
                              "reported as insufficient evidence with no score. The plausible range assumes every missing criterion at the "
                              "minimum / maximum value. Confidence = completeness x mean value-type confidence."), S))

    # Criterion matrix
    story.append(Paragraph("Side-by-side features (value 0–5 · value type)", H2))
    head = ["Feature", "Eff. weight"] + [st.sites[sid].name.split(" (")[0] for sid in sids] + ["Spread"]
    rows = [[Paragraph(_t(h), C) for h in head]]
    for c in crit:
        w_c = eff.get(c.id, 0)
        label = c.feature_label + ("" if w_c > 0 else " (not in score)")
        vals, row = [], [Paragraph(_t(label), C), f"{w_c:.2f}"]
        for sid in sids:
            fv = st.features.get(sid, {}).get(c.id)
            if fv is None or fv.value is None:
                row.append("missing")
            else:
                vals.append(fv.value)
                row.append(_t(f"{_val(fv.value)} · {fv.value_type}"))
        row.append(_val(max(vals) - min(vals)) if len(vals) >= 2 else "—")
        rows.append(row)
    w_site = (269 - 50 - 22 - 18) / max(1, len(sids))
    story.append(_table(rows, [50 * mm, 22 * mm] + [w_site * mm] * len(sids) + [18 * mm]))
    story.append(Paragraph(_t("Missing values are shown as missing and are never imputed."
                              + (f" Values are 5 x similarity to {ref.ref_id} (criteria {ref.ref_id}.<feature>)." if cfg.per_reference else "")
                              + " Zero-weight rows (e.g. operational suitability) are displayed separately and never mixed into the score."), S))

    # Breakdown per site
    story.append(PageBreak())
    story.append(Paragraph("Transparent score breakdown", H2))
    for sid in sids:
        s, r = st.sites[sid], ranked[sid]
        rows = [["Feature", "Value", "Value type", "Effective weight", "Points contributed", "Source"]]
        for b in r.breakdown:
            rows.append([Paragraph(_t(b.label + ("" if b.in_score else " (not in score)")), C), _val(b.value, dash="missing"),
                         _t(b.value_type), f"{b.effective_weight:.3f}", _fmt(b.contribution, 2), _t(b.source_id or "—")])
        block = [Paragraph(_t(f"{s.name} — score {_fmt(r.score)} (rank {_fmt(r.rank)})"), ParagraphStyle("h3", parent=P, fontName="Helvetica-Bold")),
                 _table(rows, [70 * mm, 20 * mm, 30 * mm, 30 * mm, 32 * mm, 40 * mm])]
        if s.limitations:
            block.append(Paragraph(_t("Limitations: " + "; ".join(s.limitations)), S))
        block.append(Spacer(1, 6))
        story.append(KeepTogether(block))

    # Non-replicable + sources
    nr = cfg.non_replicable.get(ref.body, [])
    if nr:
        story.append(Paragraph(f"What Earth cannot replicate for the {ref.body.title()}", H2))
        for item in nr:
            story.append(Paragraph(_t(f"• {item}"), P))
    used = sorted({b.source_id for sid in sids for b in ranked[sid].breakdown if b.source_id})
    if used:
        story.append(Paragraph("Sources referenced by the values above", H2))
        by_id = {d.source_id: d for d in st.datasets}
        for sid in used:
            d = by_id.get(sid)
            text = f"{sid}: {d.name} — {d.provider}. {d.url} ({d.provenance or d.status})" if d else f"{sid}: citation pending from research dataset"
            story.append(Paragraph(_t(text), S))
    story.append(Spacer(1, 6))
    story.append(Paragraph(_t(f"Method version: {cfg.meta.get('version', 'n/a') if isinstance(cfg.meta, dict) else 'n/a'}. "
                              "Full methodology: /methodology in the TerraAnalog AI app."), S))

    def _footer(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(14 * mm, 8 * mm, "TerraAnalog AI · Site Comparison Report" + (" · SYNTHETIC DATA" if st.is_synthetic else ""))
        canvas.drawRightString(landscape(A4)[0] - 14 * mm, 8 * mm, f"Page {d.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def _table(rows, widths):
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 7.5),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.5),
        ("BACKGROUND", (0, 0), (-1, 0), HEAD_BG),
        ("GRID", (0, 0), (-1, -1), 0.4, GRID),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
    ]))
    return t
