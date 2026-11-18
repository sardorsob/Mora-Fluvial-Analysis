"""Export the mean of an ObsPy seismic PPSD histogram with explicit axes."""

import argparse
from pathlib import Path

import numpy as np

from project_paths import result_path


def save_mean_ppsd(ppsd, output):
    """Write period (s), ascending frequency (Hz), and mean acceleration PSD (dB).

    The two axes refer to the same bins. The mean is ObsPy's histogram mean
    in dB, not a Welch estimate or a mean of linear FFT power.
    """
    if not ppsd.times_processed:
        raise ValueError("No complete PPSD segments. Check the interval and waveform gaps.")
    period_s, mean_psd_db = map(np.asarray, ppsd.get_mean())
    # ObsPy returns periods. Reverse the corresponding PSD bins when sorting by Hz.
    order = np.argsort(1 / period_s)
    period_s = period_s[order]
    np.savez(
        output, period_s=period_s, frequency_hz=1 / period_s,
        mean_acceleration_psd_db=mean_psd_db[order],
        psd_db_reference="1 (m/s^2)^2/Hz",
    )


def main():
    """Read one seismic channel and its response from local files."""
    from obspy import UTCDateTime, read, read_inventory
    from obspy.signal import PPSD

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("waveforms", help="miniSEED path or quoted glob")
    parser.add_argument("stationxml", type=Path, help="Local inventory with channel response")
    parser.add_argument("--seed-id", required=True, help="Network.station.location.channel")
    parser.add_argument("--start", required=True, type=UTCDateTime, help="UTC interval start")
    parser.add_argument("--end", required=True, type=UTCDateTime, help="UTC interval end")
    parser.add_argument("--plot", action="store_true", help="Display the PPSD histogram")
    parser.add_argument("--period", type=float, action="append", help="Plot PSD at this period in seconds")
    args = parser.parse_args()

    if args.start >= args.end:
        parser.error("--end must be later than --start")
    stream = read(args.waveforms, starttime=args.start, endtime=args.end)
    stream.traces = [trace for trace in stream if trace.id == args.seed_id]
    if not stream:
        parser.error(f"No traces match {args.seed_id} in the requested interval.")
    if len({trace.stats.sampling_rate for trace in stream}) != 1:
        parser.error("Export each sample-rate interval separately.")
    inventory = read_inventory(str(args.stationxml))
    for trace in stream:
        response = inventory.get_response(trace.id, trace.stats.starttime)
        sensitivity = response.instrument_sensitivity
        units = (sensitivity.input_units or "").upper() if sensitivity is not None else ""
        if units not in {"M", "M/S", "M/S**2"}:
            parser.error("This export requires a seismic response in m, m/s, or m/s².")
    # Keep the recorded sample rate. Skip gaps instead of treating zero fills as signal.
    ppsd = PPSD(
        stream[0].stats, metadata=inventory, skip_on_gaps=True,
        db_bins=(-200, 15, 1), period_limits=(1 / 150, 10.0),
    )
    ppsd.add(stream)
    if not ppsd.times_processed:
        parser.error("No complete PPSD segments. Check the interval and waveform gaps.")
    filename = f"{args.seed_id}_{args.start.strftime('%Y%m%dT%H%M%S')}_{args.end.strftime('%Y%m%dT%H%M%S')}.npz"
    output = result_path("fluvial_seismology", f"tables/{filename}")
    save_mean_ppsd(ppsd, output)
    print(output)
    if args.plot:
        ppsd.plot(xaxis_frequency=True)
    if args.period:
        ppsd.plot_temporal(args.period)


if __name__ == "__main__":
    main()
