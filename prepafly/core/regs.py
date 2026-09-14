"""Données réglementaires de référence pour le dossier de vol.

- REGLEMENTATION : par régime/scénario, la liste des articles applicables avec
  leur explication (repris de la structure des dossiers officiels).
- criteres() : déduit du dossier les éléments déclarés (vue/hors-vue, zone…).
- CONTRAINTES_REF : catégories standard de contraintes avec la consigne
  réglementaire associée (à documenter par l'exploitant, faute d'une base
  géospatiale automatique).

Ces textes sont des références réglementaires génériques, à vérifier avant tout
dépôt officiel ; ils ne se substituent pas aux fiches et arrêtés en vigueur.
"""
from __future__ import annotations

# Chaque entrée : (référence, explication).
_STS01 = [
    ("NOR DEVX1614320L art. 4 ; ECOI1901144D ; ECOI1934044A",
     "L'aéronef dispose d'un signalement électronique national si sa masse est ≥ 800 g."),
    ("EU 2020/639, app. 1, ch. 1, UAS.STS-01.040 1)",
     "L'aéronef dispose de l'identification directe à distance (signalement UE) si sa masse est ≥ 250 g."),
    ("EU 2020/639, app. 1, ch. 1, UAS.STS-01.020 1) f)",
     "Machine de classe C5."),
    ("EU 2019/947, art. 14, 5 b)",
     "Enregistrement de l'exploitant d'UAS en ligne sur le portail AlphaTango."),
    ("EU 2019/947, art. 9, 1",
     "Le pilote doit être âgé de 16 ans au minimum."),
    ("EU 2020/639, app. 1, ch. 1, UAS.STS-01.020 1) e) i)",
     "Le pilote doit être titulaire du CATS (théorique) et d'une attestation de formation pratique STS-01."),
    ("EU 2020/639, app. 1, ch. 1, UAS.STS-01.030 1)",
     "Manuel d'exploitation (MANEX)."),
    ("EU 2020/639, app. 1, ch. 1, UAS.STS-01.010 1)",
     "La hauteur maximale est de 120 m au-dessus de la surface."),
    ("EU 2020/639, app. 1, ch. 1, UAS.STS-01.010 1) d)",
     "Vitesse sol inférieure à 5 m/s pour un aéronef non captif sans équipage à bord."),
    ("EU 2020/639, app. 1, (3)",
     "Utilisation de l'aéronef en zone peuplée ou hors zone peuplée."),
    ("EU 2020/639, app. 1, (3)",
     "Zone au sol contrôlée (tiers exclus)."),
]

_STS02 = [
    ("EU 2020/639, app. 1, ch. 2, UAS.STS-02.020 1) f)",
     "Machine de classe C6."),
    ("EU 2019/947, art. 14, 5 b)",
     "Enregistrement de l'exploitant d'UAS sur AlphaTango."),
    ("EU 2019/947, art. 9, 1",
     "Le pilote doit être âgé de 16 ans au minimum."),
    ("EU 2020/639, app. 1, ch. 2, UAS.STS-02.020 1) e)",
     "CATS (théorique) et attestation de formation pratique STS-02."),
    ("EU 2020/639, app. 1, ch. 2, UAS.STS-02.030 1)",
     "Manuel d'exploitation (MANEX)."),
    ("EU 2020/639, app. 1, ch. 2, UAS.STS-02.010",
     "Vol hors vue (BVLOS) avec observateurs d'espace aérien, hauteur ≤ 120 m, zone au sol contrôlée en zone peu peuplée."),
]

_OPEN = [
    ("EU 2019/947, art. 4 & partie A de l'annexe",
     "Vol en catégorie ouverte : hauteur ≤ 120 m, en vue directe (VLOS), jamais au-dessus de rassemblements de personnes."),
    ("EU 2019/947, UAS.OPEN.020 / .030 / .040",
     "Sous-catégorie A1 (drone C0/C1), A2 (drone C2, distances de sécurité) ou A3 (drone C2-C4, ≥ 150 m des zones habitées)."),
    ("EU 2019/947, art. 14",
     "Enregistrement de l'exploitant (AlphaTango) dès lors que le drone dispose d'un capteur ou dépasse 250 g."),
    ("EU 2019/947, art. 9",
     "Compétences du télépilote adaptées à la sous-catégorie (attestation A1/A3 ou brevet A2)."),
]

_PDRA = [
    ("EU 2019/947, art. 5 (catégorie spécifique)",
     "Exploitation sous scénario de risque prédéfini (PDRA) : demande d'autorisation d'exploitation auprès de la DGAC."),
    ("PDRA applicable (S01/S02/G01-G03)",
     "Respect des conditions du PDRA retenu : distances, hauteur, espace aérien, zone d'exclusion des tiers."),
    ("EU 2019/947, art. 14",
     "Enregistrement de l'exploitant d'UAS (AlphaTango)."),
    ("Manuel d'exploitation (MANEX)",
     "MANEX conforme au scénario, procédures normales et d'urgence définies."),
]

_SORA = [
    ("EU 2019/947, art. 11 (SORA)",
     "Analyse de risque SORA : détermination du SAIL et des objectifs de sécurité (OSO)."),
    ("Autorisation d'exploitation DGAC",
     "Le vol nécessite une autorisation d'exploitation délivrée après instruction du dossier SORA."),
    ("EU 2019/947, art. 14",
     "Enregistrement de l'exploitant d'UAS (AlphaTango)."),
    ("Manuel d'exploitation (MANEX)",
     "MANEX et robustesse des OSO au niveau exigé par le SAIL."),
]


def reglementation(regime: str, sous_categorie: str = "") -> list[tuple[str, str]]:
    """Renvoie la liste (référence, explication) pour le régime/scénario."""
    if regime == "sts":
        return _STS02 if sous_categorie == "STS-02" else _STS01
    if regime == "open":
        return _OPEN
    if regime == "pdra":
        return _PDRA
    if regime == "sora":
        return _SORA
    return _OPEN


def criteres(d: dict) -> list[str]:
    """Éléments expressément déclarés, déduits du dossier."""
    out = []
    tv = d.get("typeVol")
    if tv == "VLOS":
        out.append("Exploitation en vue directe (VLOS)")
    elif tv == "BVLOS":
        out.append("Exploitation hors vue (BVLOS)")
    env = d.get("environnement")
    if env == "rassemblement":
        out.append("Mission en agglomération ou à proximité d'un rassemblement de personnes")
    elif env == "peuple":
        out.append("Mission en zone peuplée")
    elif env == "hors":
        out.append("Mission hors zone peuplée")
    dist = d.get("distanceTiers")
    if dist in ("30m", "5m", "150m"):
        out.append("Distance de sécurité aux tiers respectée")
    return out


# Catégories standard de contraintes et consigne réglementaire associée.
CONTRAINTES_REF = [
    ("Zone urbaine / peuplée",
     "Avant tout vol en zone peuplée, une déclaration doit être faite à la préfecture, en "
     "priorité via AlphaTango (onglet « Notification ») ou par courriel en joignant le Cerfa "
     "15476. Vérifier si le vol se situe en agglomération ou à proximité d'un rassemblement."),
    ("Routes",
     "Si des voies de circulation (route, chemin) traversent la zone d'exclusion des tiers, y "
     "porter une attention particulière. L'aéronef ne doit pas évoluer à moins de 30 m d'une "
     "autoroute ou route express, sauf si celle-ci est neutralisée."),
    ("Voies ferrées",
     "L'aéronef ne doit pas évoluer à moins de 30 m d'une voie ferrée ouverte à la circulation "
     "ferroviaire, sauf coordination avec le gestionnaire de la voie."),
    ("Élévation du sol",
     "Donné pour information : vérifier le relief et l'élévation du sol dans la zone pour tenir "
     "la hauteur réglementaire au-dessus de la surface."),
    ("Densité de population",
     "Donné pour information : estimer le nombre de personnes présentes dans et autour de la "
     "zone survolée (dimensionnement de la zone d'exclusion des tiers)."),
    ("Réseau mobile / antennes",
     "Donné pour information : présence d'antennes relais susceptibles de perturber les liaisons "
     "de commande et de retour vidéo. Repérer les émetteurs proches."),
    ("Espace aérien",
     "Vérifier les zones réglementées, NOTAM et la proximité d'aérodromes (SOFIA, Géoportail). "
     "Respecter les hauteurs et coordinations requises."),
]
