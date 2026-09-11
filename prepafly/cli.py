"""Interface en ligne de commande de PrepaFlyPy.

Permet de piloter le cœur sans interface graphique : lister/analyser des dossiers,
calculer un SORA, générer des PDF, gérer le référentiel. Utile pour l'automatisation
et les tests. Le même cœur est partagé avec l'interface web.

Exemples :
  prepafly gui                      # lance la fenêtre bureau
  prepafly web --port 8010          # lance le serveur web
  prepafly drones                   # liste les 45 modèles DJI
  prepafly dossiers                 # liste les dossiers enregistrés
  prepafly sora --dim 0.67 --vit 23 --densite d500 --arc b
  prepafly report dossier <id> -o dossier.pdf
"""
from __future__ import annotations

import argparse
import sys

from .core import drones, regimes, reports, sora, storage
from .core.version import __version__


def _cmd_drones(_args):
    for cat, items in drones.by_category().items():
        print(f"\n== {cat} ==")
        for d in items:
            print(f"  {d['modele']:<22} {d['dim']:>4} m  {d['vit']:>3} m/s  "
                  f"{d['masse']:>6} g  {d['c'] or '-'}")


def _cmd_dossiers(_args):
    store = storage.load_store()
    if not store["dossiers"]:
        print("Aucun dossier enregistré.")
        return
    for d in store["dossiers"]:
        print(f"{d['id']}  {d['titre'] or '(sans titre)':<30} régime={d.get('regime') or '-'}")


def _cmd_sora(args):
    grc = {"dim": args.dim, "vit": args.vit, "densite": args.densite,
           "mini": args.mini, "m1a": args.m1a, "m1b": args.m1b, "m2": args.m2}
    arc = {"residual": args.arc} if args.arc else {}
    r = sora.compute_sora(grc, arc)
    print(f"iGRC : {r.igrc}")
    print(f"GRC  : {r.grc} (réduction {r.reduction}, plancher {r.floor})")
    print(f"ARC  : {(r.arc_initial or '-').upper()} -> {(r.arc_residual or '-').upper()}")
    print(f"SAIL : {r.sail}")
    if r.oso_req:
        print("OSO exigés :")
        for o in r.oso_req:
            print(f"  OSO {o['id']}  {sora.REQ_TXT.get(o['lvl'], o['lvl']):<12} {o['t']}")


def _cmd_regime(args):
    store = storage.load_store()
    d = next((x for x in store["dossiers"] if x["id"] == args.dossier), None)
    if not d:
        print("Dossier introuvable.")
        return
    rec = regimes.recommend(d)
    print(f"Recommandé : {rec.short} — {rec.label}" + (f" ({rec.sub})" if rec.sub else ""))
    print(rec.why)


def _cmd_report(args):
    store = storage.load_store()
    d = next((x for x in store["dossiers"] if x["id"] == args.dossier), None) if args.dossier else None
    if args.kind == "manex":
        data = reports.manex_pdf(store)
    elif d is None:
        print("Dossier introuvable (id requis pour dossier/rapport).")
        return
    elif args.kind == "dossier":
        data = reports.dossier_pdf(store, d)
    elif args.kind == "rapport":
        data = reports.rapport_pdf(store, d)
    else:
        print("Type inconnu.")
        return
    out = args.out or f"{args.kind}.pdf"
    with open(out, "wb") as f:
        f.write(data)
    print(f"Écrit : {out} ({len(data)} octets)")


def _cmd_gui(_args):
    from . import desktop
    desktop.run()


def _cmd_web(args):
    import uvicorn
    from .server import app
    print(f"PrepaFlyPy {__version__} — http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="prepafly", description="Assistant de préparation de vol drone (PrepaFlyPy).")
    p.add_argument("--version", action="version", version=f"PrepaFlyPy {__version__}")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("gui", help="Fenêtre bureau").set_defaults(func=_cmd_gui)
    w = sub.add_parser("web", help="Serveur web local")
    w.add_argument("--host", default="127.0.0.1")
    w.add_argument("--port", type=int, default=8000)
    w.set_defaults(func=_cmd_web)

    sub.add_parser("drones", help="Lister les modèles DJI").set_defaults(func=_cmd_drones)
    sub.add_parser("dossiers", help="Lister les dossiers").set_defaults(func=_cmd_dossiers)

    s = sub.add_parser("sora", help="Calculer un SORA")
    s.add_argument("--dim", required=True)
    s.add_argument("--vit", required=True)
    s.add_argument("--densite", required=True)
    s.add_argument("--arc", default="")
    s.add_argument("--mini", action="store_true")
    s.add_argument("--m1a", default="none")
    s.add_argument("--m1b", default="none")
    s.add_argument("--m2", default="none")
    s.set_defaults(func=_cmd_sora)

    r = sub.add_parser("regime", help="Recommander un régime pour un dossier")
    r.add_argument("dossier")
    r.set_defaults(func=_cmd_regime)

    rp = sub.add_parser("report", help="Générer un PDF")
    rp.add_argument("kind", choices=["dossier", "rapport", "manex"])
    rp.add_argument("dossier", nargs="?")
    rp.add_argument("-o", "--out")
    rp.set_defaults(func=_cmd_report)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        # Sans sous-commande : lance l'interface bureau.
        _cmd_gui(args)
        return
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
