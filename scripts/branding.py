#!/usr/bin/env python3
"""Follow the public branding folder; activate complete validated generations."""
import hashlib
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import time
import urllib.request

ROOT = Path(os.getenv('BRANDING_DIR', '/branding'))
URL = os.getenv('BRANDING_URL', 'https://raw.githubusercontent.com/antixenoinitiative/wiki-compose-stack/main/branding')
FILES = {'axi_logo_new2.ico': None, **{f'axi_logo_new2_{n}x{n}.png': n for n in (16, 32, 150, 180, 192, 256)}}

def validate(name, data):
    size = FILES[name]
    if size is None:
        if len(data) < 6 or data[:4] != b'\x00\x00\x01\x00':
            raise ValueError('Invalid ICO: ' + name)
    elif (len(data) < 24 or data[:8] != b'\x89PNG\r\n\x1a\n' or
          struct.unpack('>II', data[16:24]) != (size, size)):
        raise ValueError('Wrong PNG format or dimensions: ' + name)

def fetch(name):
    request = urllib.request.Request(URL.rstrip('/') + '/' + name, headers={'User-Agent': 'AXI-Wiki-Branding/1'})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024:
        raise ValueError('Icon exceeds 1 MiB: ' + name)
    return data

def sync(fetcher=fetch):
    # Fetch and validate all files BEFORE touching the working generation.
    files = {name: fetcher(name) for name in FILES}
    for name, data in files.items():
        validate(name, data)
    digest = hashlib.sha256(b''.join(name.encode() + files[name] for name in sorted(files))).hexdigest()
    generations = ROOT / 'generations'
    generations.mkdir(parents=True, exist_ok=True)
    final = generations / digest
    if not final.exists():
        staging = Path(tempfile.mkdtemp(prefix='.incoming-', dir=generations))
        try:
            staging.chmod(0o755)
            for name, data in files.items():
                (staging / name).write_bytes(data)
                (staging / name).chmod(0o644)
            staging.rename(final)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    current = ROOT / 'current'
    changed = not current.is_symlink() or os.readlink(current) != 'generations/' + digest
    temporary = ROOT / '.next'
    temporary.unlink(missing_ok=True)
    temporary.symlink_to('generations/' + digest)
    temporary.replace(current)
    print('Branding updated.' if changed else 'Branding unchanged.', flush=True)
    # Keep generations: tiny, and a concurrent static-file reader may still use one.

def ready():
    return (ROOT / 'wiki-start.sh').is_file() and all((ROOT / 'current' / name).is_file() for name in FILES)

if __name__ == '__main__':
    if '--check' in sys.argv:
        sys.exit(0 if ready() else 1)
    ROOT.mkdir(parents=True, exist_ok=True)
    script = ROOT / '.wiki-start.sh'
    shutil.copyfile('/app/wiki-start.sh', script)
    script.chmod(0o644)
    script.replace(ROOT / 'wiki-start.sh')
    while True:
        try:
            sync()
        except Exception as exc:
            print(f'Branding update failed; previous icons retained: {exc}', file=sys.stderr, flush=True)
        time.sleep(int(os.getenv('BRANDING_INTERVAL_SECONDS', '300')))
