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


# --- Démarches à effectuer par régime (déclaration / autorisation / etc.) ------
# Chaque entrée : (type, titre, détail). Le type sert de pastille dans l'UI/PDF.
_PROC_STS01 = [
    ("declaration", "Déclaration préalable d'exploitation (STS-01)",
     "Déposer la déclaration d'exploitation en catégorie spécifique sur AlphaTango, "
     "au moins 5 jours ouvrables avant le vol. Recevoir l'accusé de réception avant d'opérer."),
    ("enregistrement", "Enregistrement de l'exploitant UAS",
     "Exploitant enregistré sur AlphaTango ; numéro d'exploitant apposé sur l'aéronef."),
    ("competence", "Compétences du télépilote",
     "CATS (théorique) + attestation de suivi de formation pratique STS-01 en cours de validité."),
    ("materiel", "Aéronef de classe C5",
     "Drone porteur du marquage de classe C5 (ou C3 muni du kit d'accessoires C5), "
     "avec identification directe à distance et signalement électronique (masse ≥ 800 g)."),
    ("document", "Manuel d'exploitation (MANEX)",
     "MANEX à jour, procédures normales et d'urgence, disponible pendant l'exploitation."),
    ("condition", "Conditions de vol STS-01",
     "VLOS, hauteur ≤ 120 m, vitesse sol ≤ 5 m/s (aéronef non captif), zone au sol contrôlée "
     "(tiers exclus), en zone peuplée ou hors zone peuplée."),
    ("assurance", "Assurance responsabilité civile",
     "Attestation d'assurance RC aéronef en cours de validité."),
]

_PROC_STS02 = [
    ("declaration", "Déclaration préalable d'exploitation (STS-02)",
     "Déclaration d'exploitation en catégorie spécifique sur AlphaTango, au moins 5 jours "
     "ouvrables avant le vol ; accusé de réception avant d'opérer."),
    ("enregistrement", "Enregistrement de l'exploitant UAS",
     "Exploitant enregistré sur AlphaTango ; numéro apposé sur l'aéronef."),
    ("competence", "Compétences du télépilote",
     "CATS (théorique) + attestation de formation pratique STS-02."),
    ("materiel", "Aéronef de classe C6",
     "Drone de classe C6, identification directe à distance et signalement électronique."),
    ("document", "Manuel d'exploitation (MANEX)", "MANEX à jour et disponible."),
    ("condition", "Conditions de vol STS-02",
     "BVLOS avec observateurs d'espace aérien, hauteur ≤ 120 m, zone au sol contrôlée "
     "en zone peu peuplée."),
    ("assurance", "Assurance responsabilité civile", "Attestation RC aéronef à jour."),
]

_PROC_OPEN = [
    ("enregistrement", "Enregistrement de l'exploitant",
     "Enregistrement sur AlphaTango dès que le drone dépasse 250 g ou embarque un capteur ; "
     "numéro d'exploitant apposé sur l'aéronef."),
    ("competence", "Compétences du télépilote",
     "A1/A3 : formation en ligne + attestation. A2 : brevet d'aptitude (examen théorique) "
     "en plus de la formation A1/A3."),
    ("condition", "Conditions de la catégorie ouverte",
     "Hauteur ≤ 120 m, en vue directe (VLOS), jamais au-dessus de rassemblements de personnes."),
    ("condition", "Distances selon la sous-catégorie",
     "A1 (drone C0/C1) : survol de tiers limité. A2 (C2) : ≥ 30 m des tiers (5 m en mode basse "
     "vitesse). A3 (C2–C4) : ≥ 150 m des zones résidentielles/commerciales/industrielles."),
    ("condition", "Pas de déclaration préalable",
     "La catégorie ouverte ne nécessite ni déclaration ni autorisation d'exploitation."),
    ("assurance", "Assurance responsabilité civile", "Assurance RC recommandée/obligatoire selon l'usage."),
]

_PROC_PDRA = [
    ("autorisation", "Autorisation d'exploitation (PDRA)",
     "Déposer une demande d'autorisation d'exploitation auprès de la DGAC sur la base du "
     "scénario standard national / PDRA retenu."),
    ("enregistrement", "Enregistrement de l'exploitant UAS", "Exploitant enregistré sur AlphaTango."),
    ("document", "Manuel d'exploitation (MANEX)",
     "MANEX conforme au PDRA, procédures normales et d'urgence."),
    ("competence", "Compétences du télépilote",
     "Formations et attestations exigées par le PDRA retenu."),
    ("condition", "Respect des conditions du PDRA",
     "Distances, hauteur, espace aérien et zone d'exclusion des tiers conformes au PDRA."),
    ("assurance", "Assurance responsabilité civile", "Attestation RC aéronef à jour."),
]

_PROC_SORA = [
    ("analyse", "Analyse de risque SORA",
     "Réaliser l'analyse SORA (iGRC/GRC, ARC, SAIL) et déterminer les objectifs de sécurité (OSO)."),
    ("autorisation", "Autorisation d'exploitation DGAC",
     "Déposer une demande d'autorisation d'exploitation avec le dossier SORA ; opérer après "
     "délivrance de l'autorisation."),
    ("document", "Manuel d'exploitation (MANEX)",
     "MANEX et démonstration de la robustesse des OSO au niveau exigé par le SAIL."),
    ("enregistrement", "Enregistrement de l'exploitant UAS", "Exploitant enregistré sur AlphaTango."),
    ("competence", "Compétences du télépilote",
     "Compétences adaptées au SAIL et aux OSO (formation, entraînement, maintien de compétences)."),
    ("assurance", "Assurance responsabilité civile", "Attestation RC aéronef à jour."),
]

PROC_TYPE_LABEL = {
    "declaration": "Déclaration", "autorisation": "Autorisation", "competence": "Compétence",
    "document": "Document", "materiel": "Matériel", "condition": "Condition",
    "enregistrement": "Enregistrement", "assurance": "Assurance", "analyse": "Analyse",
}


def procedures(regime: str, sous_categorie: str = "") -> list[tuple[str, str, str]]:
    """Démarches à effectuer pour le régime/scénario retenu : (type, titre, détail)."""
    if regime == "sts":
        return _PROC_STS02 if sous_categorie == "STS-02" else _PROC_STS01
    if regime == "pdra":
        return _PROC_PDRA
    if regime == "sora":
        return _PROC_SORA
    return _PROC_OPEN


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
