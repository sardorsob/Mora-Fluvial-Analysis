from project_paths import method_path, result_path
import obspy
from obspy import read, UTCDateTime
from obspy.io.xseed import Parser
from obspy.signal import PPSD
import numpy as np
import matplotlib.pyplot as plt
from obspy.imaging.cm import pqlx
import os
from obspy.clients.fdsn import Client
from obspy.clients import fdsn
from fractions import Fraction
from fluvial_seismology.scripts.processing import waveform_utils as waveformUtils
from fluvial_seismology.scripts.processing import download_waveforms as getData
from fluvial_seismology.scripts.processing import plot_ppsd as PPSD
from fluvial_seismology.scripts.processing import plot_spectrograms as spectraPlay
from fluvial_seismology.scripts.processing import set_workdir as set_workdir
import importlib
# Reload helpers so screening uses edits made during an interactive session.
importlib.reload(waveformUtils)
importlib.reload(getData)
importlib.reload(PPSD)
importlib.reload(spectraPlay)
importlib.reload(set_workdir)


def process_data(start_date, end_date, delta, stas):
    """Download missing waveforms and inspect spectra for each interval."""

    station_id = stas[0]
    network, station, location, channel = station_id.split('.')
    print(f"Station: {station_id}")

    # define path where .mseed files are stored
    if network == "ZE":
        path = method_path('fluvial_seismology', f'data/raw/seismic_data/NO{station}/{channel}')
    elif network == "ZD":
        path = method_path('fluvial_seismology', f'data/raw/infrasound_data/{station}')
    else:
        raise ValueError(f"Unknown network code: {network}")

    # check if the path exists, create if not
    if not os.path.exists(path):
        print(f"Path '{path}' does not exist. Creating directory...")
        os.makedirs(path, exist_ok=True)
    else:
        print(f"Path '{path}' already exists.")

    file_pattern = f'{path}/{network}.{station}.{location}.{channel}*.mseed'

    current_date = start_date

    while current_date < end_date:
        t1 = current_date
        t2 = current_date + delta # the next day
        print(f"\nProcessing data for {t1} to {t2}")

        try:

            # Use the downloader's working directory for its local file check.
            set_workdir.set_workdir('download_waveforms.py')

            print(f"Checking if any missing data for {t1} to {t2}, downloading if necessary.")
            getData.get_iris_data(t1, t2, stas, path)

            daily_stream = obspy.read(file_pattern, starttime=t1, endtime=t2)

            spectrogram_stream = daily_stream.copy()  # Keep the PPSD stream limited to the requested interval.

            # Read six extra minutes for spectral windows near the end.
            spectrogram_end = t2 + (6*60)
            try:
                set_workdir.set_workdir('download_waveforms.py')

                print(f"Checking if any missing data for {t2} to {spectrogram_end}, downloading if necessary.")
                getData.get_iris_data(t2, spectrogram_end, stas, path)

                extension_stream = obspy.read(file_pattern, starttime=t2, endtime=spectrogram_end)
                if network == "ZE" and extension_stream[0].stats.sampling_rate != 350:
                    extension_stream.resample(350)
                elif network == "ZD" and extension_stream[0].stats.sampling_rate != 100:
                    extension_stream.resample(100)
                else:
                    pass

                spectrogram_stream.extend(extension_stream)
                spectrogram_stream.merge(method=1) # avoid duplicates

            except Exception as e:
                print(f"An error occurred while processing data from {t2} to {spectrogram_end}: {e}")

            print("Making spectrogram")

            set_workdir.set_workdir('plot_spectrograms.py')
            f1 = spectraPlay.plot_spectrogram(spectrogram_stream, t1, spectrogram_end, stas)

            # Choose temporal-plot frequencies after inspecting the spectrogram.
            print("Enter frequency values for temporal plot (comma-separated, takes in fractions and decimals):")
            user_inputs = input("Example (0.5, 50, 1/100) : ").split(',')

            user_freqs = []
            #user_periods = []
            for freq in user_inputs:
                try:
                    freq = freq.strip()
                    if '/' in freq:
                        user_freqs.append(float(Fraction(freq)))
                    else:
                        user_freqs.append(float(freq))
                except ValueError:
                    print(f"Invalid input: {freq} Using default values.")

            if not user_freqs:
                print("No valid input detected. Using default frequency values.")
                user_freqs = [120, 70, 20] # default frequencies in Hz
            user_periods = [1 / freq for freq in user_freqs] # converts to periods for temporal plot

            print("Making PPSD and Temporal Plots")
            set_workdir.set_workdir('plot_ppsd.py')
            PPSD.plot_ppsd(daily_stream, t1, t2, stas, user_periods)

            round_periods = ['%.4f' % per for per in user_periods]
            print(f"Inputted frequencies: {user_freqs} --> periods: {round_periods}") # for checking
            # print(user_values) # for checking

        except Exception as e:
            print(f"An error occurred while processing data from {t1} to {t2}: {e}")

        current_date += delta # move to next day

if __name__ == "__main__":
    # Example interval and station for standalone use.
    start_date = UTCDateTime(2023, 8, 17) # Start time
    end_date = UTCDateTime(2023, 8, 18) # End time
    delta = 86400  # 1 day in seconds
    stas = [2301, 2302, 2303, 2304, 2305, 2306, 2307, 2308, 2309, 2310, 2311, 2312, 2313, 2314, 2315, 2316,
            'G2301', 'G2302', 'G2303', 'G2304', 'G2305', 'G2306', 'G2307', 'G2308', 'G2309', 'G2310', 'G2311',
            'G2312', 'G2313', 'G2314', 'G2315', 'G2316']
    stas = ['ZE.2306..GPZ'] # station IDs
    #stas = ['ZD.G2312.01.HDF'] # GEM station IDs

    # call function
    process_data(start_date, end_date, delta, stas)
    print(f"Analysis for {stas} from {start_date} to {end_date} complete.")


# run in jupyter by: %run screen_waveforms.py
# or run in terminal by: python screen_waveforms.py
