"""Extraction texte CV: PDF (pypdf) et DOCX (python-docx) + détection pièges ATS."""
import io
import re

def extract_pdf(data: bytes) -> tuple[str, dict]:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    text = "\n".join(pages)
    flags = pdf_ats_flags(reader, text)
    return text, flags

def pdf_ats_flags(reader, text: str) -> dict:
    flags = {"tables": False, "columns": False, "image_heavy": False, "low_text_ratio": False}
    n_pages = max(len(reader.pages), 1)
    n_images = 0
    for page in reader.pages:
        try:
            res = page.get("/Resources")
            if res and "/XObject" in res:
                xo = res["/XObject"].get_object()
                for obj in xo.values():
                    o = obj.get_object()
                    if o.get("/Subtype") == "/Image":
                        n_images += 1
        except Exception:
            pass
    words = len(text.split())
    # tableaux: beaucoup de lignes courtes alignées / mots isolés par page
    lines = [l for l in text.splitlines() if l.strip()]
    short = sum(1 for l in lines if len(l.split()) <= 2)
    flags["tables"] = len(lines) > 20 and short / max(len(lines), 1) > 0.55
    # colonnes: texte de page 1 dont les lignes commencent souvent par une majuscche
    # heuristique: variation forte de longueur de mots consécutifs + double espacement fréquent
    flags["columns"] = bool(re.search(r"\S+\s{3,}\S+\s{3,}\S+", text)) and words / n_pages > 120
    flags["image_heavy"] = n_images / n_pages >= 3
    flags["low_text_ratio"] = words / n_pages < 60
    return flags

def extract_docx(data: bytes) -> tuple[str, dict]:
    import docx
    d = docx.Document(io.BytesIO(data))
    parts = [p.text for p in d.paragraphs]
    n_tables = len(d.tables)
    for t in d.tables:
        for row in t.rows:
            parts.append(" | ".join(c.text for c in row.cells))
    text = "\n".join(parts)
    flags = {"tables": n_tables >= 2, "columns": False, "image_heavy": False, "low_text_ratio": len(text.split()) < 150}
    return text, flags

def extract(data: bytes, filename: str) -> tuple[str, dict]:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return extract_pdf(data)
    if name.endswith(".docx"):
        return extract_docx(data)
    if name.endswith(".doc"):
        # .doc legacy: tentative texte brut
        try:
            txt = data.decode("utf-8", errors="ignore")
            txt = re.sub(r"[^\x09\x0a\x0d\x20-\x7e\u00c0-\u017f]", " ", txt)
            return txt, {"tables": False, "columns": False, "image_heavy": True, "low_text_ratio": len(txt.split()) < 150}
        except Exception:
            return "", {"low_text_ratio": True}
    if name.endswith((".txt", ".md", ".rtf")):
        txt = data.decode("utf-8", errors="ignore")
        if name.endswith(".rtf"):
            txt = re.sub(r"\\[a-z]+-?\d* ?", "", txt)
        return txt, {"tables": False, "columns": False, "image_heavy": False, "low_text_ratio": False}
    raise ValueError("Format non supporté (PDF, DOCX, TXT)")
