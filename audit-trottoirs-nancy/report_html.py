"""Audit OSM des cheminements piétons de Nancy : cartes + HTML sémantique, imprimé en PDF balisé (render_pdf.js)."""
import pickle, sys, math, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.patches import Circle, Polygon as MPoly
from matplotlib.lines import Line2D
R = pickle.load(open(sys.argv[1], "rb")); OUTDIR = sys.argv[2]
DATE = sys.argv[3]; FONTDIR = sys.argv[4]; CT = pickle.load(open(sys.argv[5], "rb")); ZK = pickle.load(open(sys.argv[6], "rb"))
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
MAP_AR = 0.735
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
      "full": (GREEN, "Passage complet (type, bande podotactile, bordure)", 3.2), "part": (AMBER, "Passage incomplet", 3.2)}
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


# ================= Rapport HTML sémantique (rendu en PDF balisé par Chromium) =================
from html import escape as E

pct = lambda a, b: f"{100 * a / b:.0f} %" if b else "–"
fr1 = lambda x: f"{x:.1f} %".replace(".", ",")
LB = R["length_by"]; TOT = R["total_len"]
cs, ss, ks = R["cr_stats"], R["sig_stats"], R["kb_stats"]
nps = ss["ped_crossings_signals"]; snd = nps - ss["sound"].get("absent", 0)
ncr = cs["n"]; tact = ncr - cs["tactile"].get("absent", 0)
typed = ncr - cs["crossing"].get("absent", 0) - cs["crossing"].get("yes", 0)
kerbnode = ncr - cs["kerb_on_node"].get("absent", 0)
c_ = lambda cnt, k: cnt.get(k, 0)
SEP = round(100 * LB["sep"] / TOT); NOSEP = 100 - SEP
YEAR = DATE[:4]; y26 = CT["years"].get(YEAR, 0)
NAMES = {"simonpct": "Simon PICOT"}

def bar(frac, color, label=None, w="22mm"):
    """Barre décorative (masquée aux lecteurs d'écran) + valeur textuelle."""
    f = max(0, min(1, frac)); lab = label or f"{f * 100:.0f} %"
    return (f'<span class="barcell"><span class="bar" aria-hidden="true" style="width:{w}">'
            f'<span style="width:{f * 100:.1f}%;background:{color}"></span></span>'
            f'<span class="val">{E(lab)}</span></span>')

zones = R["zones"]
zsorted = sorted(zones, key=lambda z: z["len"]["sep"] / max(1, sum(z["len"].values())))
weak = ", ".join(z["name"].split(" (")[0].split(" / ")[0] for z in zsorted[:3])
zone_list = " ; ".join(f"{i} {z['name']}" for i, z in enumerate(zones, 1))

ALT1 = (f"Carte de la commune de Nancy montrant la couverture des trottoirs dans OpenStreetMap. "
        f"En vert, les rues bordées d'un trottoir dessiné : {SEP} % de la voirie, soit la quasi-totalité du centre-ville. "
        f"En rouge, les rues sans trottoir dessiné : {NOSEP} %, concentrées en périphérie, surtout dans les quartiers du nord-ouest "
        f"et à l'est le long de la Meurthe. En gris, quelques rues déclarées sans trottoir. "
        f"Sept zones prioritaires sont entourées et numérotées : {zone_list}.")
ALT2 = ("Zoom sur le centre-ville de Nancy montrant les passages piétons et les feux. "
        "Les passages complets, avec type, bande podotactile et bordure indiqués, sont en vert et dominent le centre ; "
        "les passages incomplets sont en orange. Les feux piétons dont la présence du son est indiquée sont en violet ; "
        "ceux sans information sonore sont en rouge, plus nombreux autour du CHRU et des Rives de Meurthe. "
        "Les bordures cartographiées apparaissent en petits carrés mauves.")

kpis = [(f"{SEP} %", "de la voirie bordée d'un trottoir dessiné", GREEN),
        (f"{NOSEP} %", "de la voirie sans trottoir dessiné", RED),
        (pct(ss["sound"].get("absent", 0), nps), f"des {nps} feux piétons sans information sonore", ACC),
        (pct(kerbnode, ncr), f"des {ncr} passages piétons avec bordure renseignée", AMBER)]
kpi_html = "".join(f'<li class="kpi"><span class="tick" aria-hidden="true" style="background:{c}"></span>'
                   f'<p><strong>{E(v)}</strong> <span>{E(l)}</span></p></li>' for v, l, c in kpis)

u, n, l = CT["top"][0]; L = CT["len"]; top = CT["top"]
rest = 100 - 100 * sum(t[2] for t in top[:3]) / L
seg = "".join(f'<span style="width:{100 * t[2] / L:.2f}%;background:{c}"></span>' for t, c in zip(top[:3], [ACC, "#a5b4fc", "#c7d2fe"]))
contrib_html = f'''
<div class="contrib">
  <p class="who"><strong class="big">{fr1(100 * l / L)}</strong>
     <span class="name">{E(NAMES.get(u, u))} <span class="muted">({E(u)})</span><br>
     <span class="sub">auteur des dernières mises à jour des trottoirs</span></span></p>
  <p class="badge">{pct(y26, CT["n"])} mis à jour en {YEAR}</p>
  <div class="stack" aria-hidden="true">{seg}</div>
  <p class="legend"><span>2. {E(top[1][0])} {fr1(100 * top[1][2] / L)} &nbsp;&nbsp; 3. {E(top[2][0])} {fr1(100 * top[2][2] / L)}</span>
     <span>{CT["users"] - 3} autres contributeurs {fr1(rest)}</span></p>
</div>'''

zrows = ""
for i, z in enumerate(zones, 1):
    Lz = z["len"]; t = sum(Lz.values()); a, nz = ZK["zones"][z["name"]]
    zrows += (f'<tr><td class="num">{i}</td><th scope="row">{E(z["name"])}</th>'
              f'<td>{bar(Lz["sep"] / t, GREEN, w="30mm")}</td><td>{bar(a / nz if nz else 0, RED, w="40mm")}</td></tr>')

low = c_(ks["kerb"], "lowered") + c_(ks["kerb"], "flush")
groups = [("Passages piétons", [("Type de passage indiqué", typed, typed / ncr, GREEN),
                                ("Bande podotactile indiquée", tact, tact / ncr, GREEN),
                                ("Type de bordure indiqué", kerbnode, kerbnode / ncr, AMBER),
                                ("Îlot refuge indiqué", ncr - c_(cs["island"], "absent"), (ncr - c_(cs["island"], "absent")) / ncr, RED)]),
          ("Bordures cartographiées", [("Abaissées ou à niveau", low, low / ks["n"], GREEN),
                                       ("Traversées avec bordure aux extrémités", f"{ks['xway_ends_kerb']}/{ks['xway_ends']}", ks["xway_ends_kerb"] / ks["xway_ends"], RED)]),
          ("Feux piétons", [("Présence du son indiquée", snd, snd / nps, AMBER),
                            ("Feux sonores confirmés", ss["sound"].get("yes", 0), ss["sound"].get("yes", 0) / nps, RED),
                            ("Bouton d'appel indiqué", nps - ss["button"].get("absent", 0), (nps - ss["button"].get("absent", 0)) / nps, AMBER)])]
trows = ""
for g, rows in groups:
    trows += f'<tbody><tr class="grp"><th scope="rowgroup" colspan="3">{E(g)}</th></tr>'
    for lab, v, f, col in rows:
        trows += f'<tr><th scope="row">{E(lab)}</th><td class="r">{v}</td><td>{bar(f, col, w='16mm')}</td></tr>'
    trows += "</tbody>"

recs = [("Trottoirs", RED, f"{NOSEP} % de la voirie ({(TOT - LB['sep']) / 1000:.0f} km) n'a pas encore de trottoir cartographié, surtout en périphérie. "
                           f"Les compléter en priorité dans les secteurs les moins couverts : {weak}."),
        ("Feux sonores", ACC, f"{ss['sound'].get('absent', 0)} feux piétons sur {nps} n'indiquent pas s'ils sont sonores, et seuls {ss['sound'].get('yes', 0)} sont confirmés sonores. "
                              "Un relevé de terrain (son, bouton d'appel) est à mener, en priorité autour du CHRU et des Rives de Meurthe."),
        ("Bordures", AMBER, f"{pct(*ZK['city'])} des trottoirs reliés à un passage piéton n'ont pas d'information complète sur la bordure ou la bande podotactile. "
                            "C'est l'information clé pour les personnes en fauteuil roulant et les personnes déficientes visuelles : à relever à chaque traversée."),
        ("Maintenance", GREEN, f"La donnée est vivante : {pct(y26, CT['n'])} des trottoirs ont été mis à jour en {YEAR}. "
                               "Pérenniser cette maintenance (travaux, nouveaux aménagements) par un partenariat entre la collectivité et les contributeurs.")]
rec_html = "".join(f'<li><strong class="pill" style="background:{c}">{E(a)}</strong><span>{E(t)}</span></li>' for a, c, t in recs)

FONT = lambda f: f"file://{os.path.abspath(os.path.join(FONTDIR, f))}.ttf"
TITLE = "Cartographie OSM à Nancy : couverture à 100 % + maintenance"
html = f'''<!doctype html>
<html lang="fr-FR">
<head>
<meta charset="utf-8">
<title>{E(TITLE)}</title>
<meta name="author" content="Simon PICOT">
<meta name="description" content="Audit OpenStreetMap des cheminements piétons de Nancy : trottoirs, passages piétons, bordures et feux sonores.">
<style>
@font-face {{ font-family: Inter; font-weight: 400; src: url("{FONT('Inter-Regular')}"); }}
@font-face {{ font-family: Inter; font-weight: 500; src: url("{FONT('Inter-Medium')}"); }}
@font-face {{ font-family: Inter; font-weight: 600; src: url("{FONT('Inter-SemiBold')}"); }}
@font-face {{ font-family: Inter; font-weight: 700; src: url("{FONT('Inter-Bold')}"); }}
@font-face {{ font-family: InterDisplay; font-weight: 600; src: url("{FONT('InterDisplay-SemiBold')}"); }}
@font-face {{ font-family: InterDisplay; font-weight: 700; src: url("{FONT('InterDisplay-Bold')}"); }}
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{ --navy:{NAVY}; --ink:{INK}; --muted:{MUTED}; --line:{LINE}; --acc:{ACC}; }}
html, body {{ background: #fff; }}
body {{ font-family: Inter, sans-serif; color: var(--ink); font-size: 7.8pt; line-height: 1.36;
        -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.page {{ width: 210mm; height: 297mm; position: relative; overflow: hidden; page-break-after: always; break-after: page; }}
.page:last-child {{ page-break-after: auto; break-after: auto; }}
.content {{ padding: 0 14mm; }}
.foot {{ position: absolute; left: 14mm; right: 14mm; bottom: 7mm; display: flex; justify-content: space-between; align-items: baseline; }}
.foot .src {{ font-size: 5.5pt; color: {GREY}; }}
.foot .pn {{ font-size: 6.5pt; font-weight: 600; }}

/* hero */
.hero {{ background: var(--navy); height: 76mm; padding: 9.5mm 14mm 0; color: #fff; position: relative;
         background-image: repeating-linear-gradient(-56deg, transparent 0 16px, #16304d 16px 17px);
         background-size: 75mm 58mm; background-repeat: no-repeat; background-position: right top; }}
.hero .eyebrow {{ color: #a5b4fc; font-weight: 600; font-size: 7pt; letter-spacing: .02em; }}
.hero .date {{ position: absolute; right: 14mm; top: 8.5mm; background: #1e3a5f; border-radius: 3mm; padding: 1.3mm 4mm;
               font-weight: 600; font-size: 7pt; }}
h1 {{ font-family: InterDisplay; font-weight: 700; font-size: 25pt; line-height: 1.12; margin-top: 2.4mm; }}
h1 .l2 {{ display: block; color: #c7d2fe; }}
.hero .intro {{ color: #cbd5e1; font-size: 8.6pt; line-height: 12.4pt; width: 86%; margin-top: 4.5mm; }}
.hero .intro strong {{ color: #fff; font-weight: 600; }}
.kpis {{ list-style: none; display: grid; grid-template-columns: repeat(4, 1fr); gap: 3.5mm; margin: -14mm 14mm 0; position: relative; }}
.kpi {{ background: #fff; border: .6pt solid var(--line); border-radius: 3mm; height: 24mm; padding: 2.9mm 4mm 0; }}
.kpi .tick {{ display: block; width: 7mm; height: 1.3mm; border-radius: .65mm; }}
.kpi p strong {{ display: block; font-family: InterDisplay; font-weight: 700; font-size: 22pt; line-height: 1; margin-top: 2.6mm; }}
.kpi p span {{ display: block; color: var(--muted); font-size: 6.6pt; line-height: 8.2pt; margin-top: 1.6mm; width: 34mm; }}

/* sections */
.eyebrow-s {{ color: var(--acc); font-weight: 600; font-size: 6.6pt; letter-spacing: .02em; text-transform: uppercase; }}
h2 {{ font-family: InterDisplay; font-weight: 600; font-size: 13pt; line-height: 16pt; margin: .5mm 0 2.8mm; }}
section {{ margin-top: 4.2mm; }}
section + section {{ margin-top: 4.2mm; }}
.p2 section + section {{ margin-top: 9mm; }}
.fig {{ border: .6pt solid var(--line); border-radius: 8px; overflow: hidden; }}
.fig img {{ display: block; width: 100%; }}

/* contributeurs */
.contrib {{ border: .6pt solid var(--line); border-radius: 3mm; height: 22mm; padding: 3mm 5mm 0; position: relative; }}
.contrib .who {{ display: flex; align-items: flex-start; gap: 3mm; }}
.contrib .big {{ font-family: InterDisplay; font-weight: 700; font-size: 20pt; line-height: 1; color: var(--acc); }}
.contrib .name {{ font-weight: 600; font-size: 9pt; line-height: 1.25; }}
.contrib .muted {{ color: var(--muted); font-weight: 400; font-size: 8pt; }}
.contrib .sub {{ color: var(--muted); font-weight: 400; font-size: 6.8pt; }}
.contrib .badge {{ position: absolute; right: 5mm; top: 3.5mm; background: #ecfdf5; color: #047857; font-weight: 600; font-size: 6.8pt;
                   border-radius: 2.7mm; padding: 1.1mm 3.5mm; }}
.stack {{ display: flex; height: 2.6mm; border-radius: 1.3mm; overflow: hidden; background: #e2e8f0; margin-top: 2.6mm; gap: .4pt; }}
.contrib .legend {{ display: flex; justify-content: space-between; color: var(--muted); font-size: 6.4pt; margin-top: 1mm; }}

/* tableaux */
table {{ table-layout: fixed; width: 100%; border-collapse: separate; border-spacing: 0; border: .6pt solid var(--line); border-radius: 8px; overflow: hidden; font-size: 7.3pt; }}
th, td {{ padding: 1.45mm 2.1mm; border-bottom: .4pt solid var(--line); vertical-align: middle; text-align: left; font-weight: 400; }}
tbody tr:last-child th, tbody tr:last-child td, tbody:last-child tr:last-child > * {{ border-bottom: 0; }}
table.t3 tbody:not(:last-child) tr:last-child > * {{ border-bottom: .4pt solid var(--line); }}
thead th {{ background: #f1f5f9; color: var(--muted); font-weight: 600; font-size: 6.2pt; text-transform: uppercase; padding: 1.6mm 2.1mm; }}
thead th.r, td.r {{ text-align: right; }}
tbody th[scope=row] {{ color: #334155; }}
td.num {{ color: var(--acc); font-weight: 700; text-align: center; width: 9mm; }}
tr.grp th {{ background: #f8fafc; font-weight: 600; color: var(--ink); }}
.barcell {{ display: flex; align-items: center; justify-content: flex-end; gap: 2mm; }}
.bar {{ display: inline-block; height: 3.6pt; border-radius: 1.8pt; background: #eef2f7; overflow: hidden; }}
.bar span {{ display: block; height: 100%; border-radius: 1.8pt; min-width: 3.6pt; }}
.val {{ font-weight: 500; font-size: 7pt; min-width: 8mm; text-align: right; }}
.zt th:nth-child(3), .zt th:nth-child(4) {{ text-align: right; }}
.duo {{ display: grid; grid-template-columns: 99mm 1fr; gap: 5mm; align-items: start; }}

/* recommandations */
ul.recs {{ list-style: none; border: .6pt solid var(--line); border-radius: 8px; }}
ul.recs li {{ display: grid; grid-template-columns: 25mm 1fr; gap: 4.5mm; padding: 3.2mm 4mm; border-bottom: .4pt solid var(--line); line-height: 10.6pt; }}
ul.recs li:last-child {{ border-bottom: 0; }}
.pill {{ color: #fff; font-weight: 600; font-size: 6.8pt; text-transform: uppercase; border-radius: 2.6mm; height: 5.2mm;
         display: flex; align-items: center; justify-content: center; }}

/* bandeau page 2 */
.bandeau {{ background: var(--navy); height: 11mm; display: flex; justify-content: space-between; align-items: center; padding: 0 14mm; margin-bottom: 6mm; }}
.bandeau .t {{ color: #fff; font-family: InterDisplay; font-weight: 600; font-size: 8.5pt; }}
.bandeau .r {{ color: #a5b4fc; font-weight: 600; font-size: 6.5pt; }}
.sr {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }}
</style>
</head>
<body>
<main>
<article class="page">
  <header class="hero">
    <p class="eyebrow">AUDIT OPENSTREETMAP · ACCESSIBILITÉ PIÉTONNE</p>
    <p class="date"><time datetime="{DATE[:7]}">Novembre {YEAR}</time></p>
    <h1>Cartographie OSM à Nancy <span class="l2">Couverture à 100 % + Maintenance</span></h1>
    <p class="intro"><strong>OpenStreetMap</strong> est la plus grande carte collaborative ouverte au monde. Elle est à la cartographie ce que
      Wikipédia est aux encyclopédies. Avec un groupe de contributeurs bénévoles, nous avons cartographié la plupart des cheminements
      piétons à Nancy. Ces données, directement exploitables par des applications de guidage telles que <strong>SonarVision</strong>,
      ont une valeur inestimable pour les utilisateurs déficients visuels.</p>
  </header>
  <ul class="kpis" aria-label="Chiffres clés">{kpi_html}</ul>
  <div class="content">
    <section aria-labelledby="s1">
      <p class="eyebrow-s" aria-hidden="true">01 · Trottoirs</p>
      <h2 id="s1">Couverture des trottoirs dans OpenStreetMap</h2>
      <div class="fig"><img src="map_sidewalks.png" alt="{E(ALT1)}"></div>
    </section>
    <section aria-labelledby="s2">
      <p class="eyebrow-s" aria-hidden="true">02 · Contributeurs</p>
      <h2 id="s2">Qui maintient les trottoirs ?</h2>
      {contrib_html}
    </section>
  </div>
  <footer class="foot"><span class="src">Données OpenStreetMap</span><span class="pn" aria-hidden="true">01 / 02</span></footer>
</article>

<article class="page p2">
  <div class="bandeau" aria-hidden="true"><span class="t">Cartographie OSM à Nancy</span><span class="r">AUDIT OPENSTREETMAP · NOVEMBRE {YEAR}</span></div>
  <div class="content">
    <section aria-labelledby="s3">
      <p class="eyebrow-s" aria-hidden="true">03 · Micromapping</p>
      <h2 id="s3">Zones prioritaires : patrimoine, flux et services</h2>
      <table class="zt"><colgroup><col style="width:9mm"><col style="width:66mm"><col style="width:46mm"><col></colgroup>
        <caption class="sr">Part des trottoirs dessinés et des trottoirs sans information sur les bordures ou la bande podotactile, pour les sept zones prioritaires</caption>
        <thead><tr><th scope="col"><span class="sr">Numéro</span></th><th scope="col">Zone</th><th scope="col" class="r">Trottoirs dessinés</th>
          <th scope="col" class="r">Trottoirs sans info bordures / podotactile</th></tr></thead>
        <tbody>{zrows}</tbody>
      </table>
    </section>
    <section aria-labelledby="s4">
      <p class="eyebrow-s" aria-hidden="true">04 · Traversées</p>
      <h2 id="s4">Passages piétons, bordures et feux sonores</h2>
      <div class="duo">
        <table class="t3"><colgroup><col style="width:57mm"><col style="width:16mm"><col></colgroup>
          <caption class="sr">Complétude des informations sur les passages piétons, les bordures et les feux piétons</caption>
          <thead><tr><th scope="col">Indicateur</th><th scope="col" class="r">Nombre</th><th scope="col" class="r">Part</th></tr></thead>
          {trows}
        </table>
        <div class="fig"><img src="map_crossings.png" alt="{E(ALT2)}"></div>
      </div>
    </section>
    <section aria-labelledby="s5">
      <p class="eyebrow-s" aria-hidden="true">05 · Recommandations</p>
      <h2 id="s5">Constats et priorités d'action</h2>
      <ul class="recs">{rec_html}</ul>
    </section>
  </div>
  <footer class="foot"><span class="src">Données OpenStreetMap</span><span class="pn" aria-hidden="true">02 / 02</span></footer>
</article>
</main>
</body>
</html>'''
open(os.path.join(OUTDIR, "audit.html"), "w").write(html)
print("html ok")
