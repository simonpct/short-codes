"""Par zone : % de trottoirs reliés à une traversée sans info bordure ou DEV (bande d'éveil de vigilance)."""
import glob, json, math, sys, pickle
import xml.etree.ElementTree as ET
from collections import defaultdict
from shapely.geometry import LineString, Polygon, Point
from shapely.prepared import prep
DATA, RES, OUT = sys.argv[1:4]
LAT0, LON0 = 48.69, 6.18
KX = 111320 * math.cos(math.radians(LAT0)); KY = 110574
P = lambda lon, lat: ((lon - LON0) * KX, (lat - LAT0) * KY)
nodes, ntags, ways = {}, {}, {}
for f in sorted(glob.glob(f"{DATA}/t_*.osm")):
    for ev, el in ET.iterparse(f):
        if el.tag == "node":
            i = int(el.get("id")); nodes[i] = P(float(el.get("lon")), float(el.get("lat")))
            t = {x.get("k"): x.get("v") for x in el.findall("tag")}
            if t: ntags[i] = t
            el.clear()
        elif el.tag == "way":
            t = {x.get("k"): x.get("v") for x in el.findall("tag")}
            if t.get("footway") in ("sidewalk", "crossing"):
                ways[int(el.get("id"))] = (t["footway"], [int(n.get("ref")) for n in el.findall("nd")])
            el.clear()
b = json.load(open(f"{DATA}/boundary.json"))["geometry"]
city = prep(Polygon([P(*c) for c in b["coordinates"][0]]))
R = pickle.load(open(RES, "rb"))
def has_kerb(t): return bool(t) and ("kerb" in t)
def has_dev(t): return bool(t) and ("tactile_paving" in t)
xby_node = defaultdict(list)
for wid, (k, nd) in ways.items():
    if k == "crossing":
        for n in nd: xby_node[n].append(wid)
def crossing_info(wid):
    nd = ways[wid][1]; ts = [ntags.get(n) for n in nd]
    return any(has_kerb(t) for t in ts), any(has_dev(t) for t in ts)
sw = []
for wid, (k, nd) in ways.items():
    if k != "sidewalk": continue
    pts = [nodes[n] for n in nd if n in nodes]
    if len(pts) < 2: continue
    g = LineString(pts)
    if not city.intersects(g): continue
    links = []
    for n in nd:
        for x in xby_node.get(n, []):
            kb, dv = crossing_info(x)
            # la jonction elle-même peut porter l'info
            t = ntags.get(n); kb = kb or has_kerb(t); dv = dv or has_dev(t)
            links.append((kb, dv))
        t = ntags.get(n)
        if t and t.get("highway") == "crossing": links.append((has_kerb(t), has_dev(t)))
    if not links: continue
    sw.append((g, all(k and d for k, d in links)))
def stat(sel): 
    n = len(sel); return (sum(1 for _, ok in sel if not ok), n)
out = {"city": stat(sw), "zones": {}}
for z in R["zones"]:
    circ = prep(Point(z["c"]).buffer(z["r"]))
    out["zones"][z["name"]] = stat([s for s in sw if circ.intersects(s[0])])
pickle.dump(out, open(OUT, "wb"))
print("ville", out["city"], f"{100*out['city'][0]/out['city'][1]:.0f}%")
for k, (a, n) in out["zones"].items(): print(k, a, n, f"{100*a/n:.0f}%")
