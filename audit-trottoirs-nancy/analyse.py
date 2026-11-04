"""Audit OSM des trottoirs, passages piétons, bordures et feux sonores — Nancy."""
import glob, json, math, sys, pickle
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from shapely.geometry import LineString, Point, Polygon, shape
from shapely.ops import substring, unary_union
from shapely.strtree import STRtree
from shapely.prepared import prep

DATA = sys.argv[1]
OUT = sys.argv[2]

LAT0, LON0 = 48.69, 6.18
KX = 111320 * math.cos(math.radians(LAT0)); KY = 110574
def P(lon, lat): return ((lon - LON0) * KX, (lat - LAT0) * KY)

# ---------- parse ----------
nodes, ways = {}, {}
for f in sorted(glob.glob(f"{DATA}/t_*.osm")):
    for ev, el in ET.iterparse(f):
        if el.tag == "node":
            tags = {t.get("k"): t.get("v") for t in el.findall("tag")}
            nodes[int(el.get("id"))] = (float(el.get("lon")), float(el.get("lat")), tags)
            el.clear()
        elif el.tag == "way":
            tags = {t.get("k"): t.get("v") for t in el.findall("tag")}
            ways[int(el.get("id"))] = ([int(n.get("ref")) for n in el.findall("nd")], tags)
            el.clear()
        elif el.tag == "relation":
            el.clear()
print("nodes", len(nodes), "ways", len(ways))

b = json.load(open(f"{DATA}/boundary.json"))["geometry"]
city = Polygon([P(*c) for c in b["coordinates"][0]])
cityp = prep(city)

def wgeom(nd):
    pts = [P(nodes[n][0], nodes[n][1]) for n in nd if n in nodes]
    return pts

# ---------- context layers ----------
ctx = {"building": [], "water": [], "green": [], "rail": [], "river": []}
roads, sidewalks, footways, area_hw = [], [], [], []
ROAD = {"trunk", "trunk_link", "primary", "secondary", "tertiary", "residential", "unclassified", "living_street",
        "primary_link", "secondary_link", "tertiary_link"}
for wid, (nd, t) in ways.items():
    pts = wgeom(nd)
    if len(pts) < 2: continue
    closed = nd[0] == nd[-1] and len(pts) >= 4
    hw = t.get("highway")
    if "building" in t and closed: ctx["building"].append(pts)
    elif closed and (t.get("natural") == "water" or t.get("waterway") == "riverbank" or t.get("landuse") == "basin"):
        ctx["water"].append(pts)
    elif closed and (t.get("leisure") in ("park", "garden") or t.get("landuse") in ("grass", "forest", "cemetery", "recreation_ground") or t.get("natural") == "wood"):
        ctx["green"].append(pts)
    elif t.get("waterway") in ("river", "canal"): ctx["river"].append(pts)
    elif t.get("railway") == "rail" and "service" not in t: ctx["rail"].append(pts)
    if "area:highway" in t: area_hw.append((wid, Polygon(pts) if closed else LineString(pts), t))
    if hw in ROAD and t.get("area") != "yes" and t.get("motorroad") != "yes" and t.get("tunnel") not in ("yes",):
        roads.append((wid, LineString(pts), t, nd))
    if hw == "footway" and t.get("footway") == "sidewalk" or (hw in ("path", "footway", "cycleway") and t.get("footway") == "sidewalk"):
        sidewalks.append((wid, LineString(pts), t))
    if hw in ("footway", "pedestrian", "path", "steps"):
        footways.append((wid, LineString(pts), t, nd))

roads = [r for r in roads if cityp.intersects(r[1])]
sidewalks = [s for s in sidewalks if cityp.intersects(s[1])]
print("roads", len(roads), "sidewalks", len(sidewalks), "area:highway", len(area_hw))

# ---------- sidewalk classification by 10 m pieces ----------
sw_tree = STRtree([s[1] for s in sidewalks])
def side_val(t, side):
    v = t.get(f"sidewalk:{side}") or t.get("sidewalk:both")
    if v: return v
    s = t.get("sidewalk")
    if s is None: return None
    if s in ("both",): return "yes"
    if s in ("no", "none"): return "no"
    if s == "separate": return "separate"
    if s == side: return "yes"
    if s in ("left", "right"): return "no"
    return s

def classify_tags(t):
    l, r = side_val(t, "left"), side_val(t, "right")
    vals = {l, r}
    if "separate" in vals: return "sep"
    if vals == {None}: return "none"
    if "yes" in vals: return "tag"
    if vals <= {"no", None}: return "no"
    return "tag"

CLS = ["sep", "tag", "no", "none"]
pieces = []  # (geom, cls, hwclass)
length_by = Counter(); length_by_hw = defaultdict(Counter)
for wid, g, t, nd in roads:
    gi = g.intersection(city)
    if gi.is_empty: continue
    parts = [gi] if gi.geom_type == "LineString" else [p for p in getattr(gi, "geoms", []) if p.geom_type == "LineString"]
    tc = classify_tags(t)
    for part in parts:
        L = part.length; n = max(1, int(L // 10))
        for i in range(n):
            seg = substring(part, L * i / n, L * (i + 1) / n)
            c = tc
            if c != "sep":
                mid = seg.interpolate(0.5, normalized=True)
                idx = sw_tree.query(mid.buffer(18))
                if len(idx) and min(sidewalks[j][1].distance(mid) for j in idx) <= 18:
                    c = "sep"
            pieces.append((list(seg.coords), c))
            length_by[c] += seg.length
            length_by_hw[t["highway"].replace("_link", "")][c] += seg.length
total_len = sum(length_by.values())
print({k: round(v / 1000, 1) for k, v in length_by.items()}, round(total_len / 1000, 1))

# ---------- point features ----------
def inside(n): return cityp.contains(Point(P(n[0], n[1])))
crossings, signals, kerbs = [], [], []
for nid, n in nodes.items():
    t = n[2]
    if not t: continue
    hw = t.get("highway")
    if hw == "crossing" or ("crossing" in t and hw != "traffic_signals" and t.get("railway") is None):
        if inside(n): crossings.append((nid, P(n[0], n[1]), t))
    if hw == "traffic_signals" and inside(n): signals.append((nid, P(n[0], n[1]), t))
    if t.get("barrier") == "kerb" or (t.get("kerb") and hw != "crossing"):
        if inside(n): kerbs.append((nid, P(n[0], n[1]), t))
# crossing ways
xways = [f for f in footways if f[2].get("footway") == "crossing" and cityp.intersects(f[1])]

def ped_signal(t):
    return t.get("crossing") == "traffic_signals" or t.get("crossing:signals") == "yes" or t.get("crossing_ref") == "pelican"
ped_sig = [c for c in crossings if ped_signal(c[2])]
SOUND = "traffic_signals:sound"
def sound_status(t):
    v = t.get(SOUND)
    if v is None: return "absent"
    return "yes" if v in ("yes", "walk", "locate", "beeps") else ("no" if v == "no" else "autre")
sig_stats = {
    "nodes_traffic_signals": len(signals),
    "ped_crossings_signals": len(ped_sig),
    "sound": Counter(sound_status(c[2]) for c in ped_sig),
    "sound_on_tsnodes": Counter(sound_status(s[2]) for s in signals),
    "vibration": Counter(c[2].get("traffic_signals:vibration", "absent") for c in ped_sig),
    "button": Counter(c[2].get("button_operated", "absent") for c in ped_sig),
}

cr_stats = {
    "n": len(crossings),
    "crossing": Counter(c[2].get("crossing", "absent") for c in crossings),
    "markings": Counter(c[2].get("crossing:markings", "absent") for c in crossings),
    "tactile": Counter(c[2].get("tactile_paving", "absent") for c in crossings),
    "kerb_on_node": Counter(c[2].get("kerb", "absent") for c in crossings),
    "island": Counter(c[2].get("crossing:island", "absent") for c in crossings),
    "n_ways": len(xways),
}
# crossing-way ends with a kerb node
kerb_ids = {k[0] for k in kerbs}
ends_total = ends_kerb = 0
for wid, g, t, nd in xways:
    for e in (nd[0], nd[-1]):
        ends_total += 1
        if e in kerb_ids: ends_kerb += 1
kb_stats = {"n": len(kerbs), "kerb": Counter(k[2].get("kerb", "absent") for k in kerbs),
            "tactile": Counter(k[2].get("tactile_paving", "absent") for k in kerbs),
            "height": sum(1 for k in kerbs if "kerb:height" in k[2]),
            "xway_ends": ends_total, "xway_ends_kerb": ends_kerb}

# ---------- micromapping zones ----------
def find(names, keys=("name",)):
    pts = []
    for nid, n in nodes.items():
        if n[2].get("name") in names: pts.append(P(n[0], n[1]))
    for wid, (nd, t) in ways.items():
        if t.get("name") in names and ("highway" in t or "place" in t or "tourism" in t or "historic" in t or "leisure" in t or "amenity" in t or "building" in t):
            g = wgeom(nd)
            if g: pts.append(LineString(g).centroid.coords[0] if len(g) > 1 else g[0])
    if not pts: return None
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

ZONES = [
    ("Place Stanislas / Carrière (UNESCO)", ["Place Stanislas", "Place de la Carrière"], 380, (6.1832, 48.6936)),
    ("Vieille-Ville / Porte de la Craffe", ["Porte de la Craffe", "Grande Rue"], 300, (6.1780, 48.6975)),
    ("Gare Nancy-Ville / Place Thiers", ["Place Thiers", "Nancy-Ville"], 300, (6.1755, 48.6905)),
    ("Hypercentre commercial (St-Jean / Charles III)", ["Place Charles III", "Rue Saint-Jean"], 280, (6.1800, 48.6905)),
    ("Quartier Art nouveau (Musée Éc. de Nancy)", ["Musée de l'École de Nancy", "Parc Sainte-Marie"], 350, (6.1650, 48.6850)),
    ("CHRU Hôpital Central / Faculté", ["Hôpital Central"], 300, (6.1895, 48.6835)),
    ("Rives de Meurthe / Jardin d'Eau", ["Jardin d'Eau", "Bassin Saint-Georges", "Port Saint-Georges"], 300, (6.1980, 48.6925)),
]
zones = []
for name, keys, r, fb in ZONES:
    c = find(keys)
    fbp = P(*fb)
    if c is None or math.dist(c, fbp) > 500: c = fbp
    zones.append({"name": name, "c": c, "r": r, "poly": Point(c).buffer(r)})

def in_zone(pt, z): return math.dist(pt, z["c"]) <= z["r"]
for z in zones:
    zp = prep(z["poly"])
    lb = Counter()
    for coords, c in pieces:
        mx = (coords[0][0] + coords[-1][0]) / 2; my = (coords[0][1] + coords[-1][1]) / 2
        if math.dist((mx, my), z["c"]) <= z["r"]:
            lb[c] += LineString(coords).length
    z["len"] = lb
    zc = [c for c in crossings if in_zone(c[1], z)]
    z["crossings"] = len(zc)
    z["cr_tactile"] = sum(1 for c in zc if "tactile_paving" in c[2])
    z["cr_typed"] = sum(1 for c in zc if c[2].get("crossing") not in (None, "yes"))
    zs = [c for c in zc if ped_signal(c[2])]
    z["sig"] = len(zs); z["sig_sound"] = sum(1 for c in zs if SOUND in c[2])
    z["kerbs"] = sum(1 for k in kerbs if in_zone(k[1], z))
    z["area_hw"] = sum(1 for a in area_hw if zp.intersects(a[1]))
    z["sw_ways"] = sum(1 for s in sidewalks if zp.intersects(s[1]))

res = dict(pieces=pieces, length_by=length_by, length_by_hw=length_by_hw, total_len=total_len,
           crossings=[(c[1], c[2]) for c in crossings], signals=[(s[1], s[2]) for s in signals],
           kerbs=[(k[1], k[2]) for k in kerbs], sig_stats=sig_stats, cr_stats=cr_stats, kb_stats=kb_stats,
           zones=[{k: v for k, v in z.items() if k != "poly"} for z in zones],
           city=list(city.exterior.coords), ctx=ctx, n_sidewalk_ways=len(sidewalks),
           sidewalk_len=sum(s[1].intersection(city).length for s in sidewalks),
           area_hw_total=sum(1 for a in area_hw if cityp.intersects(a[1])),
           sidewalk_geoms=[list(s[1].coords) for s in sidewalks])
pickle.dump(res, open(OUT, "wb"))
for k in ("sig_stats", "cr_stats", "kb_stats"): print(k, res[k])
for z in res["zones"]: print(z["name"], {k: (round(v) if isinstance(v, float) else v) for k, v in z.items() if k not in ("name", "c", "len")}, {k: round(v) for k, v in z["len"].items()})
