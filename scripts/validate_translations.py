"""Require identical translation keys and string leaves in every language."""
import json
from pathlib import Path
ROOT = Path('custom_components/smartify_energy')
def leaves(value, prefix=''):
    result = {}
    for key, item in value.items():
        path = f'{prefix}/{key}'
        if isinstance(item, dict):
            result.update(leaves(item, path))
        else:
            assert isinstance(item, str), (path, type(item))
            result[path] = item
    return result
base = leaves(json.loads((ROOT / 'strings.json').read_text()))
for path in (ROOT / 'translations').glob('*.json'):
    data = leaves(json.loads(path.read_text()))
    assert data.keys() == base.keys(), (path, base.keys()-data.keys(), data.keys()-base.keys())
print('Translation keys and value types match')
