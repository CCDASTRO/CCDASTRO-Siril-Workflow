"""Discovery and separate-script handoff; no Lighthouse code is imported."""
from pathlib import Path
import os

def discover(configured='', roots=None):
    if configured:
        path = Path(configured).expanduser()
        return str(path.resolve()) if path.is_file() and path.suffix.lower() == '.py' else ''
    if roots is None:
        local = Path(os.environ.get('LOCALAPPDATA', Path.home()/'.local/share'))
        roots = [local/'siril-scripts', Path.home()/'.local/share/siril-scripts']
    for root in roots:
        for relative in ('processing/Lighthouse.py', 'Lighthouse.py'):
            path = Path(root)/relative
            if path.is_file():
                return str(path.resolve())
    return ''


def handoff(host, data, metadata, destination, script):
    from ._io import load_fits
    import numpy as np
    script = discover(script)
    if not script:
        raise FileNotFoundError('Install Lighthouse through Siril Get Scripts, or locate its Lighthouse.py file.')
    original, original_meta = host.read()
    source = Path(original_meta.get('source_path', ''))
    if not source.is_file() or source.suffix.lower() not in ('.fit', '.fits', '.fts'):
        raise ValueError('Before handing off, save the active Siril source to a new FITS file. Then reopen CCDASTRO Workflow.')
    disk, _ = load_fits(source)
    if disk.shape != original.shape or not np.array_equal(disk, original):
        raise ValueError('The active Siril source has unsaved changes. Save it to a new FITS file before handing off.')
    saved = host.save(data, metadata, destination)
    try:
        host.api.cmd('load', str(Path(saved).resolve()))
    except Exception:
        host.api.cmd('load', str(source.resolve()))
        raise
    return saved
