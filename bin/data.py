# Usage:
#   python data.py <id> <start> <stop>
#   python data.py <id> <start> <stop> <parameters>
#
# <id> is the station ID, e.g., S000028 found in first column of catalog.csv
# <start> and <stop> are 20-character HAPI ISO date strings, e.g.,
# 2023-03-22T00:00:00Z
#
# The output of this script is HAPI CSV and equivalent to the response from:
#   hapi/data?dataset=<id>&start=<start>&stop=<stop>
#   hapi/data?dataset=<id>&start=<start>&stop=<stop>&parameters=<parameters>
#
# Examples:
#
#  python data.py S000028/mag 2025-10-20T00:00:00Z 2025-10-21T00:00:00Z
#  python data.py S000001/mag 2022-07-08T00:00:00Z 2022-07-09T00:00:00Z
#  python data.py S000001/doppler 2020-08-07T00:00:00Z 2022-08-08T00:00:00Z
#
#  python data.py S000028/mag 2025-10-20T00:00:00Z 2025-10-21T00:00:00Z Field_Vector
#  python data.py S000001/mag 2022-07-08T00:00:00Z 2022-07-09T00:00:00Z Field_Vector
#  python data.py S000001/doppler 2020-08-07T00:00:00Z 2022-08-08T00:00:00Z Freq

import os
import re
import sys
import json
import zipfile
import datetime

debug = True # Print debug messages to stdout

def error(emsg):
  print(emsg, file=sys.stderr)
  exit(1)


def files_needed(id, start, stop, data_dir):

  sub_dir_map = {
    'mag': 'magData',
    'doppler': 'csvData',
    'drf': '',
  }

  data_type = id.split('/')[-1]
  if data_type not in sub_dir_map:
    msg = f"Unknown dataset ID suffix for id '{id}'. "
    msg = "Expected to end with '/mag', '/doppler', or '/drf'."
    error(msg)

  # id = S000028/mag => S000028/magData
  # id = S000028/doppler => S000028/csvData
  # id = S000028/drf => S000028
  dir_base = id.replace('/' + data_type, '')
  dir_sub = sub_dir_map[data_type]
  dataset_dir = os.path.join(data_dir, dir_base, dir_sub)
  if not os.path.exists(dataset_dir):
    error(f"Dataset directory does not exist: {dataset_dir}")

  # Keep only day precision for file matching
  start = start[0:10]
  stop = stop[0:10]
  if debug:
    print(f"Debug: Looking for files with data in range [{start}, {stop}]")

  if data_type == 'mag':
    files = files_needed_mag(dataset_dir, start, stop)
  if data_type == 'doppler':
    files = files_needed_doppler(dataset_dir, start, stop)

  if debug:
    if len(files) == 0:
      print(f"Debug: No files found with data in range [{start}, {stop}]")
    else:
      print(f"Debug: Found {len(files)} files with data in range [{start}, {stop}]:")
      files_join = "  \nDebug:   ".join(files)
      print(f"Debug: {files_join}")

  return files


def files_needed_doppler(dataset_dir, start, stop):
  files_csv = [f for f in os.listdir(dataset_dir) if f.endswith(".csv")]

  files_needed = []
  for file in sorted(files_csv):
    file_date = file[0:10]
    if debug:
      print(f"Debug: File: {file}, date: {file_date}")
    if start <= file_date <= stop:
      files_needed.append(os.path.join(dataset_dir, file))

  return files_needed


def files_needed_mag(dataset_dir, start, stop):
  files_zip = [f for f in os.listdir(dataset_dir) if f.endswith(".zip")]
  files_zip.sort()

  if not files_zip:
    if debug:
      print(f"Debug: No .zip files found in dataset directory: {dataset_dir}")
    sys.exit(0)

  if debug:
    print(f"Debug: Found {len(files_zip)} files that end with .zip in {dataset_dir}")

  files_needed = []

  for file in files_zip:
    file_date = file[3:13]
    if debug:
      print(f"Debug: File: {file}, date: {file_date}")
    if start <= file_date <= stop:
      files_needed.append(os.path.join(dataset_dir, file))

  return files_needed


def print_data(id, filename, start, stop, parameters, data_dir):

  filepath = os.path.join(data_dir, id, filename)

  if id.endswith('/mag'):
    print_data_mag(filepath, start, stop, parameters)

  if id.endswith('/doppler'):
    print_data_doppler(filepath, start, stop, parameters)

def print_data_doppler(filepath, start, stop, parameters):

  with open(filepath, 'r') as f:
    for line in f:
      if debug:
        print(f"Debug: Processing line: {line.strip()}", file=sys.stderr)
      if not re.match(r'^[0-9]{4}', line):
        continue
      cols = line.split(',')
      ts = cols[0].strip()
      row = ts
      if 'Freq' or 'Vpk' in parameters:
        row += "," + cols[1].strip()
      if 'Vpk' in parameters:
        row += "," + cols[2].strip()
      print(row)

def print_data_mag(filepath, start, stop, parameters):

  def extract_data(file):
    """Read files in a zip file into a string"""
    data = ""
    with zipfile.ZipFile(file, 'r') as z:
      for filename in sorted(z.namelist()):
        with z.open(filename) as f:
          data += f.read().decode('utf-8')
    return data

  # TODO: This will be much faster if CSV files were read using Pandas, which
  # loops over lines in c code.
  data = extract_data(filepath)

  for line in data.splitlines():

    if debug:
      print(f"Debug: Processing line: {line}", file=sys.stderr)

    if line.startswith('{'):
      # Row format:
      # {'ts': '21 Oct 2025 04:01:59', 'rt': 32.5, 'lt': 41.69,
      #  'x': -45676.67, 'y': -13284.67, 'z': 16150.67,
      #  'rx': -68515, 'ry': -19927, 'rz': 24226, 'Tm': 50236.2845}
      entry = json.loads(line)
      ts = entry['ts']
      try:
        dt = datetime.datetime.strptime(ts, '%d %b %Y %H:%M:%S')
        entry['ts'] = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
      except Exception as e:
        if debug:
          print(f"Debug: Failed to parse ts '{ts}': {e}", file=sys.stderr)

    elif line.startswith('"'):
      # Row format:
      # TODO: Verify that these columns are correct.
      entry = line.split(', ')
      ts = entry[0].strip('"')
      dt = datetime.datetime.strptime(ts, '%d %b %Y %H:%M:%S')
      entry = {
        'ts': dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'x': float(entry[1]),
        'y': float(entry[2]),
        'z': float(entry[3]),
        'rx': float(entry[4]),
        'ry': float(entry[5]),
        'rz': float(entry[6]),
        'rt': float(entry[7]),
        'lt': float(entry[8]),
        'Tm': float(entry[9]),
      }
    else:
      # TODO: Read other format
      error(f"Unsupported data format in file {filepath}: {line}")

    if entry['ts'][0:20] < start:
      continue
    if entry['ts'][0:20] >= stop:
      break

    row = entry['ts']

    if 'Field_Vector' in parameters:
      row += f",{entry['x']},{entry['y']},{entry['z']}"
    if 'rxryrz' in parameters:
      row += f",{entry['rx']},{entry['ry']},{entry['rz']}"
    if 'rt' in parameters:
      row += f",{entry['rt']}"
    if 'lt' in parameters:
      row += f",{entry['lt']}"
    if 'Tm' in parameters:
      row += f",{entry['Tm']}"

    print(row)


# Get data_dir from environment variable
data_dir = os.getenv("PSWS_DATA_DIR")
script_dir = os.path.dirname(os.path.abspath(__file__))
data_dir_default = os.path.join(script_dir, "..", "data")

if not data_dir and not os.path.exists(data_dir_default):
  msg = "Environment variable PSWS_DATA_DIR not set and directory "
  msg += f"{data_dir_default} not found. Exiting with code 1."
  error(msg)
if not data_dir and os.path.exists(data_dir_default):
  data_dir = data_dir_default

try:
  data_dir = os.path.expanduser(data_dir)
except Exception:
  msg = "Could not expand PSWS_DATA_DIR env variable using "
  msg += f"os.path.expanduser('{data_dir}'). Exiting with code 1."
  error(msg)


if len(sys.argv) < 4:
  msg = "At least three command line arguments needed:\n"
  msg += "  python data.py <id> <start> <stop> [<parameters>]"
  error(msg)

id, start, stop = sys.argv[1], sys.argv[2], sys.argv[3]

if len(sys.argv) > 4:
  parameters = [p.strip() for p in sys.argv[4].split(",")]
else:
  parameters = ['Field_Vector', 'rxryrz', 'rt', 'lt', 'Tm']

if debug:
  print(f"Debug: dataset: {id}, start: {start}, stop: {stop}")

files = files_needed(id, start, stop, data_dir)
for files in files:
  print_data(id, files, start, stop, parameters, data_dir)
