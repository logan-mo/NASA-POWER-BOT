import seaborn as sns
import matplotlib.pyplot as plt
import requests
import numpy as np
import argparse
import yaml
from utils import num_of_leap_years_in_range, get_area

my_parser = argparse.ArgumentParser(
    prog="python3 download.py",
    description="Download the dataset from NASA Power API",
)
my_parser.add_argument(
    "-start",
    "--year-start",
    type=int,
    help="Year start",
    required=True,
)
my_parser.add_argument(
    "-end",
    "--year-end",
    type=int,
    help="Year end",
    required=True,
)
my_parser.add_argument(
    "-width",
    "--area-width",
    type=float,
    help="Area width",
    required=True,
)
my_parser.add_argument(
    "-height",
    "--area-height",
    type=float,
    help="Area height",
    required=True,
)
my_parser.add_argument(
    "-t",
    "--timeout",
    type=int,
    help="Timeout",
    default=60,
)
args = my_parser.parse_args()

if num_of_leap_years_in_range(start=args.year_start, end=args.year_end) > 0:
    days_per_year = 366
else:
    days_per_year = 365

with open("locations.yml", "r") as file:
    content = yaml.safe_load(file)
    target_locations = content["target_locations"]

T = days_per_year * (args.year_end - args.year_start + 1)
P = len(target_locations)
F = int(
    args.area_width * 2 * args.area_height * 2
)  # NASA POWER resolution is 1/2 deg and 1/2 deg !!!
X_all = np.zeros((T, P, F), dtype=np.float32)
y_hourly_all = np.zeros(((T * 24), P, 1), dtype=np.float32)
y_daily_all = np.zeros((T, P, 1), dtype=np.float32)

# Timesteps
t_daily, t_hourly = 0, 0
for year in range(args.year_start, args.year_end + 1):

    # Patches
    for p, key in enumerate(target_locations):
        latitude_min, latitude_max, longitude_min, longitude_max = get_area(
            target_locations[key],
            width=args.area_width,
            height=args.area_height,
        )

        print(f"{key}")
        print(f"Year: {year}")
        print("⛅ 🌞 ⚡")
        print("----------------------------------------------------------")
        print(f"Target: {target_locations[key][0]}, {target_locations[key][1]}")
        print(f"Area: {latitude_min}, {latitude_max}, {longitude_min}, {longitude_max}")
        print("----------------------------------------------------------\n")

        # Region - daily
        response_region = requests.get(
            f"https://power.larc.nasa.gov/api/temporal/daily/regional?start={year}0101&end={year}1231&latitude-min={latitude_min}&latitude-max={latitude_max}&longitude-min={longitude_min}&longitude-max={longitude_max}&community=re&parameters=ALLSKY_SFC_SW_DWN&format=json&header=true&time-standard=utc",
            verify=True,
            timeout=args.timeout,
        )
        if response_region.status_code == 200:
            content = response_region.json()

            # Header
            units = content["parameters"]["ALLSKY_SFC_SW_DWN"]["units"]
            name = content["parameters"]["ALLSKY_SFC_SW_DWN"]["longname"]
            fill_value = content["header"][
                "fill_value"
            ]  # represents missing values (measurement error)
            print(f"{name} ({units})")
            print(f"Fill value: {fill_value}", "\n")

            for f in range(F):
                features_region = content["features"][f]["properties"]["parameter"][
                    "ALLSKY_SFC_SW_DWN"
                ]
                x = list(features_region.values())
                X_all[t_daily : t_daily + len(x), p, f] = x
        else:
            raise ValueError(
                f"Cannot download region dataset with status code {response_region.status_code} 😟"
            )

        # Point - daily
        response_target = requests.get(
            f"https://power.larc.nasa.gov/api/temporal/daily/point?start={year}0101&end={year}1231&latitude={target_locations[key][0]}&longitude={target_locations[key][1]}&community=re&parameters=ALLSKY_SFC_SW_DWN&format=json&header=true&time-standard=utc",
            verify=True,
            timeout=args.timeout,
        )
        if response_target.status_code == 200:
            content = response_target.json()

            # Header
            units = content["parameters"]["ALLSKY_SFC_SW_DWN"]["units"]
            name = content["parameters"]["ALLSKY_SFC_SW_DWN"]["longname"]
            fill_value = content["header"][
                "fill_value"
            ]  # represents missing values (measurement error)
            print(f"{name} ({units})")
            print(f"Fill value: {fill_value}", "\n")

            features_point = content["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
            y = list(features_point.values())
            y_daily_all[t_daily : t_daily + len(y), p, 0] = y
        else:
            raise ValueError(
                f"Cannot download point dataset with status code {response_target.status_code} 😟\n"
            )

        # Point - hourly
        if year >= 2001:
            response_target = requests.get(
                f"https://power.larc.nasa.gov/api/temporal/hourly/point?start={year}0101&end={year}1231&latitude={target_locations[key][0]}&longitude={target_locations[key][1]}&community=re&parameters=ALLSKY_SFC_SW_DWN&format=json&header=true&time-standard=utc",
                verify=True,
                timeout=args.timeout,
            )
            if response_target.status_code == 200:
                content = response_target.json()

                # Header
                units = content["parameters"]["ALLSKY_SFC_SW_DWN"]["units"]
                name = content["parameters"]["ALLSKY_SFC_SW_DWN"]["longname"]
                fill_value = content["header"][
                    "fill_value"
                ]  # represents missing values (measurement error)
                print(f"{name} ({units})")
                print(f"Fill value: {fill_value}", "\n")

                features_point = content["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
                y = list(features_point.values())
                y_hourly_all[t_hourly : t_hourly + len(y), p, 0] = y
            else:
                raise ValueError(
                    f"Cannot download point dataset with status code {response_target.status_code} 😟\n"
                )
        else:
            y_hourly_all[t_hourly : t_hourly + (days_per_year * 24), p, 0] = -1
            print(f"Year {year} is too early for hourly data. Filled with missing value -1.\n")

    print("Dataset downloaded 🙂\n")

    t_daily += days_per_year
    t_hourly += (days_per_year * 24)

print(t_daily, " ", t_hourly)

# replace bad values with fill value -1 !!!
X_all[X_all < 0] = -1
y_daily_all[y_daily_all < 0] = -1
y_hourly_all[y_hourly_all < 0] = -1

print(f"Inputs shape: {X_all.shape}")
print(f"Target daily shape: {y_daily_all.shape}")
print(f"Target hourly shape: {y_hourly_all.shape}")

# Descriptive Statistics
print(f"Minimum: {np.min(X_all)}")
print(f"Maximum: {np.max(X_all)}")
print(f"Mean: {np.mean(X_all)}")
print(f"Standard deviation: {np.std(X_all)}\n")

# Descriptive Statistics
print(f"Minimum: {np.min(y_daily_all)}")
print(f"Maximum: {np.max(y_daily_all)}")
print(f"Mean: {np.mean(y_daily_all)}")
print(f"Standard deviation: {np.std(y_daily_all)}\n")

# Descriptive Statistics
print(f"Minimum: {np.min(y_hourly_all)}")
print(f"Maximum: {np.max(y_hourly_all)}")
print(f"Mean: {np.mean(y_hourly_all)}")
print(f"Standard deviation: {np.std(y_hourly_all)}\n")

# save dataset
np.savez_compressed("dataset", X=X_all, y_daily=y_daily_all, y_hourly=y_hourly_all)

# inputs distribution
sns.displot(X_all.reshape((-1, X_all.shape[-1])), kde=True)
plt.title("Region")

# target distribution
sns.displot(y_daily_all.reshape((-1, y_daily_all.shape[-1])), kde=True)
plt.title("Point - daily")

# target distribution
sns.displot(y_hourly_all.reshape((-1, y_hourly_all.shape[-1])), kde=True)
plt.title("Point - hourly")

plt.show()
