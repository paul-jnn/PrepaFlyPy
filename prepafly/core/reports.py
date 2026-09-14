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
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

from . import drones, regimes, regs, sora as sora_mod

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
# Titres numérotés du dossier de vol (niveaux 1/2/3).
H1N = ParagraphStyle("H1N", parent=_ss["Heading1"], textColor=BLEU, fontSize=16, spaceBefore=8, spaceAfter=8)
H2N = ParagraphStyle("H2N", parent=_ss["Heading2"], textColor=colors.HexColor("#2a2f3a"), fontSize=12.5, spaceBefore=10, spaceAfter=4)
H3N = ParagraphStyle("H3N", parent=_ss["Heading3"], textColor=GRIS, fontSize=10.5, spaceBefore=6, spaceAfter=3)
COVERT = ParagraphStyle("CoverT", parent=_ss["Title"], textColor=BLEU, fontSize=26, alignment=1, spaceAfter=10)
COVERS = ParagraphStyle("CoverS", parent=BODY, fontSize=13, alignment=1, textColor=BLEU2)
MONO = ParagraphStyle("Mono", parent=BODY, fontName="Courier", fontSize=8.5, leading=11)


def _static_map_png(lat, lon, size=(455, 250), zoom=15, markers=None, polygon=None):
    """Rend une carte statique (tuiles OSM) centrée sur le point. Renvoie des
    octets PNG, ou None si indisponible (hors ligne, tuiles inaccessibles).
    polygon : liste de sommets [lat, lon] tracés en zone de vol (optionnel)."""
    try:
        latf, lonf = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    try:
        import contextlib
        from staticmap import CircleMarker, Line, StaticMap
        m = StaticMap(size[0], size[1], url_template="https://a.tile.openstreetmap.org/{z}/{x}/{y}.png")
        # Zone de vol : contour fermé tracé sous les marqueurs (Line = rendu sûr).
        if polygon and len(polygon) >= 3:
            coords = [(p[1], p[0]) for p in polygon]  # staticmap attend (lon, lat)
            coords.append(coords[0])
            m.add_line(Line(coords, "#2f6fb0", 3))
        pts = markers if markers else [(lonf, latf, "#c0392b")]
        for mlon, mlat, color in pts:
            m.add_marker(CircleMarker((mlon, mlat), color, 11))
        # staticmap fait un print() par tuile échouée (hors ligne) : on l'étouffe.
        with contextlib.redirect_stdout(io.StringIO()):
            img = m.render(zoom=zoom)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()
    except Exception:  # noqa: BLE001 - pas de réseau/tuiles : on omet la carte
        return None


def _map_flowable(lat, lon, **kw):
    data = _static_map_png(lat, lon, **kw)
    if not data:
        return None
    img = Image(io.BytesIO(data))
    maxw = 165 * mm
    if img.drawWidth > maxw:
        r = maxw / img.drawWidth
        img.drawWidth *= r
        img.drawHeight *= r
    return img


def _poly_area_m2(zone) -> float:
    """Aire sphérique approchée (m²) d'un polygone [[lat, lon], ...]."""
    if not zone or len(zone) < 3:
        return 0.0
    import math
    R = 6378137.0
    a = 0.0
    n = len(zone)
    for i in range(n):
        lat1, lon1 = zone[i]
        lat2, lon2 = zone[(i + 1) % n]
        a += math.radians(lon2 - lon1) * (2 + math.sin(math.radians(lat1)) + math.sin(math.radians(lat2)))
    return abs(a * R * R / 2.0)


def _fmt_area(m2: float) -> str:
    return f"{round(m2)} m²" if m2 < 10000 else f"{m2 / 10000:.2f} ha"


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


# --- 1) Dossier de vol complet (structure complète, niveau dossier officiel) ---

def dossier_pdf(store: dict, dossier: dict) -> bytes:
    e = store.get("exploitant", {})
    p = _pilote_ref(store)
    d = dossier
    a = d.get("appareil", {})
    smallc = ParagraphStyle("sc", parent=SMALL, alignment=1)
    story: list = []

    # ---------- Page de garde ----------
    story.append(Spacer(1, 40))
    logo = _logo_flowable(store.get("logo"))
    if logo:
        logo.hAlign = "CENTER"
        story.append(logo)
        story.append(Spacer(1, 16))
    story.append(Paragraph(d.get("titre") or "Dossier de vol", COVERT))
    dates = f"{d.get('dateDebut','')}  →  {d.get('dateFin','')}".strip(" →")
    if dates:
        story.append(Paragraph(dates, COVERS))
    coverloc = ", ".join(x for x in [d.get("siteCp"), d.get("siteVille")] if x)
    if coverloc:
        story.append(Paragraph(coverloc, COVERS))
    story.append(Spacer(1, 26))
    story.append(Paragraph("Réalisé par " + (e.get("raison") or "l'exploitant"), smallc))
    story.append(PageBreak())

    # ---------- Sommaire ----------
    story.append(Paragraph("Sommaire", H1))
    for line in ["1 — Vue d'ensemble",
                 "2 — Informations générales (déclarant, pilote référent, machine)",
                 "3 — Classification (régime, critères, réglementation)",
                 "4 — Contraintes & points de vigilance",
                 "5 — Météo",
                 "6 — Contexte (plan de vol : zone, points de décollage et observateurs)"]:
        story.append(Paragraph(line, BODY))
    story.append(PageBreak())

    # ---------- 1 Vue d'ensemble ----------
    story.append(Paragraph("1 — Vue d'ensemble", H1N))
    story.append(Paragraph("<b>Titre</b>", BODY))
    story.append(Paragraph(d.get("titre") or "—", BODY))
    zone = d.get("zone") or []
    clat, clon = d.get("lat"), d.get("lon")
    if (not clat or not clon) and len(zone) >= 1:
        clat, clon = zone[0][0], zone[0][1]
    mp = _map_flowable(clat, clon, polygon=zone)
    if mp:
        story.append(Spacer(1, 6))
        story.append(Paragraph("<b>Zone de vol</b>", BODY))
        mp.hAlign = "CENTER"
        story.append(mp)
        story.append(Spacer(1, 6))
    loc = ", ".join(x for x in [d.get("siteAdresse"), d.get("siteCp"), d.get("siteVille")] if x) or d.get("lieu", "")
    rows = [
        ("Localisation", loc),
        ("Coordonnées", f"{d.get('lat')}, {d.get('lon')}" if d.get("lat") and d.get("lon") else "—"),
        ("Dates", dates or "—"),
        ("Hauteur maximum (m)", str(d.get("hauteurMax") or "—")),
        ("Vitesse maximale appareil (m/s)", str(d.get("grc", {}).get("vit") or "—")),
    ]
    if len(zone) >= 3:
        rows.append(("Surface de la zone", _fmt_area(_poly_area_m2(zone))))
    story.append(_kv_table(rows))
    if d.get("notes"):
        story.append(Paragraph("Informations complémentaires", H3N))
        story.append(Paragraph(d.get("notes"), BODY))
    story.append(PageBreak())

    # ---------- 2 Informations générales ----------
    story.append(Paragraph("2 — Informations générales", H1N))
    story.append(Paragraph("2.1 — Déclarant", H2N))
    story.append(_kv_table([
        ("Société", e.get("raison", "")),
        ("Responsable", e.get("responsable", "")),
        ("Adresse", f"{e.get('adresse','')} {e.get('cp','')} {e.get('ville','')}".strip()),
        ("Téléphone", e.get("tel", "")),
        ("Email", e.get("mail", "")),
        ("SIRET", e.get("siret", "")),
        ("N° exploitant UAS", e.get("numUAS", "")),
        ("Assurance RC", f"{e.get('assureur','')} — police {e.get('police','')}".strip(" —")),
    ]))
    story.append(Paragraph("2.2 — Pilote référent", H2N))
    story.append(_kv_table([
        ("Prénom", p.get("prenom", "")),
        ("Nom", p.get("nom", "")),
        ("Téléphone", p.get("tel", "")),
        ("Email", p.get("mail", "")),
        ("N° télépilote", p.get("numTele", "")),
        ("Mentions", ", ".join(p.get("mentions", [])) or "—"),
    ]))
    story.append(Paragraph("2.3 — Machine principale", H2N))
    story.append(Paragraph("Données constructeur", H3N))
    dj = drones.find(a.get("key", ""))
    story.append(_kv_table([
        ("Marque", a.get("marque", "") or ("DJI" if dj else "")),
        ("Modèle", a.get("modele", "") or (dj["modele"] if dj else "—")),
        ("Classe C", d.get("classeC", "")),
        ("Masse au décollage", f"{a.get('masse','')} g" if a.get("masse") else "—"),
        ("Vitesse max (m/s)", str(d.get("grc", {}).get("vit") or "—")),
        ("Système de géolocalisation", a.get("geoloc", "")),
    ]))
    story.append(Paragraph("Équipements", H3N))
    equ = a.get("equipements", [])
    if equ:
        for it in equ:
            story.append(Paragraph("• " + str(it), BODY))
    else:
        story.append(Paragraph("Équipements de série.", SMALL))
    story.append(Paragraph("Informations complémentaires", H3N))
    story.append(_kv_table([
        ("N° de série", a.get("serie", "")),
        ("N° d'identification à distance", a.get("numId", "")),
        ("N° d'enregistrement", a.get("numEnr", "")),
    ]))
    story.append(PageBreak())

    # ---------- 3 Classification ----------
    story.append(Paragraph("3 — Classification", H1N))
    rec = regimes.recommend(d)
    regime = d.get("regime") or rec.regime
    sub = d.get("sousCategorie") or d.get("pdra") or ""
    lbl = regimes.REGIME_LABEL.get(regime, regime or "—")
    story.append(Paragraph("La classification retenue pour cette mission est :", BODY))
    head = (sub + " — " if sub else "") + lbl
    story.append(Paragraph(f"<b>{head}</b>", COVERS))
    story.append(Paragraph("3.1 — Critères déclarés", H2N))
    crs = regs.criteres(d)
    if crs:
        for c in crs:
            story.append(Paragraph("• " + c, BODY))
    else:
        story.append(Paragraph("Renseignez le type de vol et l'environnement dans l'onglet Mission.", SMALL))
    story.append(Paragraph("3.2 — Réglementation applicable", H2N))
    reg_rows = [["Référence", "Exigence"]]
    for ref, exp in regs.reglementation(regime, sub):
        reg_rows.append([Paragraph(f"<b>{ref}</b>", SMALL), Paragraph(exp, SMALL)])
    tr = Table(reg_rows, colWidths=[62 * mm, 113 * mm])
    tr.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLEU), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 8), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, BORD),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tr)
    if regime == "sora":
        res = sora_mod.compute_sora(d.get("grc", {}), d.get("arc", {}))
        story.append(Paragraph("Analyse SORA 2.5", H2N))
        story.append(_kv_table([
            ("iGRC", str(res.igrc) if res.igrc is not None else "—"),
            ("GRC final", str(res.grc) if res.grc is not None else "—"),
            ("ARC initial / final", f"{(res.arc_initial or '—').upper()} / {(res.arc_residual or '—').upper()}"),
            ("SAIL", res.sail or "—"),
        ]))
        if res.oso_req:
            oso = [["OSO", "Objectif", "Robustesse"]]
            for o in res.oso_req:
                oso.append([o["id"], o["t"], sora_mod.REQ_TXT.get(o["lvl"], o["lvl"])])
            t2 = Table(oso, colWidths=[12 * mm, 128 * mm, 35 * mm])
            t2.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), BLEU2), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("LINEBELOW", (0, 1), (-1, -1), 0.3, BORD),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(t2)
    story.append(PageBreak())

    # ---------- 4 Contraintes ----------
    story.append(Paragraph("4 — Contraintes & points de vigilance", H1N))
    story.append(Paragraph("Catégories de contraintes à examiner sur la zone (à confronter à "
                           "Géoportail, AlphaTango et aux NOTAM). PrepaFlyPy ne détecte pas "
                           "automatiquement les contraintes géographiques : documentez celles qui "
                           "s'appliquent.", SMALL))
    for cat, cons in regs.CONTRAINTES_REF:
        story.append(Paragraph(cat, H3N))
        story.append(Paragraph(cons, BODY))
    if d.get("contraintesNotes"):
        story.append(Paragraph("Contraintes relevées par l'exploitant", H2N))
        story.append(Paragraph(d.get("contraintesNotes"), BODY))
    story.append(PageBreak())

    # ---------- 5 Météo ----------
    story.append(Paragraph("5 — Météo", H1N))
    meteo = d.get("meteo", {})
    if meteo.get("icao"):
        story.append(Paragraph(f"Aérodrome de référence : {meteo.get('icao')}", BODY))
    if meteo.get("metar"):
        story.append(Paragraph("METAR", H3N))
        story.append(Paragraph(meteo.get("metar", ""), MONO))
    if meteo.get("taf"):
        story.append(Paragraph("TAF", H3N))
        story.append(Paragraph(meteo.get("taf", ""), MONO))
    if not (meteo.get("metar") or meteo.get("taf")):
        story.append(Paragraph("Relevez la météo (onglet Mission → « Relever la météo ») avant le vol.", SMALL))
    story.append(PageBreak())

    # ---------- 6 Contexte ----------
    story.append(Paragraph("6 — Contexte (plan de vol)", H1N))
    pts = d.get("points", [])
    zone = d.get("zone") or []
    markers = []
    for pt in pts:
        try:
            markers.append((float(pt.get("lon")), float(pt.get("lat")),
                            "#e67e22" if pt.get("type") == "observateur" else "#2f6fb0"))
        except (TypeError, ValueError):
            pass
    # Carte du plan : zone dessinée + marqueurs (centre = 1er marqueur, sinon 1er sommet).
    cen = None
    if markers:
        cen = (markers[0][1], markers[0][0])
    elif len(zone) >= 1:
        cen = (zone[0][0], zone[0][1])
    if cen:
        cm = _map_flowable(cen[0], cen[1], markers=markers or None, polygon=zone, zoom=16)
        if cm:
            cm.hAlign = "CENTER"
            story.append(cm)
            story.append(Spacer(1, 6))
    if len(zone) >= 3:
        story.append(Paragraph("Surface de la zone de vol : " + _fmt_area(_poly_area_m2(zone)), BODY))
    if pts:
        rows = [["#", "Type", "Intitulé", "Latitude", "Longitude"]]
        for i, pt in enumerate(pts, 1):
            typ = {"decollage": "Décollage/atterrissage", "observateur": "Observateur"}.get(pt.get("type"), pt.get("type", ""))
            rows.append([str(i), typ, pt.get("intitule", ""), str(pt.get("lat", "")), str(pt.get("lon", ""))])
        tp = Table(rows, colWidths=[10 * mm, 45 * mm, 60 * mm, 30 * mm, 30 * mm])
        tp.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLEU), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8), ("LINEBELOW", (0, 1), (-1, -1), 0.3, BORD),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(tp)
    elif not zone:
        story.append(Paragraph("Dessinez la zone de vol et placez vos points "
                               "(onglet « Plan de vol »).", SMALL))

    # ---------- Check-list & journal ----------
    prevol = d.get("prevol", {})
    if prevol:
        story.append(Paragraph("Check-list pré-vol", H2N))
        for k, vv in prevol.items():
            mark = '<font color="#1f8a4c"><b>[X]</b></font>' if vv else '[&nbsp;&nbsp;]'
            story.append(Paragraph(mark + " " + str(k), BODY))
    journal = d.get("journal", [])
    if journal:
        story.append(Paragraph("Journal de vol", H2N))
        jr = [["Date", "Horaires", "Nb vols", "Incidents"]]
        for s in journal:
            jr.append([s.get("date", ""), f"{s.get('debut','')}-{s.get('fin','')}",
                       str(s.get("nb", "")), s.get("incidents", "")])
        tj = Table(jr, colWidths=[28 * mm, 32 * mm, 20 * mm, 95 * mm])
        tj.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLEU2), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8), ("LINEBELOW", (0, 1), (-1, -1), 0.3, BORD),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(tj)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Document généré par PrepaFlyPy — aide à la préparation de vol, ne se "
                           "substitue pas à la réglementation applicable.", SMALL))
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
