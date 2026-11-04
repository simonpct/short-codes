import glob, json, math, sys, pickle
import xml.etree.ElementTree as ET
from collections import Counter
from shapely.geometry import LineString, Polygon
from shapely.prepared import prep
DATA, OUT = sys.argv[1], sys.argv[2]
LAT0, LON0 = 48.69, 6.18
KX = 111320 * math.cos(math.radians(LAT0)); KY = 110574
P = lambda lon, lat: ((lon - LON0) * KX, (lat - LAT0) * KY)
nodes, ways = {}, {}
for f in sorted(glob.glob(f"{DATA}/t_*.osm")):
    for ev, el in ET.iterparse(f):
        if el.tag == "node": nodes[int(el.get("id"))] = P(float(el.get("lon")), float(el.get("lat"))); el.clear()
        elif el.tag == "way":
            tags = {t.get("k"): t.get("v") for t in el.findall("tag")}
            if tags.get("footway") == "sidewalk":
                ways[int(el.get("id"))] = ([int(n.get("ref")) for n in el.findall("nd")], el.get("user"), el.get("timestamp"))
            el.clear()
b = json.load(open(f"{DATA}/boundary.json"))["geometry"]
city = Polygon([P(*c) for c in b["coordinates"][0]]); cp = prep(city)
cnt, ln = Counter(), Counter(); years = Counter()
for wid, (nd, u, ts) in ways.items():
    pts = [nodes[n] for n in nd if n in nodes]
    if len(pts) < 2: continue
    g = LineString(pts)
    if not cp.intersects(g): continue
    cnt[u] += 1; ln[u] += g.intersection(city).length; years[ts[:4]] += 1
N, L = sum(cnt.values()), sum(ln.values())
res = {"n": N, "len": L, "users": len(cnt), "top": [(u, cnt[u], ln[u]) for u, _ in ln.most_common(10)], "years": years}
pickle.dump(res, open(OUT, "wb"))
print(N, round(L/1000,1), len(cnt))
for u, c, l in res["top"][:6]: print(u, c, f"{100*c/N:.1f}%", f"{100*l/L:.1f}%")
print(sorted(years.items()))
