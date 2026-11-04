"""Complète les métadonnées du PDF balisé (Info + XMP) sans toucher à la structure."""
import sys, pikepdf
src, dst = sys.argv[1:3]
pdf = pikepdf.open(src)
TITLE = "Cartographie OSM à Nancy : couverture à 100 % + maintenance"
AUTHOR = "Simon PICOT"
SUBJECT = "Audit OpenStreetMap des cheminements piétons de Nancy : trottoirs, passages piétons, bordures et feux sonores"
with pdf.open_metadata(set_pikepdf_as_editor=False) as m:
    m["dc:title"] = TITLE; m["dc:creator"] = [AUTHOR]; m["dc:description"] = SUBJECT
    m["dc:language"] = ["fr-FR"]; m["pdf:Keywords"] = "OpenStreetMap, Nancy, accessibilité, trottoirs, piétons, déficients visuels"
pdf.docinfo["/Title"] = TITLE; pdf.docinfo["/Author"] = AUTHOR; pdf.docinfo["/Subject"] = SUBJECT
pdf.docinfo["/Keywords"] = "OpenStreetMap, Nancy, accessibilité, trottoirs, piétons, déficients visuels"
pdf.Root.Lang = pikepdf.String("fr-FR")
pdf.Root.ViewerPreferences = pikepdf.Dictionary(DisplayDocTitle=True)
pdf.save(dst)
