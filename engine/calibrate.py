"""Real log -> data/calibration.json.

Reads the public HospitalOPD event log (Mendeley Data, DOI 10.17632/j2hd2239dr.1,
CC BY 4.0) and writes only summary numbers. The raw file is never committed.

    python engine/calibrate.py check path/to.csv      # run the document data check
    python engine/calibrate.py path/to.csv            # write data/calibration.json
    python engine/calibrate.py                        # use data/raw/*.csv, downloading if missing

What the log can and cannot calibrate (see the data check in the README):
  usable      arrival pattern by hour and weekday; share of visits sent to laboratory
              and imaging; the real wait between registration and the doctor
  not usable  service times (consultation start equals end on most rows; laboratory
              "duration" is result turnaround), pharmacy share (recorded for 0.2% of
              visits), staff numbers outside consultation
"""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
RAW = RAW_DIR / "HospitalOPD-noname.csv"
URL = ("https://data.mendeley.com/public-files/datasets/j2hd2239dr/files/"
       "02ec5ae9-79f0-43c0-8e1f-085ae216b4bf/file_downloaded")
REQUIRED_COLUMNS = (
    "appointment_id",
    "appointment_start_datetime",
    "prescription_doctor_id",
    "prescription_start_datetime",
    "prescription_order_id",
    "lab_start_datetime",
    "imaging_start_datetime",
    "pharmacy_start_datetime",
)
STATION_TIME_COLUMNS = (
    "appointment_start_datetime",
    "prescription_start_datetime",
    "lab_start_datetime",
    "imaging_start_datetime",
    "pharmacy_start_datetime",
)

# Timestamps are stored in UTC; the clinic is in Pakistan (UTC+5). Evidence: only after
# the shift does the Friday-prayer dip fall at 13:00 and the day start at 08:00.
UTC_OFFSET_HOURS = 5
# Volumes are stable only in these six months; earlier months are a system ramp-up.
WINDOW = ("2025-09-01", "2026-03-01")
WEEKDAYS = [0, 1, 2, 3, 4, 5]   # Monday to Saturday; Sunday runs at a quarter of the volume


def load(path):
    df = pd.read_csv(path, low_memory=False)
    for col in [c for c in df.columns if c.endswith("datetime")]:
        df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")
    return df


def resolve_input_path(arg=None, download=True):
    """Pick the raw CSV.

    If the user passes a path, use it. Otherwise use data/raw/HospitalOPD-noname.csv or
    the single CSV in data/raw/. Only download when calibration is run with no local file.
    """
    if arg:
        return Path(arg)
    if RAW.exists():
        return RAW
    csvs = sorted(RAW_DIR.glob("*.csv")) if RAW_DIR.exists() else []
    if len(csvs) == 1:
        return csvs[0]
    if len(csvs) > 1:
        names = "\n  ".join(str(p) for p in csvs)
        raise SystemExit(
            "More than one CSV found in data/raw/. Pass the file explicitly:\n"
            f"  python engine/calibrate.py data/raw/<file>.csv\n\nFound:\n  {names}"
        )
    if not download:
        raise SystemExit(
            "No CSV found. Put your file at data/raw/HospitalOPD-noname.csv, or pass a path."
        )
    print(f"downloading the HospitalOPD log to {RAW} ...")
    RAW.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(URL, RAW)
    return RAW


def data_check(path, cfg):
    """Run the six-question data check from the build guide."""
    df = load(path)
    cols = set(df.columns)
    missing = [c for c in REQUIRED_COLUMNS if c not in cols]
    station_cols = [c for c in STATION_TIME_COLUMNS if c in cols and df[c].notna().any()]
    completion_cols = [
        c for c in df.columns
        if any(word in c.lower() for word in ("complete", "completion", "end_datetime"))
    ]

    start_col = "appointment_start_datetime"
    days = 0
    visits_per_day = 0.0
    if start_col in df.columns:
        local = df[start_col] + pd.Timedelta(hours=UTC_OFFSET_HOURS)
        open_h, close_h = int(cfg["open"][:2]), int(cfg["close"][:2])
        in_hours = df[(local.dt.hour >= open_h) & (local.dt.hour < close_h)].copy()
        if not in_hours.empty:
            dates = local.loc[in_hours.index].dt.date
            days = int(dates.nunique())
            visits = in_hours["appointment_id"].nunique() if "appointment_id" in df.columns else len(in_hours)
            visits_per_day = float(visits / days) if days else 0.0

    staff_cols = [c for c in df.columns if any(word in c.lower() for word in ("staff", "doctor", "resource"))]

    answers = [
        ("Visit/patient ID and activity name",
         "yes" if "appointment_id" in cols and len(station_cols) >= 2 else "no",
         "Uses appointment_id plus wide station timestamp columns: " + ", ".join(station_cols)),
        ("Start and completion times",
         "partial" if station_cols else "no",
         "Station start timestamps are present. Completion timestamps found: "
         + (", ".join(completion_cols) if completion_cols else "none")),
        ("Wait from previous completion",
         "no" if not completion_cols else "partial",
         "This build uses wait-to-doctor as a real-data check; simulator waits come from assumptions."),
        ("Staff/resource column",
         "partial" if staff_cols else "no",
         "Columns found: " + (", ".join(staff_cols) if staff_cols else "none")),
        ("Enough days with enough patients",
         "yes" if days >= 20 and visits_per_day >= 20 else "check",
         f"{days} clinic days, about {visits_per_day:.1f} visits/day in configured hours."),
        ("Licence allows reuse with attribution",
         "manual",
         "The CSV cannot prove licence. Verify the source page; do not commit the raw file."),
    ]
    return {"rows": int(len(df)), "missing": missing, "answers": answers}


def print_data_check(result):
    print("Data check")
    print("rows:", result["rows"])
    if result["missing"]:
        print("missing columns needed by engine/calibrate.py:", ", ".join(result["missing"]))
    else:
        print("all columns needed by engine/calibrate.py are present")
    for i, (question, answer, detail) in enumerate(result["answers"], 1):
        print(f"{i}. {question}: {answer}")
        print(f"   {detail}")


def calibrate(path, cfg):
    df = load(path)
    open_h = int(cfg["open"][:2])
    close_h = int(cfg["close"][:2])

    # One appointment is one visit; a visit spans several rows (one per order line).
    visits = df.groupby("appointment_id").agg(
        arrive=("appointment_start_datetime", "min"),
        doctor=("prescription_doctor_id", "first"),
        consult_start=("prescription_start_datetime", "min"),
        lab=("lab_start_datetime", "min"),
        imaging=("imaging_start_datetime", "min"),
        pharmacy=("pharmacy_start_datetime", "min"),
    )
    local = visits["arrive"] + pd.Timedelta(hours=UTC_OFFSET_HOURS)
    visits["date"] = local.dt.date
    visits["hour"] = local.dt.hour
    visits["weekday"] = local.dt.dayofweek

    stable = visits[(local >= WINDOW[0]) & (local < WINDOW[1]) & visits["weekday"].isin(WEEKDAYS)]
    days_by_weekday = stable.groupby("weekday")["date"].nunique()
    n_days = int(days_by_weekday.sum())
    clinic = stable[(stable["hour"] >= open_h) & (stable["hour"] < close_h)]

    real_hourly = (clinic.groupby("hour").size() / n_days).reindex(range(open_h, close_h), fill_value=0)
    per_weekday = clinic.groupby("weekday").size() / days_by_weekday
    weekday_factor = per_weekday / (len(clinic) / n_days)

    consult = cfg["stations"]["consultation"]
    capacity = consult["staff"] * 60 / consult["service_min"]
    target = cfg["calibration"]["target_peak_util"]
    scale = target * capacity / real_hourly.max()

    share_lab = clinic["lab"].notna().mean()
    share_img = clinic["imaging"].notna().mean()
    share_both = (clinic["lab"].notna() & clinic["imaging"].notna()).mean()

    wait = (clinic["consult_start"] - clinic["arrive"]).dt.total_seconds() / 60
    wait = wait[(wait >= 0) & (wait <= 480)]

    # Gap between a doctor's consecutive prescriptions: a rough check on the assumed
    # consultation time. It includes idle time, so it is not used as a service time.
    orders = df.drop_duplicates("prescription_order_id")[
        ["prescription_doctor_id", "prescription_start_datetime"]].dropna()
    orders = orders.sort_values(["prescription_doctor_id", "prescription_start_datetime"])
    gap = orders.groupby("prescription_doctor_id")["prescription_start_datetime"].diff()
    gap = gap.dt.total_seconds() / 60
    gap = gap[(gap > 0) & (gap <= 60)]

    doctors_per_day = clinic.groupby("date")["doctor"].nunique()

    return {
        "source": {
            "name": "HospitalOPD event log", "repository": "Mendeley Data",
            "doi": "10.17632/j2hd2239dr.1", "licence": "CC BY 4.0",
            "url": "https://data.mendeley.com/datasets/j2hd2239dr/1",
            "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "rows": int(len(df)), "visits": int(len(visits)),
        },
        "method": {
            "utc_offset_hours": UTC_OFFSET_HOURS,
            "window": list(WINDOW),
            "weekdays": WEEKDAYS,
            "clinic_hours_local": [cfg["open"], cfg["close"]],
            "days_used": n_days,
            "visits_used": int(len(clinic)),
            "scale_rule": (f"arrivals scaled so consultation ({consult['staff']} doctors, "
                           f"{consult['service_min']} min) is {target:.0%} busy in the peak "
                           "hour of an average weekday"),
        },
        # What the simulator uses.
        "arrival_scale_factor": round(float(scale), 4),
        "arrivals_per_hour": {str(h): round(float(v * scale), 2) for h, v in real_hourly.items()},
        "weekday_factor": {str(int(d)): round(float(f), 3) for d, f in weekday_factor.items()},
        "share": {"laboratory": round(float(share_lab), 4), "imaging": round(float(share_img), 4)},
        "lab_and_imaging_share": round(float(share_both), 4),
        # What the real clinic looks like, for the calibration check and the pitch.
        "real": {
            "arrivals_per_hour": {str(h): round(float(v), 2) for h, v in real_hourly.items()},
            "visits_per_day": round(float(len(clinic) / n_days), 1),
            "visits_per_day_by_weekday": {str(int(d)): round(float(v), 1) for d, v in per_weekday.items()},
            "doctors_per_day_median": float(doctors_per_day.median()),
            "wait_to_doctor": {
                "definition": "appointment_start_datetime to prescription_start_datetime",
                "visits": int(len(wait)),
                "median_min": float(wait.median()),
                "share_over_30": round(float((wait > 30).mean()), 3),
                "share_over_60": round(float((wait > 60).mean()), 3),
            },
            "consult_cycle_proxy_min": {
                "definition": "gap between a doctor's consecutive prescriptions, 1 to 60 min",
                "median": float(gap.median()), "mean": round(float(gap.mean()), 1),
            },
            "pharmacy_share_recorded": round(float(clinic["pharmacy"].notna().mean()), 4),
        },
        "not_calibrated": {
            "service_min": "no usable service durations in the log; config values are assumptions",
            "pharmacy share": "pharmacy is recorded for under 1% of visits; config value is an assumption",
            "staff": "only doctors are identified, across many specialties; config values are assumptions",
        },
    }


def main():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    args = sys.argv[1:]
    if args and args[0] in ("check", "data-check"):
        path = resolve_input_path(args[1] if len(args) > 1 else None, download=False)
        print_data_check(data_check(path, cfg))
        return
    if args and args[0] in ("calibrate", "run"):
        args = args[1:]
    path = resolve_input_path(args[0] if args else None)
    check = data_check(path, cfg)
    if check["missing"]:
        print_data_check(check)
        raise SystemExit("Cannot calibrate until the missing columns are mapped or added.")
    result = calibrate(path, cfg)
    out = ROOT / cfg["calibration"]["file"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print("arrival scale factor:", result["arrival_scale_factor"])
    print("arrivals per hour   :", result["arrivals_per_hour"])
    print("weekday factor      :", result["weekday_factor"])
    print("shares              :", result["share"], "both:", result["lab_and_imaging_share"])
    print("real wait to doctor :", result["real"]["wait_to_doctor"])


if __name__ == "__main__":
    main()
