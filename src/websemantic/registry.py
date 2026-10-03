"""Local, reviewed model catalogue and adapter dispatch. No LLM-selected imports."""

import importlib
import json
from pathlib import Path

import yaml


def environments():
    return json.loads(Path(__file__).with_name('environments.json').read_text(encoding='utf-8'))


def load_descriptor(workspace, model):
    item = next((item for item in environments() if item['id'] == model), None)
    if item is None:
        raise ValueError('Environnement non déclaré.')
    descriptor = yaml.safe_load((Path(workspace) / 'descriptors' / item['descriptor'] / 'descriptor.yaml').read_text(encoding='utf-8'))
    if not isinstance(descriptor, dict):
        raise TypeError('Descripteur non conforme.')
    return descriptor


def load_hook(reference):
    if not isinstance(reference, str) or reference.count(':') != 1:
        raise ValueError('Point d’entrée local absent ou invalide.')
    module, name = reference.split(':')
    if not module.startswith('websemantic.adapters.') or not name.isidentifier():
        raise ValueError('Seuls les adaptateurs locaux relus sont autorisés.')
    try:
        function = getattr(importlib.import_module(module), name)
    except (ImportError, AttributeError):
        raise ValueError('Adaptateur local absent ou incomplet.') from None
    if not callable(function):
        raise TypeError('Point d’entrée non exécutable.')
    return function


def execute(scenario, descriptor, workspace, output_root=None):
    from websemantic.core.validation import validate

    if validate(scenario, descriptor).decision != 'execute':
        raise ValueError('Configuration non validée ; aucun adaptateur lancé.')
    adapter = load_hook(descriptor.get('runtime', {}).get('adapter'))
    return adapter(scenario, descriptor, workspace, output_root)
