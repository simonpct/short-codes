"""Contrôle d'accessibilité d'un PDF balisé : critères PDF/UA (Matterhorn) principaux + ordre de lecture des balises."""
import sys, re
from collections import defaultdict, Counter
import pikepdf

PATH = sys.argv[1]
pdf = pikepdf.open(PATH)
root = pdf.Root
ok, ko, warn = [], [], []
def chk(cond, msg, level="ko"):
    (ok if cond else (ko if level == "ko" else warn)).append(msg)

# ---- document ----
chk(root.get("/MarkInfo", {}).get("/Marked", False) is True, "MarkInfo /Marked = true (document balisé)")
chk("/StructTreeRoot" in root, "Arbre de structure présent")
chk(str(root.get("/Lang", "")) != "", f"Langue du document : {root.get('/Lang')}")
chk(root.get("/ViewerPreferences", {}).get("/DisplayDocTitle", False) is True, "DisplayDocTitle = true (titre affiché)")
with pdf.open_metadata() as m:
    chk(bool(m.get("dc:title")), f"Titre XMP (dc:title) : {m.get('dc:title')}")
    chk(m.get("pdfuaid:part") is not None, "Identifiant PDF/UA (pdfuaid:part) dans le XMP", "warn")
chk("/Outlines" in root, "Signets présents")
# polices
fonts_ok = True
for page in pdf.pages:
    for name, f in page.Resources.get("/Font", {}).items():
        fd = f.get("/FontDescriptor") or (f.get("/DescendantFonts")[0].get("/FontDescriptor") if "/DescendantFonts" in f else None)
        emb = fd is not None and any(k in fd for k in ("/FontFile", "/FontFile2", "/FontFile3"))
        if not emb or "/ToUnicode" not in f: fonts_ok = False
chk(fonts_ok, "Polices intégrées avec table ToUnicode (texte extractible et vocalisable)")
pua = []
for page in pdf.pages:
    for name, f in page.Resources.get("/Font", {}).items():
        if "/ToUnicode" in f:
            pua += re.findall(r"<([0-9A-Fa-f]{4})>\s*<([Ee][0-9A-Fa-f]{3}|[Ff][0-8][0-9A-Fa-f]{2})>", f.ToUnicode.read_bytes().decode("latin1"))
chk(not pua, "Aucun glyphe associé à un caractère Unicode privé (sinon lu comme vide)" + (f" — {len(pua)} trouvés" if pua else ""))
# annotations / ordre de tabulation
for i, page in enumerate(pdf.pages, 1):
    if "/Annots" in page:
        chk(page.get("/Tabs") == "/S", f"Page {i} : ordre de tabulation /Tabs=/S")

# ---- structure ----
rolemap = root.StructTreeRoot.get("/RoleMap", {})
def role(e):
    s = str(e.get("/S")); seen = 0
    while s in rolemap and seen < 5: s = str(rolemap[s]); seen += 1
    return s
pages_idx = {p.objgen: i for i, p in enumerate(pdf.pages)}
# texte par (page, mcid)
sys.path.insert(0, __import__("os").path.dirname(__file__))
from mcid_text import extract
mcid_text, unmarked_txt = extract(PATH)
chk(not any(t.strip() for t in unmarked_txt.values()), "Tout le texte est balisé ou marqué décoratif" + ("" if not any(t.strip() for t in unmarked_txt.values()) else f" — hors balise : {dict(unmarked_txt)}"))
PAINT = {"S","s","f","F","f*","B","B*","b","b*","Tj","TJ","'",'"',"Do","sh","INLINE IMAGE"}
bad = 0
for page in pdf.pages:
    md = 0; prev = None
    for operands, op in pikepdf.parse_content_stream(page):
        o = str(op)
        if o in ("BDC","BMC"): md += 1
        elif o == "EMC": md -= 1
        elif md == 0 and o in PAINT: bad += 1
chk(bad == 0, f"Tout le contenu graphique (fonds, traits, images) est balisé ou décoratif (opérations hors balise : {bad})")

seq = []  # (profondeur, rôle, texte)
heads = []; figs = []; tables = []
def mcids(e, pg):
    out = []
    k = e.get("/K")
    items = list(k) if isinstance(k, pikepdf.Array) else ([] if k is None else [k])
    for it in items:
        if isinstance(it, int): out.append(("mc", pg, int(it)))
        elif isinstance(it, pikepdf.Dictionary):
            t = str(it.get("/Type", ""))
            if t == "/MCR": out.append(("mc", pages_idx.get(it.Pg.objgen, pg) if "/Pg" in it else pg, int(it.MCID)))
            elif t == "/OBJR": pass
            else: out.append(("el", it))
    return out
def text_of(e, pg):
    s = ""
    for it in mcids(e, pg):
        if it[0] == "mc": s += mcid_text.get((it[1], it[2]), "")
        else:
            p2 = pages_idx.get(it[1].Pg.objgen, pg) if "/Pg" in it[1] else pg
            s += text_of(it[1], p2)
    return s
def walk(e, depth, pg):
    r = role(e)
    if "/Pg" in e: pg = pages_idx.get(e.Pg.objgen, pg)
    if r == "/Figure":
        alt = str(e.get("/Alt", "")); figs.append(alt)
        seq.append((depth, "Image", alt or "⚠ SANS TEXTE ALTERNATIF")); return
    if r in ("/H1", "/H2", "/H3", "/H4", "/H5", "/H6"):
        heads.append(int(r[2])); seq.append((depth, f"Titre {r[2]}", text_of(e, pg).strip())); return
    if r == "/Table": tables.append(e)
    if r in ("/P", "/TH", "/TD", "/LI", "/Caption", "/Lbl", "/LBody"):
        t = re.sub(r"\s+", " ", text_of(e, pg)).strip()
        lab = {"/P": "Paragraphe", "/TH": "En-tête", "/TD": "Cellule", "/LI": "Élément de liste", "/Caption": "Légende"}.get(r, r[1:])
        if r == "/TH" and "/A" in e:
            a = e.A; a = a[0] if isinstance(a, pikepdf.Array) else a
            if "/Scope" in a: lab += f" ({str(a.Scope)[1:]})"
        if t or r in ("/TD", "/TH"): seq.append((depth, lab, t or "(vide)"))
        return
    if r in ("/Table", "/L", "/TR", "/Document", "/Sect", "/Art", "/Div", "/NonStruct", "/Part", "/THead", "/TBody", "/Strong", "/Span"):
        marker = {"/Table": "Tableau", "/L": "Liste", "/TR": "Ligne"}.get(r)
        kids = [it for it in mcids(e, pg)]
        if marker: seq.append((depth, marker, ""))
        loose = "".join(mcid_text.get((it[1], it[2]), "") for it in kids if it[0] == "mc").strip()
        if loose: seq.append((depth + 1, "Texte", re.sub(r"\s+", " ", loose)))
        for it in kids:
            if it[0] == "el": walk(it[1], depth + (1 if marker else 0), pg)
        return
    seq.append((depth, r[1:], re.sub(r"\s+", " ", text_of(e, pg)).strip()))

K = root.StructTreeRoot.K
for e in (K if isinstance(K, pikepdf.Array) else [K]): walk(e, 0, 0)

chk(all(figs) and figs, f"Images avec texte alternatif : {sum(1 for f in figs if f)}/{len(figs)}")
chk(heads.count(1) == 1, f"Un seul titre de niveau 1 (trouvés : {heads.count(1)})")
chk(all(b - a <= 1 for a, b in zip(heads, heads[1:])), f"Niveaux de titres sans saut : {heads}")
def has_th(t):
    found = False
    def w(e):
        nonlocal found
        if isinstance(e, pikepdf.Dictionary):
            if role(e) == "/TH": found = True
            k = e.get("/K")
            if isinstance(k, pikepdf.Array):
                for x in k: w(x)
            elif isinstance(k, pikepdf.Dictionary): w(k)
    w(t); return found
chk(tables and all(has_th(t) for t in tables), f"Tableaux avec cellules d'en-tête : {sum(has_th(t) for t in tables)}/{len(tables)}")

print("=== CONTRÔLES ===")
for m in ok: print("  OK   ", m)
for m in warn: print("  ATTENTION", m)
for m in ko: print("  ÉCHEC", m)
print(f"\n=== ORDRE DE LECTURE (balises) — {len(seq)} éléments ===")
for d, r_, t in seq:
    print("  " * d + f"[{r_}] {t[:150]}")
