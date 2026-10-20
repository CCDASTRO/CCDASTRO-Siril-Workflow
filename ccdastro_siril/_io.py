"""FITS interchange only; no custom XISF decoder or compression code."""
from pathlib import Path
import json
import numpy as np
from ._core import image_array

def load_fits(path):
    from astropy.io import fits
    with fits.open(path,memmap=False) as hdus:
        a=hdus[0].data; header=hdus[0].header.copy()
        if a is None: raise ValueError('FITS primary HDU has no image.')
        a=np.asarray(a)
        if a.dtype.kind=='u' and a.dtype.itemsize==2: a=a.astype(np.float32)/65535
        if a.ndim==3 and a.shape[0] in (1,3): a=a[0] if a.shape[0]==1 else np.moveaxis(a,0,-1)
        return image_array(a),{'fits_header':header.tostring(),'source_path':str(Path(path).resolve())}

def save_fits(path,data,metadata):
    from astropy.io import fits
    p=Path(path)
    if p.exists(): raise FileExistsError('Choose a new filename; existing files are not overwritten.')
    a=image_array(data)
    raw=next((metadata[k] for k in ('fits_header','original_header','header') if metadata.get(k) is not None),None)
    if isinstance(raw,fits.Header): header=raw.copy()
    elif isinstance(raw,str) and raw: header=fits.Header.fromstring(raw,sep='\n' if '\n' in raw else '')
    elif isinstance(raw,dict): header=fits.Header(raw)
    else: header=fits.Header()
    header.add_history('CCDASTRO independent workflow 0.4.2; original source preserved.')
    payload=np.moveaxis(a,-1,0) if a.ndim==3 else a
    # Astropy updates FITS structural cards to match the new image shape.
    fits.PrimaryHDU(payload,header).writeto(p,overwrite=False)
    return str(p.resolve())
