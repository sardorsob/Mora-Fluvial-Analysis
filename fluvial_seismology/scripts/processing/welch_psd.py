"""Estimate response-corrected velocity spectra from an ObsPy stream."""

import numpy as np
from scipy.signal import welch


def welch_psd(
    stream, inventory, fmin=1.0, fmax=None, nperseg=None,
    noverlap=None, window="hann", scaling="density", *, channel=None,
    pre_filt=None,
):
    """Return frequency in Hz and velocity power in dB.

    Density uses (m/s)²/Hz; spectrum scaling uses (m/s)². Select a channel
    explicitly for a stream with multiple traces, and merge its segments first.
    By default the output band ends at 150 Hz or 90% of Nyquist, whichever
    is lower. Supply response filter corners for a different passband.
    """
    traces = [tr for tr in stream if channel is None or tr.stats.channel == channel]
    if len(traces) != 1:
        raise ValueError("Select exactly one merged trace for Welch PSD.")
    trace = traces[0].copy()
    fs = trace.stats.sampling_rate
    nyquist = fs / 2
    if pre_filt is None:
        pre_filt = (0.5, 0.8, 0.90 * nyquist, 0.98 * nyquist)
    if len(pre_filt) != 4 or not 0 < pre_filt[0] < pre_filt[1] < pre_filt[2] < pre_filt[3] < nyquist:
        raise ValueError("Set four increasing pre_filt corners below Nyquist.")
    if fmax is None:
        fmax = min(150.0, pre_filt[2])
    if not pre_filt[1] <= fmin < fmax <= pre_filt[2]:
        raise ValueError("Set fmin and fmax inside the response filter passband.")
    if np.ma.is_masked(trace.data) or not np.isfinite(trace.data).all():
        raise ValueError("Select a finite, gap-free waveform interval.")
    if len(trace.data) < 2 or (nperseg is not None and nperseg < 2):
        raise ValueError("Welch PSD needs at least two samples per segment.")

    trace.remove_response(inventory=inventory, pre_filt=pre_filt, output="VEL")

    # Use 60 seconds by default. Cap the segment before deriving its overlap.
    nperseg = min(nperseg if nperseg is not None else max(2, round(60 * fs)), len(trace.data))
    if noverlap is not None and not 0 <= noverlap < nperseg:
        raise ValueError("noverlap must be smaller than the effective segment length.")
    hz, power = welch(
        trace.data, fs=fs, window=window, nperseg=nperseg, noverlap=noverlap,
        detrend="constant", return_onesided=True, scaling=scaling,
    )
    band = (hz >= fmin) & (hz <= fmax)
    with np.errstate(divide="ignore"):  # Zero power is -inf dB.
        return hz[band], 10 * np.log10(power[band])
