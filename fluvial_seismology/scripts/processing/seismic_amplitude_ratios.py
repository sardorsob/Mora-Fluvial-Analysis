import numpy as np
import obspy.signal.filter as filter
import time
import matplotlib.pyplot as plt
from numpy import median
import numpy.ma as ma
import matplotlib.dates as mdates
from obspy import UTCDateTime


def medianFilter(trace, windowLength):
    datamin = np.array([])
    for windata in trace.slide(window_length=windowLength, step=windowLength):
        datamin = np.append(datamin, np.median(windata.data))
    trace.data = datamin
    trace.stats.sampling_rate = 1.0 / windowLength
    trace.stats.delta = float(windowLength)
    trace.stats.npts = len(datamin)
    trace.verify()


def saraCalc(trace, windowLength, decimate=False, decFactor=4, envelope=True):
    '''
    Function to calculate the median amplitude of a trace similar to Taisne (2011). Data is changed in place, so the
    original data is gone.

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
    Generate masked Stream given a noise window and signal to noise ratio
    :param S: Stream of data of interest
    :param startTime: noise start time (UTCDateTime)
    :param endTime: noise end time (UTCDateTime)
    :param snRatio: signal to noise ratio
    :return: masked Stream, dictionary of snRatios with keys of tr.id
    '''
    Snoise = S.copy().slice(starttime=startTime, endtime=endTime)
    sn = dict()
    for tr in Snoise:
        sn[tr.id] = (median(tr.data) * snRatio)
    SS = S.copy()
    for tr in SS:
        try:
            tr.data = ma.masked_less_equal(tr, sn[tr.id])
        except:
            print('{} has no data in the given noise window!'.format(tr.id))

    return SS, sn

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

    diff = False
    # Check starttime
    newStart = None
    if tr1.stats.starttime != tr2.stats.starttime:
        diff = True
        newStart = max([tr1.stats.starttime, tr2.stats.starttime])
    else:
        newStart = tr1.stats.starttime

    newEnd = None
    if tr1.stats.endtime != tr2.stats.endtime:
        diff = True
        newEnd = min([tr1.stats.endtime, tr2.stats.endtime])
    else:
        newEnd = tr1.stats.endtime

    if diff:
        tr1 = tr1.trim(starttime=newStart, endtime=newEnd)
        tr2 = tr2.trim(starttime=newStart, endtime=newEnd)
        diff = False

    # Check length
    if len(tr1.data) != len(tr2.data):
        diff = True
        print('Still have different length of data. Need some more work bro.')
        raise

    return tr1, tr2

def calcRatio(S, sta1, sta2, maskedStream=None):

    tt2 = []
    ratNoise = []
    # Get data from specific station
    tr1 = S.select(station=sta1)[0]
    tr2 = S.select(station=sta2)[0]
    tr1, tr2 = checkDataRatio(tr1, tr2)
    data1 = tr1.data
    data2 = tr2.data
    tt1 = tr1.times(type="matplotlib")
    rat = np.divide(data1, data2)
    if maskedStream:
        ntr1 = maskedStream.select(station=sta1)[0]
        ntr2 = maskedStream.select(station=sta2)[0]
        ntr1, ntr2 = checkDataRatio(ntr1, ntr2)
        noise1 = ntr1.data
        noise2 = ntr2.data
        tt2 = ntr1.times(type="matplotlib")
        if noise1.size > 0 and noise2.size > 0:
            ratNoise = np.divide(noise1, noise2)

    return tt1, rat, tt2, ratNoise


def plotRatio(S, sta1, sta2, ax=None, maskedStream=None, symbol='-', returnRatio=False):

    buffer = 0.1
    if not ax:
        f = plt.figure(figsize=[15,8])
        ax = f.add_subplot()
    tt1, rat, tt2, ratNoise = calcRatio(S, sta1, sta2, maskedStream=maskedStream)
    ax.semilogy(tt1, rat, symbol, color='gray', label='%s/%s Raw Ratio' % (sta1, sta2))
    # Now plot
    if maskedStream:
        try:
            ax.semilogy(tt2, ratNoise, symbol, color='black', label='%s/%s Good SNR Ratio' % (sta1, sta2))
            ax.set_ylim([ma.MaskedArray.min(ratNoise), ma.MaskedArray.max(ratNoise)])
        except:
            print('No noise data...nice try.')
            ax.set_ylim([min(rat), max(rat)])
    else:
        ax.set_ylim([min(rat), max(rat)])

    ax.xaxis_date()
    ax.tick_params(axis='x', labelbottom='on')
    locator = mdates.AutoDateLocator(minticks=5, maxticks=10)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    ax.legend()
    ax.grid(which='both')
    if returnRatio:
        return ax, tt1, rat, tt2, ratNoise
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
