from project_paths import method_path, result_path
import obspy
from obspy import read, UTCDateTime
from obspy.clients import fdsn
import os


def get_iris_data(t1, t2, stas, path):
    """Download missing miniSEED windows from IRIS."""

    if not os.path.exists(path):
        print(f"Path '{path}' does not exist. Creating directory...")
        os.makedirs(path, exist_ok=True)
    else:
        print(f"Path '{path}' already exists.")

    # The first station ID selects the archive service and waveform codes.
    station_id = stas[0]
    network, station, location, channel = station_id.split('.')
    print(f"Station: {station_id}")
    file_pattern = f'{path}/{network}.{station}.{location}.{channel}*.mseed'

    if network == "ZE":  # PH5 archive for the three-component nodes.
        dataselect_url = 'http://service.iris.edu/ph5ws/dataselect/1'
        client = fdsn.client.Client(
            service_mappings={
                'dataselect': dataselect_url,
            },
        )
    elif network == "ZD":  # miniSEED archive for GEM and RT130 instruments.
        dataselect_url = 'http://service.iris.edu/fdsnws/dataselect/1'
        client = fdsn.client.Client(
            service_mappings={
                'dataselect': dataselect_url,
            },
        )
    else:
        raise ValueError(f"Unknown network code: {network}")

    # IRIS credentials
    username = os.environ.get("MORA_IRIS_USERNAME")
    password = os.environ.get("MORA_IRIS_PASSWORD")
    if bool(username) != bool(password):
        raise ValueError("Set both MORA_IRIS_USERNAME and MORA_IRIS_PASSWORD, or neither.")
    if username:
        client.set_credentials(username, password)
    window_start = t1
    extract_delta = 1800  # Download in 30-minute windows.

    while window_start < t2:
        for station_id in stas:
            print(f"Checking data for station {station_id} from {window_start} to {window_start + extract_delta}")

            existing_files = [f for f in os.listdir(path) if f.endswith('.mseed')]

            filename_pattern = f'{network}.{station}.{location}.{channel}_{window_start.strftime("%Y%m%d%H%M%S")}.mseed'

            file_exists = False
            for filename in existing_files:
                if filename_pattern in filename:
                    file_exists = True
                    break

            if file_exists:
                print(f"Data for {station_id} from {window_start} to {window_start + extract_delta} already stored locally. Skipping download.")
            else:
                print(f"Retrieving data for {station_id} from {window_start} to {window_start + extract_delta}")
                try:
                    stream = client.get_waveforms(network, station, location, channel, window_start, window_start + extract_delta)
                    print(f"Data for {station_id} retrieved successfully.")

                    if network == "ZE":
                        print('Resampling to 350')
                        stream.resample(350)  # Three-component node rate in Hz.
                    if network == "ZD":
                        print('Resampling to 100')
                        stream.resample(100)  # GEM rate in Hz.

                    print('Saving data to .mseed files...')
                    for tr in stream:
                        filename = os.path.join(path, f'{tr.id}_{tr.stats.starttime.strftime("%Y%m%d%H%M%S")}.mseed')
                        tr.write(filename)
                        print(f"Saved {filename}")
                except Exception as e:
                    print(f"Error retrieving data for {station_id} from {window_start} to {window_start + extract_delta}: {e}")

        window_start += extract_delta

    print('Data retrieval and saving completed.')


if __name__ == "__main__":
    # Example interval and station for standalone use.
    start_date = UTCDateTime(2024, 8, 8) # Start time
    end_date = UTCDateTime(2024, 8, 12) # End time
    stas = [2301, 2302, 2303, 2304, 2305, 2306, 2307, 2308, 2309, 2310, 2311, 2312, 2313, 2314, 2315, 2316,
            'G2301', 'G2302', 'G2303', 'G2304', 'G2305', 'G2306', 'G2307', 'G2308', 'G2309', 'G2310', 'G2311',
            'G2312', 'G2313', 'G2314', 'G2315', 'G2316']
    stas = ['ZE.2411..GPZ'] # 3C station ID
    #stas = ['ZD.G2310.01.HDF'] # GEM station ID
    nowsta = stas[0]
    network, station, location, channel = nowsta.split('.')

    # define path where .mseed files are stored
    if network == "ZE":
        path = method_path('fluvial_seismology', f'data/raw/seismic_data/NO{station}/{channel}')
    elif network == "ZD":
        path = method_path('fluvial_seismology', f'data/raw/infrasound_data/{station}')
    else:
        raise ValueError(f"Unknown network code: {network}")

    get_iris_data(t1=start_date, t2=end_date, stas=stas, path=path)

# run in jupyter by: %run download_waveforms.py
# or run in terminal by: python download_waveforms.py
