import numpy as np
import obspy.signal.filter as filter
import time
import matplotlib.pyplot as plt
from numpy import median
import numpy.ma as ma
import matplotlib.dates as mdates
from obspy import UTCDateTime


def medianFilter(trace, windowLength):
    """Replace trace samples with medians from nonoverlapping windows."""
    window_medians = np.array([])
    for trace_window in trace.slide(window_length=windowLength, step=windowLength):
        window_medians = np.append(window_medians, np.median(trace_window.data))
    trace.data = window_medians
    trace.stats.sampling_rate = 1.0 / windowLength
    trace.stats.delta = float(windowLength)
    trace.stats.npts = len(window_medians)
    trace.verify()


def saraCalc(trace, windowLength, decimate=False, decFactor=4, envelope=True):
    '''
    Compute a median amplitude series in place using a method similar to Taisne (2011).

    :param trace: obspy Trace
    :param windowLength: length of median window in seconds
    :param decimate: boolean value on whether to decimate the trace first (suggested for long traces)
    :param decFactor: integer decimation factor
    :param envelope: boolean value on whether to take the envelope
    :return:
    '''

    # Decimate
    if decimate:
        #print('Decimating...')
        trace.decimate(decFactor)
        #print('Done decimating...')
    # Envelope
    if envelope:
        ticenv = time.perf_counter()
        data_envelope = filter.envelope(trace.data)
        trace.data = data_envelope
        tocenv = time.perf_counter()
        #print('Envelope Elapsed Time %0.2f s' % (tocenv - ticenv,))

    # Median filter
    ticmin = time.perf_counter()
    medianFilter(trace, windowLength)
    tocmin = time.perf_counter()
    #print('Median Elapsed Time %0.2f s' % (tocmin - ticmin,))

def calcNoise(S, startTime, endTime, snRatio):
    '''
    Mask values at or below the median noise times the signal-to-noise threshold.
    :param S: Stream of data of interest
    :param startTime: noise start time (UTCDateTime)
    :param endTime: noise end time (UTCDateTime)
    :param snRatio: signal to noise ratio
    :return: masked stream and per-trace amplitude thresholds keyed by trace ID
    '''
    noise_stream = S.copy().slice(starttime=startTime, endtime=endTime)
    noise_thresholds = dict()
    for tr in noise_stream:
        noise_thresholds[tr.id] = (median(tr.data) * snRatio)
    masked_stream = S.copy()
    for tr in masked_stream:
        try:
            tr.data = ma.masked_less_equal(tr, noise_thresholds[tr.id])
        except:
            print('{} has no data in the given noise window!'.format(tr.id))

    return masked_stream, noise_thresholds

def plotMedian(S, ax=None, normalize=True):

    if not ax:
        f = plt.figure(figsize=[15,8])
        ax = f.add_subplot()
    for tr in S:
        tt = tr.times(type='matplotlib')
        if normalize:
            # Plot normalized
            ax.plot(tt, np.divide(tr.data, max(tr.data)), '-', label='{} Normalized'.format(tr.stats.station))
            ax.set_ylim([0, 1.0])
        else:
            ax.plot(tt, tr.data, '-', label=tr.stats.station)
    ax.legend()
    ax.grid()
    ax.xaxis_date()
    ax.tick_params(axis='x', labelbottom='on')
    locator = mdates.AutoDateLocator(minticks=5, maxticks=10)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    return ax

def plotCumMedian(S, ax=None, normalize=True):
    if not ax:
        f = plt.figure(figsize=[15,8])
        ax = f.add_subplot()
    for tr in S:
        tt = tr.times(type='matplotlib')
        if normalize:
            cumsum = np.cumsum(tr.data)
            # Plot normalized
            ax.plot(tt, np.divide(cumsum, max(cumsum)), '-', label='{} Cumulative Normalized'.format(tr.stats.station))
            ax.set_ylim([0, 1.0])
        else:
            ax.plot(tt, np.cumsum(tr.data), '-', label=tr.stats.station)
    ax.legend()
    ax.grid()
    ax.xaxis_date()
    ax.tick_params(axis='x', labelbottom='on')
    locator = mdates.AutoDateLocator(minticks=5, maxticks=10)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    return ax

def checkDataRatio(tr1, tr2):
    """Return the shared interval if both traces have matching sample times."""
    shared_start = max(tr1.stats.starttime, tr2.stats.starttime)
    shared_end = min(tr1.stats.endtime, tr2.stats.endtime)
    if shared_start > shared_end:
        raise ValueError("Traces have no overlapping samples.")
    tr1 = tr1.slice(shared_start, shared_end)
    tr2 = tr2.slice(shared_start, shared_end)
    if (
        tr1.stats.sampling_rate != tr2.stats.sampling_rate
        or tr1.stats.starttime != tr2.stats.starttime
        or tr1.stats.npts != tr2.stats.npts
    ):
        raise ValueError("Traces must share a sample grid in the overlapping interval.")
    return tr1, tr2

def calcRatio(S, sta1, sta2, maskedStream=None):

    masked_times = []
    masked_ratio = []
    # Divide the first station's amplitude by the second station's amplitude.
    tr1 = S.select(station=sta1)[0]
    tr2 = S.select(station=sta2)[0]
    tr1, tr2 = checkDataRatio(tr1, tr2)
    data1 = tr1.data
    data2 = tr2.data
    raw_times = tr1.times(type="matplotlib")
    raw_ratio = np.divide(data1, data2)
    if maskedStream:
        ntr1 = maskedStream.select(station=sta1)[0]
        ntr2 = maskedStream.select(station=sta2)[0]
        ntr1, ntr2 = checkDataRatio(ntr1, ntr2)
        noise1 = ntr1.data
        noise2 = ntr2.data
        masked_times = ntr1.times(type="matplotlib")
        if noise1.size > 0 and noise2.size > 0:
            masked_ratio = np.divide(noise1, noise2)

    return raw_times, raw_ratio, masked_times, masked_ratio


def plotRatio(S, sta1, sta2, ax=None, maskedStream=None, symbol='-', returnRatio=False):

    buffer = 0.1
    if not ax:
        f = plt.figure(figsize=[15,8])
        ax = f.add_subplot()
    raw_times, raw_ratio, masked_times, masked_ratio = calcRatio(S, sta1, sta2, maskedStream=maskedStream)
    ax.semilogy(raw_times, raw_ratio, symbol, color='gray', label='%s/%s Raw Ratio' % (sta1, sta2))
    if maskedStream:
        try:
            ax.semilogy(masked_times, masked_ratio, symbol, color='black', label='%s/%s Good SNR Ratio' % (sta1, sta2))
            ax.set_ylim([ma.MaskedArray.min(masked_ratio), ma.MaskedArray.max(masked_ratio)])
        except:
            print('No masked ratio values to plot. Using the raw ratio limits.')
            ax.set_ylim([min(raw_ratio), max(raw_ratio)])
    else:
        ax.set_ylim([min(raw_ratio), max(raw_ratio)])

    ax.xaxis_date()
    ax.tick_params(axis='x', labelbottom='on')
    locator = mdates.AutoDateLocator(minticks=5, maxticks=10)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    ax.legend()
    ax.grid(which='both')
    if returnRatio:
        return ax, raw_times, raw_ratio, masked_times, masked_ratio
    else:
        return ax


def plotRatioMedian(S, sta1, sta2, plotStart=None, plotEnd=None, maskedStream=None, normalize=True, symbol='-'):

    f = plt.figure(figsize=[15, 8])
    ax = f.add_subplot(211)
    if maskedStream:
        ax, tt1, rat, tt2, ratNoise = plotRatio(S, sta1, sta2, ax=ax, maskedStream=maskedStream,
                       returnRatio=True, symbol=symbol)
    else:
        ax, tt1, rat, tt2, ratNoise = plotRatio(S, sta1, sta2, ax=ax, maskedStream=None,
                       returnRatio=True, symbol=symbol)

    ax2 = f.add_subplot(212, sharex=ax)
    Splot = S.select(station=sta1)
    Splot += S.select(station=sta2)
    ax2 = plotMedian(Splot, ax=ax2, normalize=normalize)
    if not plotStart:
        plotStart = min(tt1)
    else:
        plotStart = plotStart.matplotlib_date
    if not plotEnd:
        plotEnd = max(tt1)
    else:
        plotEnd = plotEnd.matplotlib_date
    ax.set_xlim([plotStart, plotEnd])
    return f, ax, ax2
