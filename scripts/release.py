"""Idempotently publish the manifest version at exactly the tested commit."""
import json
import os
from pathlib import Path
import re
import subprocess

version = json.loads(Path('custom_components/smartify_energy/manifest.json').read_text())['version']
assert re.fullmatch(r'\d+\.\d+\.\d+', version), version
ref = os.environ.get('GITHUB_REF', '')
if ref.startswith('refs/tags/'):
    assert ref.split('/')[-1].removeprefix('v') == version, 'Tag and manifest version differ'
sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
changelog = Path('CHANGELOG.md').read_text()
match = re.search(rf'^## {re.escape(version)}\b.*?(?=^## |\Z)', changelog, re.M | re.S)
assert match, 'Missing changelog section'
notes = Path(os.environ.get('RUNNER_TEMP', '/tmp')) / 'sep-release-notes.md'
notes.write_text(match.group())
tag = ref.split('/')[-1] if ref.startswith('refs/tags/') else version
existing = subprocess.run(['gh','release','view',tag,'--json','tagName'], capture_output=True, text=True)
if existing.returncode == 0:
    print(f'Release {tag} already exists; leaving it unchanged')
else:
    tags = subprocess.check_output(['git','tag','--list', tag], text=True).strip()
    if tags:
        assert subprocess.check_output(['git','rev-list','-n','1',tag],text=True).strip() == sha, 'Existing tag points to another commit'
    subprocess.run(['gh','release','create',tag,'--target',sha,'--title',f'Smartify Energy Pro {version}',
                    '--notes-file',str(notes),'--latest'],check=True)
