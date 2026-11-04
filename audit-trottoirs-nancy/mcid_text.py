"""Texte par (page, MCID) et texte non balisé, via l'interpréteur pdfminer."""
from collections import defaultdict
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams

class Dev(PDFPageAggregator):
    def __init__(self, rsrc):
        super().__init__(rsrc, laparams=LAParams()); self.stack = []; self.out = defaultdict(str); self.unmarked = defaultdict(str); self.pno = 0
    def begin_tag(self, tag, props=None):
        mc = props.get("MCID") if isinstance(props, dict) else None
        self.stack.append((getattr(tag, "name", str(tag)), mc))
    def end_tag(self):
        if self.stack: self.stack.pop()
    def render_char(self, matrix, font, fontsize, scaling, rise, cid, ncs, graphicstate):
        w = super().render_char(matrix, font, fontsize, scaling, rise, cid, ncs, graphicstate)
        ch = self.cur_item._objs[-1].get_text() if self.cur_item._objs else ""
        mc = next((m for _, m in reversed(self.stack) if m is not None), None)
        art = any(t == "Artifact" for t, _ in self.stack)
        if mc is not None: self.out[(self.pno, mc)] += ch
        elif not art: self.unmarked[self.pno] += ch
        return w

def extract(path):
    with open(path, "rb") as f:
        doc = PDFDocument(PDFParser(f)); rm = PDFResourceManager(); dev = Dev(rm); it = PDFPageInterpreter(rm, dev)
        for i, page in enumerate(PDFPage.create_pages(doc)):
            dev.pno = i; it.process_page(page)
    return dev.out, dev.unmarked
if __name__ == "__main__":
    import sys
    out, un = extract(sys.argv[1])
    print(len(out), "segments balisés")
    for p, t in un.items(): print(f"NON BALISÉ p{p+1}:", repr(t[:600]))
