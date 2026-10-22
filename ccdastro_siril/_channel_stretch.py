"""Independent channel MTF stretch; plans are fixed before preview sampling."""
from copy import deepcopy
import numpy as np


def defaults():
    return {'targets': [.23, .23, .23], 'amounts': [100., 100., 100.]}


def validate(settings):
    if set(settings) != {'targets', 'amounts'}:
        raise ValueError('Expected three targets and three amounts.')
    for key, lo, hi in [('targets', .01, .5), ('amounts', 0., 100.)]:
        values = settings[key]
        if not isinstance(values, (list, tuple)) or len(values) != 3:
            raise ValueError('Three channel values are required.')
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) or not lo <= v <= hi for v in values):
            raise ValueError(f'Invalid channel {key}.')


def plan(data, settings):
    validate(settings)
    a = np.asarray(data)
    if a.ndim != 3 or a.shape[-1] != 3 or not np.issubdtype(a.dtype, np.floating) or min(a.shape[:2]) < 2:
        raise ValueError('Use a linear RGB image, or load three registered mono FITS masters.')
    if not np.isfinite(a).all() or a.min() < 0 or a.max() > 1:
        raise ValueError('Channel stretching requires finite, normalized samples in 0–1.')
    sample = a[::max(1, int(np.ceil(a.shape[0]/512))), ::max(1, int(np.ceil(a.shape[1]/512)))]
    med = np.median(sample, axis=(0, 1)).astype(np.float64)
    mad = np.median(np.abs(sample-med), axis=(0, 1))*1.4826
    result = []
    for c, name in enumerate(('R', 'G', 'B')):
        amount = settings['amounts'][c]/100
        if amount == 0:
            result.append({'black': 0., 'midtones': .5, 'amount': 0.})
            continue
        black = float(np.clip(med[c]-2.8*mad[c], 0, .95))
        if not black < med[c] < 1:
            raise ValueError(f'{name}: insufficient tonal range; set its amount to zero or choose another input.')
        v = (med[c]-black)/(1-black)
        target = settings['targets'][c]
        m = float(v*(target-1)/(2*target*v-target-v))
        result.append({'black': black, 'midtones': m, 'amount': amount})
    return result


def apply_plan(data, parameters, cancel=lambda: False):
    result = np.array(data, dtype=np.float32, copy=True)
    for y in range(0, result.shape[0], 64):
        if cancel():
            raise InterruptedError('Cancelled; current result is unchanged.')
        for c, p in enumerate(parameters):
            if p['amount'] == 0:
                continue
            source = result[y:y+64, :, c].astype(np.float64)
            x = np.clip((source-p['black'])/(1-p['black']), 0, 1)
            m = p['midtones']
            stretched = (m-1)*x/np.minimum((2*m-1)*x-m, -1e-20)
            result[y:y+64, :, c] = np.clip(source+p['amount']*(stretched-source), 0, 1)
    return result


def stretch(data, targets=None, amounts=None, cancel=lambda: False):
    settings = defaults()
    if targets is not None: settings['targets'] = deepcopy(targets)
    if amounts is not None: settings['amounts'] = deepcopy(amounts)
    return apply_plan(data, plan(data, settings), cancel)
