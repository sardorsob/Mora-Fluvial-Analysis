# -*- coding: utf-8 -*-
"""
Python translation of R/eseis::signal_spectrum()

Calculate the spectrum of a time series using either:
- modified periodogram ('periodogram'), or
- autoregressive spectral estimation ('autoregressive')

Optional features:
- running-mean smoothing (n spectral bins)
- linear interpolation to a fixed resolution (res), with linear or log frequency spacing

Returns: dict {'frequency': np.ndarray, 'power': np.ndarray}
Or, for 'eseis-like' inputs (dict with keys 'signal' and 'meta': {'dt': ...}), returns
the same dict updated with a 'spectrum' key containing the frequency/power table
and a minimal 'history' entry.

Dependencies:
- numpy, scipy.signal
- Optional: spectrum (for Burg AR PSD), statsmodels (fallback AR)

Notes:
- Frequencies returned are Hz, from 0 to Nyquist (fs/2).
- Periodogram power is linear (x^2/Hz with density scaling).
  Convert positive power to dB with 10*log10(power).
- The experimental AR branches need amplitude normalization checks before
  comparison with response-corrected PSDs.
- dt is the *sampling period* (seconds); fs=1/dt is sampling frequency (Hz).

R sources: eseis::signal_spectrum (periodogram, AR; smoothing; interpolation).
  See: https://rdrr.io/github/coffeemuggler/eseis/src/R/signal_spectrum.R
"""
import warnings
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from scipy.signal import periodogram

# Optional AR dependencies
try:
    # Burg AR (closest match to R's spec.ar common usage)
    from spectrum import burg
    _HAVE_SPECTRUM = True
except Exception:
    _HAVE_SPECTRUM = False

try:
    # Yule-Walker fallback
    import statsmodels.api as sm
    _HAVE_STATSMODELS = True
except Exception:
    _HAVE_STATSMODELS = False


def _running_mean(x: np.ndarray, k: int) -> np.ndarray:
    """Running mean identical in spirit to caTools::runmean."""
    if k is None or k <= 1:
        return x
    # 'same' keeps vector length aligned with R behavior (border effects smoothed)
    kernel = np.ones(int(k), dtype=float) / float(k)
    # NumPy's 'same' uses the longer input length. Keep one output per bin.
    start = (len(kernel) - 1) // 2
    return np.convolve(x, kernel, mode='full')[start:start + len(x)]


def _ar_psd_burg(x: np.ndarray, fs: float, order: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Burg AR spectrum. If order not provided, use a modest default (e.g., 16)
    which is common for smooth ambient noise spectra.

    Returns f (Hz) and PSD (linear).
    """
    if order is None:
        order = 16
    if not _HAVE_SPECTRUM:
        raise ImportError("Burg AR requires the 'spectrum' package. Install `pip install spectrum`.")

    # Burg returns AR coefficients; we evaluate PSD on a frequency grid
    # Use a dense frequency grid up to Nyquist
    nfft = 4096
    f = np.linspace(0.0, fs / 2.0, num=nfft//2 + 1)

    # Estimate AR model
    ar = burg.Burg(x, order=order)
    ar()

    # Compute AR PSD: sigma2 / |1 - sum a_k e^{-j2πf k/fs}|^2
    # spectrum library has a method for PSD over normalized freq; we adapt to Hz.
    # Use ar.spectrum() which returns normalized freq [0, 0.5]; scale to Hz.
    psd_norm = ar.spectrum()  # default length nfft; normalized frequencies [0, 0.5]
    # Build matching Hz axis for psd_norm:
    f_norm = np.linspace(0.0, 0.5, len(psd_norm))
    f_hz = f_norm * fs
    # Clip to [0, fs/2]
    m = (f_hz >= 0) & (f_hz <= fs / 2.0)
    return f_hz[m], np.asarray(psd_norm)[m]


def _ar_psd_yule_walker(x: np.ndarray, fs: float, order: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Yule-Walker AR PSD fallback using statsmodels.
    """
    if not _HAVE_STATSMODELS:
        raise ImportError("Yule-Walker fallback requires 'statsmodels'. Install `pip install statsmodels`.")
    if order is None:
        order = 16

    # Estimate AR params via Yule-Walker
    # Fit AR via Yule-Walker (statsmodels has yule_walker helper)
    ar_params, sigma = sm.tsa.stattools.yule_walker(x, order=order)
    # Build PSD on Hz grid
    nfft = 4096
    f = np.linspace(0.0, fs / 2.0, num=nfft//2 + 1)
    w = 2.0 * np.pi * f / fs
    # AR transfer function magnitude squared: sigma^2 / |1 - sum a_k e^{-j w k}|^2
    denom = np.ones_like(w, dtype=complex)
    for k, a_k in enumerate(ar_params, start=1):
        denom -= a_k * np.exp(-1j * w * k)
    psd = (sigma**2) / np.abs(denom)**2
    return f, psd.real


def signal_spectrum(
    data: Union[np.ndarray, Dict[str, Any], List[Any]],
    dt: Optional[float] = None,
    method: str = "periodogram",
    n: Optional[int] = None,
    res: Optional[int] = None,
    log: bool = False,
    **kwargs
) -> Union[Dict[str, np.ndarray], Dict[str, Any], List[Any]]:
    """
    Calculate the spectrum of a time series (R/eseis::signal_spectrum port).

    Parameters
    ----------
    data : np.ndarray | dict | list
        Numeric vector (1D numpy array), an 'eseis-like' dict {'signal': array, 'meta': {'dt': ...}},
        or a list of such elements.
    dt : float, optional
        Sampling period [s]. If omitted and 'data' is not eseis-like, defaults to 1/200 s, with a warning.
        If 'data' is eseis-like, dt is read from data['meta']['dt'].
    method : {'periodogram', 'autoregressive'}
        Spectrum estimator. Default 'periodogram' (modified periodogram).
    n : int, optional
        Width of the running mean in spectral bins, before interpolation.
    res : int, optional
        Target resolution (#points) for the spectrum; if provided, linear interpolation is performed.
    log : bool
        If True, interpolation uses log-spaced frequency values; otherwise linear spacing.
    **kwargs : dict
        Additional keyword args passed to the estimator. For periodogram, typical kwargs include 'window', 'scaling'.

    Returns
    -------
    dict or eseis-like dict or list
        If input is an array: {'frequency': f, 'power': Pxx}
        If input is eseis-like dict: returns that dict updated with 'spectrum'
            (DataFrame-like dict) and minimal 'history'.
        If input is list: list of outputs for each element.
    """
    # Handle list input
    if isinstance(data, list):
        return [signal_spectrum(d, dt=dt, method=method, n=n, res=res, log=log, **kwargs) for d in data]

    # Eseis-like object?
    eseis_class = False
    if isinstance(data, dict) and ('signal' in data) and ('meta' in data) and ('dt' in data['meta']):
        eseis_class = True
        eseis_data = data
        x = np.asarray(eseis_data['signal'], dtype=float)
        dt = eseis_data['meta']['dt']
    else:
        # Raw numeric vector
        x = np.asarray(data, dtype=float)
        if dt is None:
            warnings.warn("Sampling frequency missing! Set to 1/200", RuntimeWarning)
            dt = 1.0 / 200.0  # match R's default
    fs = 1.0 / float(dt)  # sampling frequency in Hz

    # Compute spectrum
    method = (method or "periodogram").lower()
    if method == "periodogram":
        # SciPy periodogram (linear PSD) – closest to R spec.pgram default behavior
        # You can pass window/scaling in kwargs; e.g., window='hann', scaling='density'

        kwargs.setdefault("scaling", "density")
        kwargs.setdefault("detrend", "constant")
        kwargs.setdefault("nfft", x.size)
        f, Pxx = periodogram(x, fs=fs, **kwargs)
    elif method == "autoregressive":
        # Try Burg AR first; fallback to Yule-Walker
        try:
            f, Pxx = _ar_psd_burg(x, fs, order=kwargs.get('order', None))
        except Exception:
            f, Pxx = _ar_psd_yule_walker(x, fs, order=kwargs.get('order', None))
    else:
        raise ValueError("Keyword for method not supported! Use 'periodogram' or 'autoregressive'.")

    # Optional running-mean smoothing (n samples)
    if n is not None:
        Pxx = _running_mean(Pxx, int(n))

    # Optional interpolation to 'res' points (linear or log frequency spacing)
    if res is not None:
        # Build interpolation target frequency vector
        if log:
            # Use log-spaced frequencies between the smallest positive freq and max
            # (avoid f=0 for log spacing)
            fmin_pos = np.min(f[f > 0.0]) if np.any(f > 0.0) else f[1]
            f_int = np.exp(np.linspace(np.log(fmin_pos), np.log(np.max(f)), num=int(res)))
        else:
            f_int = np.linspace(np.min(f), np.max(f), num=int(res))

        # Interpolate once after smoothing. Linear interpolation cannot turn
        # nonnegative power into negative values between neighboring bins.
        Pxx = np.interp(f_int, f, Pxx)
        f = f_int

    # Compose output
    out_table = {'frequency': f, 'power': Pxx}

    if eseis_class:
        # Update 'eseis-like' dict with spectrum and minimal history
        eseis_data['spectrum'] = out_table
        # Minimal history entry (mirrors R semantics at a high level)
        hist_entry = {
            'time': 'now',  # left as string; add datetime if desired
            'call': 'signal_spectrum()',
            'arguments': {'dt': dt, 'n': n, 'res': res, 'method': method}
        }
        # Append to history
        try:
            eseis_data.setdefault('history', []).append(hist_entry)
            eseis_data['meta']['type'] = 'spectrum'
        except Exception:
            pass
        return eseis_data


    # Keep power linear so it can be combined before conversion to dB.
    return out_table
