import os
import json
from datetime import datetime

import madrigalWeb.madrigalWeb

debug = True        # Print debug info to stdout.
update = False      # False => used cached files when available.
test_run = False    # True => only get 1st experiment's files and 1st file's parameters.

url = 'https://cedar.openmadrigal.org'
user = ['CEDAR Example', 'example@gmail.com', 'CEDAR/GEM tutorial day 2025']

ids = None  # None for all ids
#ids = [8250]  # For testing, everything works
#ids = [8255] # No experiments

dirs = {
  'instruments': 'cache/madrigal/instruments',
  'data':        'cache/madrigal/data',
  'info':        'cache/hapi/info'
}


if debug:
  print(f"Calling madrigalWeb.madrigalWeb.MadrigalData('{url})'")

madDB = madrigalWeb.madrigalWeb.MadrigalData(url)


def format_time(exp, which):
  format_template = "{0:04d}-{1:02d}-{2:02d}T{3:02d}:{4:02d}:{5:02d}Z"
  timestamp = format_template.format(
    exp[f'{which}year'], exp[f'{which}month'], exp[f'{which}day'],
    exp[f'{which}hour'], exp[f'{which}min'], exp[f'{which}sec'])

  return timestamp


def write_json(file_name, data):
  if not os.path.exists(os.path.dirname(file_name)):
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
  with open(file_name, 'w') as f:
    json.dump(data, f, indent=2)


def to_dicts(obj):
  return [o.__dict__ for o in obj if o is not None]


def add_experiments(instrument, start, stop):

  experiment_dir = os.path.join(dirs['instruments'], str(instrument['code']))
  cache_file = os.path.join(experiment_dir, "experiments.json")

  if not update and os.path.exists(cache_file):
    # Load from cache
    with open(cache_file, 'r') as f:
      if debug:
        print(f'Reading {cache_file}')
      instrument['experiments'] = json.load(f)
    return

  if debug:
    msg = "Calling getExperiments() For instrument with code "
    msg += f"'{instrument['code']}' and name '{instrument['name']}'"
    print(msg)

  experiments = madDB.getExperiments(instrument['code'], *start, *stop)

  experiments = to_dicts(experiments)

  instrument['experiments'] = experiments

  if debug:
    if len(experiments) == 0:
      print("  No experiments found")
    else:
      print(f"  Found {len(experiments)} experiments")
    print(f'  Writing {cache_file}')

  write_json(cache_file, experiments)


def add_files(instrument):

  experiments = instrument['experiments']
  if len(experiments) == 0:
    return

  for idx, experiment in enumerate(experiments):

    if idx == 1 and test_run:
      # Only get files for first experiment
      break

    files_dir = os.path.join(str(instrument['code']), str(experiment['id']))
    files_file = os.path.join(dirs['instruments'], files_dir, "files.json")
    if not update and os.path.exists(files_file):
      # Load from cache
      with open(files_file, 'r') as f:
        if debug:
          print(f'Reading {files_file}')
        experiment['files'] = json.load(f)
      continue

    if debug:
      r = f"{idx+1}/{len(experiments)}"
      msg = f"  Experiment #{r}: id = '{experiment['id']}'; start = "
      msg += f"'{format_time(experiment, 'start')}'; stop = "
      msg += f"'{format_time(experiment, 'end')}'"
      print(msg)
      msg = "  Calling getExperimentFiles()"
      print(msg)

    files = madDB.getExperimentFiles(experiment['id'])

    if len(files) == 0:
      del experiment
      if debug:
        print("   Experiment has no files. Deleting experiment.")
      return

    files = to_dicts(files)

    if len(files) == 0:
      # TODO: Need to update catalog.json to remove this experiment.
      if debug:
        print("    No files found")

    experiment['files'] = files

    if debug:
      s = "s" if len(files) != 1 else ""
      print(f"    Found {len(files)} file{s}")

    if debug:
      print(f'    Writing {files_file}')
    write_json(files_file, files)


def add_parameters(instrument):

  experiments = instrument['experiments']
  for experiment in experiments:
    if 'files' not in experiment:
      continue

    files = experiment['files']
    for idx, file in enumerate(files):

      if idx == 1 and test_run:
        # Only get parameters for first file in first experiment
        break

      parameters_dir = os.path.join(str(instrument['code']), str(experiment['id']), f"{idx:09d}")
      parameters_file = os.path.join(dirs['instruments'], parameters_dir, "parameters.json")
      if not update and os.path.exists(parameters_file):
        # Load from cache
        with open(parameters_file, 'r') as f:
          if debug:
            print(f'Reading {parameters_file}')
          file['parameters'] = json.load(f)
        continue

      if debug:
        r = f"{idx+1}/{len(files)}"
        msg = f"    File #{r}: name = '{file['name']}'"
        print(msg)
        msg = "    Calling getExperimentFileParameters()"
        print(msg)

      parameters = madDB.getExperimentFileParameters(file['name'])

      if len(parameters) == 0:
        del file
        if debug:
          print("     File has no parameters. Deleting file.")
        return

      parameters = to_dicts(parameters)

      file['parameters'] = parameters

      if debug:
        s = "s" if len(parameters) != 1 else ""
        print(f"    Found {len(parameters)} parameter{s}")
        print(f'    Writing {parameters_file}')

      write_json(parameters_file, parameters)


def all_parameters(experiments):
  # Not tested.
  common_params = None
  for experiment in experiments:
    for file in experiment['files']:
      param_names = set()
      for parameter in file['parameters']:
        param_names.add(parameter['name'])
      if common_params is None:
        common_params = param_names
      else:
        common_params = common_params.intersection(param_names)
  return common_params


def download_file():

      if False:
        out_file = os.path.join(dirs['data'], file['name'].lstrip("/"))
        out_dir = os.path.dirname(out_file)
        if not os.path.exists(out_dir):
          os.makedirs(out_dir, exist_ok=True)

        if update or not os.path.exists(out_file):
          if debug:
            print(f"    Calling downloadFile() for {file['name']}")
          madDB.downloadFile(file['name'], out_file, *user, format='hdf5')

        if not update and debug:
          print(f"    Using cached file {out_file}")

        if debug:
          print(f"    Calling getExperimentFileParameters() for {out_file}")


def hapi_info(instrument):

  experiments = instrument['experiments']
  if len(experiments) == 0:
    return

  info = {
    'start': format_time(experiments[0], 'start'),
    'stop': format_time(experiments[-1], 'end'),
    'location':[
      instrument['latitude'],
      instrument['longitude'],
      instrument['altitude']
    ],
    'parameters': None,
    'additionalMetadata': [
      {
        'name': 'Instrument Metadata',
        'content': instrument
      },
      {
        'name': 'Experiment Metadata',
        'content': experiments
      }
    ]
  }

  parameters = []
  # Loop over madrigal instrument parameters
  for idx, p in enumerate(instrument.get('parameters', [])):

    if p.get('mnemonic', None) is None:
      if debug:
        print(f"    Parameter #{idx} has no mnemonic. Skipping.")
      continue

    parameter = {
      'name': p['mnemonic']
    }
    if p.get('description', None) is not None:
      parameter['description'] = p['description']
    if p.get('units', None) is not None:
      parameter['units'] = p['units']
    else:
      parameter['units'] = None

    parameters.append(parameter)

  info['parameters'] = parameters

  cache_file = os.path.join(dirs['info'], f"{instrument['code']}.json")
  if debug:
    print(f"Writing {cache_file}")
  write_json(cache_file, info)

  return info


# Read top-level instrument metadata generated by catalog.py from cache
fname = dirs['instruments'] + '.json'
with open(fname, 'r') as f:
  if debug:
    print(f'Reading {fname}')
  instruments = json.load(f)

if debug:
  print(f'Found {len(instruments)} instruments from catalog')

start = [1950, 1, 1, 0, 0, 0]
stop = [1 + datetime.now().year, 1, 1, 0, 0, 0]

infos = {}
for instrument in instruments:

  if ids is not None and instrument['code'] not in ids:
    continue

  # Read instrument metadata generated by catalog.py from cache
  fname = os.path.join(dirs['instruments'], f"{instrument['code']}.json")
  if not os.path.exists(fname):
    # Skip instruments omitted by catalog.py
    continue

  with open(fname, 'r') as f:
    if debug:
      print(f'Reading {fname}')
    instrument = json.load(f)

  # Add experiments to each instrument dict.
  add_experiments(instrument, start, stop)

  # Add files to each instrument dict.
  add_files(instrument)

  # Add parameters to each file dict.
  add_parameters(instrument)

  # Cache full instrument metadata
  fname = fname[:-5] + '.all.json'
  if not test_run:
    if debug:
      print(f"Writing {fname}")
    write_json(fname, instrument)

  # Create HAPI info response for this instrument
  info = hapi_info(instrument)
