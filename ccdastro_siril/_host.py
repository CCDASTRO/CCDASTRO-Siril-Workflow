"""Siril adapter. Only explicit exports change the active Siril image."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
from ._core import image_array

def normalize(data):
    a=np.asarray(data)
    if a.dtype==np.uint16: a=a.astype(np.float32)/65535
    if a.ndim==3 and a.shape[0] in (1,3): a=a[0] if a.shape[0]==1 else np.moveaxis(a,0,-1)
    return image_array(a)

def to_siril(data):
    a=image_array(data)
    return np.ascontiguousarray(np.moveaxis(a,-1,0) if a.ndim==3 else a[None,...],dtype=np.float32)

class ImageNotReadyError(RuntimeError):
    """The host has no usable single image available for transfer."""

IMAGE_NOT_READY = ('Open a single image in Siril and wait for loading to finish, '
                   'then launch CCDASTRO Workflow again. No image was changed.')

class Host:
    title='Siril'
    native_commands={'subsky','platesolve','spcc','starnet','autostretch','saturation','rmgreen','denoise','deconv','ght'}
    def __init__(self,siril): self.api=siril
    def read(self):
        if not self.api.is_image_loaded():
            raise ImageNotReadyError(IMAGE_NOT_READY)
        try:
            pixels=self.api.get_image_pixeldata(preview=False)
        except Exception as error:
            if 'no fits image' in str(error).lower():
                raise ImageNotReadyError(IMAGE_NOT_READY) from error
            raise
        if pixels is None:
            raise ImageNotReadyError(IMAGE_NOT_READY)
        a=normalize(pixels)
        return a,{'fits_header':self.api.get_image_fits_header(return_as='str') or '', 'source_path':self.api.get_image_filename() or ''}
    def save(self,data,metadata,path):
        path=Path(path)
        if path.exists(): raise FileExistsError('Choose a new filename; existing files are not overwritten.')
        if not self.api.save_image_file(to_siril(data),metadata.get('fits_header',''),str(path)):
            raise RuntimeError('Siril did not save the result.')
        return str(path)
    def publish(self,data,metadata,name='CCDASTRO result'):
        raise RuntimeError('Use Save result to FITS. Siril has one active image; the source is left unchanged.')
    def native(self,data,metadata,parameters):
        command=parameters.get('command'); args=parameters.get('args',[])
        if command not in self.native_commands or not isinstance(args,list) or not all(isinstance(x,str) and '\n' not in x and '\r' not in x for x in args):
            raise ValueError('Choose a supported Siril image-processing command with a string argument list.')
        original,original_meta=self.read()
        source=Path(original_meta.get('source_path',''))
        if not source.is_file() or source.suffix.lower() not in ('.fit','.fits','.fts'):
            raise ValueError('Native Siril passes require a saved FITS source. Portable passes can use any loaded image.')
        from ._io import load_fits
        disk,_=load_fits(source)
        if disk.shape!=original.shape or not np.array_equal(disk,original):
            raise ValueError('The active Siril image has unsaved changes. Save it to a new FITS file before native passes.')
        # Native commands receive a scratch FITS image. The verified unchanged source is restored.
        with TemporaryDirectory(prefix='ccdastro-siril-') as folder:
            working=Path(folder)/'working.fit'
            self.save(data,metadata,working)
            try:
                self.api.cmd('load',str(working)); self.api.cmd(command,*args)
                result,meta=self.read(); meta['source_path']=metadata.get('source_path','')
                return result,meta
            finally:
                # Reload the original document when it is an unmodified disk-backed input;
                # otherwise restore the pixel/header snapshot before scratch cleanup.
                self.api.cmd('load',str(source))
    def log(self,message): self.api.log(message)
