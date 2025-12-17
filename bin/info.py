import os
import json

import util

debug = True        # Print debug info to stdout.
update = False      # False => used cached files when available.

test_run = False # True => only get 1st experiment's files and 1st file's parameters.
ids = None      # None for all ids
#ids = [8250]   # Everything works
#ids = [8255]   # No experiments


def format_time(exp, which):
  format_template = "{0:04d}-{1:02d}-{2:02d}T{3:02d}:{4:02d}:{5:02d}Z"
  timestamp = format_template.format(
    exp[f'{which}year'], exp[f'{which}month'], exp[f'{which}day'],
    exp[f'{which}hour'], exp[f'{which}min'], exp[f'{which}sec'])

  return timestamp


def add_experiments(instrument, madrigal_dir):

  from datetime import datetime

  start = [1950, 1, 1, 0, 0, 0]
  stop = [1 + datetime.now().year, 1, 1, 0, 0, 0]

  experiments_dir = os.path.join(madrigal_dir, 'instruments', str(instrument['code']))
  experiments_file = os.path.join(experiments_dir, "experiments.json")

  if not update and os.path.exists(experiments_file):
    # Load from cache
    instrument['experiments'] = util.read_json(experiments_file, debug=debug)
    return

  if debug:
    msg = "Calling getExperiments() For instrument with code "
    msg += f"'{instrument['code']}' and name '{instrument['name']}'"
    print(msg)

  madrigalData = util.madrigalData(debug=debug)

  experiments = madrigalData.getExperiments(instrument['code'], *start, *stop)

  experiments = util.to_dicts(experiments)

  instrument['experiments'] = experiments

  if debug:
    if len(experiments) == 0:
      print("  No experiments found")
    else:
      print(f"  Found {len(experiments)} experiments")

  util.write_json(experiments_file, experiments, debug=debug, indent=2)


def add_files(instrument, madrigal_dir):

  experiments = instrument['experiments']
  if len(experiments) == 0:
    return

  for idx, experiment in enumerate(experiments):

    if idx == 1 and test_run:
      # Only get files for first experiment
      break

    files_dir = os.path.join(str(instrument['code']), str(experiment['id']))
    files_file = os.path.join(madrigal_dir, 'instruments', files_dir, "files.json")
    if not update and os.path.exists(files_file):
      # Load from cache
      experiment['files'] = util.read_json(files_file, debug=debug)
      continue

    if debug:
      r = f"{idx+1}/{len(experiments)}"
      msg = f"  Experiment #{r}: id = '{experiment['id']}'; start = "
      msg += f"'{format_time(experiment, 'start')}'; stop = "
      msg += f"'{format_time(experiment, 'end')}'"
      print(msg)
      msg = "  Calling getExperimentFiles()"
      print(msg)

    madrigalData = util.madrigalData(debug=debug)

    files = madrigalData.getExperimentFiles(experiment['id'])

    if len(files) == 0:
      del experiment
      if debug:
        print("   Experiment has no files. Deleting experiment.")
      return

    files = util.to_dicts(files)

    if len(files) == 0:
      # TODO: Need to update catalog.json to remove this experiment.
      if debug:
        print("    No files found")

    experiment['files'] = files

    if debug:
      s = "s" if len(files) != 1 else ""
      print(f"    Found {len(files)} file{s}")

    util.write_json(files_file, files, debug=debug, indent=4)


def add_parameters(instrument, madrigal_dir):

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
      parameters_file = os.path.join(madrigal_dir, 'instruments', parameters_dir, "parameters.json")
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

      madrigalData = util.madrigalData(debug=debug)
      parameters = madrigalData.getExperimentFileParameters(file['name'])

      if len(parameters) == 0:
        del file
        if debug:
          print("     File has no parameters. Deleting file.")
        return

      parameters = util.to_dicts(parameters)

      file['parameters'] = parameters

      if debug:
        s = "s" if len(parameters) != 1 else ""
        print(f"    Found {len(parameters)} parameter{s}")
        print(f'    Writing {parameters_file}')

      util.write_json(parameters_file, parameters, debug=debug, indent=4)


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


def hapi_info(instrument, hapi_dir):

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

  cache_file = os.path.join(hapi_dir, 'info', f"{instrument['code']}.json")
  util.write_json(cache_file, info, debug=debug)

  return info


config = util.config()

madrigal_dir = os.path.join(config['dataDir'], "madrigal")
hapi_dir = os.path.join(config['dataDir'], "hapi")

# Read top-level instrument metadata generated by catalog.py
instruments_file = os.path.join(madrigal_dir, "instruments.json")
instruments = util.read_json(instruments_file, debug=debug)

if debug:
  print(f'Found {len(instruments)} instruments from catalog')

for instrument in instruments:

  if ids is not None and instrument['code'] not in ids:
    continue

  # Instrument metadata generated by catalog.py from cache
  instrument_file = f"{instrument['code']}.json"
  instrument_file = os.path.join(madrigal_dir, "instruments", instrument_file)

  if not os.path.exists(instrument_file):
    # Skip instruments omitted by catalog.py
    continue

  instrument = util.read_json(instrument_file, debug=debug)

  # Add experiments to each instrument dict.
  add_experiments(instrument, madrigal_dir)

  # Add files to each instrument dict.
  add_files(instrument, madrigal_dir)

  # Add parameters to each file dict.
  add_parameters(instrument, madrigal_dir)

  if not test_run:
    # Cache all instrument metadata
    instrument_file_all = instrument_file[:-5] + '.all.json'
    util.write_json(instrument_file_all, instrument, debug=debug)

  # Create HAPI info response for this instrument
  info = hapi_info(instrument, hapi_dir)
