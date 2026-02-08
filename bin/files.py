import os
from pathlib import Path

# For debugging - print first two lines of each file only
print_first_lines = False

# Get all files in ../data/*/magData directories
data_dir = Path(os.path.join(os.path.dirname(__file__), '..', 'data'))

def error(emsg):
  import sys
  print(emsg, file=sys.stderr)
  exit(1)

def error_log(filepath, line, line_no, emsg=None, e=None):
  print("    Error:")
  print(f"      Line {line_no}: {line}")
  if emsg:
    print(f"      Problem: {emsg}")
  if e:
    print(f"      Error: {e}")

def files(data_type):
  all_files = {}

  if data_type == 'mag':
    sub_dir = 'magData'

  for dir_name in data_dir.iterdir():
    if dir_name.is_dir():
      all_files[dir_name.name] = {}
      print(f"Found directory: {dir_name.name}")
      mag_data_dir = dir_name / sub_dir
      if not mag_data_dir.exists() or not mag_data_dir.is_dir():
        continue
      files = []
      for f in mag_data_dir.iterdir():
        if f.is_file() and f.name.endswith('.zip'):
          files.append(str(f.relative_to(data_dir)))
      files.sort()
      all_files[dir_name.name] = files

  return all_files

def print_data_mag(filepath):

  import re
  import sys
  import json
  import zipfile
  import datetime

  import pandas as pd

  debug = False

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

  parameters = None

  if print_first_lines:
    line_no = 0
    for line in data.splitlines():
      line_no += 1
      if line_no < 3:
        print(f"    line {line_no}: {line}")

      if line_no == 3:
        break

    return

  line_no = 0
  print(f"    # of lines: {len(data.splitlines())}")
  print(f"    first line: {data.splitlines()[0]}")
  print(f"    last line:  {data.splitlines()[-1]}")
  format = None

  format_last = None
  rows = []
  for line in data.splitlines():

    line_no += 1
    if debug:
      print(f"Debug: Processing line: {line}", file=sys.stderr)

    if line.startswith('{'):
      format = 1
      if format != format_last and format_last is not None:
        error_log(filepath, line, line_no, "Inconsistent row format")
        break
      format_last = 1
      # Row format:
      # {'ts': '21 Oct 2025 04:01:59', 'rt': 32.5, 'lt': 41.69,
      #  'x': -45676.67, 'y': -13284.67, 'z': 16150.67,
      #  'rx': -68515, 'ry': -19927, 'rz': 24226, 'Tm': 50236.2845}
      entry = json.loads(line)
      if len(entry) != 10:
        error_log(filepath, line, line_no, "Number of fields != 10")
        break

      ts = entry['ts']
      try:
        dt = datetime.datetime.strptime(ts, '%d %b %Y %H:%M:%S')
        entry['ts'] = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
      except Exception as e:
        error_log(filepath, line, line_no, "Failed to parse time value", e)
        break

    elif re.match(r'^"\d', line):
      # Row format:
      # TODO: Verify that these columns are correct.
      entry = line.split(', ')

      if len(entry) == 9:
        format = 2
      if len(entry) == 10:
        format = 3
      if format != format_last and format_last is not None:
        error_log(filepath, line, line_no, "Inconsistent row format")
        break
      format_last = format

      ts = entry[0].strip('"')
      try:
        dt = datetime.datetime.strptime(ts, '%d %b %Y %H:%M:%S')
      except Exception as e:
        error_log(filepath, line, line_no, "Failed to parse time value", e)
        break

      if format == 2:
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
          'Tm': -9999999
        }

      if format == 3:
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
      error_log(filepath, line, line_no, "Non-data line")
      break

    last_line = line
    row = entry['ts']

    if False:
      if parameters is None or 'Field_Vector' in parameters:
        row += f",{entry['x']},{entry['y']},{entry['z']}"
      if parameters is None or 'rxryrz' in parameters:
        row += f",{entry['rx']},{entry['ry']},{entry['rz']}"
      if parameters is None or 'rt' in parameters:
        row += f",{entry['rt']}"
      if parameters is None or 'lt' in parameters:
        row += f",{entry['lt']}"
      if parameters is None or 'Tm' in parameters:
        row += f",{entry['Tm']}"
    else:
      row = [
              entry['ts'], entry['x'], entry['y'], entry['z'],
              entry['rx'], entry['ry'], entry['rz'],
              entry['rt'], entry['lt'], entry['Tm']
            ]
      rows.append(row)

  # Create DataFrame from list of lists with time as index
  df = pd.DataFrame(rows, columns=['time', 'x', 'y', 'z', 'rx', 'ry', 'rz', 'rt', 'lt', 'Tm'])
  df['time'] = pd.to_datetime(df['time'])
  df.set_index('time', inplace=True)

  # Check that time is monotonically increasing
  if not df.index.is_monotonic_increasing:
    error_log(filepath, None, -1, "Time values are not monotonically increasing")

  return df

mag_files = files('mag')

for dataset in mag_files:
  print(f"Dataset: {dataset}")
  for filepath in mag_files[dataset]:
    print(f"  File: {filepath}")
    print_data_mag(os.path.join(data_dir, filepath))