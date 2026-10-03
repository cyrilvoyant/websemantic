"""PowerShell-friendly terminal proof of concept. No generated code execution."""

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

import yaml

from websemantic.gemini import GeminiError, extract, load_private_key
from websemantic.semantics import describe
from websemantic.session import ClarificationNeeded, Session


def show(session):
    if session.pending_clarification:
        print(session.pending_clarification)
        return
    result = session.result()
    print("\nDemande -> paramètres -> contrôle -> TLS -> résultats")
    decisions = {
        "execute": "Les paramètres passent les contrôles. /run lance le calcul.",
        "clarify": "Il reste des informations à préciser avant le calcul.",
        "refuse": "TLS ne permet pas de traiter cette demande.",
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
        print("Tunnel : " + "; ".join(geometry) + ".")
    missing = [issue.field for issue in result.issues if issue.code == "missing"]
    if missing:
        names = [describe(field.split('.')[1])[0] for field in missing[:4]]
        print("À préciser : " + ", ".join(names) + (f" et {len(missing)-4} autres champs." if len(missing)>4 else '.'))
        print("Pour un premier essai : « prends les valeurs par défaut », puis /r.")
    unaccepted = [issue for issue in result.issues if issue.code == "unaccepted_assumption"]
    if unaccepted:
        print(
            f"{len(unaccepted)} hypothèses attendent votre accord. "
            "Consultez /details, puis /accept pour accepter le profil proposé."
        )
    for issue in result.issues:
        if issue.code not in ("missing", "unaccepted_assumption"):
            print(f"À vérifier : {issue.field} ({issue.code}).")


def details(session):
    print(f"{'Paramètre':28} | {'Valeur':22} | {'Unité':16} | État")
    print('-' * 90)
    for group in ("inputs", "experiment"):
        for name in session.descriptor[group]:
            record = getattr(session.scenario, group).get(name)
            label, unit, _ = describe(name)
            status = 'manquant' if not record else ('fourni' if record.origin == 'provided' else ('hypothèse validée' if record.accepted else 'à valider'))
            print(f"{label:28} | {record.value if record else '?'!s:22} | {unit:16} | {status}")
    print("\nComprendre une variable : /e altitude_m. Modifier : /set inputs.altitude_m 10 (en m).")
    sources = sorted({record.source for group in ('inputs', 'experiment') for record in getattr(session.scenario, group).values() if record.source})
    for source in sources:
        print('Source des hypothèses :', source)


def explain(session, name):
    name = name.split('.')[-1]
    for group in ('inputs', 'experiment'):
        if name in session.descriptor[group]:
            label, unit, definition = describe(name)
            print(f"{label} — unité : {unit}. {definition}")
            spec = session.descriptor[group][name]
            if 'values' in spec:
                print('Choix possibles : ' + ', '.join(spec['values']))
            print(f"Modifier : /set {group}.{name} VALEUR (valeur dans cette unité ; catégorie entre guillemets).")
            record = getattr(session.scenario, group).get(name)
            if record and record.source:
                print('Source :', record.source)
            return
    print('Variable inconnue. /d affiche le tableau ; exemples : length_m, altitude_m, traffic_level.')


def results_table(session, target, medians):
    import pandas as pd

    means = pd.read_csv(target / 'kpis.csv').mean(numeric_only=True)
    recorded = json.loads((target / 'manifest.json').read_text(encoding='utf-8'))['scenario']['experiment']
    print(f"\nRésultats simulés : {recorded['n_days']['value']} jours, "
          f"{recorded['n_runs']['value']} réalisations.")
    print(f"{'Indicateur':30} | {'Médiane':12} | {'Moyenne':12} | Unité")
    for name, label, unit in (
        ('total_mwh', 'Énergie sur la période', 'MWh'),
        ('annualized_mwh', 'Énergie annualisée', 'MWh/an'),
        ('peak_kw', 'Pic au pas de calcul', 'kW'),
        ('specific_kwh_m_year', 'Énergie par longueur', 'kWh/(m·an)'),
        ('load_factor', 'Facteur de charge', '1 (sans dimension)'),
    ):
        print(f"{label:30} | {medians[name]:12.3f} | {means[name]:12.3f} | {unit}")
    print('Moyenne et médiane entre réalisations. Annualisation par 365/durée ; spécifique tous tubes, par mètre de tunnel.')
    print('Données synthétiques sans calibration terrain. p10–p90 : dispersion horaire, pas intervalle de confiance.')
    print('Résultats et provenance :', target)
    print('Pour une étude plus détaillée, utiliser le simulateur TLS complet : ' +
          os.environ.get('WEBSEMANTIC_TLS_URL', session.descriptor['software']['repository']))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Websemantic : conversation Gemini et TLS local."
    )
    parser.add_argument("command", choices=["models", "describe", "chat"])
    parser.add_argument("name", nargs="?", default="tls")
    parser.add_argument("--model", default="tls", choices=["tls"])
    parser.add_argument("--llm", default="gemini-3.5-flash-lite")
    parser.add_argument("--max-calls", type=int, default=0, help="0 : sans plafond local (quota fournisseur inchangé).")
    parser.add_argument('--output-dir', type=Path, default=os.environ.get('WEBSEMANTIC_OUTPUT_DIR'))
    parser.add_argument('--open-results', action='store_true')
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
    if args.name != "tls" or args.max_calls < 0:
        parser.error("TLS seulement; --max-calls doit être positif ou zéro.")
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
    last_output = None
    print(
        f"WebSemantic_TLS / {args.llm}. " + (f"Maximum {args.max_calls} appels." if args.max_calls else 'Sans plafond local de conversation ; quotas Gemini applicables.')
    )
    print('Outils : /d tableau | /e variable | /p proposer | /v valider | /r calculer | /q quitter')
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
            if line.startswith('\\'):
                line = '/' + line[1:]
            aliases = {'/r': '/run', '/v': '/accept', '/d': '/details', '/p': '/profile', '/a': '/help', '/q': '/quit'}
            if line.startswith('/') and not line.startswith(('/set ', '/e ')):
                line = aliases.get(line.split()[0], line.split()[0])
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
            elif line.startswith('/e '):
                explain(session, line.split(maxsplit=1)[1])
            elif line == "/profile":
                session.propose_profile()
                print(
                    "Profil DEMONSTRATION propose, jamais des mesures reelles. Verifiez ci-dessous puis /accept."
                )
                show(session)
            elif line == "/accept":
                session.accept_profile()
                session.pending_clarification = None
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

                target, medians = run(session.scenario, descriptor, args.workspace, args.output_dir)
                last_output = (target, medians)
                results_table(session, target, medians)
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
                if args.open_results and os.name == 'nt':
                    os.startfile(target)
            elif line.startswith("/"):
                print("Commande inconnue. /help")
            else:
                if last_output and ('moyenne' in line.lower() or 'résultat' in line.lower()) and not any(word in line.lower() for word in ('prend', 'utilise', 'profil', 'mix')):
                    results_table(session, *last_output)
                    print('Ces résultats concernent le dernier calcul enregistré ; /r recalcule le scénario actuel.')
                    if args.once:
                        return 0
                    continue
                local_message = session.local_intent(line)
                if local_message:
                    print('TLS >', local_message)
                    show(session)
                    if args.once:
                        return 0
                    continue
                if args.max_calls and session.calls >= args.max_calls:
                    print(
                        "Plafond d'appels atteint. Les commandes locales restent disponibles."
                    )
                    if args.once:
                        return 1
                    continue
                session.calls += 1
                print("Gemini interprete la demande...")
                load_private_key(args.workspace)
                state = {group: {name: {'value': record.value, 'accepted': record.accepted, 'origin': record.origin} for name, record in getattr(session.scenario, group).items()} for group in ('inputs', 'experiment')}
                parsed, _usage = extract(line, descriptor, session.history, args.llm, state=state)
                session.apply(line, parsed)
                print("Gemini >", parsed.get("message", ""))
                print(
                    f"Appels Gemini : {session.calls}" + (f"/{args.max_calls}." if args.max_calls else '.')
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
        finally:
            if not args.once:
                print("\nOutils : /d tableau et unités | /e variable | /p proposer | /v valider | /r calculer | /set modifier | /q quitter")


if __name__ == "__main__":
    raise SystemExit(main())
