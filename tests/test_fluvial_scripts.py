"""Regression checks for the seismic scripts' optional ObsPy workflow."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

try:
    from obspy import Stream, Trace, UTCDateTime, read
except ModuleNotFoundError as error:
    if error.name != "obspy":
        raise
    HAVE_OBSPY = False
else:
    HAVE_OBSPY = True


def make_trace(seconds=8, rate=100, station="TEST", start=0):
    t = np.arange(round(seconds * rate) + 1) / rate
    return Trace(
        np.sin(2 * np.pi * 8 * t).astype(np.float64),
        {"network": "ZE", "station": station, "channel": "GPZ",
         "sampling_rate": rate, "starttime": UTCDateTime(start)},
    )


@unittest.skipUnless(HAVE_OBSPY, "ObsPy is required for seismic tests")
class SeismicScriptTests(unittest.TestCase):
    def setUp(self):
        import matplotlib

        matplotlib.use("Agg")

    def tearDown(self):
        from matplotlib import pyplot as plt

        plt.close("all")

    def test_download_requests_each_station_and_stops_at_requested_end(self):
        from fluvial_seismology.scripts.processing import download_waveforms as downloader

        start = UTCDateTime(0)
        end = start + 20
        stations = ["ZE.LEFT..GPZ", "ZE.RIGHT..GPZ"]
        requests = []

        class FakeClient:
            def __init__(self, **kwargs):
                pass

            def get_waveforms(self, network, station, location, channel, t1, t2):
                requests.append((network, station, location, channel, t1, t2))
                return Stream([make_trace(seconds=t2 - t1, station=station, start=t1)])

        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            # A failed prior write must not prevent the next station from being downloaded.
            (Path(tmp) / "ZE.LEFT..GPZ_19700101000000.mseed").touch()
            with patch.object(downloader.fdsn.client, "Client", FakeClient), patch.dict("os.environ", {}, clear=True):
                downloader.get_iris_data(start, end, stations, tmp)
                downloader.get_iris_data(start, end, stations, tmp)
            self.assertEqual(requests, [
                ("ZE", "LEFT", "", "GPZ", start, end),
                ("ZE", "RIGHT", "", "GPZ", start, end),
            ])
            self.assertEqual({read(str(file))[0].id for file in Path(tmp).glob("*.mseed")}, set(stations))

    def test_calibration_impact_window_uses_node_from_trace(self):
        from fluvial_seismology.scripts.processing import plot_calibration_signals as calib

        trace = make_trace(station="C2510")
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            with patch("matplotlib.figure.Figure.savefig") as save:
                calib.impact_window(trace, trace.stats.starttime, 1, 3, 100, tmp, trace.id)
            destinations = [Path(call.args[0]) for call in save.call_args_list]
            self.assertEqual(len(destinations), 2)
            self.assertTrue(all(path.parent.parent.name == "2510" for path in destinations))

    def test_single_fft_window_returns_frequency_aligned_magnitudes(self):
        from fluvial_seismology.scripts.processing import waveform_utils as waveform

        trace = make_trace(seconds=4)
        frequencies, magnitude = waveform.stackSpectraContinuous(
            Stream([trace]), window_length=4, step=2,
        )
        expected = np.abs(np.fft.rfft(trace.data))
        self.assertEqual(magnitude.shape, frequencies.shape)
        np.testing.assert_allclose(magnitude, expected)

    def test_multiday_spectrogram_with_low_band_and_no_envelope(self):
        from fluvial_seismology.scripts.processing import waveform_utils as waveform

        trace = make_trace(seconds=12)
        figure = waveform.multiDaySpectrogram(
            Stream([trace]), averageLength=10, fftLength=4,
            minFreq=0.2, maxFreq=25, plotAverage=False,
        )
        figure.canvas.draw()
        frequency_axes = [ax for ax in figure.axes if ax.get_ylabel() == "Frequency, Hz"]
        self.assertEqual(len(frequency_axes), 2)

    def test_multiday_spectrogram_skips_tail_shorter_than_one_fft(self):
        from fluvial_seismology.scripts.processing import waveform_utils as waveform

        trace = make_trace(seconds=12)
        figure = waveform.multiDaySpectrogram(
            Stream([trace]), averageLength=20, fftLength=12,
            minFreq=0.5, maxFreq=25, plotAverage=False,
        )
        figure.canvas.draw()
        frequency_axes = [ax for ax in figure.axes if ax.get_ylabel() == "Frequency, Hz"]
        self.assertEqual(len(frequency_axes), 1)
        mesh = frequency_axes[0].collections[0]
        times = mesh.get_coordinates()[0, :, 0]
        self.assertEqual(len(times), 2)
        self.assertAlmostEqual((times[1] - times[0]) * 86400, 12)

    def test_waveform_spectrogram_returns_figure_and_axes(self):
        from fluvial_seismology.scripts.processing import waveform_utils as waveform

        trace = make_trace(seconds=10)
        figure, axis_waveform, axis_spectrum = waveform.plotSpectrogram(Stream([trace]))
        self.assertIs(axis_waveform.figure, figure)
        self.assertIs(axis_spectrum.figure, figure)
        self.assertEqual(len(axis_spectrum.images), 1)

    def test_spectra_time_returns_numeric_rsam_values(self):
        from fluvial_seismology.scripts.processing import waveform_utils as waveform

        trace = make_trace(seconds=122)
        figure, _, _, _, times, rsam = waveform.plotSpectraTime(
            Stream([trace]), winlength=60, step=60, specWin=4, specStep=2, rsamWin=0.5,
        )
        figure.canvas.draw()
        self.assertEqual(len(times), len(rsam))
        self.assertTrue(np.isfinite(rsam).all())
        self.assertEqual(times[:2], [trace.stats.starttime, trace.stats.starttime + 30])

    def test_clipped_waveform_is_masked(self):
        from fluvial_seismology.scripts.processing import waveform_utils as waveform

        trace = Trace(
            np.array([0, 2300, 0, -2300, 0], dtype=float),
            {"network": "UW", "station": "TEST", "channel": "EHZ"},
        )
        result = waveform.applyClipMask(Stream([trace]))
        np.testing.assert_array_equal(np.ma.getmaskarray(result[0].data), [0, 1, 1, 1, 0])
        self.assertFalse(np.ma.is_masked(trace.data))

    def test_alignment_rejects_wrong_pick_or_shift_count(self):
        from fluvial_seismology.scripts.processing import waveform_utils as waveform

        stream = Stream([make_trace(station="A"), make_trace(station="B")])
        for keyword, values in (("picks", [UTCDateTime(1)]), ("shifts", [1])):
            with self.subTest(keyword=keyword), self.assertRaisesRegex(ValueError, keyword):
                waveform.plotRelativeAlign(stream, **{keyword: values})

    def test_particle_motion_uses_one_normalization_across_components(self):
        from matplotlib import pyplot as plt
        from fluvial_seismology.scripts.processing import waveform_utils as waveform

        vertical = make_trace()
        north = vertical.copy()
        east = vertical.copy()
        north.data *= 2
        east.data *= 4
        waveform.plotParticleMotion(Stream([vertical]), Stream([north]), Stream([east]))
        axes = plt.gcf().axes
        self.assertEqual(len(axes), 4)
        self.assertAlmostEqual(np.max(axes[0].lines[0].get_ydata()), 0.25)
        self.assertAlmostEqual(np.max(axes[1].lines[0].get_ydata()), 0.5)
        self.assertGreater(np.max(east.data), 3)

    def test_dead_analog_filter_checks_adjacent_traces(self):
        from fluvial_seismology.scripts.processing import waveform_utils as waveform

        stream = Stream([make_trace(station="A"), make_trace(station="B"), make_trace(station="C")])
        stream[2].data *= 100
        with contextlib.redirect_stdout(io.StringIO()):
            result = waveform.detectDeadAnalog(stream)
        self.assertEqual([trace.stats.station for trace in result], ["C"])
        self.assertEqual(len(stream), 3)

    def test_ratio_rejects_equal_length_traces_on_different_sample_grids(self):
        from fluvial_seismology.scripts.processing import seismic_amplitude_ratios as ratio

        trace_a = make_trace(seconds=8, station="A")
        trace_b = make_trace(seconds=8, station="B", start=0.002)
        with self.assertRaisesRegex(ValueError, "sample grid"):
            ratio.calcRatio(Stream([trace_a, trace_b]), "A", "B")

    def test_autoregressive_fallback_is_finite_for_narrowband_signal(self):
        from fluvial_seismology.scripts.processing import signal_spectrum as spectra

        if not spectra._HAVE_STATSMODELS:
            self.skipTest("statsmodels is required for Yule-Walker")
        t = np.arange(12001) / 100
        noise = np.random.default_rng(42).normal(0, 0.1, t.size)
        data = 800 * np.sin(2 * np.pi * 8 * t) + np.sin(2 * np.pi * 17 * t) + noise
        with patch.object(spectra, "_HAVE_SPECTRUM", False):
            result = spectra.signal_spectrum(data, dt=0.01, method="autoregressive")
        self.assertTrue(np.isfinite(result["power"]).all())
        self.assertAlmostEqual(result["frequency"][np.argmax(result["power"])], 8, places=1)
