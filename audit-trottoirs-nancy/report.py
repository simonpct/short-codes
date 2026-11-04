"""Rapport PDF 2 pages — audit OSM des cheminements piétons de Nancy."""
import pickle, sys, math, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.patches import Circle, Polygon as MPoly
from matplotlib.lines import Line2D
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image, NextPageTemplate, PageBreak, Flowable)
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

R = pickle.load(open(sys.argv[1], "rb")); OUTDIR = sys.argv[2]; PDF = sys.argv[3]
DATE = sys.argv[4]; FONTDIR = sys.argv[5]; CT = pickle.load(open(sys.argv[6], "rb")); ZK = pickle.load(open(sys.argv[7], "rb"))
# fusion : « renseigné sur la chaussée seulement » = trottoir non dessiné
R["pieces"] = [(g, "none" if c == "tag" else c) for g, c in R["pieces"]]
R["length_by"]["none"] += R["length_by"].pop("tag", 0)

# ---------------- palette ----------------
NAVY = "#0b1f33"; INK = "#0f172a"; MUTED = "#64748b"; LINE = "#e2e8f0"; SOFT = "#f8fafc"
ACC = "#4f46e5"
GREEN, AMBER, RED, GREY = "#10b981", "#f59e0b", "#ef4444", "#94a3b8"
COL = {"sep": GREEN, "tag": AMBER, "no": GREY, "none": RED}
LAB = {"sep": "Trottoir dessiné", "no": "Pas de trottoir déclaré", "none": "Trottoir non dessiné"}

# ---------------- maps ----------------
plt.rcParams.update({"font.family": "Inter", "font.size": 7, "text.color": INK})

def base(ax):
    ax.add_collection(PolyCollection(R["ctx"]["green"], facecolor="#e7f3ec", edgecolor="none", zorder=0))
    ax.add_collection(PolyCollection(R["ctx"]["water"], facecolor="#dbeafe", edgecolor="none", zorder=0))
    ax.add_collection(LineCollection(R["ctx"]["river"], colors="#bfdbfe", linewidths=1.4, zorder=0))
    ax.add_collection(PolyCollection(R["ctx"]["building"], facecolor="#eef1f5", edgecolor="none", zorder=0.5))
    ax.add_collection(LineCollection(R["ctx"]["rail"], colors="#cbd5e1", linewidths=0.6, linestyles=(0, (3, 2)), zorder=0.6))
    ax.add_patch(MPoly(R["city"], closed=True, fill=False, edgecolor=NAVY, lw=0.9, ls=(0, (5, 2.5)), zorder=5))
    ax.set_aspect("equal"); ax.axis("off")

def scalebar(ax, x, y, L=500):
    ax.plot([x, x + L / 2], [y, y], color=INK, lw=2.4, solid_capstyle="butt", zorder=10)
    ax.plot([x + L / 2, x + L], [y, y], color="white", lw=2.4, solid_capstyle="butt", zorder=10)
    ax.plot([x, x + L], [y, y], color=INK, lw=0.4, zorder=11)
    ax.text(x + L, y + 45, f"{L} m", ha="right", va="bottom", fontsize=5.5, color=MUTED, zorder=10)
    ax.text(x, y + 45, "0", ha="left", va="bottom", fontsize=5.5, color=MUTED, zorder=10)

def legend(ax, handles, title=None, fs=6):
    lg = ax.legend(handles=handles, loc="lower left", fontsize=fs, frameon=True, framealpha=0.95,
                   edgecolor="none", facecolor="white", title=title, title_fontsize=fs, alignment="left",
                   borderpad=0.9, handlelength=1.6, labelspacing=0.55)
    lg.get_frame().set_boxstyle("round,pad=0.2,rounding_size=0.8")
    if title: lg.get_title().set_fontweight("semibold")

xs = [p[0] for p in R["city"]]; ys = [p[1] for p in R["city"]]
MAP_AR = 0.76
X0, X1 = min(xs) - 60, max(xs) + 60
cyy = (min(ys) + max(ys)) / 2; hh = (X1 - X0) * MAP_AR
Y0, Y1 = cyy - hh / 2, cyy + hh / 2

fig = plt.figure(figsize=(7.4, 7.4 * MAP_AR), dpi=300)
ax = fig.add_axes([0, 0, 1, 1]); base(ax)
for c in ["no", "none", "sep"]:
    segs = [p[0] for p in R["pieces"] if p[1] == c]
    ax.add_collection(LineCollection(segs, colors=COL[c], linewidths=1.15, capstyle="round",
                                     zorder=3.5 if c == "none" else 3))
for i, z in enumerate(R["zones"], 1):
    ax.add_patch(Circle(z["c"], z["r"], fc=ACC, alpha=0.06, ec="none", zorder=5.5))
    ax.add_patch(Circle(z["c"], z["r"], fill=False, ec=ACC, lw=1.1, zorder=6))
    ang = math.radians(48)
    lx, ly = z["c"][0] + z["r"] * math.cos(ang), z["c"][1] + z["r"] * math.sin(ang)
    ax.add_patch(Circle((lx, ly), 70, fc=ACC, ec="white", lw=1, zorder=7))
    ax.text(lx, ly - 4, str(i), ha="center", va="center", color="white", fontsize=6, weight="bold", zorder=8)
ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1)
h = [Line2D([], [], color=COL[c], lw=2.6, solid_capstyle="round", label=LAB[c]) for c in ["sep", "none", "no"]]
h.append(Line2D([], [], marker="o", ls="", mfc=(0.31, 0.27, 0.9, 0.12), mec=ACC, ms=8, label="Zone de micromapping prioritaire"))
legend(ax, h, "Voirie analysée")
scalebar(ax, X1 - 750, Y0 + 200)
ax.text(X1 - 60, Y0 + 60, "© contributeurs OpenStreetMap", ha="right", va="bottom", fontsize=4.5, color=MUTED, zorder=10)
fig.savefig(f"{OUTDIR}/map_sidewalks.png", dpi=300); plt.close(fig)

# zoom crossings
cx = sum(z["c"][0] for z in R["zones"]) / len(R["zones"]); cy = sum(z["c"][1] for z in R["zones"]) / len(R["zones"])
W = H = 2500
fig = plt.figure(figsize=(4.0, 4.0), dpi=300)
ax = fig.add_axes([0, 0, 1, 1]); base(ax)
ax.add_collection(LineCollection([p[0] for p in R["pieces"]], colors="#d5dbe3", linewidths=0.7, zorder=2))
ax.add_collection(LineCollection(R["sidewalk_geoms"], colors="#9fdcc3", linewidths=0.5, zorder=2.2))
def cr_cat(t):
    if t.get("crossing") == "traffic_signals" or t.get("crossing:signals") == "yes":
        return "sig_snd" if "traffic_signals:sound" in t else "sig"
    return "full" if (t.get("crossing") not in (None, "yes") and "tactile_paving" in t and "kerb" in t) else "part"
CC = {"sig_snd": (ACC, "Feu piéton — son renseigné", 7), "sig": (RED, "Feu piéton — son non renseigné", 7),
      "full": (GREEN, "Passage complet (type, bande d'éveil, bordure)", 3.2), "part": (AMBER, "Passage incomplet", 3.2)}
for k in ["part", "full", "sig", "sig_snd"]:
    pts = [c[0] for c in R["crossings"] if cr_cat(c[1]) == k]
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=CC[k][2], c=CC[k][0], lw=0.25 if k.startswith("sig") else 0,
               edgecolors="white", zorder=5 if k.startswith("sig") else 4)
kp = [k[0] for k in R["kerbs"]]
ax.scatter([p[0] for p in kp], [p[1] for p in kp], s=1.3, marker="s", c="#8b5cf6", lw=0, zorder=4.5)
for i, z in enumerate(R["zones"], 1):
    ax.add_patch(Circle(z["c"], z["r"], fill=False, ec=ACC, lw=0.7, ls=(0, (3, 2)), zorder=6))
    ang = math.radians(48)
    lx, ly = z["c"][0] + z["r"] * math.cos(ang), z["c"][1] + z["r"] * math.sin(ang)
    ax.add_patch(Circle((lx, ly), 55, fc=ACC, ec="white", lw=0.6, zorder=7))
    ax.text(lx, ly - 3, str(i), ha="center", va="center", color="white", fontsize=4.6, weight="bold", zorder=8)
ax.set_xlim(cx - W / 2, cx + W / 2); ax.set_ylim(cy - H / 2 - 150, cy + H / 2 - 150)
h = [Line2D([], [], marker="o", ls="", mfc=CC[k][0], mec="none", ms=4, label=CC[k][1]) for k in CC]
h.append(Line2D([], [], marker="s", ls="", mfc="#8b5cf6", mec="none", ms=3, label="Bordure cartographiée"))
h.append(Line2D([], [], color="#9fdcc3", lw=1.6, label="Trottoir dessiné"))
legend(ax, h, fs=5)
scalebar(ax, cx + W / 2 - 560, cy - H / 2 - 150 + 110, 400)
fig.savefig(f"{OUTDIR}/map_crossings.png", dpi=300); plt.close(fig)

# ---------------- fonts & styles ----------------
for name, f in [("In", "Inter-Regular"), ("InL", "Inter-Light"), ("InM", "Inter-Medium"), ("InS", "Inter-SemiBold"),
                ("InB", "Inter-Bold"), ("ID", "InterDisplay-SemiBold"), ("IDB", "InterDisplay-Bold"), ("IDX", "InterDisplay-ExtraBold")]:
    pdfmetrics.registerFont(TTFont(name, os.path.join(FONTDIR, f + ".ttf")))
addMapping("In", 0, 0, "In"); addMapping("In", 1, 0, "InS"); addMapping("In", 0, 1, "In"); addMapping("In", 1, 1, "InS")

def st(**k):
    d = dict(fontName="In", fontSize=7.8, leading=10.6, textColor=colors.HexColor(INK)); d.update(k)
    return ParagraphStyle("s", **d)
BODY = st(); SMALL = st(fontSize=6.4, leading=8.4, textColor=colors.HexColor(MUTED))
EYEBROW = st(fontName="InS", fontSize=6.6, leading=8, textColor=colors.HexColor(ACC))
H2 = st(fontName="ID", fontSize=13, leading=16, spaceAfter=3)

def section(num, eyebrow, title):
    return [Paragraph(f"{num}&nbsp;&nbsp;·&nbsp;&nbsp;{eyebrow.upper()}", EYEBROW), Paragraph(title, H2)]

pct = lambda a, b: f"{100 * a / b:.0f} %" if b else "–"
LB = R["length_by"]; TOT = R["total_len"]
cs, ss, ks = R["cr_stats"], R["sig_stats"], R["kb_stats"]
nps = ss["ped_crossings_signals"]; snd = nps - ss["sound"].get("absent", 0)
ncr = cs["n"]; tact = ncr - cs["tactile"].get("absent", 0)
typed = ncr - cs["crossing"].get("absent", 0) - cs["crossing"].get("yes", 0)
kerbnode = ncr - cs["kerb_on_node"].get("absent", 0)

class Bar(Flowable):
    """Mini barre de progression + valeur."""
    def __init__(self, frac, color, w=24 * mm, label=None):
        super().__init__(); self.f = max(0, min(1, frac)); self.c = color; self.w = w; self.label = label
    def wrap(self, aw, ah): return self.w, 7
    def draw(self):
        c = self.canv; bw = self.w - 11 * mm
        c.setFillColor(colors.HexColor("#eef2f7")); c.roundRect(0, 1.6, bw, 3.6, 1.8, stroke=0, fill=1)
        if self.f > 0:
            c.setFillColor(colors.HexColor(self.c)); c.roundRect(0, 1.6, max(3.6, bw * self.f), 3.6, 1.8, stroke=0, fill=1)
        c.setFillColor(colors.HexColor(INK)); c.setFont("InM", 7)
        c.drawRightString(self.w, 1.2, self.label or f"{self.f * 100:.0f} %")

def tstyle(extra=()):
    return TableStyle([
        ("FONT", (0, 0), (-1, -1), "In", 7.3), ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(INK)),
        ("FONT", (0, 0), (-1, 0), "InS", 6.2), ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(MUTED)),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor(LINE)),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(LINE)), ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4.4),
        ("TOPPADDING", (0, 0), (-1, 0), 4), ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), *extra])

# ---------------- page decorations ----------------
PW, PH = A4; M = 14 * mm; FW = PW - 2 * M
HEAD1 = 84 * mm   # hauteur bandeau page 1

def kpi_card(c, x, y, w, h, val, lab, color):
    c.setFillColor(colors.white); c.setStrokeColor(colors.HexColor(LINE)); c.setLineWidth(0.6)
    c.roundRect(x, y, w, h, 3 * mm, stroke=1, fill=1)
    c.setFillColor(colors.HexColor(color)); c.roundRect(x + 4 * mm, y + h - 4.2 * mm, 7 * mm, 1.3 * mm, 0.65 * mm, stroke=0, fill=1)
    c.setFillColor(colors.HexColor(INK)); c.setFont("IDB", 22); c.drawString(x + 4 * mm, y + h - 13.5 * mm, val)
    c.setFillColor(colors.HexColor(MUTED)); c.setFont("In", 6.6)
    for i, line in enumerate(lab.split("\n")): c.drawString(x + 4 * mm, y + 6.2 * mm - i * 8.2, line)

def footer(c, doc):
    c.setFont("In", 5.5); c.setFillColor(colors.HexColor(GREY)); c.drawString(M, 8 * mm, "Données OpenStreetMap")
    c.setFont("InS", 6.5); c.setFillColor(colors.HexColor(INK)); c.drawRightString(PW - M, 8 * mm, f"{doc.page:02d} / 02")

def page1(c, doc):
    c.saveState()
    c.setFillColor(colors.HexColor(NAVY)); c.rect(0, PH - HEAD1, PW, HEAD1, stroke=0, fill=1)
    c.setStrokeColor(colors.HexColor("#16304d")); c.setLineWidth(0.6)
    for i in range(14): c.line(PW - 70 * mm + i * 6 * mm, PH, PW - 30 * mm + i * 6 * mm, PH - HEAD1 + 18 * mm)
    c.setFillColor(colors.HexColor("#a5b4fc")); c.setFont("InS", 7)
    c.drawString(M, PH - 15 * mm, "AUDIT OPENSTREETMAP  ·  ACCESSIBILITÉ PIÉTONNE")
    c.setFillColor(colors.white); c.setFont("IDB", 25); c.drawString(M, PH - 26 * mm, "Cartographie OSM à Nancy")
    c.setFillColor(colors.HexColor("#c7d2fe")); c.drawString(M, PH - 35.5 * mm, "Couverture à 100 % + Maintenance")
    intro = Paragraph(
        "<b>OpenStreetMap</b> est la plus grande carte collaborative ouverte au monde. Elle est à la cartographie ce que "
        "Wikipédia est aux encyclopédies. Avec un groupe de contributeurs bénévoles, nous avons cartographié la plupart "
        "des cheminements piétons à Nancy. Ces données, directement exploitables par des applications de guidage telles que "
        "<b>SonarVision</b>, ont une valeur inestimable pour les utilisateurs déficients visuels.",
        st(fontSize=8.6, leading=12.4, textColor=colors.HexColor("#cbd5e1")))
    iw, ih = intro.wrap(FW * 0.86, 40 * mm); intro.drawOn(c, M, PH - 43 * mm - ih)
    txt = "Novembre 2026"; tw = pdfmetrics.stringWidth(txt, "InS", 7) + 8 * mm
    c.setFillColor(colors.HexColor("#1e3a5f")); c.roundRect(PW - M - tw, PH - 17.5 * mm, tw, 6 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white); c.setFont("InS", 7); c.drawCentredString(PW - M - tw / 2, PH - 15.3 * mm, txt)
    gap = 3.5 * mm; w = (FW - 3 * gap) / 4; h = 24 * mm; y = PH - HEAD1 - h / 2 + 2 * mm
    data = [(pct(LB["sep"], TOT), "de la voirie bordée d'un\ntrottoir dessiné", GREEN),
            (pct(LB["none"], TOT), "de la voirie sans\ntrottoir dessiné", RED),
            (pct(ss["sound"].get("absent", 0), nps), f"des {nps} feux piétons sans\ninformation sonore", ACC),
            (pct(kerbnode, ncr), f"des {ncr} passages piétons\navec bordure renseignée", AMBER)]
    for i, (v, l, col) in enumerate(data): kpi_card(c, M + i * (w + gap), y, w, h, v, l, col)
    footer(c, doc); c.restoreState()

def page2(c, doc):
    c.saveState()
    c.setFillColor(colors.HexColor(NAVY)); c.rect(0, PH - 11 * mm, PW, 11 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white); c.setFont("ID", 8.5); c.drawString(M, PH - 7 * mm, "Cartographie OSM à Nancy")
    c.setFillColor(colors.HexColor("#a5b4fc")); c.setFont("InS", 6.5); c.drawRightString(PW - M, PH - 7 * mm, "AUDIT OPENSTREETMAP  ·  NOVEMBRE 2026")
    footer(c, doc); c.restoreState()

doc = BaseDocTemplate(PDF, pagesize=A4, title="Audit OSM — cheminements piétons de Nancy", author="Audit OpenStreetMap",
                      subject="Trottoirs, micromapping, passages piétons, bordures, feux sonores")
top1 = PH - HEAD1 - 14 * mm
doc.addPageTemplates([
    PageTemplate("p1", [Frame(M, 13 * mm, FW, top1 - 13 * mm, id="a", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=page1),
    PageTemplate("p2", [Frame(M, 13 * mm, FW, PH - 17 * mm - 13 * mm, id="b", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=page2)])

def card(img, w, h):
    return Table([[Image(img, width=w - 2, height=h - 2)]], colWidths=[w],
                 style=[("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(LINE)), ("ROUNDEDCORNERS", [8, 8, 8, 8]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1),
                        ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)])

s = [NextPageTemplate("p2")]
# ===== PAGE 1 =====
s += section("01", "Trottoirs", "Couverture des trottoirs dans OpenStreetMap")
s.append(card(f"{OUTDIR}/map_sidewalks.png", FW, FW * MAP_AR))
s.append(Spacer(1, 8))

s += section("02", "Contributeurs", "Qui maintient les trottoirs ?")
NAMES = {"simonpct": "Simon PICOT"}
fr = lambda x: f"{x:.1f} %".replace(".", ",")
class Contrib(Flowable):
    H = 22 * mm
    def wrap(self, aw, ah): return FW, self.H
    def draw(self):
        c = self.canv; h = self.H; L = CT["len"]; top = CT["top"]
        c.setFillColor(colors.white); c.setStrokeColor(colors.HexColor(LINE)); c.setLineWidth(0.6)
        c.roundRect(0, 0, FW, h, 3 * mm, stroke=1, fill=1)
        u, n, l = top[0]
        c.setFillColor(colors.HexColor(ACC)); c.setFont("IDB", 20); c.drawString(5 * mm, h - 10.5 * mm, fr(100 * l / L))
        vw = pdfmetrics.stringWidth(fr(100 * l / L), "IDB", 20)
        c.setFillColor(colors.HexColor(INK)); c.setFont("InS", 9)
        c.drawString(8 * mm + vw, h - 7.2 * mm, f"{NAMES.get(u, u)}")
        nw = pdfmetrics.stringWidth(NAMES.get(u, u), "InS", 9)
        c.setFillColor(colors.HexColor(MUTED)); c.setFont("In", 8); c.drawString(9.5 * mm + vw + nw, h - 7.2 * mm, f"({u})")
        c.setFont("In", 6.8); c.drawString(8 * mm + vw, h - 10.6 * mm, "auteur des dernières mises à jour des trottoirs")
        # barre empilée
        x0, bw, y = 5 * mm, FW - 10 * mm, 5.2 * mm
        c.setFillColor(colors.HexColor("#e2e8f0")); c.roundRect(x0, y, bw, 2.6 * mm, 1.3 * mm, stroke=0, fill=1)
        c.setFillColor(colors.HexColor(ACC)); c.roundRect(x0, y, bw * l / L, 2.6 * mm, 1.3 * mm, stroke=0, fill=1)
        x = x0 + bw * l / L
        for (u2, n2, l2), col in zip(top[1:3], ["#a5b4fc", "#c7d2fe"]):
            c.setFillColor(colors.HexColor(col)); c.rect(x + 0.4, y, bw * l2 / L - 0.4, 2.6 * mm, stroke=0, fill=1); x += bw * l2 / L
        rest = 100 - 100 * sum(t[2] for t in top[:3]) / L
        c.setFillColor(colors.HexColor(MUTED)); c.setFont("In", 6.4)
        c.drawString(x0, 1.8 * mm, f"2. {top[1][0]}  {fr(100 * top[1][2] / L)}     3. {top[2][0]}  {fr(100 * top[2][2] / L)}")
        c.drawRightString(x0 + bw, 1.8 * mm, f"{CT['users'] - 3} autres contributeurs  {fr(rest)}")
        # pastille droite
        y26 = CT["years"].get(DATE[:4], 0); t = f"{100 * y26 / CT['n']:.0f} % mis à jour en {DATE[:4]}"
        tw = pdfmetrics.stringWidth(t, "InS", 6.8) + 7 * mm
        c.setFillColor(colors.HexColor("#ecfdf5")); c.roundRect(FW - 5 * mm - tw, h - 9.5 * mm, tw, 5.4 * mm, 2.7 * mm, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#047857")); c.setFont("InS", 6.8); c.drawCentredString(FW - 5 * mm - tw / 2, h - 7.6 * mm, t)
s.append(Contrib())
s.append(PageBreak())

# ===== PAGE 2 =====
s += section("03", "Micromapping", "Zones prioritaires : patrimoine, flux et services")
rows = [["", "ZONE", "TROTTOIRS DESSINÉS", "TROTTOIRS SANS INFO BORDURES / DEV"]]
for i, z in enumerate(R["zones"], 1):
    L = z["len"]; t = sum(L.values()); a, n = ZK["zones"][z["name"]]
    rows.append([str(i), z["name"], Bar(L["sep"] / t, GREEN, 44 * mm), Bar(a / n if n else 0, RED, 44 * mm)])
s.append(Table(rows, colWidths=[9 * mm, 77 * mm, 48 * mm, 48 * mm],
               style=tstyle([("ALIGN", (0, 0), (1, -1), "LEFT"), ("ALIGN", (0, 0), (0, -1), "CENTER"),
                             ("FONT", (0, 1), (0, -1), "InB", 7.4), ("TEXTCOLOR", (0, 1), (0, -1), colors.HexColor(ACC))])))
s.append(Spacer(1, 16))

s += section("04", "Traversées", "Passages piétons, bordures et feux sonores")
def c_(cnt, k): return cnt.get(k, 0)
def grp(t): return [Paragraph(f'<font name="InS">{t}</font>', st(fontSize=7.3)), "", ""]
low = c_(ks["kerb"], "lowered") + c_(ks["kerb"], "flush")
rows = [["INDICATEUR", "NOMBRE", "PART"],
        grp(f"Passages piétons ({ncr})"),
        ["Type de passage indiqué", typed, Bar(typed / ncr, GREEN)],
        ["Bande d'éveil (DEV) indiquée", tact, Bar(tact / ncr, GREEN)],
        ["Type de bordure indiqué", kerbnode, Bar(kerbnode / ncr, AMBER)],
        ["Îlot refuge indiqué", ncr - c_(cs["island"], "absent"), Bar((ncr - c_(cs["island"], "absent")) / ncr, RED)],
        grp(f"Bordures cartographiées ({ks['n']})"),
        ["Abaissées ou à niveau", low, Bar(low / ks["n"], GREEN)],
        ["Hauteur mesurée", ks["height"], Bar(ks["height"] / ks["n"], RED)],
        ["Traversées avec bordure aux extrémités", f"{ks['xway_ends_kerb']}/{ks['xway_ends']}", Bar(ks["xway_ends_kerb"] / ks["xway_ends"], RED)],
        grp(f"Feux piétons ({nps})"),
        ["Présence du son indiquée", snd, Bar(snd / nps, AMBER)],
        ["Feux sonores confirmés", ss["sound"].get("yes", 0), Bar(ss["sound"].get("yes", 0) / nps, RED)],
        ["Vibreur indiqué", nps - ss["vibration"].get("absent", 0), Bar((nps - ss["vibration"].get("absent", 0)) / nps, AMBER)],
        ["Bouton d'appel indiqué", nps - ss["button"].get("absent", 0), Bar((nps - ss["button"].get("absent", 0)) / nps, AMBER)]]
grp_rows = [i for i, r in enumerate(rows) if i and r[1] == ""]
ts = tstyle([("SPAN", (0, i), (-1, i)) for i in grp_rows] +
            [("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f8fafc")) for i in grp_rows] +
            [("TEXTCOLOR", (0, 1), (0, -1), colors.HexColor("#334155"))])
t3 = Table([r if isinstance(r[0], Paragraph) else [r[0], str(r[1]), r[2]] for r in rows],
           colWidths=[54 * mm, 17 * mm, 28 * mm], style=ts)
mw = FW - 99 * mm - 5 * mm
s.append(Table([[t3, card(f"{OUTDIR}/map_crossings.png", mw, mw)]], colWidths=[99 * mm + 5 * mm, mw],
               style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                      ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
s.append(Spacer(1, 16))

s += section("05", "Recommandations", "Constats et priorités d'action")
zsorted = sorted(R["zones"], key=lambda z: z["len"]["sep"] / max(1, sum(z["len"].values())))
weak = ", ".join(z["name"].split(" (")[0].split(" / ")[0] for z in zsorted[:3])
y26 = CT["years"].get(DATE[:4], 0)
recs = [
    ("Trottoirs", RED, f"{pct(LB['none'], TOT)} de la voirie ({LB['none'] / 1000:.0f} km) n'a pas encore de trottoir cartographié, surtout en périphérie. "
                       f"Les compléter en priorité dans les secteurs les moins couverts : {weak}."),
    ("Feux sonores", ACC, f"{ss['sound'].get('absent', 0)} feux piétons sur {nps} n'indiquent pas s'ils sont sonores, et seuls {ss['sound'].get('yes', 0)} sont confirmés sonores. "
                          "Un relevé de terrain (son, vibreur, bouton d'appel) est à mener, en priorité autour du CHRU et des Rives de Meurthe."),
    ("Bordures", AMBER, f"{pct(*ZK['city'])} des trottoirs reliés à un passage piéton n'ont pas d'information complète sur la bordure ou la bande d'éveil (DEV). "
                        "C'est l'information clé pour les personnes en fauteuil roulant et les personnes aveugles : à relever à chaque traversée."),
    ("Maintenance", GREEN, f"La donnée est vivante : {pct(y26, CT['n'])} des trottoirs ont été mis à jour en {DATE[:4]}. "
                           "Pérenniser cette maintenance (travaux, nouveaux aménagements) par un partenariat entre la collectivité et les contributeurs."),
]
class Pill(Flowable):
    def __init__(self, text, color): super().__init__(); self.t = text; self.c = color
    def wrap(self, aw, ah): return 25 * mm, 5.2 * mm
    def draw(self):
        c = self.canv; c.setFillColor(colors.HexColor(self.c)); c.roundRect(0, 0, 25 * mm, 5.2 * mm, 2.6 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont("InS", 6.8); c.drawCentredString(12.5 * mm, 1.75 * mm, self.t.upper())
rrows = [[Pill(a, col), Paragraph(t, BODY)] for a, col, t in recs]
s.append(Table(rrows, colWidths=[31 * mm, FW - 31 * mm],
               style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm), ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                      ("LEFTPADDING", (1, 0), (1, -1), 0),
                      ("TOPPADDING", (0, 0), (-1, -1), 3.4 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.4 * mm),
                      ("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor(LINE)),
                      ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(LINE)), ("ROUNDEDCORNERS", [8, 8, 8, 8])]))
doc.build(s)
