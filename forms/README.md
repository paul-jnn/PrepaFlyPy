# Gabarits de formulaires officiels

Déposez ici les PDF officiels à champs pour un remplissage automatique :

- `cerfa_15476-04.pdf` — déclaration préalable (Cerfa 15476*04)
- `form_r5-uas-derog_v4.pdf` — demande de dérogation R5-UAS-DEROG

Ces fichiers ne sont pas versionnés par défaut (formulaires officiels susceptibles
d'évoluer). Sans eux, PrepaFlyPy génère un **brouillon lisible** reprenant les
valeurs à reporter — l'application n'est jamais bloquée.

Quand les gabarits sont présents, complétez `FIELD_MAPS` dans
`prepafly/core/forms.py` avec les vrais noms de champs (relevables ainsi) :

```python
from pypdf import PdfReader
r = PdfReader("forms/cerfa_15476-04.pdf")
print(r.get_fields().keys())
```

L'AOT (occupation du domaine public) est toujours générée comme lettre : le
Cerfa 14023 voirie n'est pas un PDF interactif.
