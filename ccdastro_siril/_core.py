"""CCDASTRO image processing for Siril.

Copyright (c) 2026 Chuck Faranda / CCDASTRO, Inc. All rights reserved.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from copy import deepcopy
import json
from pathlib import Path
import numpy as np

VERSION = '0.4.0'

def image_array(data):
    a = np.asarray(data)
    if a.ndim not in (2, 3) or (a.ndim == 3 and a.shape[-1] != 3):
        raise ValueError('Expected a mono H×W or RGB H×W×3 image.')
    if not np.issubdtype(a.dtype, np.floating):
        raise ValueError('A floating-point image is required; integer data must be normalized by the host adapter.')
    if not np.isfinite(a).all():
        raise ValueError('Image contains nonfinite samples.')
    if min(a.shape[:2]) < 2:
        raise ValueError('Image is too small.')
    return np.array(a, dtype=np.float32, copy=True)

def smooth(a, b, x):
    t = np.clip((x-a)/(b-a), 0, 1)
    return t*t*(3-2*t)

def tone_defaults():
    return dict(hue_enabled=False, hue=0., width=45., feather=30., min_saturation=5.,
        range='All tones', invert=False, amount=100., exposure=0., contrast=0.,
        shadows=0., highlights=0., whites=0., blacks=0., saturation=0., vibrance=0.,
        temperature=0., tint=0., curves={k:[0., .25, .5, .75, 1.] for k in ('RGB','R','G','B')})

def validate_tone(p):
    if set(p) != set(tone_defaults()):
        raise ValueError('Unrecognized or incomplete Color & Tone settings.')
    limits = dict(hue=(0,360), width=(1,180), feather=(1,180), min_saturation=(0,100),
        amount=(0,100), exposure=(-2,2), **{k:(-100,100) for k in ('contrast','shadows','highlights','whites','blacks','saturation','vibrance','temperature','tint')})
    for k,(lo,hi) in limits.items():
        if isinstance(p[k],bool) or not isinstance(p[k],(float,int)) or not np.isfinite(p[k]) or not lo <= p[k] <= hi:
            raise ValueError(f'Invalid {k}.')
    if type(p['hue_enabled']) is not bool or type(p['invert']) is not bool or p['range'] not in ('All tones','Shadows','Midtones','Highlights'):
        raise ValueError('Invalid mask selection.')
    if set(p['curves']) != {'RGB','R','G','B'}:
        raise ValueError('Invalid curve channels.')
    for points in p['curves'].values():
        if len(points) != 5 or points[0] != 0 or points[-1] != 1 or not np.isfinite(points).all() or not (np.diff(points)>0).all():
            raise ValueError('Curve points must increase from black to white.')

def curve_value(x, points):
    if np.array_equal(points, [0,.25,.5,.75,1]):
        return x
    y = np.asarray(points); delta = 4*np.diff(y); m = np.empty(5)
    m[0], m[4] = delta[0], delta[3]
    m[1:4] = 2*delta[:-1]*delta[1:]/(delta[:-1]+delta[1:])
    x = np.clip(x,0,1); i = np.minimum(3,(x*4).astype(int)); t=x*4-i
    return np.clip((2*t**3-3*t*t+1)*y[i]+(t**3-2*t*t+t)*m[i]/4+(-2*t**3+3*t*t)*y[i+1]+(t**3-t*t)*m[i+1]/4,0,1)

def hue_degrees(rgb):
    hi=rgb.max(axis=-1); lo=rgb.min(axis=-1); d=hi-lo; safe=np.maximum(d,1e-12)
    r,g,b=np.moveaxis(rgb,-1,0)
    h=np.where(hi==r,(g-b)/safe,np.where(hi==g,2+(b-r)/safe,4+(r-g)/safe))
    return np.where(d<1e-12,0,(h*60)%360)

def selection_mask(data, p):
    rgb = data if data.ndim==3 else np.repeat(data[...,None],3,-1)
    lum=np.clip(rgb @ np.array([.2126,.7152,.0722]),0,1); mask=np.ones(lum.shape)
    if p['hue_enabled']:
        if data.ndim!=3: raise ValueError('Hue masks require RGB.')
        hi=rgb.max(axis=-1); lo=rgb.min(axis=-1); sat=(hi-lo)/np.maximum(hi,1e-12)
        distance=np.abs(hue_degrees(rgb)-p['hue']); distance=np.minimum(distance,360-distance)
        inner=p['width']/2; outer=min(180,inner+p['feather']); threshold=p['min_saturation']/100
        sat_mask=np.zeros_like(sat) if threshold==1 else smooth(threshold,min(1,threshold+.1),sat)
        mask=(1-smooth(inner,outer,distance))*sat_mask
    if p['range']=='Shadows': mask*=1-smooth(.12,.55,lum)
    elif p['range']=='Midtones': mask*=smooth(.04,.35,lum)*(1-smooth(.65,.96,lum))
    elif p['range']=='Highlights': mask*=smooth(.45,.88,lum)
    if p['invert']: mask=1-mask
    return np.clip(mask,0,1)*p['amount']/100

def color_tone(data, settings, cancel=lambda:False):
    validate_tone(settings); a=image_array(data); p=settings
    color=a.ndim==3
    if not color and (p['hue_enabled'] or any(p[k] for k in ('temperature','tint','saturation','vibrance')) or any(p['curves'][k]!=[0,.25,.5,.75,1] for k in ('R','G','B'))):
        raise ValueError('Color controls require RGB.')
    result=a.copy()
    identity=all(p[k]==0 for k in ('exposure','contrast','shadows','highlights','whites','blacks','saturation','vibrance','temperature','tint')) and all(v==[0,.25,.5,.75,1] for v in p['curves'].values())
    if identity or p['amount']==0: return result
    for y in range(0,a.shape[0],64):
        if cancel(): raise InterruptedError('Cancelled; current result is unchanged.')
        source=a[y:y+64].astype(np.float64); rgb=source if color else np.repeat(source[...,None],3,-1)
        mask=selection_mask(source,p)[...,None]; lum=np.clip(rgb @ np.array([.2126,.7152,.0722]),0,1)
        lift=p['shadows']/400*(1-lum)**2+p['highlights']/400*lum**2+p['whites']/500*smooth(.6,1,lum)+p['blacks']/500*(1-smooth(0,.4,lum))
        x=np.clip(rgb*2**p['exposure'],0,1)
        x=np.clip(x+p['contrast']/50*x*(1-x)*(2*x-1)+lift[...,None],0,1)
        if color:
            gains=2**(np.array([p['temperature']+p['tint']*.5,-p['tint'],-p['temperature']+p['tint']*.5])/200)
            x=np.clip(x*gains,0,1)
        x=curve_value(x,p['curves']['RGB'])
        if color:
            x=np.stack([curve_value(x[...,c],p['curves'][key]) for c,key in enumerate(('R','G','B'))],-1)
        if color and (p['saturation'] or p['vibrance']):
            l=x @ np.array([.2126,.7152,.0722]); hi=x.max(axis=-1); lo=x.min(axis=-1)
            sat=(hi-lo)/np.maximum(hi,1e-12); scale=np.maximum(0,(1+p['saturation']/100)*(1+p['vibrance']/100*(1-sat)))
            delta=x-l[...,None]
            for c in range(3):
                dc=delta[...,c]; bound=np.where(dc>0,(1-l)/np.maximum(dc,1e-20),np.where(dc<0,-l/np.minimum(dc,-1e-20),np.inf))
                scale=np.minimum(scale,bound)
            x=l[...,None]+scale[...,None]*delta
        adjusted=np.where(mask==0,rgb,np.clip(rgb+mask*(x-rgb),0,1))
        result[y:y+64]=adjusted if color else adjusted[...,0]
    return result

def linked_stretch(data,target=.23):
    if not .01<=target<=.5: raise ValueError('Median target must be 0.01–0.5.')
    a=image_array(data); sample=a[::max(1,a.shape[0]//256),::max(1,a.shape[1]//256)]
    med=np.median(sample,axis=(0,1)); mad=np.median(np.abs(sample-med),axis=(0,1))*1.4826
    black=float(np.clip(np.mean(med-2.8*mad),0,.95)); center=float(np.mean(med))
    if center<=black or center>=1: raise ValueError('Insufficient tonal range for automatic stretching.')
    v=(center-black)/(1-black); mtf=(v*(target-1))/(2*target*v-target-v)
    x=np.clip((a-black)/(1-black),0,1)
    return np.asarray((mtf-1)*x/np.minimum((2*mtf-1)*x-mtf,-1e-20),np.float32)

def suppress_green(data,amount=.5):
    if not 0<=amount<=1: raise ValueError('Amount must be 0–1.')
    a=image_array(data)
    if a.ndim!=3: raise ValueError('Green suppression requires RGB.')
    a[...,1]=(1-amount)*a[...,1]+amount*np.minimum(a[...,1],np.maximum(a[...,0],a[...,2]))
    return a

def background_plane(data,amount=1.):
    if not 0<=amount<=1: raise ValueError('Amount must be 0–1.')
    a=image_array(data); color=a.ndim==3; v=a if color else a[...,None]; h,w=v.shape[:2]
    yy,xx=np.mgrid[0:h:max(1,h//96),0:w:max(1,w//96)]
    design=np.stack([np.ones(xx.size),(xx.ravel()/(w-1)-.5),(yy.ravel()/(h-1)-.5)],1)
    grid_y,grid_x=np.indices((h,w),dtype=np.float32); basis=[np.ones((h,w)),grid_x/(w-1)-.5,grid_y/(h-1)-.5]
    for c in range(v.shape[-1]):
        sample=v[yy,xx,c].ravel(); keep=sample<=np.quantile(sample,.65)
        for _ in range(4):
            coef=np.linalg.lstsq(design[keep],sample[keep],rcond=None)[0]; residual=sample-design@coef
            sigma=max(1e-6,1.4826*np.median(np.abs(residual[keep]-np.median(residual[keep]))))
            keep=(np.abs(residual-np.median(residual[keep]))<2.5*sigma)
            if keep.sum()<12: raise ValueError('Not enough background samples for a plane fit.')
        v[...,c]-=amount*(coef[1]*basis[1]+coef[2]*basis[2])
    return v if color else v[...,0]

def crop(data,x,y,width,height):
    a=image_array(data)
    if not all(type(v) is int for v in (x,y,width,height)) or min(x,y)<0 or min(width,height)<2 or x+width>a.shape[1] or y+height>a.shape[0]:
        raise ValueError('Crop must lie inside the image.')
    return a[y:y+height,x:x+width].copy()

def recombine(starless,stars,amount=1.,method='screen'):
    a=image_array(starless); b=image_array(stars)
    if a.shape!=b.shape: raise ValueError('Stars and starless images must be registered with matching shapes.')
    if not 0<=amount<=2 or method not in ('screen','add'): raise ValueError('Invalid recombination settings.')
    return np.clip(1-(1-a)*(1-b*amount) if method=='screen' else a+b*amount,0,1).astype(np.float32)

@dataclass
class Step:
    kind: str
    parameters: dict=field(default_factory=dict)
    enabled: bool=True
    review: bool=True

def evaluate(data,step,cancel=lambda:False):
    p=step.parameters
    if step.kind=='color_tone': return color_tone(data,p,cancel)
    if step.kind=='stretch': return linked_stretch(data,**p)
    if step.kind=='green': return suppress_green(data,**p)
    if step.kind=='background': return background_plane(data,**p)
    if step.kind=='crop': return crop(data,**p)
    raise ValueError(f'Unsupported portable operation: {step.kind}')

class Session:
    def __init__(self,data,metadata=None):
        self.source=image_array(data); self.source.setflags(write=False)
        self.current=self.source.copy(); self.metadata=deepcopy(metadata or {}); self.audit=[]
    def candidate(self,step,cancel=lambda:False):
        if not step.enabled: return self.current.copy()
        return image_array(evaluate(self.current,step,cancel))
    def accept(self,step,candidate):
        self.current=image_array(candidate)
        self.audit.append(asdict(step))
    def report(self):
        return dict(version=VERSION,steps=deepcopy(self.audit),shape=list(self.current.shape),minimum=float(self.current.min()),maximum=float(self.current.max()),median=float(np.median(self.current)))

def write_report(path,report):
    Path(path).write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
