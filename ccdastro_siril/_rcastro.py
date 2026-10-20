"""RC-Astro CLI integration. No vendor code, models or credentials are bundled."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json,math,os,re,shutil,subprocess
import numpy as np
from ._core import image_array,VERSION

TOOLS={'bxt':'BlurXTerminator','nxt':'NoiseXTerminator','sxt':'StarXTerminator'}
DEFAULTS={'bxt':{'ss':.5,'sn':.5,'ash':0.,'ansp':True,'nsd':0.},'nxt':{'dn':.9,'it':2},'sxt':{'stars':True,'unscreen':True}}

def find_executable():
    candidates=[shutil.which('rc-astro'),str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'RC-Astro/CLI/rc-astro.exe')]
    return next((p for p in candidates if p and Path(p).is_file()),'')

def process_args(executable,args,cancel=lambda:False,timeout=None):
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    process=subprocess.Popen([str(executable),*args],cwd=str(Path(executable).parent),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace',creationflags=flags)
    import time
    started=time.monotonic()
    try:
        while True:
            if cancel():raise InterruptedError('RC-Astro operation cancelled. Candidate was not accepted.')
            if timeout is not None and time.monotonic()-started>timeout:raise TimeoutError('RC-Astro did not respond to the tool query.')
            try:
                stdout,stderr=process.communicate(timeout=.2)
                return process.returncode,stdout,stderr
            except subprocess.TimeoutExpired:pass
    finally:
        if process.poll() is None:
            process.terminate()
            try:process.communicate(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.communicate()

def probe(executable,tool,cancel=lambda:False):
    if tool not in TOOLS:raise ValueError('Unsupported RC-Astro tool.')
    if not Path(executable).is_file():raise ValueError('Select the installed RC-Astro CLI executable first.')
    code,stdout,_=process_args(executable,[tool,'--json'],cancel,25)
    if code:raise RuntimeError('RC-Astro could not describe this tool. Check its installation and activation outside the workflow.')
    try:schema=json.loads(stdout)
    except ValueError as error:raise RuntimeError('RC-Astro returned an invalid parameter document.') from error
    if not isinstance(schema,dict) or not isinstance(schema.get('schemaVersion'),int) or schema['schemaVersion']<4:raise RuntimeError('This integration requires an RC-Astro CLI with schema version 4 or later.')
    if schema.get('license',{}).get('valid') is not True:raise RuntimeError(TOOLS[tool]+' is not activated for this RC-Astro CLI installation. Activate it with RC-Astro, then try again.')
    return schema

def tool_arguments(tool,settings,schema):
    parameters={p['name']:p for p in schema.get('parameters',[]) if isinstance(p,dict) and 'name' in p}
    values=dict(DEFAULTS[tool]);values.update(settings.get('values',{}))
    if set(values)-set(DEFAULTS[tool]):raise ValueError('Unsupported RC-Astro parameter.')
    if tool=='bxt' and settings.get('linear_confirmed') is not True:raise ValueError('BlurXTerminator requires linear, unstretched input. Confirm this in its settings and run it before stretching.')
    args=[];pinned=set()
    if tool=='bxt' and settings.get('correct_only'):
        mode=next((m for m in schema.get('modes',[]) if m.get('name')=='correctOnlyMode'),None)
        if mode is None:raise ValueError('This CLI/model does not expose Correct Only mode.')
        args.append(mode['flag']);pinned=set(mode.get('pins',{}))
    for name,value in values.items():
        if name in pinned:continue
        # Automatic PSF owns its diameter; do not send a conflicting manual value.
        if name=='nsd' and values.get('ansp'):continue
        parameter=parameters.get(name)
        if parameter is None and tool=='sxt' and name=='stars':parameter=parameters.get('difference')
        if parameter is None:raise ValueError(f'The installed {TOOLS[tool]} model does not support {name}.')
        flag=parameter.get('flag','')
        if not re.fullmatch(r'--[a-zA-Z][a-zA-Z0-9-]*',flag):raise ValueError('Invalid flag in RC-Astro parameter schema.')
        if parameter.get('type')=='bool':
            if type(value) is not bool:raise ValueError('Expected a boolean RC-Astro parameter.')
            args.append(flag if value else flag+'=false')
        else:
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('Expected a finite numeric RC-Astro parameter.')
            if value<parameter.get('min',value) or value>parameter.get('max',value):raise ValueError(f'{name} is outside the installed model range.')
            if parameter.get('type')=='int' and int(value)!=value:raise ValueError('Expected an integer RC-Astro parameter.')
            args.extend([flag,str(value)])
    return args

def read_result(path,expected_shape):
    from astropy.io import fits
    with fits.open(path,memmap=False) as hdus:
        data=np.asarray(hdus[0].data,dtype=np.float32)
        if str(hdus[0].header.get('ROWORDER','BOTTOM-UP')).upper()=='TOP-DOWN':data=np.flip(data,axis=-2)
        if data.ndim==3 and data.shape[0] in (1,3):data=data[0] if data.shape[0]==1 else np.moveaxis(data,0,-1)
        result=image_array(data)
    if result.shape!=expected_shape:raise ValueError('RC-Astro output dimensions do not match the input.')
    return result

def run_tool(data,settings,cancel=lambda:False):
    from astropy.io import fits
    tool=settings.get('tool');executable=settings.get('executable') or find_executable()
    schema=probe(executable,tool,cancel);args=tool_arguments(tool,settings,schema)
    device=settings.get('device','auto')
    if device not in ('auto','cpu'):raise ValueError('Choose automatic device selection or CPU.')
    host=['--host','CCDASTRO-SirilWorkflow-'+VERSION] if schema['schemaVersion']>=6 else []
    source=image_array(data)
    with TemporaryDirectory(prefix='ccdastro-rcastro-') as folder:
        folder=Path(folder);input_file=folder/'input.fit';output=folder/'result.fit'
        header=fits.Header();header['ROWORDER']='BOTTOM-UP'
        payload=np.moveaxis(source,-1,0) if source.ndim==3 else source
        fits.PrimaryHDU(payload,header).writeto(input_file,overwrite=False)
        command=[tool,*host,'--device',device,'--depth','32F','--json','-o',str(output),*args,str(input_file)]
        code,stdout,stderr=process_args(executable,command,cancel)
        events=[]
        for line in stdout.splitlines():
            try:event=json.loads(line)
            except ValueError:continue
            if isinstance(event,dict):events.append(event)
        errors=[str(e.get('message','RC-Astro failed.')) for e in events if e.get('event')=='error']
        if code or errors:raise RuntimeError('\n'.join(errors) or 'RC-Astro processing failed (exit '+str(code)+'). Check its installation, license and selected device.')
        if cancel():raise InterruptedError('RC-Astro operation cancelled.')
        if not output.is_file():raise RuntimeError('RC-Astro returned without a result image.')
        result=read_result(output,source.shape);stars=None
        if tool=='sxt' and settings.get('values',{}).get('stars',True):
            sidecars=[]
            for event in events:
                if event.get('event')=='status' and event.get('phase')=='complete' and event.get('output'):
                    path=Path(event['output']);path=path if path.is_absolute() else folder/path
                    if path.resolve().parent==folder.resolve() and path.resolve()!=output.resolve() and path.is_file():sidecars.append(path)
            for suffix in ('-stars','-difference'):
                candidate=output.with_name(output.stem+suffix+output.suffix)
                if candidate.is_file():sidecars.append(candidate)
            if not sidecars:raise RuntimeError('StarXTerminator did not produce the requested stars image; nothing was accepted.')
            stars=read_result(sidecars[0],source.shape)
        return {'image':result,'stars':stars,'method':'screen' if settings.get('values',{}).get('unscreen',True) else 'add'}
