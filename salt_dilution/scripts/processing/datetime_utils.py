# other functions that might be useful
import csv
import glob
from collections import defaultdict
import os
from datetime import datetime, time

# newer version - returns dict
def get_file_paths(path: str, search_key: str, recursive: bool = False) -> dict:
    """
    Retrieves a dictionary mapping subdirectories to lists of matching file paths.

    Args:
        path (str): The base directory path to search in.
        search_key (str): The pattern to match files (e.g., '*.xlsx' or '*.csv').
        recursive (bool): Whether to search recursively in subdirectories.

    Returns:
        dict: Keys are subdirectory names (relative to path), values are lists of absolute file paths.
    """
    if not os.path.isdir(path):
        raise NotADirectoryError(f"The path {path} is not a valid directory.")

    file_dict = defaultdict(list)

    # Construct the glob pattern
    pattern = os.path.join(path, "**", search_key) if recursive else os.path.join(path, search_key)

    for file_path in glob.glob(pattern, recursive=recursive):
        if os.path.isfile(file_path):
            abs_path = os.path.abspath(file_path)
            # Get relative subdirectory name; '.' for base dir
            subdir = os.path.relpath(os.path.dirname(file_path), path)
            file_dict[subdir].append(abs_path)

    return dict(file_dict)

def extract_times_from_csv(csv_path, datetime_column):
    """
    Reads a CSV file and extracts time components from a datetime column.

    Parameters:
        csv_path (str): Path to the CSV file.
        datetime_column (str): Name of the column containing datetime strings.

    Returns:
        list of datetime.time: List of time objects extracted from the datetime column.
    """
    times = []

    with open(csv_path, 'r', newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            dt_str = row[datetime_column]
            time_obj = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").time()
            times.append(time_obj)

    return times

def compute_time_differences_in_seconds(time_list):
    """
    Computes the difference in seconds between consecutive time values.

    Parameters:
        time_list (list of datetime.time): The list of time values.

    Returns:
        list of float: Time differences in seconds between consecutive entries.
    """
    diffs = []
    cumulative = [0.0]
    for i in range(1, len(time_list)):
        t1 = datetime.combine(datetime.min, time_list[i - 1])
        t2 = datetime.combine(datetime.min, time_list[i])
        delta_seconds = (t2 - t1).total_seconds()
        diffs.append(delta_seconds)
        cumulative.append(cumulative[-1] + delta_seconds)

    return diffs, cumulative

# my version
def get_ec_values(start_time:time,end_time:time,data:dict):
    #target_time = time(14, 50, 33)

    # check if it's in the list
    if start_time in data['Date Time']:
        start_index = data['Date Time'].index(start_time)
    if end_time in data['Date Time']:
        end_index = data['Date Time'].index(end_time)

        #msnt_time = sum(time_diffs[start_index:])
        ec_bg = data['Actual Conductivity (µS/cm) (790478)'][:start_index,end_index:]
        trail_data = data['Actual Conductivity (µS/cm) (790478)'][start_index:end_index]
        print(f"selecting {len(trail_data)} EC values beginning at {data['Date Time'][start_index]} to {data['Date Time'][end_index]}")
    else:
        print("Not found")
    return ec_bg, trail_data
# target time as a time object
# 14:50:33
# improved by co-pilot
def get_measurement_time_values(start_time_str:str, end_time_str:str, data:dict, show_data=True):
    start_time = datetime.strptime(start_time_str, "%H:%M:%S").time()
    end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()
    """ Keeping this here in case in doesn't work in dilutionUtils."""
    if start_time in data['Date Time']:
        start_index = data['Date Time'].index(start_time)
    else:
        print(f"Start time {start_time} not found.")
        return None, None, None
    if end_time in data['Date Time']:
        end_index = data['Date Time'].index(end_time)
        ec_bg = data['Actual Conductivity (µS/cm) (790478)'][:start_index]
        ec_data = data['Actual Conductivity (µS/cm) (790478)'][start_index:end_index]
        time_list = data['Date Time'][start_index:end_index]
    else:
        print(f"End time {end_time} not found.")
        return None, None, None
    if show_data==False:
        print(f"selecting {len(ec_data)} EC values beginning at {data['Date Time'][start_index]} to {data['Date Time'][end_index]}")
    else:
        return ec_bg, ec_data, time_list
