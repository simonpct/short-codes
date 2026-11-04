import pickle, sys, math, datetime
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.patches import Circle, Polygon as MPoly
from matplotlib.lines import Line2D
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image, FrameBreak, NextPageTemplate, KeepInFrame)
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

R = pickle.load(open(sys.argv[1], "rb")); OUTDIR = sys.argv[2]; PDF = sys.argv[3]
DATE = sys.argv[4] if len(sys.argv) > 4 else datetime.date.today().isoformat()

COL = {"sep": "#1b9e57", "tag": "#f2b134", "no": "#7a7a7a", "none": "#d7301f"}
LAB = {"sep": "Trottoir dessiné (voie séparée)", "tag": "Renseigné sur la chaussée seulement",
       "no": "Absence déclarée (sidewalk=no)", "none": "Aucune information"}
INK, MUTED, ACC = "#1d2733", "#5b6672", "#1f4e79"

def base(ax, light=False):
    ax.add_collection(PolyCollection(R["ctx"]["green"], facecolor="#e3efdc", edgecolor="none", zorder=0))
    ax.add_collection(PolyCollection(R["ctx"]["water"], facecolor="#cfe3f3", edgecolor="none", zorder=0))
    ax.add_collection(LineCollection(R["ctx"]["river"], colors="#9cc3e4", linewidths=1.2, zorder=0))
    ax.add_collection(PolyCollection(R["ctx"]["building"], facecolor="#ebe8e4", edgecolor="none", zorder=0.5))
    ax.add_collection(LineCollection(R["ctx"]["rail"], colors="#b9b2a8", linewidths=0.6, linestyles="--", zorder=0.6))
    ax.add_patch(MPoly(R["city"], closed=True, fill=False, edgecolor=INK, lw=1.0, ls=(0, (4, 2)), zorder=5))
    ax.set_aspect("equal"); ax.axis("off")

def scalebar(ax, x, y, L=500):
    ax.plot([x, x + L], [y, y], color=INK, lw=2, solid_capstyle="butt", zorder=10)
    ax.text(x + L / 2, y + 40, f"{L} m", ha="center", va="bottom", fontsize=6, color=INK, zorder=10)
    ax.annotate("N", xy=(x - 120, y + 200), xytext=(x - 120, y), ha="center", fontsize=7, color=INK,
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.8), zorder=10)

xs = [p[0] for p in R["city"]]; ys = [p[1] for p in R["city"]]
X0, X1, Y0, Y1 = min(xs) - 80, max(xs) + 80, min(ys) - 80, max(ys) + 80
_cy=(Y0+Y1)/2; _h=(X1-X0)*5.6/7.4; Y0, Y1 = _cy-_h/2, _cy+_h/2

# ---------- Map 1: sidewalks ----------
fig = plt.figure(figsize=(7.4, 5.6), dpi=300)
ax = fig.add_axes([0, 0, 1, 1]); base(ax)
for c in ["no", "tag", "none", "sep"]:
    segs = [p[0] for p in R["pieces"] if p[1] == c]
    ax.add_collection(LineCollection(segs, colors=COL[c], linewidths=1.1 if c != "sep" else 1.2,
                                     zorder=3 if c != "none" else 3.5, capstyle="round"))
for i, z in enumerate(R["zones"], 1):
    ax.add_patch(Circle(z["c"], z["r"], fill=False, ec=ACC, lw=1.3, zorder=6))
    ang = math.radians(50)
    lx, ly = z["c"][0] + z["r"] * math.cos(ang), z["c"][1] + z["r"] * math.sin(ang)
    ax.add_patch(Circle((lx, ly), 75, fc=ACC, ec="white", lw=0.8, zorder=7))
    ax.text(lx, ly, str(i), ha="center", va="center", color="white", fontsize=6.5, weight="bold", zorder=8)
ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1)
h = [Line2D([], [], color=COL[c], lw=2.5, label=LAB[c]) for c in ["sep", "tag", "no", "none"]]
h.append(Line2D([], [], marker="o", ls="", mfc="none", mec=ACC, ms=8, label="Zone de micromapping prioritaire"))
ax.legend(handles=h, loc="lower left", fontsize=6.3, frameon=True, framealpha=0.92, edgecolor="#cccccc",
          title="Voirie (rues principales à résidentielles)", title_fontsize=6.5, alignment="left")
scalebar(ax, X1 - 900, Y0 + 150)
fig.savefig(f"{OUTDIR}/map_sidewalks.png", dpi=300); plt.close(fig)

# ---------- Map 2: crossings / signals / kerbs (centre-ville zoom) ----------
cx = sum(z["c"][0] for z in R["zones"]) / len(R["zones"]); cy = sum(z["c"][1] for z in R["zones"]) / len(R["zones"])
W, H = 2600, 2600
fig = plt.figure(figsize=(4.0, 4.0), dpi=300)
ax = fig.add_axes([0, 0, 1, 1]); base(ax)
ax.add_collection(LineCollection([p[0] for p in R["pieces"]], colors="#c9ced4", linewidths=0.6, zorder=2))
ax.add_collection(LineCollection(R["sidewalk_geoms"], colors="#7fbf9b", linewidths=0.5, zorder=2.2))
def cr_cat(t):
    if t.get("crossing") == "traffic_signals" or t.get("crossing:signals") == "yes":
        return "sig_snd" if "traffic_signals:sound" in t else "sig"
    full = t.get("crossing") not in (None, "yes") and "tactile_paving" in t and "kerb" in t
    return "full" if full else "part"
CC = {"sig_snd": ("#1f4e79", "Feu piéton — son renseigné", 9), "sig": ("#d7301f", "Feu piéton — son NON renseigné", 9),
      "full": ("#1b9e57", "Passage complet (type + podotactile + bordure)", 5), "part": ("#f2b134", "Passage incomplet", 5)}
for k in ["part", "full", "sig", "sig_snd"]:
    pts = [c[0] for c in R["crossings"] if cr_cat(c[1]) == k]
    if pts: ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=CC[k][2] / 2.2, c=CC[k][0], lw=0, zorder=4 + (k.startswith("sig")))
kp = [k[0] for k in R["kerbs"]]
if kp: ax.scatter([p[0] for p in kp], [p[1] for p in kp], s=1.6, marker="s", c="#6a3d9a", lw=0, zorder=4.5)
for i, z in enumerate(R["zones"], 1):
    ax.add_patch(Circle(z["c"], z["r"], fill=False, ec=ACC, lw=0.8, ls=(0, (3, 2)), zorder=6))
    ax.text(z["c"][0] + z["r"] * 0.64, z["c"][1] + z["r"] * 0.77, str(i), fontsize=6, color=ACC, weight="bold", zorder=8)
ax.set_xlim(cx - W / 2, cx + W / 2); ax.set_ylim(cy - H / 2, cy + H / 2)
h = [Line2D([], [], marker="o", ls="", mfc=CC[k][0], mec="none", ms=4, label=CC[k][1]) for k in ["sig_snd", "sig", "full", "part"]]
h.append(Line2D([], [], marker="s", ls="", mfc="#6a3d9a", mec="none", ms=3, label="Bordure (barrier=kerb)"))
h.append(Line2D([], [], color="#7fbf9b", lw=1.5, label="Trottoir dessiné"))
ax.legend(handles=h, loc="lower left", fontsize=5.2, frameon=True, framealpha=0.92, edgecolor="#cccccc")
scalebar(ax, cx + W / 2 - 700, cy - H / 2 + 120, 400)
ax.add_patch(plt.Rectangle((0,0),1,1,transform=ax.transAxes,fill=False,ec="#cccccc",lw=0.6,zorder=20))
fig.savefig(f"{OUTDIR}/map_crossings.png", dpi=300); plt.close(fig)

# ---------- PDF ----------
pdfmetrics.registerFont(TTFont("DV", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
from reportlab.lib.fonts import addMapping
addMapping("DV", 0, 0, "DV"); addMapping("DV", 1, 0, "DVB")
def st(**k):
    d = dict(fontName="DV", fontSize=8, leading=10.2, textColor=colors.HexColor(INK)); d.update(k)
    return ParagraphStyle("x", **d)
H1 = st(fontName="DVB", fontSize=16, leading=19)
H2 = st(fontName="DVB", fontSize=10, leading=12, textColor=colors.HexColor(ACC), spaceBefore=4, spaceAfter=2)
BODY = st(); SMALL = st(fontSize=6.6, leading=8.2, textColor=colors.HexColor(MUTED))
pct = lambda a, b: f"{100 * a / b:.0f} %" if b else "–"

LB = R["length_by"]; TOT = R["total_len"]
cs, ss, ks = R["cr_stats"], R["sig_stats"], R["kb_stats"]
nps = ss["ped_crossings_signals"]; snd = nps - ss["sound"].get("absent", 0)
ncr = cs["n"]; tact = ncr - cs["tactile"].get("absent", 0)
typed = ncr - cs["crossing"].get("absent", 0) - cs["crossing"].get("yes", 0)
kerbnode = ncr - cs["kerb_on_node"].get("absent", 0)

def kpi(val, lab, color):
    return Table([[Paragraph(f'<font name="DVB" size="15" color="{color}">{val}</font>', st(alignment=1, leading=17))],
                  [Paragraph(lab, st(fontSize=6.6, leading=8, alignment=1, textColor=colors.HexColor(MUTED)))]],
                 colWidths=[44 * mm], style=[("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d5dbe1")),
                                              ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f6f8fa")),
                                              ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)])

TS = [("FONT", (0, 0), (-1, -1), "DV", 7), ("FONT", (0, 0), (-1, 0), "DVB", 7),
      ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor(INK)),
      ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef4")),
      ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor(ACC)),
      ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fb")]),
      ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
      ("TOPPADDING", (0, 0), (-1, -1), 1.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6),
      ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]

def header_footer(c, doc):
    c.saveState()
    c.setFillColor(colors.HexColor(ACC)); c.rect(0, A4[1] - 6 * mm, A4[0], 6 * mm, fill=1, stroke=0)
    c.setFont("DV", 6.5); c.setFillColor(colors.HexColor(MUTED))
    c.drawString(12 * mm, 7 * mm, f"Données © contributeurs OpenStreetMap (ODbL) — extraction du {DATE} via l'API OSM — périmètre : commune de Nancy (relation 52399)")
    c.drawRightString(A4[0] - 12 * mm, 7 * mm, f"{doc.page} / 2")
    c.restoreState()

doc = BaseDocTemplate(PDF, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=10 * mm, bottomMargin=12 * mm,
                      title="Audit OSM accessibilité piétonne — Nancy", author="Audit OpenStreetMap")
fw = A4[0] - 24 * mm
doc.addPageTemplates([PageTemplate("p", [Frame(12 * mm, 11 * mm, fw, A4[1] - 21 * mm, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=header_footer)])

s = []
s.append(Paragraph("Audit OpenStreetMap — cheminements piétons de Nancy", H1))
s.append(Paragraph("Trottoirs, zones de micromapping, passages piétons, bordures et feux sonores · "
                   f"{TOT / 1000:.0f} km de voirie analysés (rues principales à résidentielles, hors voies rapides, service et piétonnes)", st(textColor=colors.HexColor(MUTED))))
s.append(Spacer(1, 5))
s.append(Table([[kpi(pct(LB["sep"], TOT), "de la voirie bordée d'un<br/>trottoir dessiné", COL["sep"]),
                 kpi(pct(LB["none"], TOT), "de la voirie sans aucune<br/>information trottoir", COL["none"]),
                 kpi(pct(snd, nps), f"des {nps} feux piétons avec<br/>info sonore renseignée", ACC),
                 kpi(pct(tact, ncr), f"des {ncr} passages piétons<br/>avec info podotactile", "#b26b00")]],
               colWidths=[fw / 4] * 4, style=[("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
s.append(Spacer(1, 4))
s.append(Paragraph("1 · Couverture des trottoirs dans OSM", H2))
s.append(Image(f"{OUTDIR}/map_sidewalks.png", width=fw, height=fw * 5.6 / 7.4))
s.append(Spacer(1, 3))

hw_order = ["trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "living_street"]
hw_fr = {"trunk": "Artère (trunk)", "primary": "Principale", "secondary": "Secondaire", "tertiary": "Tertiaire", "unclassified": "Non classée",
         "residential": "Résidentielle", "living_street": "Zone de rencontre"}
rows = [["Type de voie", "Longueur", "Trottoir dessiné", "Tag chaussée", "sidewalk=no", "Sans info"]]
for k in hw_order:
    c = R["length_by_hw"].get(k)
    if not c: continue
    t = sum(c.values())
    rows.append([hw_fr[k], f"{t / 1000:.1f} km", pct(c["sep"], t), pct(c["tag"], t), pct(c["no"], t), pct(c["none"], t)])
rows.append(["Total", f"{TOT / 1000:.1f} km", pct(LB["sep"], TOT), pct(LB["tag"], TOT), pct(LB["no"], TOT), pct(LB["none"], TOT)])
tbl = Table(rows, colWidths=[30 * mm, 18 * mm, 24 * mm, 20 * mm, 19 * mm, 17 * mm], style=TS + [("FONT", (0, -1), (-1, -1), "DVB", 7)])
worst = max((k for k in hw_order if k in R["length_by_hw"]), key=lambda k: R["length_by_hw"][k]["none"])
txt = (f"<b>Lecture.</b> {R['n_sidewalk_ways']} tronçons <i>footway=sidewalk</i> ({R['sidewalk_len'] / 1000:.0f} km) sont dessinés. "
       f"<b>{pct(LB['sep'], TOT)}</b> du linéaire de voirie en est bordé ; <b>{pct(LB['tag'], TOT)}</b> n'ont qu'une "
       f"indication sur la chaussée (<i>sidewalk=both/left/right</i>), insuffisante pour le routage piéton fin, et "
       f"<b>{pct(LB['none'], TOT)}</b> n'ont <b>aucune</b> information (en rouge). Le déficit le plus lourd en volume concerne les voies "
       f"<b>{hw_fr[worst].lower()}s</b>. Méthode : chaque tronçon de 10 m est classé « dessiné » si une voie <i>footway=sidewalk</i> "
       f"passe à moins de 18 m ou si la chaussée porte <i>sidewalk=separate</i>.")
s.append(Table([[tbl, Paragraph(txt, BODY)]], colWidths=[130 * mm, fw - 130 * mm],
               style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("LEFTPADDING", (1, 0), (1, 0), 6)]))

# ---- page 2 ----
s.append(FrameBreak())
s.append(Paragraph("2 · Zones de micromapping prioritaires", H2))
s.append(Paragraph("Secteurs à forte valeur patrimoniale, touristique ou de flux piéton, où une cartographie fine "
                   "(trottoirs, bordures, <i>area:highway</i>, passages complets) est attendue. Rayon 280–380 m.", BODY))
s.append(Spacer(1, 2))
rows = [["#", "Zone", "Trottoir\ndessiné", "Sans\ninfo", "Passages\n(typés)", "Podo-\ntactile", "Feux piét.\n(son)", "Bordures", "area:\nhighway"]]
for i, z in enumerate(R["zones"], 1):
    L = z["len"]; t = sum(L.values())
    rows.append([str(i), z["name"], pct(L["sep"], t), pct(L["none"], t), f"{z['crossings']} ({z['cr_typed']})",
                 pct(z["cr_tactile"], z["crossings"]), f"{z['sig']} ({z['sig_sound']})", str(z["kerbs"]), str(z["area_hw"])])
zt = Table(rows, colWidths=[5 * mm, 62 * mm, 15 * mm, 13 * mm, 18 * mm, 14 * mm, 18 * mm, 15 * mm, 13 * mm], style=TS + [("ALIGN", (0, 0), (0, -1), "CENTER"), ("ALIGN", (1, 0), (1, -1), "LEFT")])
s.append(zt)
s.append(Spacer(1, 4))

s.append(Paragraph("3 · Passages piétons, bordures et feux sonores", H2))
def c(cnt, k): return cnt.get(k, 0)
rows = [["Indicateur", "Valeur", "Taux"],
        ["Passages piétons (nœuds)", str(ncr), ""],
        ["  … type précisé (crossing=*)", str(typed), pct(typed, ncr)],
        ["  … marquage (crossing:markings)", str(ncr - c(cs["markings"], "absent")), pct(ncr - c(cs["markings"], "absent"), ncr)],
        ["  … bande podotactile renseignée", str(tact), pct(tact, ncr)],
        ["  … dont podotactile = yes", str(c(cs["tactile"], "yes")), pct(c(cs["tactile"], "yes"), ncr)],
        ["  … bordure renseignée (kerb=*)", str(kerbnode), pct(kerbnode, ncr)],
        ["  … îlot refuge renseigné", str(ncr - c(cs["island"], "absent")), pct(ncr - c(cs["island"], "absent"), ncr)],
        ["Voies footway=crossing dessinées", str(cs["n_ways"]), ""],
        ["  … extrémités avec nœud bordure", f"{ks['xway_ends_kerb']}/{ks['xway_ends']}", pct(ks["xway_ends_kerb"], ks["xway_ends"])],
        ["Bordures (barrier=kerb / kerb=*)", str(ks["n"]), ""],
        ["  … abaissée / à niveau", str(c(ks["kerb"], "lowered") + c(ks["kerb"], "flush")), pct(c(ks["kerb"], "lowered") + c(ks["kerb"], "flush"), ks["n"])],
        ["  … hauteur mesurée (kerb:height)", str(ks["height"]), pct(ks["height"], ks["n"])],
        ["Carrefours à feux (highway=traffic_signals)", str(ss["nodes_traffic_signals"]), ""],
        ["Passages piétons à feux", str(nps), ""],
        ["  … son renseigné (traffic_signals:sound)", str(snd), pct(snd, nps)],
        ["  … dont sonore = yes", str(ss["sound"].get("yes", 0)), pct(ss["sound"].get("yes", 0), nps)],
        ["  … vibration renseignée", str(nps - ss["vibration"].get("absent", 0)), pct(nps - ss["vibration"].get("absent", 0), nps)],
        ["  … bouton d'appel renseigné", str(nps - ss["button"].get("absent", 0)), pct(nps - ss["button"].get("absent", 0), nps)]]
bold_rows = [i for i, r in enumerate(rows) if i and not r[0].startswith("  ")]
t3 = Table(rows, colWidths=[56 * mm, 17 * mm, 12 * mm], style=TS + [("FONT", (0, i), (0, i), "DVB", 7) for i in bold_rows])
mw = fw - 85 * mm - 4 * mm
s.append(Table([[t3, [Image(f"{OUTDIR}/map_crossings.png", width=mw, height=mw),
                       Paragraph("Zoom centre-ville : passages piétons selon complétude des attributs, feux piétons selon présence de l'info sonore.", SMALL)]]],
               colWidths=[85 * mm + 4 * mm, mw], style=[("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
s.append(Spacer(1, 3))

s.append(Paragraph("4 · Constats et recommandations", H2))
zsorted = sorted(R["zones"], key=lambda z: z["len"]["sep"] / max(1, sum(z["len"].values())))
weak = ", ".join(z["name"].split(" (")[0] for z in zsorted[:3])
rec = [
    f"<b>Trottoirs :</b> {pct(LB['none'], TOT)} du linéaire sans information. Priorité 1 : renseigner a minima <i>sidewalk:both/left/right</i> "
    f"sur les voies sans tag ; priorité 2 : dessiner les trottoirs en voies séparées dans les zones prioritaires les moins couvertes ({weak}).",
    f"<b>Feux sonores :</b> {ss['sound'].get('absent',0)} feux piétons sur {nps} ({pct(ss['sound'].get('absent',0), nps)}) n'ont pas l'attribut <i>traffic_signals:sound</i>, "
    f"et seuls {ss['sound'].get('yes',0)} sont déclarés sonores. Relevé terrain à mener (sonore / vibreur / bouton), en priorité autour du CHRU et des Rives de Meurthe : "
    "ces données conditionnent le guidage des personnes aveugles et malvoyantes.",
    f"<b>Passages piétons :</b> {pct(tact, ncr)} renseignent la bande podotactile et {pct(kerbnode, ncr)} la bordure. Compléter <i>crossing:markings</i>, "
    f"<i>tactile_paving</i>, <i>kerb</i> et dessiner les <i>footway=crossing</i> reliant les trottoirs.",
    f"<b>Bordures :</b> {ks['n']} nœuds seulement ; {pct(ks['xway_ends_kerb'], ks['xway_ends'])} des extrémités de traversées dessinées portent une bordure. "
    "Ajouter <i>barrier=kerb</i> + <i>kerb=lowered/raised/flush</i> à chaque jonction trottoir/traversée (clé de l'accessibilité fauteuil).",
    "<b>Micromapping :</b> seul le pôle gare dispose de surfaces <i>area:highway</i>. Étendre ce niveau de détail à Stanislas / Vieille-Ville "
    "et à l'hypercentre, via des cartoparties ciblées (StreetComplete, GoMap!!, JOSM sur orthophotos).",
]
for r_ in rec: s.append(Paragraph("• " + r_, st(leftIndent=7, firstLineIndent=-7, spaceAfter=1.5)))
s.append(Spacer(1, 2))
s.append(Paragraph("Méthode : données OSM brutes téléchargées par tuiles via l'API 0.6, filtrées sur le contour communal. Les zones de micromapping sont définies "
                   "manuellement autour de lieux emblématiques (UNESCO, pôle gare, hypercentre, Art nouveau, CHRU, port). Un tronçon « dessiné » peut "
                   "n'avoir un trottoir que d'un côté ; les taux de passages incluent les nœuds hors voirie analysée.", SMALL))
doc.build(s)
