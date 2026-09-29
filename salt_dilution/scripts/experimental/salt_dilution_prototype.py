from project_paths import method_path
import configparser
from pathlib import Path
import numpy as np

def load_config(path: str = method_path("salt_dilution", "config/dilution_draft.ini")) -> dict:
    """ instantiate the dil_config.ini file and read in the parameters to a dictionary"""
    config = configparser.ConfigParser()
    config.read(path)
    dil_dict = {
        "calibration_file": config["calibration"]["file"],
        "injection_volume": float(config["injection"]["volume"]),
        "background_conductivity": float(config["background"]["conductivity"]),
        "ec_file": config["time_series"]["ec_file"],
        "time_file": config["time_series"]["time_file"],
    }
    return dil_dict

class SaltDilutionGauging:
    def __init__(self, Vc: float, injection_volume: float):
        self.Vc = Vc
        self.injection_volume = injection_volume
        self.RC_sec = self.injection_volume / (self.Vc + self.injection_volume)
        self.RC_values = []
        self.EC_values = None
        self.k = None

    def compute_secondary_solution_RC(self) -> float:
        self.RC_sec = self.injection_volume / (self.Vc + self.injection_volume)
        return self.RC_sec

    def compute_calibration_RC(self, additions_of_injection: list[float]) -> list[float]:
        if self.RC_sec is None:
            self.compute_secondary_solution_RC()
        self.RC_values = [self.RC_sec * Vi / (self.Vc + Vi) for Vi in additions_of_injection]
        return self.RC_values

    def compute_k(self, RC_values: list[float], EC_values: list[float]) -> float:
        self.k = max(RC_values) / (max(EC_values) - min(EC_values))
        return self.k

    def get_background_ec(self, start_time, end_time):
        data = np.array(self.EC_values)
        self.background_ec = data[start_time:end_time].mean() # needs to index of time values for this to work.
        return self.background_ec
    def get_BTC_area(self, background_ec, injection_volume, ec_data, start_time, end_time):
        data = np.array(ec_data)
        concentration = np.diff(data).cumsum()

    def calculate_Q(self, injection_volume: float, delta_EC: float) -> float:
        """
        Calculate stream discharge (Q) using volume of injection solution and change in EC.
        Q = injection volume / (k * delta_EC) not correct, needs time
        """
        if self.k is None:
            raise ValueError("Calibration constant k must be computed before calculating Q.")
        if delta_EC == 0:
            raise ValueError("delta_EC must not be zero.")
        Q = injection_volume / (self.k * delta_EC)
        return Q # this doesn't work

    @classmethod
    def from_calibration_csv(cls, filepath: str) -> "SaltDilutionGauging":
        data = np.genfromtxt(filepath, delimiter=",", names=True)

        # Extract volumes
        Vc = data["Vol_secondary_mL"][0]
        injection_volume = data["Vol_cal_solution_mL"][1]  # skip the zero row

        # Create instance
        obj = cls(Vc=Vc, injection_volume=injection_volume)

        # Compute secondary RC
        obj.compute_secondary_solution_RC()

        # Get additions and EC values
        additions = [float(x) for x in data["Vol_cal_solution_mL"][1:]]  # skip first row
        EC_values = [float(x) for x in data["Specific_CD_uS_per_cm"][1:]]  # same

        # Compute calibration RCs and k
        obj.compute_calibration_RC(additions)
        obj.compute_k(obj.RC_values, EC_values)

        # Store EC values
        obj.EC_values = EC_values

        return obj

    @classmethod # needs work
    def estimate_Q_from_csv(cls, filepath: str, mass_salt: float) -> float:
        """
        Estimate stream discharge (Q) from a CSV file containing EC measurements.
        Assumes the CSV has a column 'EC_stream_uS_per_cm' with EC values before and after salt addition.
        The delta_EC is calculated as max(EC) - min(EC).
        """
        data = np.genfromtxt(filepath, delimiter=",", names=True)
        # Extract EC values from the stream
        # add code to extract the column names to line below
        EC_stream = [float(x) for x in data["Actual_Conductivity_µScm_790478"]] # returns no field of this name
        delta_EC = max(EC_stream) - min(EC_stream)
        # Use calibration from the same file
        gauge = cls.from_calibration_csv(filepath)
        Q = gauge.calculate_Q(gauge.injection_volume, delta_EC)
        return Q
