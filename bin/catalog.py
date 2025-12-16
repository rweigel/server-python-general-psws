import os
import json

import madrigalWeb.madrigalWeb

debug = True
update = False
categories = ["Magnetometers", "Fabry-Perots"] # None for all categories

files = {
  'instruments': 'cache/madrigal/instruments.json',
  'catalog': 'cache/hapi/catalog.json'
}
dirs = {
  'instruments': 'cache/madrigal/instruments'
}

# The URL of the main Madrigal site you want to access
madrigalUrl = 'https://cedar.openmadrigal.org'


def write_json(file_name, data):
  if not os.path.exists(os.path.dirname(file_name)):
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
  with open(file_name, 'w') as f:
    json.dump(data, f, indent=2)


def getAllInstruments(update, categories=None):
  """Calls getAllInstruments() and returns a list of instrument dicts.

  Caches the result in catalog.instruments.json unless update=True.

  If categories is not None, filters instruments to only those in the given
  list of categories.
  """
  cache_dir = os.path.dirname(files['instruments'])
  os.makedirs(cache_dir, exist_ok=True)

  # Create the main object to get all needed info from Madrigal
  madrigalData = madrigalWeb.madrigalWeb.MadrigalData(madrigalUrl)

  if update or not os.path.exists(files['instruments']):
    # Get all instruments from Madrigal
    if debug:
      print(f'Calling getAllInstruments: {madrigalUrl}')
    instrument_objects = madrigalData.getAllInstruments()

    # Convert to list of dicts for JSON serialization.
    instruments = []
    for instrument in instrument_objects:
      instruments.append(instrument.__dict__)

    # Cache
    with open(files['instruments'], 'w') as f:
      if debug:
        print(f'Writing {files['instruments']}')
      json.dump(instruments, f, indent=2)

  else:

    # Load from cache
    with open(files['instruments'], 'r') as f:
      if debug:
        print(f'Reading {files['instruments']}')
      instruments = json.load(f)

  if debug:
    print(f'Found {len(instruments)} instruments')

  if categories is not None:
    # Filter instruments by category
    instruments = [instrument for instrument in instruments if instrument['category'] in categories]

  return instruments


def catalog(instruments):
  catalog_list = []
  # If mnemonic is unique, use it as id?
  for instrument in instruments:
    dataset = {
      'id': instrument['code'],
      'title': instrument['name'],
      'x_category': instrument['category'],
      'x_mnemonic': instrument['mnemonic'],
    }
    catalog_list.append(dataset)
  return catalog_list

instruments = getAllInstruments(update, categories=categories)
catalog_list = catalog(instruments)

if debug:
  print(f'Writing {files["catalog"]}')
write_json(files['catalog'], catalog_list)

for instrument in instruments:
  cache_file = os.path.join(dirs['instruments'], f"{instrument['code']}.json")
  if debug:
    print(f'Writing {cache_file}')
  write_json(cache_file, instrument)

catalog_json = json.dumps(catalog_list, indent=2)
print(catalog_json)
