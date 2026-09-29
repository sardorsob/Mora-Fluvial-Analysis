from project_paths import method_path
from salt_dilution.scripts.experimental.salt_dilution_prototype import SaltDilutionGauging, load_config

config = load_config(method_path("salt_dilution", "config/dilution_draft.ini"))

csv_path = method_path("salt_dilution", "data/examples/calibration.csv")
csv_trial = method_path("salt_dilution", "data/examples/20250709_144014_790478.csv")

calibrate = SaltDilutionGauging.from_calibration_csv(csv_path)
discharge = SaltDilutionGauging.estimate_Q_from_csv(csv_trial, 13.0)

print("RC_sec:", calibrate.RC_sec)
print("k value:", calibrate.k)
print("RC values:", calibrate.RC_values)
print("EC values:", calibrate.EC_values)
print("Estimate of Q:", discharge)
