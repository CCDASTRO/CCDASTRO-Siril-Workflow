from pathlib import Path
import zipfile,hashlib
root=Path(__file__).resolve().parent.parent
out=root/'dist';out.mkdir(exist_ok=True)
version='0.5.0';label='Siril';package='ccdastro_siril'
archive=out/f'CCDASTRO-{label}-Workflow-{version}.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for relative in ['CCDASTRO_Siril_Workflow.py',package,'presets','README.md','INSTALL.md','INSTALL-WINDOWS.txt','LICENSE.txt','THIRD_PARTY_NOTICES.md']:
        path=root/relative
        for item in ([path] if path.is_file() else sorted(path.rglob('*'))):
            if item.is_file() and '__pycache__' not in item.parts and item.suffix!='.pyc':
                if item.suffix in ('.py','.md','.txt','.json'): item.read_bytes().decode('utf-8-sig')
                z.write(item,Path(f'CCDASTRO-{label}-Workflow')/item.relative_to(root))
runtime=(root/package/'_core.py').read_text(encoding='utf-8')
installer=(root/'installer/workflow.iss').read_text(encoding='utf-8')
if f"VERSION = '{version}'" not in runtime or f'#define AppVersion "{version}"' not in installer:raise ValueError('Runtime, packaging and installer versions differ.')
files=[archive,out/f'CCDASTRO-{label}-Workflow-{version}-Setup.exe']
for file in files:
    if not file.is_file():raise FileNotFoundError(file)
(out/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files))
print('Built installer, portable ZIP and SHA256SUMS.txt')
