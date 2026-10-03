"""Prepare a small Lambda package on Windows; excludes local environments/secrets."""
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
output = root / 'tmp' / 'upload-deployment'
output.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(output / 'lambda.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for folder, pattern in ((root / 'backend', '*.py'), (root / 'data' / 'ground_truth', '*.json')):
        for source in folder.rglob(pattern):
            archive.write(source, source.relative_to(root).as_posix())
template = (root / 'infra' / 'template.yaml').read_text(encoding='utf-8')
template = template.replace('CodeUri: ../', 'CodeUri: ./lambda.zip')
(output / 'template.yaml').write_text(template, encoding='utf-8')
print('Prepared tmp/upload-deployment/lambda.zip and template.yaml')
