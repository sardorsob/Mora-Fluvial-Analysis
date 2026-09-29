from pathlib import Path
import csv
import configparser
from datetime import datetime, time
import glob
import os
from typing import Dict, List, Tuple, Union, Any

import numpy as np
from matplotlib import pyplot as plt
from scipy import stats

def load_config(path: str) -> Tuple[Dict[str, str], Dict[str, Any], Dict[str, int]]:
    """ instantiate the dil_config.ini file and read in the parameters to a dictionary"""
    config = configparser.ConfigParser()
    config.read(path)
    file_dict = {
        "data_folder": config["file_operations"]["folder_path"],
        "search_string": config["file_operations"]["injection_data"],
        "calibration_file": config["file_operations"]["calibration_csv_name"]
    }
    injection_dict = {
        "injection_volume": int(config["injection"]["volume_primary_solution"]),
        "mass_salt": int(config["injection"]["mass_salt"]),
        "bg_start":config["injection"]["bg_start"],
        "bg_end":config["injection"]["bg_end"],
        "trial_start":config["injection"]["trial_start"],
        "trial_end":config["injection"]["trial_end"],
        "record_end":config["injection"]["record_end"]
    }
    calibration_dict = {
        "initial_volume_secondary": config["calibration"]["volume_secondary_solution"],
        "volume_injection_solution sample": config["calibration"]["volume_injection_solution_sample"],
        "initial_volume_calibration": None,
        "Addition_of_secondary": None
    }
    config_dir = Path(path).expanduser().resolve().parent
    for key in ("data_folder", "calibration_file"):
        file_dict[key] = str((config_dir / file_dict[key]).resolve())
    return file_dict, injection_dict, calibration_dict

def get_file_paths(path:str, search_key:str) -> list:
    """"
    Retrieves a sorted list of file paths from a specified directory based on a search key.
    Args:
        path (str): The directory path to search in.
        search_key (str): The pattern to match files (e.g., '*.xlsx' or '*.csv').
    Returns:
        list: A sorted list of file paths that match the search key.
    """
    if not os.path.isdir(path):
        """
        Raises an exception if the provided path is not a valid directory.
        """
        raise NotADirectoryError(f"The path {path} is not a valid directory.")
    base_path = path
    path_list = glob.glob(os.path.join(base_path, search_key))

    return sorted(path_list)

def read_csv(file_path: str) -> list:
    """Reads a CSV file and returns its contents as a list of dictionaries.
    Args:
        file_path (str): The path to the CSV file.
    Returns:
        list: A list of dictionaries where each dictionary represents a row in the CSV file.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)  # Reads CSV into a list of dictionaries
        return list(reader)

def extract_fields(data):
    """
    Returns a dictionary where each key is the index of the input list.

    Parameters:
        data (list of dict): The input list of dictionaries.

    Returns:
        dict: A dictionary of {field_name: [float_values]}.
    """
    def parse_value(value):
        # Try to parse as float
        try:
            return float(value)
        except (ValueError, TypeError):
            pass
        # Try to parse as datetime
        try:
            time_obj = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").time()
            time_str = time_obj.strftime("%H:%M:%S")
            return time_str
        except (ValueError, TypeError):
            pass
        # Fallback: return as-is
        return value

    if not data:
        return {}
    cal_dict = {
        key: [parse_value(d[key]) for d in data]
        for key in data[0].keys()
    }
    return cal_dict

def time_diff_sec(start:str, end:str):
    """ Calculate the diffence in seconds between two times.
        Parameters instantiated in configuration file.

        Parameters:
            start (string): "%H:%M:%S"
            end (string): "%H:%M:%S"
        Returns:
            float: difference in seconds between the inputs.
        """
    t1 = datetime.strptime(start,"%H:%M:%S")
    t2 = datetime.strptime(end,"%H:%M:%S")
    diff_seconds = (t2-t1).total_seconds()

    return int(diff_seconds)

def get_measurement_values(bg_start_time_str:str, bg_end_time_str:str, trial_start_time_str:str, trial_end_time_str:str,data:dict, show_data=True):
    """ not sure if I need this function."""
    bg_start_time = datetime.strptime(bg_start_time_str, "%H:%M:%S").time()
    bg_end_time = datetime.strptime(bg_end_time_str, "%H:%M:%S").time()

    trial_start_time = datetime.strptime(trial_start_time_str, "%H:%M:%S").time()
    trial_end_time = datetime.strptime(trial_end_time_str, "%H:%M:%S").time()

    if bg_start_time in data['Date Time']:
        bg_start_index = data['Date Time'].index(bg_start_time)
        trial_start_index = data['Date Time'].index(trial_start_time)
    else:
        print(f"Start time {bg_start_time} not found.")
        return None, None, None
    if trial_end_time in data['Date Time']:
        bg_end_index = data['Date Time'].index(bg_end_time)
        trial_end_index = data['Date Time'].index(trial_end_time)
        ec_bg = data['Actual Conductivity (µS/cm)'][bg_start_index:bg_end_index] # this is different than original field
        ec_trial = data['Actual Conductivity (µS/cm)'][trial_start_index:trial_end_index]
        bg_time = data['Date Time'][bg_start_index:bg_end_index]
        trial_time = data['Date Time'][trial_start_index:trial_end_index]
    else:
        print(f"End time {trial_end_time} not found.")
        return None, None, None
    if show_data==False:
        print(f"Background Data:\n{len(ec_bg)} values,\nDuration: {len(bg_time)},\nFrom {data['Date Time'][bg_start_index]} to {data['Date Time'][bg_end_index]}.")
        print(f"Trial Data:\n{len(ec_trial)} values,\nDuration: {len(trial_time)},\nFrom {data['Date Time'][trial_start_index]} to {data['Date Time'][trial_end_index]}.")
    else:
        return ec_bg, bg_time, ec_trial, trial_time

def compute_time_differences_in_seconds(time_list_str):
    """
    Computes the difference in seconds between consecutive time values.
    Parameters come from a list.

    Parameters:
        time_list_str (list of strings): The list of time values.

    Returns:
        list of float: Time differences in seconds between consecutive entries.
    """

    diffs = []
    cumulative = [0.0]
    for i in range(1, len(time_list_str)):
        t1 = datetime.strptime(time_list_str[i - 1],"%H:%M:%S")
        t2 = datetime.strptime(time_list_str[i],"%H:%M:%S")
        #t1 = datetime.combine(datetime.min, time_list[i - 1])
        #t2 = datetime.combine(datetime.min, time_list[i])
        delta_seconds = (t2 - t1).total_seconds()
        diffs.append(delta_seconds)
        cumulative.append(cumulative[-1] + delta_seconds)

    return diffs, cumulative

def secondary_solution_RC(injection_solution: float, Vo: float) -> float:
    """
    Calculate the relative concentration (RC) of the secondary solution.
    Which is a sample of the injection solution mixed with 1L pure stream water.

    Parameters:
        injection_solution (float): Volume of the solute added (in mL).
        Vo (float): Initial volume of water before injection (in mL).

    Returns:
        float: Relative concentration of the secondary solution.

    Raises:
        ValueError: If Vo or injection_solution is negative or zero.
        TypeError: If inputs are not floats or ints.
    """
    if not isinstance(injection_solution, (int, float)) or not isinstance(Vo, (int, float)):
        raise TypeError("Both 'injection_solution' and 'Vo' must be numeric (int or float).")
    if Vo <= 0 or injection_solution <= 0:
        raise ValueError("'Vo' and 'injection_solution' must be greater than 0.")

    RC_sec = injection_solution / (Vo + injection_solution)
    return RC_sec


def calibration_RC(RC_sec: float, additions_of_injection: List[float], Vc: float) -> List[float]:
    """
    Calculate a list of relative concentrations for calibration.

    Parameters:
        RC_sec (float): Relative concentration of the secondary solution.
        additions_of_injection (List[float]): Volumes of additional injections (in mL).
        Vc (float): Volume of the stream or container before additions (in mL).

    Returns:
        List[float]: Relative concentrations after each addition.

    Raises:
        ValueError: If any input is invalid or contains negative values.
    """
    if not isinstance(RC_sec, (int, float)):
        raise TypeError("'RC_sec' must be a float or int.")
    if not isinstance(additions_of_injection, list) or not all(isinstance(v, (int, float)) for v in additions_of_injection):
        raise TypeError("'additions_of_injection' must be a list of numeric values.")
    if Vc <= 0:
        raise ValueError("'Vc' must be greater than 0.")
    # multiply Vi by the index values to get cumulative additions
    RC = [RC_sec * (Vi * idx) / (Vc + (Vi * idx)) for idx, Vi in enumerate(additions_of_injection)]
    return RC


def calculate_k(RC_values: Union[List[float], np.ndarray], EC_values: Union[List[float], np.ndarray]) -> float:
    """
    Calculate the mixing coefficient (k) from RC and EC values.

    Parameters:
        RC_values (List[float] or np.ndarray): Relative concentration values.
        EC_values (List[float] or np.ndarray): Electrical conductivity values.

    Returns:
        float: Mixing coefficient k.

    Raises:
        ValueError: If lists are empty or not the same length.
        TypeError: If inputs are not numeric arrays or lists.
    """
    RC_arr = np.asarray(RC_values, dtype=float)
    EC_arr = np.asarray(EC_values, dtype=float)

    if RC_arr.size == 0 or EC_arr.size == 0:
        raise ValueError("RC_values and EC_values must not be empty.")
    if RC_arr.size != EC_arr.size:
        raise ValueError("RC_values and EC_values must be the same length.")

    k = RC_arr.max() / (EC_arr.max() - EC_arr.min())
    return k

# this function is werid should edit
def get_background_ec(start_time=None, end_time=None, ec_data=None):
    if isinstance(start_time,int) and isinstance(end_time,int):
        data = np.array(ec_data)
        background_ec = data[start_time:end_time].mean()
        return background_ec
    else:
        data = np.array(ec_data)
        background_ec = data[:].mean()
        return background_ec

def calculate_Q(ec_bg:float, ec_data:list, slope:float, bg_sec:int, trial_sec:int, time_step:Union[List[float], np.ndarray], injection_volume:float) -> float:
    data = np.array(ec_data[bg_sec:trial_sec])
    ec_diff = (data - ec_bg) * slope
    BTC_area = np.sum(np.multiply(ec_diff, time_step[bg_sec:trial_sec]))
    vol_m3 = injection_volume / 1000000 # convert ml to m^3
    Q = vol_m3 / BTC_area
    return Q

def plot_calibration(cal_data, RC):
    """ this doesn't work. returns that conductivity list is a string..."""
    fig, ax = plt.subplots(1, 1, figsize=(10,6))

    # the .to_numpy() attribute converts to a vector in order to do vector operations
    cond_series = np.array(cal_data['Conductivity'])
    conc_series = np.array(RC)

    # add the calibration points to the plot
    ax.plot(cond_series, conc_series, 'go', label="Calibration Points")

    ax.set_xlabel('Temperature Compenstated Conductivity [uS/cm]')
    ax.set_ylabel('Relative Concentration of Injection Solution [mL/mL]')
    ax.set_title('Salt Dilution Measurement Calibration')

    # add best fit line
    results = stats.linregress(cond_series, conc_series)
    # the stats.linregress output is a 5-tuple, r_value is the correlation coefficient
    slope, intercept, r_value, p_value, std_err = results

    #  create an array between the minimum and maximum calibration points
    x_range = np.linspace(cond_series.min(), cond_series.max(),  100)

    # use the best fit slope and intercept to construct the best fit line
    best_fit = [x * slope + intercept for x in x_range]

    # add the best fit line to the plot
    ax.plot(x_range, best_fit, 'b--', label='Best Fit (R^2 = {:.2f})'.format(r_value**2))
    # by default a legend is not shown, so we need to call the attribute.
    plt.legend()

def plot_injection(data:dict,
                   time_elapsed:Union[List[float], np.ndarray],
                   bg_sec:int, trial_sec:int,
                   total_diff:Union[List[float], np.ndarray],
                   show_background=False):
    """ Plot the data of interest"""
    ec_data = data[:len(time_elapsed)]
    bg_value = get_background_ec(0,bg_sec,data)
    bg_values = bg_value * np.array(total_diff)

    fig, ax = plt.subplots(1, 1, figsize=(10,6))
    if show_background==True:
        ax.plot(time_elapsed[1:], bg_values, 'ro',label='Background')

        ax.plot(time_elapsed[bg_sec:trial_sec],
            data[bg_sec:trial_sec], 'go',
            label='Injection')
        ax.plot(time_elapsed,ec_data, color='blue', label='Record')
    else:
        ax.plot(time_elapsed,ec_data, color='blue', label='Record')



    # label the axes, and set the plot title
    ax.set_xlabel('Time Elapsed (s)')
    ax.set_ylabel('Temp. Compenstated Conductivity [uS/cm]')
    ax.set_title('Salt Dilution Measurement')
    plt.legend()
    plt.tight_layout()

def plot_data(data, time):
    """ this doesn't work. returns that conductivity list is a string..."""
    fig, ax = plt.subplots(1, 1, figsize=(10,6))

    # the .to_numpy() attribute converts to a vector in order to do vector operations
    y_series = np.array(data)
    x_series = np.array(time)

    # add the calibration points to the plot
    ax.plot(x_series, y_series, 'go', label="data")

    ax.set_xlabel('Time (h:m:s)')
    ax.set_ylabel('Conductivity')
    ax.set_title('Salt Dilution Injection')


    plt.legend()
    plt.tight_layout()
