"""PowerShell-friendly terminal proof of concept. No generated code execution."""

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

import yaml

from websemantic import web_research
from websemantic.conversation import explicit_consent, requested_actions
from websemantic.gemini import GeminiError, extract, load_private_key
from websemantic.geography import apply_report, location, research, show_report
from websemantic.registry import environments, execute, load_descriptor
from websemantic.semantics import describe
from websemantic.session import ClarificationNeeded, Session

ENVIRONMENTS = {str(i): (item['id'], item['namespace'], item['definition'])
                for i, item in enumerate(environments(), 1)}
AVAILABLE = {item['id'] for item in environments() if item['available']}
DEFAULT_MODEL = next(item['id'] for item in environments() if item['available'])


def choose_environment():
    while True:
        print('\nWebSemantic — choisissez votre environnement :')
        for number, (_, namespace, definition) in ENVIRONMENTS.items():
            print(f'{number} — {namespace} — {definition}')
        print('q — quitter')
        try:
            choice = input('Votre choix (' + ', '.join(ENVIRONMENTS) + ') > ').strip().lower()
        except (EOFError, KeyboardInterrupt):
            print('\nFin de session.')
            return None
        if choice in ('q', '/q', 'quit', 'exit'):
            return None
        if choice not in ENVIRONMENTS:
            print('Saisissez ' + ', '.join(ENVIRONMENTS) + '.')
            continue
        model, namespace, _ = ENVIRONMENTS[choice]
        if model not in AVAILABLE:
            print(f'{namespace} — Work in progress.')
            continue
        return model


def presentation(session):
    return session.descriptor.get('presentation', {})


def show(session):
    if session.scenarios:
        questions = []
        seen = set()
        for label, child in session.scenarios.items():
            for question in child.questions:
                key = question['question']
                if question['blocking'] and key not in seen:
                    questions.append((label, question))
                    seen.add(key)
        if questions:
            for label, question in questions[:2]:
                print(f'{label} : {question["question"]}')
            return
        for label, child in session.scenarios.items():
            print(label + ' :')
            show(child)
        for issue in session.result().issues:
            if issue.code == 'comparison_control':
                print('À harmoniser :', describe(issue.field.split('.')[-1], session.descriptor)[0], '— même valeur pour les deux scénarios.')
        return
    if session.pending_clarification:
        print(session.pending_clarification)
        return
    result = session.result()
    if result.decision == 'refuse':
        print('Le logiciel ne permet pas de traiter cette demande.')
    missing = [issue.field for issue in result.issues if issue.code == 'missing']
    if missing:
        names = [describe(field.split('.')[1], session.descriptor)[0] for field in missing[:4]]
        print('À préciser : ' + ', '.join(names) + (f' et {len(missing)-4} autres champs.' if len(missing)>4 else '.'))
        if any('default' in spec for group in ('inputs', 'experiment') for spec in session.descriptor.get(group, {}).values()):
            print('Pour un premier essai : « prends les valeurs par défaut ». Le calcul demandé attend les informations suffisantes.')
    unaccepted = [issue for issue in result.issues if issue.code == 'unaccepted_assumption']
    if unaccepted:
        print(f'{len(unaccepted)} hypothèses attendent votre accord. Demandez le tableau pour les examiner, puis dites « J’accepte les hypothèses proposées » si vous souhaitez les utiliser.')
    for issue in result.issues:
        if issue.code not in ('missing', 'unaccepted_assumption'):
            print(f'À vérifier : {issue.field} ({issue.code}).')


def details(session, full=False):
    if session.scenarios:
        for label, child in session.scenarios.items():
            print('\n' + label)
            details(child, full=full)
        return
    print(f"{'Paramètre':28} | {'Défaut':16} | {'Retenue':16} | {'Unité':16} | Origine / état")
    print('-' * 110)
    for group in ('inputs', 'experiment'):
        for name, spec in session.descriptor.get(group, {}).items():
            primary = presentation(session).get('primary_fields')
            if not full and (spec.get('display_hidden') or (primary and f'{group}.{name}' not in primary)):
                continue
            record = getattr(session.scenario, group).get(name)
            label, unit, _ = describe(name, session.descriptor)
            status = 'manquant' if not record else ('fourni' if record.origin == 'provided' else ('hypothèse validée' if record.accepted else 'à valider'))
            print(f"{label:28} | {spec.get('default', '—')!s:16} | {record.value if record else 'à préciser'!s:16} | {unit:16} | {status}")
    print('Pour aller plus loin, demandez le détail complet, une définition ou une modification en une phrase.')
    for source in sorted({record.source for group in ('inputs', 'experiment') for name, record in getattr(session.scenario, group).items() if record.source and (full or not session.descriptor[group][name].get('operational_default'))}):
        print('Source des hypothèses :', source)


def formulas(session):
    if session.scenarios:
        for label, child in session.scenarios.items():
            print('\n' + label)
            formulas(child)
        return
    entries = session.descriptor.get('model_equations', [])
    if not entries:
        print('Les formules de cet environnement ne sont pas encore documentées.')
        return
    for entry in entries:
        print(f"{entry['label']} [{entry['unit']}] : {entry['expression']}")
        print(entry['meaning'])
    for table in session.descriptor.get('coefficient_display', []):
        group, name = table['field'].split('.')
        record = getattr(session.scenario, group).get(name)
        if record and record.value in table['values']:
            print(table['template'].format(choice=record.value, **table['values'][record.value]))
    print(presentation(session).get('formula_note', 'Les formules et leurs limites sont documentées dans le référentiel du modèle.'))


def ask_questions(session, questions=None):
    for question in session.questions if questions is None else questions:
        if not question['blocking']:
            print('Pour préciser :', question['question'])


def explain(session, name):
    name = name.split('.')[-1]
    from websemantic.units import fold

    matches = [field for group in ('inputs', 'experiment')
               for field, spec in session.descriptor.get(group, {}).items()
               if fold(name) in {fold(field), fold(spec.get('label', field)),
                                 *(fold(alias) for alias in spec.get('aliases', []))}]
    if len(matches) == 1:
        name = matches[0]
    for group in ('inputs', 'experiment'):
        if name in session.descriptor.get(group, {}):
            label, unit, definition = describe(name, session.descriptor)
            print(f'{label} — unité : {unit}. {definition}')
            spec = session.descriptor[group][name]
            if 'values' in spec:
                print('Choix possibles : ' + ', '.join(spec['values']))
            print(f'Pour le modifier, indiquez le nouveau choix en précisant {label.lower()} et son unité.')
            record = getattr(session.scenario, group).get(name)
            if record and record.source:
                print('Source :', record.source)
            return
    print('Paramètre non reconnu. Demandez le tableau des paramètres pour retrouver son nom.')


def results_table(session, target, medians):
    if medians.get('comparison') is True:
        print('\nComparaison des médianes des réalisations :')
        print(f"{'Indicateur':24} | {'Scénario 1':16} | {'Scénario 2':16} | {'Écart 1−2':16} | Unité")
        manifest = json.loads((target / 'manifest.json').read_text(encoding='utf-8'))
        for indicator, values in medians['differences'].items():
            spec = session.descriptor['comparison']['indicator_labels'][indicator]
            print(f"{spec['label']:24} | {values['scenario_1']:16.3f} | {values['scenario_2']:16.3f} | {values['difference_1_minus_2']:16.3f} | {spec['unit']}")
        primary = medians['differences'][session.descriptor['comparison']['primary_indicator']]
        difference = primary['difference_1_minus_2']
        if difference == 0:
            print('Les deux scénarios ont la même consommation médiane sur la période simulée.')
        else:
            direction = 'plus' if difference > 0 else 'moins'
            relative = primary['relative_percent_vs_2']
            suffix = f'{abs(relative):.1f} % de {direction}' if relative is not None else f'{direction} (référence nulle : pourcentage indéfini)'
            print(f'Dans cette simulation, le scénario 1 consomme {suffix} que le scénario 2.')
        print('La comparaison dépend de tous les paramètres retenus ; elle ne démontre pas l’effet isolé d’un seul équipement. Données synthétiques ; annualisation par extrapolation. Mêmes graines, sans garantie de tirages identiques après changement de configuration.')
        print('Dossier des résultats :', target)
        for path in manifest['controlled_fields']:
            group, name = path.split('.')
            record = manifest['scenarios']['scenario_1'][group][name]
            if not session.descriptor[group][name].get('display_hidden'):
                label, unit, _ = describe(name, session.descriptor)
                print(f'Commun aux deux scénarios : {label} = {record["value"]} {unit}.')
        return
    config = presentation(session).get('results', {})
    manifest = json.loads((target / 'manifest.json').read_text(encoding='utf-8'))
    scenario = manifest['scenario']
    context_path = target / 'geographic-context.json'
    context = json.loads(context_path.read_text(encoding='utf-8')) if context_path.is_file() else {}
    headline = config.get('headline')
    if headline:
        location_text = headline.get('location_template', ' à {city}').format(city=context['city']) if context.get('city') else ''
        print('\n' + headline['template'].format(value=medians[headline['indicator']], location=location_text))
    recap = []
    for group, names in (('inputs', config.get('recap_fields', [])), ('experiment', config.get('context_fields', []))):
        for name in names:
            if name in scenario[group]:
                label, unit, _ = describe(name, session.descriptor)
                record = scenario[group][name]
                value = record['value']
                if type(value) in (int, float):
                    value = f'{value:g}'
                recap.append(f'{label.lower()} {value}' + ('' if unit in ('nombre', 'catégorie', 'identifiant') else ' ' + unit))
    if recap:
        print('Hypothèses retenues : ' + '; '.join(recap) + '.')
    if config.get('table'):
        import pandas as pd

        means = pd.read_csv(target / config['table']).mean(numeric_only=True)
        print(f"{'Indicateur':30} | {'Médiane':12} | {'Moyenne':12} | Unité")
        selected = config.get('display_indicators')
        for name, label, unit in config.get('indicators', []):
            if selected is None or name in selected:
                print(f'{label:30} | {medians[name]:12.3f} | {means[name]:12.3f} | {unit}')
    for note in config.get('notes', []):
        print(note)
    print('Dossier des résultats :', target)


def suggestions(session, has_results=False):
    ui = presentation(session)
    missing = [issue for issue in session.result().issues if issue.code == 'missing']
    if missing:
        field = missing[0].field.split('.')[-1]
        label, unit, _ = describe(field, session.descriptor)
        fourth = (f'Préciser {label.lower()} ({unit}) et comprendre son rôle.', '/e ' + field)
    else:
        fourth = ('Revoir les hypothèses, leurs unités et leurs sources avant de calculer.', '/details')
    fifth = tuple(ui.get('event_suggestion', ['Comprendre les limites du modèle.', '/uncertainty']))
    if session.geographic_context:
        fifth = (f"Vérifier les hypothèses pour {session.geographic_context['city']}, les unités et leurs sources.", '/details')
    if has_results:
        fifth = ('Comprendre la dispersion et les limites des résultats déjà calculés.', '/uncertainty')
    initial = [tuple(item) for item in ui.get('suggestions', [])[:3]]
    fallback = [('Comprendre le périmètre du logiciel.', '/show'), ('Examiner les paramètres déclarés.', '/details'), ('Comprendre les hypothèses du profil.', '/profile')]
    initial += fallback[len(initial):]
    return initial + [fourth, fifth]


def run_if_ready(session, args, descriptor):
    if not session.run_requested or session.pending_clarification or session.geographic_pending or any(item['blocking'] for item in session.questions) or session.result().decision != 'execute':
        return None

    print('Calcul en cours…')
    if session.scenarios:
        from websemantic.comparison import run

        target, medians = run(session.scenarios, descriptor, args.workspace, args.output_dir)
        for child in session.scenarios.values():
            child.run_requested = False
    else:
        target, medians = execute(session.scenario, descriptor, args.workspace, args.output_dir)
    session.run_requested = False
    if getattr(session, 'geographic_context', None):
        (target / 'geographic-context.json').write_text(json.dumps(session.geographic_context, ensure_ascii=False, indent=2), encoding='utf-8')
    if session.web_reports:
        (target / 'web-context.json').write_text(json.dumps(session.web_reports, ensure_ascii=False, indent=2), encoding='utf-8')
    results_table(session, target, medians)
    (target / 'conversation.json').write_text(json.dumps({
        'environment': presentation(session).get('namespace', args.model), 'llm': args.llm, 'calls': session.calls, 'history': session.history,
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
    state = session.state()
    report = web_research.research(question, args.llm, state, descriptor=session.descriptor)
    session.add_questions(report.get('questions', []))
    session.web_reports.append(report)
    session.history.append({'user': question, 'assistant': report['answer'], 'web_context': report})
    output_root = Path(getattr(args, 'output_dir', None) or args.workspace / 'runs')
    output_root.mkdir(parents=True, exist_ok=True)
    with (output_root / 'documentation.jsonl').open('a', encoding='utf-8') as journal:
        journal.write(json.dumps(report, ensure_ascii=False) + '\n')
    web_research.show_report(report, presentation(session).get("short_name", "WebSemantic"))
    for item in report.get('questions', []):
        print('Pour préciser :', item['question'])


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Websemantic : conversation et simulation scientifique locale."
    )
    parser.add_argument("command", choices=["models", "describe", "chat"])
    parser.add_argument("name", nargs="?", default=DEFAULT_MODEL)
    parser.add_argument("--model", choices=[item[0] for item in ENVIRONMENTS.values()], help="Environnement pour un démarrage direct ou une demande non interactive.")
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
            print(f"{namespace} — {definition} — " + ('disponible' if model in AVAILABLE else 'Work in progress'))
        return 0
    if args.max_calls < 0:
        parser.error("--max-calls doit être positif ou zéro.")
    if args.name != DEFAULT_MODEL and args.model is None:
        args.model = args.name
    if args.model is not None and args.model not in AVAILABLE:
        print(f'websemantic.{args.model} — Work in progress.')
        if args.once or args.direct or args.command != 'chat':
            return 2
        args.model = None
    if args.command == 'chat' and not args.once and not args.direct:
        args.model = choose_environment()
        if args.model is None:
            return 0
    args.model = args.model or DEFAULT_MODEL
    try:
        descriptor = load_descriptor(args.workspace, args.model)
    except (OSError, ValueError, TypeError):
        print(
            "Descripteur introuvable : utiliser --workspace avec le dossier semantic-sim-layer."
        )
        return 1
    if args.command == "describe":
        print(yaml.safe_dump(descriptor, allow_unicode=True, sort_keys=False))
        return 0
    session = Session(descriptor)
    namespace = presentation(session).get("namespace", "websemantic." + args.model)
    last_output = None
    choices = []
    print(f"WebSemantic — {presentation(session).get('short_name', args.model)}")
    print('Écrivez votre demande : je peux proposer des hypothèses, expliquer les paramètres ou lancer le calcul après validation.')
    print(
        "La validation ou une modification déclenche le calcul dès que le scénario est complet."
    )
    while True:
        try:
            may_run = False
            line = args.once if args.once else input("\n" + namespace + " > ").strip()
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
                print('Saisissez 1 à 5, ou écrivez votre question.')
            elif line == '/events':
                for field in presentation(session).get('events', []):
                    explain(session, field)
            elif line == '/uncertainty':
                print(presentation(session).get('uncertainty_text', 'Consultez les limites et incertitudes déclarées du modèle.'))
            elif line == "/help":
                print(
                    "/s suggestions | /show résumé | /d tableau | /details-all tous les paramètres | "
                    "/e NOM définition | /formulas formules | /p proposer | /v accepter | "
                    "/web QUESTION sources | /set GROUPE.NOM VALEUR modifier | /r calculer | /q quitter"
                )
            elif line == "/show":
                show(session)
            elif line == "/details":
                details(session)
            elif line == '/details-all':
                details(session, full=True)
            elif line == '/formulas':
                formulas(session)
            elif line.startswith('/e '):
                explain(session, line.split(maxsplit=1)[1])
            elif line.startswith('/web '):
                answer_from_web(session, line.split(maxsplit=1)[1], args)
            elif line == '/web':
                print('Exemple : /web ' + presentation(session).get('web_example', 'sources scientifiques du modèle'))
            elif line == "/profile":
                session.propose_profile()
                session.history.append({'user': '/profile', 'assistant': 'Profil de démonstration proposé, à valider.'})
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
                if session.pending_clarification:
                    print(session.pending_clarification)
                    if args.once:
                        return 1
                    continue
                session.accept_profile()
                session.run_requested = True
                session.history.append({'user': '/accept', 'assistant': 'Hypothèses acceptées ; calcul automatique soumis aux contrôles.'})
                print(
                    "Hypothèses proposées acceptées."
                )
                show(session)
                may_run = True
            elif line.startswith("/set "):
                _, path, text = line.split(" ", 2)
                session.set_value(path, text)
                session.history.append({'user': line, 'assistant': 'Paramètre modifié ; calcul automatique soumis aux contrôles.'})
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
                place = location(line, descriptor)
                if place and session.geographic_context and session.geographic_context.get('city') == descriptor['geography']['places'][place]['city'] and not any(word in line.lower() for word in ('recherche', 'internet', 'sources', 'actualise', 'documente')):
                    place = None
                if place:
                    session.geographic_pending = True
                    session.pending_clarification = 'Le contexte géographique demandé doit être consulté et validé avant le calcul.'
                    if args.max_calls and session.calls + 2 > args.max_calls:
                        raise GeminiError('Ce contexte nécessite deux appels Gemini ; plafond local insuffisant.')
                    load_private_key(args.workspace)
                    session.calls += 1
                    parsed, _usage = extract(line, descriptor, session.history, args.llm, state=session.state())
                    session.apply(line, parsed)
                    session.pending_clarification = 'Analyse géographique en attente ; aucun calcul.'
                    session.calls += 1
                    report = research(place, args.llm, descriptor)
                    apply_report(session, line, report)
                    show_report(session)
                    show(session)
                    if args.once:
                        return 0
                    continue
                local_message = session.local_intent(line)
                if local_message:
                    print(presentation(session).get('short_name', 'WebSemantic') + ' >', local_message)
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
                load_private_key(args.workspace)
                state = session.state()
                parsed, _usage = extract(line, descriptor, session.history, args.llm, state=state)
                if parsed.get('needs_web') is True:
                    if session.run_requested and not previous_run_requested:
                        session.pending_clarification = 'Cette demande de calcul nécessite des informations externes. Précisez et validez les paramètres concernés ; /v seul ne résout pas cette demande.'
                    session.run_requested = previous_run_requested
                    answer_from_web(session, line, args)
                    if args.once:
                        return 0
                    continue
                actions = requested_actions(parsed)
                unresolved = session.pending_clarification
                session.apply(line, parsed)
                if unresolved and not session.scenarios and not parsed['updates'] and actions:
                    session.pending_clarification = unresolved
                if 'quit' in actions:
                    return 0
                if 'propose' in actions:
                    session.propose_profile()
                if 'accept' in actions:
                    if session.geographic_pending or session.pending_clarification:
                        raise ClarificationNeeded(session.pending_clarification or 'Le contexte documentaire doit être résolu avant validation.')
                    if not explicit_consent(line, parsed.get('acceptance_evidence')):
                        session.run_requested = False
                        raise ClarificationNeeded('Les hypothèses restent non acceptées. Confirmez explicitement votre accord si vous souhaitez les utiliser.')
                    session.accept_profile()
                    session.run_requested = True
                    session.history.append({'user': line, 'assistant': 'Hypothèses explicitement acceptées après extraction des valeurs fournies.'})
                if 'details' in actions:
                    details(session, full=parsed.get('detail_level') == 'full')
                if 'explain' in actions:
                    explain(session, parsed.get('parameter', ''))
                if 'suggest' in actions:
                    for number, (label, _) in enumerate(suggestions(session, last_output is not None), 1):
                        print(f'{number}. {label}')
                if 'formulas' in actions:
                    formulas(session)
                if not (session.run_requested and session.result().decision == 'execute'):
                    print("WebSemantic >", parsed.get("message", ""))
                if parsed["updates"] or session.run_requested or actions & {"propose", "accept"}:
                    show(session)
                elif session.pending_clarification:
                    print(session.pending_clarification)
                ask_questions(session, parsed.get('questions', []))
                for chunk in parsed.get('scenario_updates', []):
                    child = session.scenarios.get(chunk['scenario'])
                    if child and any(not item['blocking'] for item in chunk.get('questions', [])):
                        print(chunk['scenario'] + ' :')
                        ask_questions(child, chunk.get('questions', []))
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


if __name__ == "__main__":
    raise SystemExit(main())
