#!/usr/bin/env python3
"""Create a hosting release and a separate editable-source archive."""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parent

def pack(target, files):
    with ZipFile(target, 'w', ZIP_DEFLATED, compresslevel=9) as archive:
        # Cloud workspaces may use umask 077. Hosting files must stay readable
        # after extraction, regardless of the builder's local permissions.
        folders = sorted({parent.as_posix()+'/' for path,name in files for parent in Path(name).parents if parent.as_posix() != '.'})
        for name in folders:
            info = ZipInfo(name)
            info.create_system = 3
            info.external_attr = (0o40755 << 16) | 0x10
            archive.writestr(info, b'')
        for path, name in files:
            info = ZipInfo.from_file(path, name)
            info.external_attr = 0o100644 << 16
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    with ZipFile(target) as archive:
        assert archive.testzip() is None
    return {'file':target.name,'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}

if __name__ == '__main__':
    info = json.loads((ROOT/'dist/build-info.json').read_text())
    if info['mode'] != 'production':
        raise SystemExit('Hosting release requires a production build: python build.py --production')
    static = [(path,path.relative_to(ROOT/'dist').as_posix()) for path in sorted((ROOT/'dist').rglob('*')) if path.is_file() and path.name != 'build-info.json']
    assert any(name == 'index.html' for path,name in static)
    hosting = ROOT/'avenor-hosting-production.zip'
    results = [pack(hosting, static)]
    shutil.copyfile(hosting, ROOT/'avenor-hosting.zip')
    sources = []
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if not path.is_file() or path.suffix in ('.zip','.pyc') or '__pycache__' in relative.parts:
            continue
        if any(part.startswith('.') for part in relative.parts) and relative.as_posix() != '.gitignore':
            continue
        sources.append((path,relative.as_posix()))
    results.append(pack(ROOT/'avenor-site.zip', sources))
    print(json.dumps({'hosting_files':len(static),'source_files':len(sources),'releases':results},indent=2))
