from project_paths import method_path, result_path
import obspy
from obspy import read, UTCDateTime
from obspy.clients import fdsn
from obspy.io.mseed import ObsPyMSEEDError
import os


def get_iris_data(t1, t2, stas, path):
    """Download missing miniSEED windows from IRIS."""

    if not os.path.exists(path):
        print(f"Path '{path}' does not exist. Creating directory...")
        os.makedirs(path, exist_ok=True)
    else:
        print(f"Path '{path}' already exists.")

    archives = {
        "ZE": ("http://service.iris.edu/ph5ws/dataselect/1", 350),
        "ZD": ("http://service.iris.edu/fdsnws/dataselect/1", 100),
    }
    station_codes = [station_id.split('.') for station_id in stas]

    # IRIS credentials
    username = os.environ.get("MORA_IRIS_USERNAME")
    password = os.environ.get("MORA_IRIS_PASSWORD")
    if bool(username) != bool(password):
        raise ValueError("Set both MORA_IRIS_USERNAME and MORA_IRIS_PASSWORD, or neither.")
    clients = {}
    for network, _, _, _ in station_codes:
        if network not in archives:
            raise ValueError(f"Unknown network code: {network}")
        if network not in clients:
            url, _ = archives[network]
            client = fdsn.client.Client(service_mappings={'dataselect': url})
            if username:
                client.set_credentials(username, password)
            clients[network] = client

    window_start = t1
    extract_delta = 1800  # Download in 30-minute windows.

    while window_start < t2:
        window_end = min(window_start + extract_delta, t2)
        for network, station, location, channel in station_codes:
            station_id = '.'.join((network, station, location, channel))
            print(f"Checking data for station {station_id} from {window_start} to {window_end}")
            cached_path = os.path.join(path, f'{station_id}_{window_start.strftime("%Y%m%d%H%M%S")}.mseed')
            cached = ()
            if os.path.isfile(cached_path):
                try:
                    cached = read(cached_path, format="MSEED", headonly=True)
                except (OSError, ObsPyMSEEDError) as error:
                    print(f"Could not read cached waveform {cached_path}: {error}")
            if any(
                tr.id == station_id
                and tr.stats.starttime <= window_start + tr.stats.delta
                and tr.stats.endtime >= window_end - tr.stats.delta
                for tr in cached
            ):
                print(f"Data for {station_id} from {window_start} to {window_end} already stored locally. Skipping download.")
                continue
            print(f"Retrieving data for {station_id} from {window_start} to {window_end}")
            try:
                stream = clients[network].get_waveforms(network, station, location, channel, window_start, window_end)
                print(f"Data for {station_id} retrieved successfully.")

                _, target_rate = archives[network]
                print(f'Resampling to {target_rate}')
                stream.resample(target_rate)

                print('Saving data to .mseed files...')
                for tr in stream:
                    filename = os.path.join(path, f'{tr.id}_{tr.stats.starttime.strftime("%Y%m%d%H%M%S")}.mseed')
                    tr.write(filename)
                    print(f"Saved {filename}")
            except Exception as e:
                print(f"Error retrieving data for {station_id} from {window_start} to {window_end}: {e}")

        window_start = window_end

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
