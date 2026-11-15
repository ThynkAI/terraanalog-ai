"""Refresh the seven-page submission PDF using the existing dark 960x540 design.
Optional --overview and --science PNGs replace the repository's earlier UI captures.
Run with the backend environment (ReportLab/Pillow/pypdf already installed).
"""
import argparse
import io
import sys
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from PIL import Image

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP / 'backend'))
from app.loader import load_store
from app.config import RESEARCH_DATA_DIR
from app.case_studies import build_case_studies

W, H = 960, 540
BG, INK, MUTED, CYAN, ORANGE = '#080d18', '#f3f5f8', '#b5becd', '#67d4ee', '#f6a77c'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
pdfmetrics.registerFont(TTFont('UI', FONT)); pdfmetrics.registerFont(TTFont('UIBold', BOLD))


def make(output, overview=None, science=None):
    doc = build_case_studies(load_store(RESEARCH_DATA_DIR))
    c = Canvas(str(output), pagesize=(W, H))
    c.setTitle('TerraAnalog AI - Seven-slide project demonstration')
    c.setAuthor('Deep Kanabar / ThynkAI')
    def text(value, x, y, width, size=18, color=INK, bold=False):
        style = ParagraphStyle('body', fontName='UIBold' if bold else 'UI', fontSize=size, leading=size*1.38, textColor=HexColor(color))
        p = Paragraph(value, style); _, height = p.wrap(width, 900);p.drawOn(c, x, H-y-height);return height
    def page(num, label, title):
        c.setFillColor(HexColor(BG));c.rect(0,0,W,H,fill=1,stroke=0)
        c.setFillColor(HexColor(CYAN));c.rect(0,0,7,H,fill=1,stroke=0)
        text(label.upper(),42,32,860,10,CYAN)
        text(title,42,57,875,29,bold=True)
        c.setStrokeColor(HexColor('#263044'));c.line(42,34,918,34)
        text('TerraAnalog AI  /  NASA Space Apps 2026',42,513,760,8,MUTED)
        text(f'{num} / 7',870,513,48,8,MUTED)
    def link(label,url,x,y,width,size=12):
        h=text(escape(label),x,y,width,size,CYAN);c.linkURL(url,(x,H-y-h,x+width,H-y),relative=0)
    def image(path, x, y, width, height):
        if path and Path(path).exists():
            im=Image.open(path).convert('RGB'); im.thumbnail((1100,800)); ratio=min(width/im.width,height/im.height)
            iw,ih=im.width*ratio,im.height*ratio
            buffer=io.BytesIO();im.save(buffer,format='JPEG',quality=85);buffer.seek(0)
            c.drawImage(ImageReader(buffer),x+(width-iw)/2,H-y-ih,iw,ih)
    page(1,'Earth analog intelligence','Earth as a testbed for the Moon and Mars')
    text('TerraAnalog AI',42,152,420,39,bold=True)
    text('A source-traceable research tool for choosing where to test a specific mission on Earth.',42,224,410,21,MUTED)
    text('28 Earth sites<br/>14 planetary references<br/>10 specialized profiles + general mode',42,329,400,19,CYAN)
    text('Project lead: Deep Kanabar',42,453,500,12,MUTED)
    image(overview or APP/'docs/screenshots/19-final-homepage.png',498,145,420,310)
    c.showPage()
    page(2,'The problem','A useful analog depends on the test')
    for x,title,body in [(42,'Mission objective','A rover traverse, a cave robot and an ice-prospecting procedure need different terrain and evidence.'),(344,'Evidence quality','Regional models, published observations and missing measurements support different levels of inference.'),(646,'Field decisions','A shortlist needs a source trail and a plan for what to measure before organizing a campaign.')]:
        text(title,x,160,270,21,bold=True);text(body,x,211,270,18,MUTED)
    text('The contribution: a reproducible comparison and research workflow, with explicit assumptions and practical limits.',42,395,850,23,CYAN)
    c.showPage()
    page(3,'Open Earth, Moon and Mars data','The evidence stays attached to the score')
    items=[('770','Measured / derived'),('1,519','Modeled'),('1,673','Provisional'),('378','Missing')]
    for i,(v,label) in enumerate(items):
        x=42+i*226;text(v,x,152,210,37,CYAN,bold=True);text(label,x,210,210,16,MUTED)
    text('4,340 feature records. Missing values remain null.',42,279,850,22,bold=True)
    text('NASA LRO LOLA and MGS MOLA support regional terrain comparisons. Earth inputs include Copernicus DEM, WorldCover, CHELSA, ERA5, SoilGrids and permafrost models. Literature supplies additional context and proxy values.',42,328,850,18,MUTED)
    link('Dataset catalog, licenses and per-feature provenance', 'https://terraanalog-web-cqgu.onrender.com/data',42,440,850)
    c.showPage()
    page(4,'Scientific cases','Benchmark comparisons reveal the trade-offs')
    y=137
    for case in doc['cases']:
        row=next(r for r in case['comparisons'] if r['site_id']==case['site_id'])
        b,s=row['result'],row['stress_result']
        title={'holuhraun-mobility':'Holuhraun / Elysium mobility','undara-cave-robotics':'Undara / Tranquillitatis caves','svalbard-polar-prospecting':'Svalbard / Shackleton prospecting'}[case['id']]
        text(title,42,y,535,20,bold=True)
        text(f"Baseline {b['score']:.1f}, rank {b['rank']}   /   Stress {s['score']:.1f}, rank {s['rank']}",590,y,328,15,CYAN)
        text(case['stress_label']+'. '+case['novelty_status']+'.',42,y+36,870,14,MUTED)
        y+=103
    text('Each row uses one fixed target for the case and all three benchmarks. Scores are proxies out of 100. Stress tests remove selected weights and renormalize the remainder. Holuhraun-Elysium is exploratory for this mobility profile.',42,450,870,11,MUTED)
    c.showPage()
    page(5,'The working tool','A complete path through the evidence')
    image(science or APP/'docs/screenshots/18-scientific-case-final.png',42,136,550,320)
    text('1. Choose a target and objective<br/><br/>2. Compare the case with the challenge benchmarks<br/><br/>3. Remove an influential proxy<br/><br/>4. Inspect sources and export evidence',630,151,285,17,MUTED)
    link('Open the scientific case studies','https://terraanalog-web-cqgu.onrender.com/science',42,463,850,14)
    c.showPage()
    page(6,'Verification and boundaries','Software consistency supports an auditable shortlist')
    text('17 committed-data checks passed',42,143,850,25,CYAN,bold=True)
    text('The final audit checks 2,352 compatible site scores, coordinate conventions, missing-value preservation, source attribution and consistent benchmarks.',42,192,850,18,MUTED)
    text('588 published rankings reproduced',42,278,850,25,CYAN,bold=True)
    text('No rank mismatches. Maximum unrounded score difference is below 0.00005 points. This is a computational regression check. Independent field validation remains future work.',42,328,850,18,MUTED)
    link('Current build, automated tests, mobile and accessibility checks','https://github.com/ThynkAI/terraanalog-ai/actions',42,445,850,13)
    c.showPage()
    page(7,'Sources, impact and next steps','A research decision teams can inspect and repeat')
    text('Earth cannot reproduce planetary gravity, vacuum or thin atmosphere, radiation and cryogenic cold traps. Site labels do not establish novelty, permission or hardware qualification.',42,136,850,19,MUTED)
    text('Next: targeted literature assessment, permitted local surveys and measurements of the proxies that drive the result.',42,229,850,20,CYAN)
    text('Primary context: Voigt et al. 2025 (10.3847/PSJ/adb5f1), Horvath et al. 2022 (10.1029/2022GL099710), Queensland Parks, NASA AMASE and ESA. Full citations, image licenses and data sources appear in the app and repository.',42,306,850,13,MUTED)
    link('Live app: terraanalog-web-cqgu.onrender.com','https://terraanalog-web-cqgu.onrender.com',42,386,850,15)
    link('Source and evidence: github.com/ThynkAI/terraanalog-ai','https://github.com/ThynkAI/terraanalog-ai',42,422,850,14)
    text('AI assistance supported research, code and documentation under the project lead\'s direction. Runtime recommendations use deterministic scoring and keyword parsing. NASA does not endorse this project.',42,469,850,10,MUTED)
    c.showPage();c.save()

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--overview');p.add_argument('--science');args=p.parse_args()
    make(APP/'docs/TerraAnalog-AI-Space-Apps-Demo.pdf',args.overview,args.science)
