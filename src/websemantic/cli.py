"""PowerShell-friendly terminal proof of concept. No generated code execution."""

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

import yaml

from websemantic import web_research
from websemantic.gemini import GeminiError, extract, load_private_key
from websemantic.geography import apply_report, location, research, show_report
from websemantic.semantics import describe
from websemantic.session import ClarificationNeeded, Session

ENVIRONMENTS = {
    '1': ('tls', 'websemantic.tls', 'Tunnel Load Simulator : demande électrique des tunnels routiers'),
    '2': ('lql', 'websemantic.lql', 'LQL-Equiv : équivalences radiobiologiques'),
    '3': ('pvlib', 'websemantic.pvlib', 'pvlib : modélisation des systèmes photovoltaïques'),
}


def choose_environment():
    while True:
        print('\nWebSemantic — choisissez votre environnement :')
        for number, (_, namespace, definition) in ENVIRONMENTS.items():
            print(f'{number} — {namespace} — {definition}')
        print('q — quitter')
        try:
            choice = input('Votre choix (1, 2 ou 3) > ').strip().lower()
        except (EOFError, KeyboardInterrupt):
            print('\nFin de session.')
            return None
        if choice in ('q', '/q', 'quit', 'exit'):
            return None
        if choice not in ENVIRONMENTS:
            print('Saisissez 1, 2 ou 3.')
            continue
        model, namespace, _ = ENVIRONMENTS[choice]
        if model != 'tls':
            print(f'{namespace} — Work in progress.')
            continue
        return model


def show(session):
    if session.pending_clarification:
        print(session.pending_clarification)
        return
    result = session.result()
    print("\nDemande -> paramètres -> contrôle -> TLS -> résultats")
    decisions = {
        "execute": "Les paramètres passent les contrôles. " + ('Le calcul demandé peut démarrer.' if session.run_requested else 'Vous pouvez demander le calcul en une phrase.'),
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
        print("Pour un premier essai : « prends les valeurs par défaut ». Le calcul demandé attend les informations suffisantes.")
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


def suggestions(session, has_results=False):
    missing = [issue for issue in session.result().issues if issue.code == 'missing']
    if missing:
        field = missing[0].field.split('.')[-1]
        label, unit, _ = describe(field)
        fourth = (f"Préciser {label.lower()} ({unit}) et comprendre son rôle.", '/e ' + field)
    else:
        fourth = ('Revoir les hypothèses, leurs unités et leurs sources avant de calculer.', '/details')
    fifth = ('Comprendre les hypothèses d’accidents et de pollution.', '/events')
    if session.geographic_context:
        fifth = (f"Vérifier les hypothèses pour {session.geographic_context['city']}, les unités et leurs sources.", '/details')
    if has_results:
        fifth = ('Comprendre la dispersion et les limites des résultats déjà calculés.', '/uncertainty')
    return [
        ('Préciser l’objectif : énergie consommée sur une période (MWh).', "Je souhaite estimer l'énergie électrique totale du tunnel sur la période simulée."),
        ('Préciser l’objectif : puissance maximale appelée (kW).', 'Je souhaite estimer la puissance électrique maximale du tunnel au pas de calcul.'),
        ('Préciser l’objectif : énergie par mètre de tunnel (kWh/(m·an)).', "Je souhaite obtenir l'énergie annualisée par mètre de tunnel, tous tubes compris."),
        fourth, fifth,
    ]


def run_if_ready(session, args, descriptor):
    if not session.run_requested or session.pending_clarification or session.geographic_pending or session.result().decision != 'execute':
        return None
    from websemantic.adapters.tls import run

    print('Les informations sont suffisantes : lancement du calcul demandé.')
    target, medians = run(session.scenario, descriptor, args.workspace, args.output_dir)
    session.run_requested = False
    if getattr(session, 'geographic_context', None):
        (target / 'geographic-context.json').write_text(json.dumps(session.geographic_context, ensure_ascii=False, indent=2), encoding='utf-8')
    if session.web_reports:
        (target / 'web-context.json').write_text(json.dumps(session.web_reports, ensure_ascii=False, indent=2), encoding='utf-8')
    results_table(session, target, medians)
    (target / 'conversation.json').write_text(json.dumps({
        'environment': 'websemantic.tls', 'llm': args.llm, 'calls': session.calls, 'history': session.history,
        'validation': asdict(session.result()),
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    if args.open_results and os.name == 'nt':
        os.startfile(target)
    return target, medians


def answer_from_web(session, question, args):
    if args.max_calls and session.calls >= args.max_calls:
        raise GeminiError('Plafond local atteint ; la recherche documentaire nécessite un appel Gemini.')
    load_private_key(args.workspace)
    session.calls += 1
    state = {name: {'value': record.value, 'unit': record.unit} for name, record in session.scenario.inputs.items()}
    report = web_research.research(question, args.llm, state)
    session.web_reports.append(report)
    session.history.append({'user': question, 'assistant': report['answer'], 'web_context': report})
    output_root = Path(getattr(args, 'output_dir', None) or args.workspace / 'runs')
    output_root.mkdir(parents=True, exist_ok=True)
    with (output_root / 'documentation.jsonl').open('a', encoding='utf-8') as journal:
        journal.write(json.dumps(report, ensure_ascii=False) + '\n')
    web_research.show_report(report)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Websemantic : conversation Gemini et TLS local."
    )
    parser.add_argument("command", choices=["models", "describe", "chat"])
    parser.add_argument("name", nargs="?", default="tls")
    parser.add_argument("--model", choices=["tls", "lql", "pvlib"], help="Environnement pour un démarrage direct ou une demande non interactive.")
    parser.add_argument('--direct', action='store_true', help='Démarrage sans menu pour les scripts.')
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
        "--once", help="Une seule demande sans menu interactif ; le calcul explicitement demandé reste soumis aux contrôles."
    )
    args = parser.parse_args(argv)
    if args.command == "models":
        for model, namespace, definition in ENVIRONMENTS.values():
            print(f"{namespace} — {definition} — " + ('disponible' if model == 'tls' else 'Work in progress'))
        return 0
    if args.name != "tls" or args.max_calls < 0:
        parser.error("TLS seulement; --max-calls doit être positif ou zéro.")
    if args.model in ('lql', 'pvlib'):
        print(f'websemantic.{args.model} — Work in progress.')
        if args.once or args.direct or args.command != 'chat':
            return 2
        args.model = None
    if args.command == 'chat' and not args.once and not args.direct:
        args.model = choose_environment()
        if args.model is None:
            return 0
    args.model = args.model or 'tls'
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
    choices = []
    print(
        f"websemantic.tls / {args.llm}. " + (f"Maximum {args.max_calls} appels." if args.max_calls else 'Sans plafond local de conversation ; quotas Gemini applicables.')
    )
    print('Outils : /s 5 suggestions | /d tableau | /e variable | /web question | /p proposer | /v valider | /r calculer | /q quitter')
    print(
        "Un calcul demandé démarre dès que les informations et validations sont suffisantes. /s pour vous guider."
    )
    while True:
        try:
            may_run = False
            line = args.once if args.once else input("\nwebsemantic.tls > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nFin de session.")
            return 0
        try:
            if not line:
                continue
            if choices and line in ('1', '2', '3', '4', '5'):
                line = choices[int(line)-1][1]
                choices = []
                print('Choix >', line)
            elif line not in ('/s', '\\s'):
                choices = []
            if line.startswith('\\'):
                line = '/' + line[1:]
            aliases = {'/r': '/run', '/v': '/accept', '/d': '/details', '/p': '/profile', '/a': '/help', '/q': '/quit', '/s': '/suggest'}
            if line.startswith('/') and not line.startswith(('/set ', '/e ', '/web ')):
                line = aliases.get(line.split()[0], line.split()[0])
            if line in ("/quit", "/exit"):
                return 0
            if line == '/suggest':
                choices = suggestions(session, last_output is not None)
                print('Pour préciser votre objectif ou le scénario :')
                for number, (label, _) in enumerate(choices, 1):
                    print(f'{number}. {label}')
                print('Saisissez 1 à 5, ou écrivez votre question. Les choix 1–3 demandent un calcul, soumis aux contrôles et à la validation des hypothèses.')
            elif line == '/events':
                explain(session, 'accident_probability_per_day')
                explain(session, 'pollution_probability_per_day')
            elif line == '/uncertainty':
                print('p10–p90 décrit la dispersion entre trajectoires simulées, pas un intervalle de confiance. '
                      'Le modèle couvre bruit, trafic et événements ; erreurs de paramètres, de structure et de calibration ne sont pas couvertes. '
                      'L’annualisation extrapole la période. /d permet de revoir les hypothèses.')
            elif line == "/help":
                print(
                    "/s (5 suggestions); /show (explication); /details (paramètres techniques); /profile (propose le profil); /accept (accepte ses valeurs); "
                    "/web question (recherche documentaire); /set inputs.length_m 2000; /set experiment.n_days 365; /run; /quit"
                )
            elif line == "/show":
                show(session)
            elif line == "/details":
                details(session)
            elif line.startswith('/e '):
                explain(session, line.split(maxsplit=1)[1])
            elif line.startswith('/web '):
                answer_from_web(session, line.split(maxsplit=1)[1], args)
            elif line == '/web':
                print('Exemple : /web CETU rôle de la ventilation et de l’éclairage dans la consommation électrique d’un tunnel')
            elif line == "/profile":
                session.propose_profile()
                may_run = True
                print(
                    "Profil DEMONSTRATION propose, jamais des mesures reelles. Verifiez ci-dessous puis /accept."
                )
                show(session)
            elif line == "/accept":
                if session.geographic_pending:
                    print('Le contexte géographique n’a pas abouti. Reformulez la demande avec la ville pour réessayer ; /v ne remplace pas la consultation des sources.')
                    if args.once:
                        return 1
                    continue
                session.accept_profile()
                session.pending_clarification = None
                print(
                    "Hypothèses proposées acceptées."
                )
                show(session)
                may_run = True
            elif line.startswith("/set "):
                _, path, text = line.split(" ", 2)
                session.set_value(path, text)
                show(session)
                may_run = True
            elif line == "/run":
                session.run_requested = True
                may_run = True
                show(session)
            elif line.startswith("/"):
                print("Commande inconnue. /help")
            else:
                if web_research.explicitly_requested(line):
                    answer_from_web(session, line, args)
                    if args.once:
                        return 0
                    continue
                previous_run_requested = session.run_requested
                session.request_calculation(line)
                if line.lower().strip() in ('annule le calcul', 'ne calcule pas', 'stop le calcul'):
                    print('Demande de calcul en attente annulée. Le scénario est conservé.')
                    if args.once:
                        return 0
                    continue
                if line.lower().strip() in ('calcule', 'calcule maintenant', 'lance le calcul', 'simule', 'fais le calcul', 'recalcule'):
                    show(session)
                    output = run_if_ready(session, args, descriptor)
                    if output:
                        last_output = output
                    if args.once:
                        return 0
                    continue
                if last_output and not session.run_requested and ('moyenne' in line.lower() or 'résultat' in line.lower()) and not any(word in line.lower() for word in ('prend', 'utilise', 'profil', 'mix')):
                    results_table(session, *last_output)
                    print('Ces résultats concernent le dernier calcul enregistré ; /r recalcule le scénario actuel.')
                    if args.once:
                        return 0
                    continue
                place = location(line)
                if place:
                    session.geographic_pending = True
                    session.pending_clarification = 'Le contexte géographique demandé doit être consulté et validé avant le calcul.'
                    if args.max_calls and session.calls + 2 > args.max_calls:
                        raise GeminiError('Ce contexte nécessite deux appels Gemini ; plafond local insuffisant.')
                    load_private_key(args.workspace)
                    session.calls += 1
                    parsed, _usage = extract(line, descriptor, session.history, args.llm)
                    session.apply(line, parsed)
                    session.pending_clarification = 'Analyse géographique en attente ; aucun calcul.'
                    session.calls += 1
                    report = research(place, args.llm)
                    apply_report(session, line, report)
                    show_report(session)
                    show(session)
                    if args.once:
                        return 0
                    continue
                local_message = session.local_intent(line)
                if local_message:
                    print('TLS >', local_message)
                    show(session)
                    output = run_if_ready(session, args, descriptor)
                    if output:
                        last_output = output
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
                if parsed.get('needs_web') is True:
                    session.run_requested = previous_run_requested
                    answer_from_web(session, line, args)
                    if args.once:
                        return 0
                    continue
                session.apply(line, parsed)
                print("Gemini >", parsed.get("message", ""))
                print(
                    f"Appels Gemini : {session.calls}" + (f"/{args.max_calls}." if args.max_calls else '.')
                )
                show(session)
                may_run = True
            if may_run:
                output = run_if_ready(session, args, descriptor)
                if output:
                    last_output = output
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
                print("\nOutils : /s suggestions | /d tableau et unités | /e variable | /web question | /p proposer | /v valider | /r calculer | /set modifier | /q quitter")


if __name__ == "__main__":
    raise SystemExit(main())
