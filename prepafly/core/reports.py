"""Génération des documents PDF : dossier de vol, rapport de mission client, MANEX.

Utilise reportlab (pur Python, aucun binaire externe). Chaque fonction renvoie les
octets du PDF. Le logo de l'exploitant (image, chemin ou octets) est repris en
en-tête du rapport client et du MANEX.
"""
from __future__ import annotations

import base64
import datetime
import io
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

from . import drones, regimes, sora as sora_mod

# --- Palette / styles ---------------------------------------------------------
BLEU = colors.HexColor("#1b3a6b")
BLEU2 = colors.HexColor("#2f6fb0")
GRIS = colors.HexColor("#555f6d")
BORD = colors.HexColor("#d3ddea")
VERT = colors.HexColor("#1f8a4c")
ROUGE = colors.HexColor("#c0392b")

_ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=_ss["Heading1"], textColor=BLEU, fontSize=17, spaceAfter=2)
H2 = ParagraphStyle("H2", parent=_ss["Heading2"], textColor=BLEU2, fontSize=12, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("Body", parent=_ss["BodyText"], fontSize=9.5, leading=13, textColor=colors.HexColor("#222a35"))
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8, textColor=GRIS)
KICK = ParagraphStyle("Kick", parent=BODY, fontSize=8, textColor=BLEU2, spaceAfter=0)


def _logo_flowable(logo) -> Optional[Image]:
    """Accepte un data-URI, des octets ou un chemin ; renvoie une Image ou None."""
    if not logo:
        return None
    try:
        if isinstance(logo, str) and logo.startswith("data:"):
            b64 = logo.split(",", 1)[1]
            data = base64.b64decode(b64)
            src = io.BytesIO(data)
        elif isinstance(logo, (bytes, bytearray)):
            src = io.BytesIO(bytes(logo))
        else:
            src = str(logo)  # chemin
        img = Image(src)
        maxw, maxh = 45 * mm, 20 * mm
        ratio = min(maxw / img.imageWidth, maxh / img.imageHeight)
        img.drawWidth = img.imageWidth * ratio
        img.drawHeight = img.imageHeight * ratio
        return img
    except Exception:  # noqa: BLE001 - logo invalide : on l'ignore
        return None


def _header(story: list, title: str, subtitle: str, exploitant: dict, logo=None):
    left = []
    img = _logo_flowable(logo)
    if img:
        left.append(img)
    else:
        left.append(Paragraph(exploitant.get("raison") or "Exploitant", H2))
    right = [
        Paragraph(title, H1),
        Paragraph(subtitle, SMALL),
        Paragraph("Édité le " + datetime.date.today().strftime("%d/%m/%Y"), SMALL),
    ]
    t = Table([[left, right]], colWidths=[60 * mm, 115 * mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 1, BORD),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))


def _kv_table(rows: list[tuple[str, str]], col1=45 * mm, col2=130 * mm) -> Table:
    data = [[Paragraph(f"<b>{k}</b>", BODY), Paragraph(v or "—", BODY)] for k, v in rows]
    t = Table(data, colWidths=[col1, col2])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORD),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _build(story: list, title_meta: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=title_meta,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm)
    doc.build(story)
    return buf.getvalue()


def _pilote_ref(store: dict) -> dict:
    ref = store.get("referent")
    for p in store.get("pilotes", []):
        if p["id"] == ref:
            return p
    return store.get("pilotes", [{}])[0] if store.get("pilotes") else {}


def _appareil_label(d: dict) -> str:
    a = d.get("appareil", {})
    dj = drones.find(a.get("key", ""))
    if dj:
        return f"DJI {dj['modele']}"
    return " ".join(x for x in [a.get("marque"), a.get("modele")] if x) or "—"


# --- 1) Dossier de vol complet ------------------------------------------------

def dossier_pdf(store: dict, dossier: dict) -> bytes:
    e = store.get("exploitant", {})
    p = _pilote_ref(store)
    a = dossier.get("appareil", {})
    story: list = []
    _header(story, "Dossier de vol", dossier.get("titre") or "Mission", e, store.get("logo"))

    story.append(Paragraph("Exploitant", H2))
    story.append(_kv_table([
        ("Raison sociale", e.get("raison", "")),
        ("N° exploitant UAS", e.get("numUAS", "")),
        ("SIRET", e.get("siret", "")),
        ("Assurance RC", f"{e.get('assureur','')} — police {e.get('police','')}".strip(" —")),
    ]))

    story.append(Paragraph("Télépilote", H2))
    story.append(_kv_table([
        ("Nom", f"{p.get('prenom','')} {p.get('nom','')}".strip()),
        ("N° télépilote", p.get("numTele", "")),
        ("Mentions", ", ".join(p.get("mentions", [])) or "—"),
    ]))

    story.append(Paragraph("Appareil", H2))
    story.append(_kv_table([
        ("Modèle", _appareil_label(dossier)),
        ("N° de série", a.get("serie", "")),
        ("Classe C", dossier.get("classeC", "")),
        ("Masse au décollage", f"{a.get('masse','')} g" if a.get("masse") else "—"),
    ]))

    story.append(Paragraph("Mission & site", H2))
    site = ", ".join(x for x in [dossier.get("siteAdresse"), dossier.get("siteCp"),
                                 dossier.get("siteVille")] if x) or dossier.get("lieu", "")
    coords = (f"{dossier.get('lat')}, {dossier.get('lon')}"
              if dossier.get("lat") and dossier.get("lon") else "—")
    story.append(_kv_table([
        ("Lieu / site", site),
        ("Coordonnées", coords),
        ("Dates", f"{dossier.get('dateDebut','')} → {dossier.get('dateFin','')}".strip(" →")),
        ("Hauteur max", f"{dossier.get('hauteurMax','')} m" if dossier.get("hauteurMax") else "—"),
        ("Type de vol", dossier.get("typeVol", "")),
    ]))
    meteo = dossier.get("meteo", {})
    if meteo.get("metar"):
        story.append(Paragraph("Météo relevée (METAR)", H2))
        story.append(Paragraph(meteo.get("metar", ""), SMALL))

    story.append(Paragraph("Régime & conformité", H2))
    rec = regimes.recommend(dossier)
    regime = dossier.get("regime") or rec.regime
    story.append(_kv_table([
        ("Régime retenu", regimes.REGIME_LABEL.get(regime, regime or "—")),
        ("Sous-catégorie / scénario", dossier.get("sousCategorie") or dossier.get("pdra") or "—"),
        ("Recommandation auto.", f"{regimes.REGIME_SHORT.get(rec.regime, '')} — {rec.why}"),
    ]))

    if regime == "sora":
        res = sora_mod.compute_sora(dossier.get("grc", {}), dossier.get("arc", {}))
        story.append(Paragraph("Analyse SORA 2.5", H2))
        story.append(_kv_table([
            ("iGRC", str(res.igrc) if res.igrc is not None else "—"),
            ("GRC final", str(res.grc) if res.grc is not None else "—"),
            ("ARC initial / final", f"{(res.arc_initial or '—').upper()} / {(res.arc_residual or '—').upper()}"),
            ("SAIL", res.sail or "—"),
        ]))
        if res.oso_req:
            oso_rows = [["OSO", "Objectif", "Robustesse"]]
            for o in res.oso_req:
                oso_rows.append([o["id"], o["t"], sora_mod.REQ_TXT.get(o["lvl"], o["lvl"])])
            t = Table(oso_rows, colWidths=[12 * mm, 128 * mm, 35 * mm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), BLEU),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 1), (-1, -1), 0.3, BORD),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(t)

    # Check-list pré-vol
    prevol = dossier.get("prevol", {})
    if prevol:
        story.append(Paragraph("Check-list pré-vol", H2))
        rows = [[("☑" if v else "☐") + "  " + str(k)] for k, v in prevol.items()]
        if rows:
            t = Table(rows, colWidths=[175 * mm])
            t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9),
                                   ("TOPPADDING", (0, 0), (-1, -1), 1),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
            story.append(t)

    # Journal
    journal = dossier.get("journal", [])
    if journal:
        story.append(Paragraph("Journal de vol", H2))
        jr = [["Date", "Horaires", "Nb vols", "Incidents"]]
        for s in journal:
            jr.append([s.get("date", ""), f"{s.get('debut','')}-{s.get('fin','')}",
                       str(s.get("nb", "")), s.get("incidents", "")])
        t = Table(jr, colWidths=[28 * mm, 32 * mm, 20 * mm, 95 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLEU2), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8), ("LINEBELOW", (0, 1), (-1, -1), 0.3, BORD),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t)

    story.append(Spacer(1, 10))
    story.append(Paragraph("Document généré par PrepaFlyPy — aide à la préparation de vol, "
                           "ne se substitue pas à la réglementation applicable.", SMALL))
    return _build(story, "Dossier de vol")


# --- 2) Rapport de mission client --------------------------------------------

def rapport_pdf(store: dict, dossier: dict) -> bytes:
    e = store.get("exploitant", {})
    p = _pilote_ref(store)
    story: list = []
    _header(story, "Rapport de mission", dossier.get("titre") or "Prestation drone", e, store.get("logo"))

    story.append(Paragraph("Client", H2))
    story.append(_kv_table([("Client", dossier.get("client", "")),
                            ("Lieu", dossier.get("lieu") or dossier.get("siteVille", "")),
                            ("Dates", f"{dossier.get('dateDebut','')} → {dossier.get('dateFin','')}".strip(" →"))]))

    story.append(Paragraph("Prestation réalisée", H2))
    story.append(Paragraph(dossier.get("notes") or "Prestation de captation/inspection par drone.", BODY))

    story.append(Paragraph("Moyens mis en œuvre", H2))
    story.append(_kv_table([
        ("Exploitant", e.get("raison", "")),
        ("Télépilote", f"{p.get('prenom','')} {p.get('nom','')}".strip()),
        ("Appareil", _appareil_label(dossier)),
        ("Régime d'exploitation", regimes.REGIME_LABEL.get(dossier.get("regime", ""), dossier.get("regime", "") or "—")),
        ("Assurance RC", e.get("assureur", "")),
    ]))

    meteo = dossier.get("meteo", {})
    story.append(Paragraph("Conditions", H2))
    story.append(_kv_table([
        ("Hauteur max", f"{dossier.get('hauteurMax','')} m" if dossier.get("hauteurMax") else "—"),
        ("Météo", meteo.get("metar", "—") or "—"),
    ]))

    journal = dossier.get("journal", [])
    if journal:
        story.append(Paragraph("Déroulé", H2))
        for s in journal:
            line = f"{s.get('date','')} · {s.get('debut','')}-{s.get('fin','')} · {s.get('nb','')} vol(s)"
            if s.get("incidents"):
                line += f" · {s.get('incidents')}"
            story.append(Paragraph(line, BODY))

    story.append(Spacer(1, 12))
    story.append(Paragraph(f"{e.get('raison','MGI')} — {e.get('adresse','')} {e.get('cp','')} "
                           f"{e.get('ville','')} · {e.get('tel','')} · {e.get('mail','')}", SMALL))
    return _build(story, "Rapport de mission")


# --- 3) Trame de MANEX --------------------------------------------------------

_MANEX_PLAN = [
    ("A", "Généralités", ["Présentation de l'exploitant", "Domaine d'activité et types de missions",
                          "Organisation et responsabilités", "Amendements et diffusion du manuel"]),
    ("B", "Personnel", ["Télépilotes et qualifications", "Formation initiale et maintien de compétences",
                        "Aptitude médicale et facteurs humains"]),
    ("C", "Matériel", ["Aéronefs exploités et caractéristiques", "Maintenance et suivi",
                       "Équipements de sécurité et de télécommunication"]),
    ("D", "Opérations", ["Préparation de vol (analyse de site, météo, NOTAM, zones)",
                         "Procédures normales", "Procédures d'urgence et de secours",
                         "Comptes rendus d'événements"]),
    ("E", "Annexes", ["Modèles de documents (check-lists, journal)", "Assurances",
                      "Références réglementaires"]),
]


def manex_pdf(store: dict) -> bytes:
    e = store.get("exploitant", {})
    story: list = []
    _header(story, "MANEX (trame)", "Manuel d'exploitation — à relire et adapter", e, store.get("logo"))
    story.append(Paragraph("Cette trame est pré-remplie à partir de votre référentiel. Ce n'est "
                           "pas un MANEX validé : elle doit être relue, complétée et adaptée à "
                           "votre exploitation.", SMALL))

    story.append(Paragraph("Fiche exploitant", H2))
    story.append(_kv_table([
        ("Raison sociale", e.get("raison", "")), ("Forme juridique", e.get("forme", "")),
        ("SIRET", e.get("siret", "")), ("N° exploitant UAS", e.get("numUAS", "")),
        ("Responsable", e.get("responsable", "")),
        ("Adresse", f"{e.get('adresse','')} {e.get('cp','')} {e.get('ville','')}".strip()),
        ("Assurance RC", f"{e.get('assureur','')} — police {e.get('police','')}".strip(" —")),
    ]))

    pil = store.get("pilotes", [])
    if pil:
        story.append(Paragraph("Télépilotes", H2))
        rows = [["Nom", "N° télépilote", "Mentions"]]
        for p in pil:
            rows.append([f"{p.get('prenom','')} {p.get('nom','')}".strip(),
                         p.get("numTele", ""), ", ".join(p.get("mentions", []))])
        t = Table(rows, colWidths=[60 * mm, 45 * mm, 70 * mm])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), BLEU2),
                               ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("FONTSIZE", (0, 0), (-1, -1), 8),
                               ("LINEBELOW", (0, 1), (-1, -1), 0.3, BORD)]))
        story.append(t)

    fleet = {}
    for d in store.get("dossiers", []):
        lab = _appareil_label(d)
        if lab != "—":
            fleet[lab] = d.get("appareil", {}).get("serie", "")
    if fleet:
        story.append(Paragraph("Parc matériel (d'après les dossiers)", H2))
        story.append(_kv_table([(k, f"n° série {v}" if v else "—") for k, v in fleet.items()]))

    for code, titre, points in _MANEX_PLAN:
        story.append(Paragraph(f"Partie {code} — {titre}", H2))
        for pt in points:
            story.append(Paragraph(f"• {pt}", BODY))
            story.append(Paragraph("À compléter.", SMALL))

    return _build(story, "MANEX (trame)")
