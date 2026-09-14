"""Formulaires officiels.

Le Cerfa 15476*04 (déclaration préalable) et la dérogation R5-UAS-DEROG sont des
PDF à champs. S'ils sont fournis dans le dossier `forms/` du projet, on les remplit
avec pypdf à partir de l'exploitant, du télépilote référent et de la mission. Sinon,
on génère un équivalent lisible (lettre) avec reportlab, pour ne jamais bloquer.

L'AOT (occupation du domaine public) est toujours une lettre générée : le Cerfa
14023 voirie n'est pas interactif.

Le mappage exact des champs des Cerfa dépend des noms internes des gabarits ; il est
volontairement isolé dans FIELD_MAPS pour être ajusté sans toucher au reste.
"""
from __future__ import annotations

import datetime
import io
from pathlib import Path
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

FORMS_DIR = Path(__file__).resolve().parent.parent.parent / "forms"

# Noms de fichiers gabarits attendus (à déposer dans forms/). La casse n'importe
# pas sous Windows ; on résout aussi le fichier réel pour les autres systèmes.
TPL = {
    "cerfa": "cerfa_15476-04.pdf",
    "derog": "form_r5-uas-derog_v4.pdf",
}


def _pilote_ref(store: dict) -> dict:
    ref = store.get("referent")
    for p in store.get("pilotes", []):
        if p["id"] == ref:
            return p
    return store.get("pilotes", [{}])[0] if store.get("pilotes") else {}


def _tpl_path(kind: str):
    """Chemin du gabarit, en tolérant la casse du nom de fichier."""
    want = TPL.get(kind, "")
    p = FORMS_DIR / want
    if p.exists():
        return p
    if FORMS_DIR.exists():
        for f in FORMS_DIR.iterdir():
            if f.name.lower() == want.lower():
                return f
    return None


def template_available(kind: str) -> bool:
    return _tpl_path(kind) is not None


def _cerfa_fill(store: dict, dossier: dict):
    """Valeurs de champs pour le Cerfa 15476*04 : (champs texte, cases à cocher)."""
    e = store.get("exploitant", {})
    p = _pilote_ref(store)
    d = dossier
    resp = (e.get("responsable") or "").strip()
    parts = resp.split()
    resp_prenom, resp_nom = (parts[0], " ".join(parts[1:])) if len(parts) >= 2 else ("", resp)
    adresse = f"{e.get('adresse','')} {e.get('cp','')} {e.get('ville','')}".strip()
    contact = " / ".join(x for x in [e.get("tel", ""), e.get("mail", "")] if x)
    text = {
        "Raison sociale ou dénomination": e.get("raison", ""),
        "Adresse du siège social": adresse,
        "Identifiant SIRENSIRET RCSRNE": e.get("siret", ""),
        "Nom_2": resp_nom, "Prénom_2": resp_prenom, "Qualité": "Gérant" if resp else "",
        "Adresse postale_2": adresse,
        "Fixe  Portable Courriel": contact, "Fixe  Portable Courriel_2": contact,
        "Télépilote 1Nom": p.get("nom", ""), "Télépilote 1Prénom": p.get("prenom", ""),
        "Télépilote 1Téléphone portable": p.get("tel", ""), "Télépilote 1Courriel": p.get("mail", ""),
        "Code postalRow1": d.get("siteCp", ""), "LocalitéRow1": d.get("siteVille", ""),
        "AdresseRow1": d.get("siteAdresse", ""),
        "Le  JJMMAAAA": datetime.date.today().strftime("%d/%m/%Y"),
    }
    checks = []
    regime, sub = d.get("regime"), d.get("sousCategorie", "")
    if regime == "sts" and sub != "STS-02":
        checks.append("Scénario standard européen STS01 joindre une copie de laccusé de "
                      "réception de déclaration dactivité émis par la DGAC")
    if regime == "open":
        checks.append("Catégorie ouverte")
        checks.append({"A1": "Souscatégorie A1", "A2": "Souscatégorie A2",
                       "A3": "Souscatégorie A3"}.get(sub, ""))
    env = d.get("environnement")
    if env == "peuple":
        checks.append("En agglomération")
    elif env == "rassemblement":
        checks.append("A proximité dun rassemblement de personnes décrire")
    text = {k: v for k, v in text.items() if v}
    return text, [c for c in checks if c]


def _latin1(s: str) -> bytes:
    """Prépare une chaîne pour un flux PDF (police Helvetica / WinAnsi)."""
    repl = {"—": "-", "–": "-", "’": "'", "‘": "'",
            "“": '"', "”": '"', "…": "...", " ": " ", " ": " "}
    for a, b in repl.items():
        s = s.replace(a, b)
    s = s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return s.encode("latin-1", "replace")


def _add_text_appearances(writer, text: dict) -> None:
    """Construit un flux d'apparence par champ texte rempli.

    pypdf ne sait pas générer les apparences de ce Cerfa ; sans elles, beaucoup de
    visualiseurs (dont le lecteur intégré) n'affichent pas les valeurs. On les crée
    donc à la main, tout en gardant les champs éditables.
    """
    from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject,
                               NameObject, NumberObject)
    try:
        acro = writer._root_object["/AcroForm"].get_object()
        fonts = acro["/DR"].get_object()["/Font"].get_object()
        helv = fonts.get("/Helv")
    except Exception:  # noqa: BLE001
        helv = None
    for page in writer.pages:
        annots = page.get("/Annots")
        if not annots:
            continue
        for a in annots:
            wd = a.get_object()
            name = wd.get("/T")
            if name is None and wd.get("/Parent"):
                name = wd["/Parent"].get_object().get("/T")
            if name not in text:
                continue
            try:
                rect = [float(x) for x in wd["/Rect"]]
            except Exception:  # noqa: BLE001
                continue
            w = abs(rect[2] - rect[0])
            h = abs(rect[3] - rect[1])
            size = 9.0 if h > 13 else max(6.0, h - 3)
            body = _latin1(str(text[name]))
            content = (b"/Tx BMC\nq\nBT /Helv %.1f Tf 0 g 2 %.2f Td (" % (size, (h - size) / 2.0)
                       + body + b") Tj ET\nQ\nEMC")
            xo = DecodedStreamObject()
            xo.set_data(content)
            xo[NameObject("/Type")] = NameObject("/XObject")
            xo[NameObject("/Subtype")] = NameObject("/Form")
            xo[NameObject("/BBox")] = ArrayObject(
                [NumberObject(0), NumberObject(0), NumberObject(w), NumberObject(h)])
            res = DictionaryObject()
            fd = DictionaryObject()
            if helv is not None:
                fd[NameObject("/Helv")] = helv
            res[NameObject("/Font")] = fd
            xo[NameObject("/Resources")] = res
            ref = writer._add_object(xo)
            ap = DictionaryObject()
            ap[NameObject("/N")] = ref
            wd[NameObject("/AP")] = ap


def _fill_pdf_template(kind: str, text: dict, checks: list) -> bytes:
    import contextlib
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(str(_tpl_path(kind)))
    writer = PdfWriter()
    writer.append(reader)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        for page in writer.pages:
            if text:
                writer.update_page_form_field_values(page, text, auto_regenerate=False)
            if checks:
                writer.update_page_form_field_values(page, {c: "/On" for c in checks}, auto_regenerate=False)
    # Apparences des champs texte (les cases à cocher gardent leurs apparences natives).
    _add_text_appearances(writer, text)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _letter(title: str, lines: list[str]) -> bytes:
    ss = getSampleStyleSheet()
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=10.5, leading=15)
    h = ParagraphStyle("h", parent=ss["Heading1"], fontSize=15)
    story = [Paragraph(title, h), Spacer(1, 8)]
    for ln in lines:
        story.append(Paragraph(ln or "&nbsp;", body))
        story.append(Spacer(1, 4))
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=22 * mm, rightMargin=22 * mm,
                      topMargin=22 * mm, bottomMargin=22 * mm, title=title).build(story)
    return buf.getvalue()


def cerfa_values(store: dict, dossier: dict) -> dict:
    """Valeurs métier à injecter (indépendant du gabarit)."""
    e = store.get("exploitant", {})
    p = _pilote_ref(store)
    return {
        "exploitant_raison": e.get("raison", ""),
        "exploitant_siret": e.get("siret", ""),
        "exploitant_uas": e.get("numUAS", ""),
        "exploitant_adresse": f"{e.get('adresse','')} {e.get('cp','')} {e.get('ville','')}".strip(),
        "telepilote_nom": f"{p.get('prenom','')} {p.get('nom','')}".strip(),
        "telepilote_num": p.get("numTele", ""),
        "mission_lieu": dossier.get("lieu") or dossier.get("siteVille", ""),
        "mission_dates": f"{dossier.get('dateDebut','')} - {dossier.get('dateFin','')}".strip(" -"),
        "mission_hauteur": str(dossier.get("hauteurMax", "")),
    }


def generate(kind: str, store: dict, dossier: dict) -> bytes:
    """Génère un formulaire. kind ∈ {cerfa, derog, aot}."""
    e = store.get("exploitant", {})
    p = _pilote_ref(store)
    if kind == "cerfa":
        # Remplissage du vrai Cerfa 15476*04 si le gabarit est présent.
        if template_available("cerfa"):
            text, checks = _cerfa_fill(store, dossier)
            return _fill_pdf_template("cerfa", text, checks)
        # Repli lisible si le gabarit manque.
        vals = cerfa_values(store, dossier)
        lines = [f"<b>{k}</b> : {v}" for k, v in vals.items() if v]
        lines.append("")
        lines.append("<i>Gabarit Cerfa introuvable dans forms/. Reporter ces valeurs sur le "
                     "formulaire officiel.</i>")
        return _letter("Déclaration préalable (Cerfa 15476*04) — brouillon", lines)

    if kind == "derog":
        # Les champs du gabarit dérogation ne sont pas nommés de façon exploitable :
        # on fournit un brouillon lisible à reporter (le gabarit vierge reste dans forms/).
        vals = cerfa_values(store, dossier)
        lines = [f"<b>{k}</b> : {v}" for k, v in vals.items() if v]
        lines.append("")
        lines.append("<i>Document de travail généré par PrepaFlyPy. Reporter ces valeurs sur "
                     "le formulaire officiel R5-UAS-DEROG (forms/).</i>")
        return _letter("Demande de dérogation R5-UAS-DEROG — brouillon", lines)

    if kind == "aot":
        today = datetime.date.today().strftime("%d/%m/%Y")
        gest = dossier.get("forms", {}).get("aotGestionnaire", "le gestionnaire de voirie")
        objet = dossier.get("forms", {}).get("aotObjet", "réalisation de prises de vues par drone")
        lieu = dossier.get("lieu") or dossier.get("siteVille", "")
        lines = [
            f"{e.get('raison','')}<br/>{e.get('adresse','')}<br/>{e.get('cp','')} {e.get('ville','')}",
            "", f"À l'attention de {gest}", "", f"Objet : demande d'autorisation d'occupation "
            f"temporaire du domaine public (AOT) — {objet}", "",
            f"Madame, Monsieur,", "",
            f"Dans le cadre d'une prestation par aéronef télépiloté ({objet}) prévue à "
            f"{lieu} du {dossier.get('dateDebut','')} au {dossier.get('dateFin','')}, "
            f"je sollicite l'autorisation d'occupation temporaire du domaine public nécessaire "
            f"au décollage, à l'atterrissage et à la mise en place du périmètre de sécurité.",
            "",
            f"L'exploitant {e.get('raison','')} (n° UAS {e.get('numUAS','')}) est assuré en "
            f"responsabilité civile auprès de {e.get('assureur','')}. Le télépilote "
            f"{p.get('prenom','')} {p.get('nom','')} est déclaré et qualifié.",
            "", "Je reste à votre disposition pour toute précision.", "",
            f"Fait le {today}.", "", f"{e.get('responsable','')}, {e.get('raison','')}",
        ]
        return _letter("Demande d'AOT", lines)

    raise ValueError(f"Formulaire inconnu : {kind}")
