import numpy as np

def convert_volume(value, from_unit, to_unit):
    """
    Convert volume between metric units from cubic centimeters to cubic meters.
    Works with both scalar values and numpy arrays.

    Supported units: 'cm3', 'ml', 'cl', 'dl', 'l', 'dal', 'hl', 'kl', 'm3'
    """
    units_in_liters = {
        'cm3': 0.001,
        'ml': 0.001,
        'cl': 0.01,
        'dl': 0.1,
        'l': 1.0,
        'dal': 10.0,
        'hl': 100.0,
        'kl': 1000.0,
        'm3': 1000.0
    }

    if from_unit not in units_in_liters or to_unit not in units_in_liters:
        raise ValueError("Units must be one of: 'cm3', 'ml', 'cl', 'dl', 'l', 'dal', 'hl', 'kl', 'm3'.")

    # Convert input to a NumPy array for broadcasting support
    value = np.asarray(value, dtype=float)

    # Convert to liters, then to the target unit
    liters = value * units_in_liters[from_unit]
    result = liters / units_in_liters[to_unit]

    return result

def convert_mass(value, from_unit, to_unit):
    """
    Convert mass between metric units from centigrams to kilograms.

    Supported units: 'cg', 'dg', 'g', 'hg', 'kg'

    Parameters:
        value (float): The numeric mass value to convert.
        from_unit (str): The unit of the input value. Must be one of 'cg', 'dg', 'g', 'hg', 'kg'.
        to_unit (str): The desired output unit. Must be one of 'cg', 'dg', 'g', 'hg', 'kg'.

    Returns:
        float: Converted mass in the target unit.
    """
    units_in_grams = {
        'cg': 0.01,
        'dg': 0.1,
        'g': 1.0,
        'hg': 100.0,
        'kg': 1000.0
    }

    if from_unit not in units_in_grams or to_unit not in units_in_grams:
        raise ValueError("Units must be one of 'cg', 'dg', 'g', 'hg', or 'kg'.")

    # Convert input to a NumPy array for broadcasting support
    value = np.asarray(value, dtype=float)

    # Convert from source unit to grams
    grams = value * units_in_grams[from_unit]

    # Convert from grams to target unit
    result = grams / units_in_grams[to_unit]

    return result
