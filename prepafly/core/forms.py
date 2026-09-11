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

# Noms de fichiers gabarits attendus (à déposer dans forms/).
TPL = {
    "cerfa": "cerfa_15476-04.pdf",
    "derog": "form_r5-uas-derog_v4.pdf",
}

# Mappage {nom_de_champ_PDF: fonction(store, dossier) -> valeur}. À ajuster selon
# les vrais noms de champs des gabarits (relevables avec pypdf).
# Laissé minimal ici ; complété quand les gabarits sont présents.
FIELD_MAPS: dict[str, dict] = {"cerfa": {}, "derog": {}}


def _pilote_ref(store: dict) -> dict:
    ref = store.get("referent")
    for p in store.get("pilotes", []):
        if p["id"] == ref:
            return p
    return store.get("pilotes", [{}])[0] if store.get("pilotes") else {}


def template_available(kind: str) -> bool:
    return (FORMS_DIR / TPL.get(kind, "")).exists()


def _fill_pdf_template(kind: str, values: dict) -> bytes:
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(str(FORMS_DIR / TPL[kind]))
    writer = PdfWriter()
    writer.append(reader)
    for page in writer.pages:
        writer.update_page_form_field_values(page, values)
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
    if kind in ("cerfa", "derog"):
        vals = cerfa_values(store, dossier)
        if template_available(kind) and FIELD_MAPS.get(kind):
            mapped = {pdf_field: fn(store, dossier) if callable(fn) else vals.get(fn, "")
                      for pdf_field, fn in FIELD_MAPS[kind].items()}
            return _fill_pdf_template(kind, mapped)
        # Repli lisible tant que le gabarit/mappage n'est pas fourni.
        title = ("Déclaration préalable (Cerfa 15476*04) — brouillon"
                 if kind == "cerfa" else "Demande de dérogation R5-UAS-DEROG — brouillon")
        lines = [f"<b>{k}</b> : {v}" for k, v in vals.items() if v]
        lines.append("")
        lines.append("<i>Document de travail généré par PrepaFlyPy. Reporter ces valeurs "
                     "sur le formulaire officiel, ou déposer le gabarit PDF dans forms/ pour "
                     "un remplissage automatique.</i>")
        return _letter(title, lines)

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
