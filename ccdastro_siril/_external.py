"""Optional GraXpert and authenticated SyQon CLI adapters; no vendor assets."""
from pathlib import Path
from tempfile import TemporaryDirectory
import os,re,shutil,math
import numpy as np
from ._core import image_array
from ._rcastro import process_args,read_result

SYQON_MODELS={'axiom-mini':'Axiom Mini (star separation)','axiom':'Axiom V3 (star separation)','prism-essential':'Prism Essential (denoise)','prism-advanced':'Prism Advanced (denoise)','prism-ultra':'Prism Ultra (denoise)','prism-max':'Prism Max (denoise)','prism-legacy-v1':'Prism Legacy V1 (denoise)','prism-legacy-v2':'Prism Legacy V2 (denoise)','parallax-nano':'Parallax Nano','parallax':'Parallax','deep-gradient':'Deep Gradient'}

def discover(provider,configured=''):
    local=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'AppData/Local')));program=Path(os.environ.get('ProgramFiles','C:/Program Files'))
    if provider=='graxpert':candidates=[configured,shutil.which('GraXpert'),str(local/'Programs/GraXpert/GraXpert.exe'),str(program/'GraXpert/GraXpert.exe')]
    elif provider=='syqon':
        registered=''
        if os.name=='nt':
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\App Paths\syqon-cli.exe') as key:registered=winreg.QueryValue(key,None)
            except OSError:pass
        candidates=[configured,os.environ.get('SYQON_CLI_PATH'),registered,str(local/'Programs/SyQon Studio/syqon-cli.exe'),shutil.which('syqon-cli')]
    else:raise ValueError('Unsupported optional provider.')
    return next((str(Path(p)) for p in candidates if p and Path(p).is_file()),'')

def syqon_catalog(executable,cancel=lambda:False):
    code,version,_=process_args(executable,['--version'],cancel,25)
    if code or 'syqon' not in version.lower():raise RuntimeError('This executable is not a supported SyQon Studio CLI.')
    code,models,error=process_args(executable,['--list-models'],cancel,25)
    if code:raise RuntimeError('SyQon model discovery failed. Update Studio and finish its sign-in/Required Items setup. '+error[-500:])
    found=[line.split()[0] for line in models.splitlines() if line.split() and line.split()[0] in SYQON_MODELS]
    if not found:raise RuntimeError('The installed SyQon CLI did not advertise a supported model.')
    return found

def number(parameters,key,default,low,high,integer=False):
    value=parameters.get(key,default)
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:raise ValueError(f'Invalid {key} value.')
    if integer and int(value)!=value:raise ValueError(f'{key} must be an integer.')
    return int(value) if integer else float(value)

def build_arguments(settings,input_path,output_path,stars_path=None):
    provider=settings.get('provider');operation=settings.get('operation');device=settings.get('device','auto')
    if device not in ('auto','cpu'):raise ValueError('Choose automatic acceleration or CPU.')
    if provider=='graxpert':
        if operation not in ('background','denoise'):raise ValueError('Unsupported GraXpert operation.')
        args=['-cli','-cmd','background-extraction' if operation=='background' else 'denoising','-output',str(Path(output_path).with_suffix('')),'-gpu','false' if device=='cpu' else 'true']
        model=settings.get('ai_version','latest')
        if not isinstance(model,str) or (model!='latest' and not re.fullmatch(r'\d+\.\d+\.\d+',model)):raise ValueError('Use latest or a numeric GraXpert model version.')
        if model!='latest':args+=['-ai_version',model]
        if operation=='background':
            correction=settings.get('correction','Subtraction')
            if correction not in ('Subtraction','Division'):raise ValueError('Unsupported background correction.')
            args+=['-correction',correction,'-smoothing',str(number(settings,'amount',.5,0,1))]
        else:args+=['-strength',str(number(settings,'amount',.5,0,1)),'-batch_size','1']
        return args+[str(input_path)]
    if provider!='syqon' or operation not in SYQON_MODELS:raise ValueError('Unsupported SyQon model.')
    if device=='cpu':raise ValueError('SyQon Studio CLI manages its own device; use Auto in this integration.')
    domain=settings.get('domain','linear')
    if domain not in ('linear','nonlinear'):raise ValueError('Declare whether input is linear or non-linear.')
    if operation in ('prism-essential','prism-advanced','prism-legacy-v2','deep-gradient') and domain!='linear':raise ValueError('This SyQon model requires linear input.')
    if operation=='prism-legacy-v1' and domain!='nonlinear':raise ValueError('Prism Legacy V1 requires non-linear input.')
    args=['--model',operation,'--precision','f32','--domain',domain,'--application',str(number(settings,'amount',1,0,1))]
    if operation.startswith('axiom'):
        args+=['--axiom-stretch','auto' if domain=='linear' else 'identity']
        if settings.get('stars',True) and stars_path is not None:args+=['--stars-output',str(stars_path)]
    if operation.startswith('parallax'):
        if operation=='parallax':
            family=settings.get('family','aesthetics')
            if family not in ('aesthetics','classic'):raise ValueError('Unsupported Parallax family.')
            args+=['--family',family]
        stages=[settings.get(name,True) for name in ('correction','reduction','deblur')]
        if not all(type(v) is bool for v in stages) or not any(stages):raise ValueError('Enable at least one Parallax stage.')
        for name,value in zip(('correction','reduction','deblur'),stages):args+=['--'+name,str(value).lower()]
        args+=['--reduction-level',str(number(settings,'reduction_level',3,0,10)),'--deblur-strength',str(number(settings,'deblur_strength',.5,0,1))]
    return args+[str(input_path),str(output_path)]

def run_external(data,settings,cancel=lambda:False):
    from astropy.io import fits
    provider=settings.get('provider');executable=settings.get('executable') or discover(provider)
    if not executable or not Path(executable).is_file():raise ValueError('Install or locate the optional tool first.')
    if provider=='syqon' and settings.get('operation') not in syqon_catalog(executable,cancel):raise ValueError('This SyQon CLI does not advertise the selected model.')
    source=image_array(data)
    with TemporaryDirectory(prefix='ccdastro-optional-') as folder:
        folder=Path(folder);input_path=folder/'input.fits';output=folder/'result.fits';stars_path=folder/'stars.fits'
        header=fits.Header();header['ROWORDER']='BOTTOM-UP'
        fits.PrimaryHDU(np.moveaxis(source,-1,0) if source.ndim==3 else source,header).writeto(input_path,overwrite=False)
        args=build_arguments(settings,input_path,output,stars_path)
        code,stdout,stderr=process_args(executable,args,cancel)
        if cancel():raise InterruptedError('Optional-tool processing cancelled.')
        if code:
            if provider=='syqon' and code==4:raise RuntimeError('SyQon denied model access. Sign in and install Required Items in SyQon Studio; verify the model entitlement there. Source unchanged.')
            raise RuntimeError(f'{provider} failed (exit {code}). '+(stderr or stdout)[-1800:])
        if not output.is_file():raise RuntimeError('The tool returned without the requested result file. Source unchanged.')
        result=read_result(output,source.shape);stars=None;method='add'
        if provider=='syqon' and settings.get('operation','').startswith('axiom') and settings.get('stars',True):
            if not stars_path.is_file():raise RuntimeError('SyQon did not return the requested stars output; nothing was accepted.')
            stars=read_result(stars_path,source.shape)
            add_error=np.mean(np.abs(source-(result+stars)));screen_error=np.mean(np.abs(source-(1-(1-result)*(1-stars))))
            method='screen' if screen_error<add_error else 'add'
        return {'image':result,'stars':stars,'method':method}
