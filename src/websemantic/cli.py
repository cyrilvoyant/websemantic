"""PowerShell-friendly terminal proof of concept. No generated code execution."""

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

import yaml

from websemantic.gemini import GeminiError, extract
from websemantic.session import ClarificationNeeded, Session


def show(session):
    if session.pending_clarification:
        print(session.pending_clarification)
        return
    result = session.result()
    print("\nVotre demande -> paramètres -> validation -> calcul TLS -> résultats expliqués")
    decisions = {
        "execute": "Le scénario est complet et validé. Tapez /run pour lancer le calcul local.",
        "clarify": "Le scénario doit encore être précisé ou confirmé avant le calcul.",
        "refuse": "Cette demande ne peut pas être exécutée dans le périmètre déclaré de TLS.",
    }
    print(decisions.get(result.decision, result.decision))
    inputs = session.scenario.inputs
    geometry = []
    for name, label, unit in (
        ("length_m", "longueur", "m"),
        ("n_tubes", "nombre de tubes", ""),
        ("n_lanes_per_tube", "voies par tube", ""),
    ):
        record = inputs.get(name)
        if record:
            geometry.append(f"{label} : {record.value} {unit}".strip())
    if geometry:
        print("Le tunnel décrit a les caractéristiques suivantes : " + "; ".join(geometry) + ".")
    missing = [issue.field for issue in result.issues if issue.code == "missing"]
    if missing:
        print("Il manque encore les paramètres suivants : " + ", ".join(missing) + ".")
    print("Les valeurs du profil de démonstration sont des hypothèses à accepter explicitement.")
    print("Le simulateur produit des données synthétiques ; elles ne constituent pas des mesures terrain.")
    for issue in result.issues:
        if issue.code != "missing":
            print(f"Le paramètre {issue.field} nécessite une correction ou une confirmation ({issue.code}).")


def details(session):
    for group in ("inputs", "experiment"):
        print(f"\n{group}:")
        for name in session.descriptor[group]:
            record = getattr(session.scenario, group).get(name)
            print(
                f"  {name}: {record.value if record else '?'} "
                f"[{record.origin if record else 'missing'}; "
                f"{'accepte' if record and record.accepted else 'extrait/non accepte'}]"
            )
    result = session.result()
    print(f"\nDecision : {result.decision}")
    for issue in result.issues:
        print(f"  {issue.field}: {issue.code}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Websemantic : conversation Gemini et TLS local."
    )
    parser.add_argument("command", choices=["models", "describe", "chat"])
    parser.add_argument("name", nargs="?", default="tls")
    parser.add_argument("--model", default="tls", choices=["tls"])
    parser.add_argument("--llm", default="gemini-3.5-flash-lite")
    parser.add_argument("--max-calls", type=int, default=5)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path(
            os.environ.get("WEBSEMANTIC_WORKSPACE", Path(__file__).resolve().parents[2])
        ),
    )
    parser.add_argument(
        "--once", help="Une seule demande, sans simulation automatique."
    )
    args = parser.parse_args(argv)
    if args.command == "models":
        print(
            "tls : disponible; LQL-Equiv et pvlib : integration future apres gel du coeur."
        )
        return 0
    if args.name != "tls" or args.max_calls < 1 or args.max_calls > 30:
        parser.error("TLS seulement; --max-calls entre 1 et 30.")
    try:
        descriptor = yaml.safe_load(
            (args.workspace / "descriptors/tls/descriptor.yaml").read_text(
                encoding="utf-8"
            )
        )
    except OSError:
        print(
            "Descripteur introuvable : utiliser --workspace avec le dossier semantic-sim-layer."
        )
        return 1
    if args.command == "describe":
        print(yaml.safe_dump(descriptor, allow_unicode=True, sort_keys=False))
        return 0
    session = Session(descriptor)
    print(
        f"Websemantic / TLS / {args.llm}. Maximum {args.max_calls} appels dans cette session."
    )
    print(
        "Une phrase = un appel Gemini. Aucun calcul automatique. /help pour les commandes."
    )
    while True:
        try:
            line = args.once if args.once else input("\nWebSemantic_TLS > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nFin de session.")
            return 0
        try:
            if not line:
                continue
            if line in ("/quit", "/exit"):
                return 0
            if line == "/help":
                print(
                    "/show (explication); /details (paramètres techniques); /profile (propose le profil); /accept (accepte ses valeurs); "
                    "/set inputs.length_m 2000; /set experiment.n_days 365; /run; /quit"
                )
            elif line == "/show":
                show(session)
            elif line == "/details":
                details(session)
            elif line == "/profile":
                session.propose_profile()
                print(
                    "Profil DEMONSTRATION propose, jamais des mesures reelles. Verifiez ci-dessous puis /accept."
                )
                show(session)
            elif line == "/accept":
                session.accept_profile()
                print(
                    "Valeurs du profil propose explicitement acceptees; aucun calcul lance."
                )
                show(session)
            elif line.startswith("/set "):
                _, path, text = line.split(" ", 2)
                session.set_value(path, text)
                show(session)
            elif line == "/run":
                if session.pending_clarification:
                    raise ClarificationNeeded(session.pending_clarification)
                from websemantic.adapters.tls import run

                target, medians = run(session.scenario, descriptor, args.workspace)
                print("\nScénario validé -> simulations Monte Carlo -> médianes -> interprétation")
                print(
                    f"Sur les {session.scenario.experiment['n_days'].value} jours simulés, "
                    f"la médiane de l'énergie totale est de {medians['total_mwh']:.3f} MWh. "
                    f"La médiane de la puissance maximale est de {medians['peak_kw']:.2f} kW."
                )
                print(
                    f"La médiane du facteur de charge est de {medians['load_factor']:.3f}. "
                    "Ce rapport compare la puissance moyenne à la puissance maximale de chaque simulation."
                )
                print(
                    f"L'énergie annualisée médiane est de {medians['annualized_mwh']:.3f} MWh/an. "
                    "Elle résulte d'une extrapolation par 365/n_days ; une période courte "
                    "ne représente pas nécessairement toutes les saisons."
                )
                print(
                    "Ces résultats sont calculés par TLS, sous les hypothèses acceptées. "
                    "Ils ne valident pas la consommation d'un tunnel réel. "
                    "La variabilité simulée ne couvre pas toutes les erreurs du modèle."
                )
                print(f"CSV et provenance : {target}")
                print(
                    "annualized_mwh = extrapolation 365/n_days; pas une mesure terrain."
                )
                (target / "conversation.json").write_text(
                    json.dumps(
                        {
                            "llm": args.llm,
                            "calls": session.calls,
                            "history": session.history,
                            "validation": asdict(session.result()),
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            elif line.startswith("/"):
                print("Commande inconnue. /help")
            else:
                if session.calls >= args.max_calls:
                    print(
                        "Plafond d'appels atteint. Les commandes locales restent disponibles."
                    )
                    if args.once:
                        return 1
                    continue
                session.calls += 1
                print("Gemini interprete la demande...")
                parsed, _usage = extract(line, descriptor, session.history, args.llm)
                session.apply(line, parsed)
                print("Gemini >", parsed.get("message", ""))
                print(
                    f"Appels Gemini utilisés : {session.calls}/{args.max_calls}."
                )
                show(session)
            if args.once:
                return 0
        except ClarificationNeeded as exc:
            print(f"\nWebsemantic > {exc}")
            if args.once:
                return 1
        except (GeminiError, ValueError, KeyError, TypeError, OSError) as exc:
            print(f"Erreur : {exc}")
            if args.once:
                return 1


if __name__ == "__main__":
    raise SystemExit(main())
