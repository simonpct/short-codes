"""Post-traitement du PDF balisé produit par Chromium :
1. tout contenu hors balise (texte masqué aux lecteurs d'écran, fonds, barres décoratives) est marqué /Artifact,
   comme l'exige PDF/UA (Matterhorn 01-005) ;
2. métadonnées Info + XMP (titre, auteur, sujet, langue), affichage du titre.
La structure (arbre de balises, MCID) n'est pas modifiée."""
import sys, pikepdf

src, dst = sys.argv[1:3]
pdf = pikepdf.open(src)

PATH_BUILD = {"m", "l", "c", "v", "y", "h", "re"}
PATH_PAINT = {"S", "s", "f", "F", "f*", "B", "B*", "b", "b*", "n"}
TEXT_SHOW = {"Tj", "TJ", "'", '"'}
XOBJ = {"Do", "sh", "INLINE IMAGE"}
BMC = lambda: ([pikepdf.Name("/Artifact")], pikepdf.Operator("BMC"))
EMC = lambda: ([], pikepdf.Operator("EMC"))

def artifactize(ops):
    out, md, path_start = [], 0, None
    for operands, op in ops:
        o = str(op)
        if o in ("BDC", "BMC"):
            md += 1; out.append((operands, op)); continue
        if o == "EMC":
            md -= 1; out.append((operands, op)); continue
        if md > 0:
            out.append((operands, op)); continue
        if o in PATH_BUILD:
            if path_start is None: path_start = len(out)
            out.append((operands, op)); continue
        if o in PATH_PAINT:
            if path_start is None: path_start = len(out)
            if o == "n" or (len(out) and str(out[-1][1]) in ("W", "W*")):  # tracé de découpe : n'imprime rien
                out.append((operands, op)); path_start = None; continue
            out.insert(path_start, BMC()); out.append((operands, op)); out.append(EMC()); path_start = None; continue
        if o in ("W", "W*"):
            out.append((operands, op)); continue
        if o in TEXT_SHOW or o in XOBJ:
            out.append(BMC()); out.append((operands, op)); out.append(EMC()); continue
        out.append((operands, op))
    return out

for page in pdf.pages:
    ops = pikepdf.parse_content_stream(page)
    page.Contents = pdf.make_stream(pikepdf.unparse_content_stream(artifactize(ops)))

TITLE = "Cartographie OSM à Nancy : couverture à 100 % + maintenance"
AUTHOR = "Simon PICOT"
SUBJECT = "Audit OpenStreetMap des cheminements piétons de Nancy : trottoirs, passages piétons, bordures et feux sonores"
KW = "OpenStreetMap, Nancy, accessibilité, trottoirs, piétons, déficients visuels"
with pdf.open_metadata(set_pikepdf_as_editor=False) as m:
    m["dc:title"] = TITLE; m["dc:creator"] = [AUTHOR]; m["dc:description"] = SUBJECT
    m["dc:language"] = ["fr-FR"]; m["pdf:Keywords"] = KW
pdf.docinfo["/Title"] = TITLE; pdf.docinfo["/Author"] = AUTHOR; pdf.docinfo["/Subject"] = SUBJECT; pdf.docinfo["/Keywords"] = KW
pdf.Root.Lang = pikepdf.String("fr-FR")
pdf.Root.ViewerPreferences = pikepdf.Dictionary(DisplayDocTitle=True)
pdf.save(dst)
