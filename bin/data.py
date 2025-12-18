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
#  python data.py S000028 2025-10-20T00:00:00Z 2025-10-21T00:00:00Z
#  python data.py S000028 2025-10-20T00:00:00Z 2025-10-21T00:00:00Z Field_Vector

import os
import re
import sys
import json
import datetime

debug = False


def error(emsg):
  print(emsg, file=sys.stderr)
  exit(1)


def files_needed(id, start, stop, data_dir):
  dataset_dir = os.path.join(data_dir, id)
  if not os.path.exists(dataset_dir):
    print(f"Directory not found: {dataset_dir}", file=sys.stderr)
    sys.exit(1)

  files = [f for f in os.listdir(dataset_dir) if f.endswith("runmag.log")]
  files.sort()
  if not files:
    sys.exit(0)

  if debug:
    print(f"Debug: Found {len(files)} files that end with runmag.log in {dataset_dir}")

  # Extract date from files with name of form w2naf-20251021-runmag.log
  date_re = re.compile(r'-[0-9]{8}-')

  files_needed = []
  # Convert from HAPI ISO date to YYYYMMDD, which is used in filenames
  start = start.replace("-", "")[0:8]
  stop = stop.replace("-", "")[0:8]

  if debug:
    print(f"Debug: Looking for files with data in range [{start}, {stop}]")

  for file in files:
    m = date_re.search(file)
    if m:
      file_date = m.group(0)[1:-1]  # YYYYMMDD
      if start <= file_date <= stop:
        files_needed.append(file)

  if debug:
    print(f"Debug: Found {len(files_needed)} files with data in range [{start}, {stop}]")

  return files_needed


def read_file(id, filename, start, stop, parameters, data_dir):
  filepath = os.path.join(data_dir, id, filename)
  # Row format:
  # {'ts': '21 Oct 2025 04:01:59', 'rt': 32.5, 'lt': 41.69,
  #  'x': -45676.67, 'y': -13284.67, 'z': 16150.67,
  #  'rx': -68515, 'ry': -19927, 'rz': 24226, 'Tm': 50236.2845}
  with open(filepath, 'r') as f:
    for line in f:
      if line.startswith('{'):
        entry = json.loads(line)
      else:
        # TODO: Read other format
        pass

      ts = entry['ts']
      try:
        dt = datetime.datetime.strptime(ts, '%d %b %Y %H:%M:%S')
        entry['ts'] = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
      except Exception as e:
        if debug:
          print(f"Debug: Failed to parse ts '{ts}': {e}", file=sys.stderr)

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


with open(os.path.join(os.path.dirname(__file__), "..", "config.json"), 'r') as f:
  try:
    config_all = json.load(f)
    config = config_all['module']
  except Exception as e:
    error(f"Error: Could not parse config file: {e}")
    exit(1)

# Get data_dir from environment variable
data_dir = config.get('data_dir', None)
if data_dir is None:
  error("No data_dir in config['module']. Exiting with code 1.")

try:
  data_dir = os.path.expanduser(data_dir)
except Exception as e:
  error(f"Could not expand data_dir = '{data_dir}': {e}. Exiting with code 1.")

if debug:
  print(f"data_dir: {data_dir}")

if len(sys.argv) < 4:
  error("At least three command line arguments needed: python data.py <id> <start> <stop> [<parameters>]")

id, start, stop = sys.argv[1], sys.argv[2], sys.argv[3]

if len(sys.argv) > 4:
  parameters = [p.strip() for p in sys.argv[4].split(",")]
else:
  parameters = ['Field_Vector', 'rxryrz', 'rt', 'lt', 'Tm']

if debug:
  print(f"Debug: dataset: {id}, start: {start}, stop: {stop}")

files = files_needed(id, start, stop, data_dir)
for files in files:
  read_file(id, files, start, stop, parameters, data_dir)
