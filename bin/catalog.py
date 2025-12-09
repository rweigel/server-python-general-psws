import os
import json

import madrigalWeb.madrigalWeb

debug = True
update = False
categories = ["Magnetometers"] # None for all categories

# The URL of the main Madrigal site you want to access
madrigalUrl = 'https://cedar.openmadrigal.org'

def getAllInstruments(update, categories=None):
  """Calls getAllInstruments() and returns a list of instrument dicts.

  Caches the result in catalog.instruments.json unless update=True.

  If categories is not None, filters instruments to only those in the given
  list of categories.
  """
  cache_file = 'catalog.instruments.json'

  # Create the main object to get all needed info from Madrigal
  madrigalData = madrigalWeb.madrigalWeb.MadrigalData(madrigalUrl)

  if update or not os.path.exists(cache_file):
    # Get all instruments from Madrigal
    if debug:
      print(f'Calling getAllInstruments: {madrigalUrl}')
    instrument_objects = madrigalData.getAllInstruments()

    # Convert to list of dicts for JSON serialization.
    instruments = []
    for instrument in instrument_objects:
      instruments.append(instrument.__dict__)

    # Cache
    with open(cache_file, 'w') as f:
      if debug:
        print('Writing instruments.json')
      json.dump(instruments, f, indent=2)

  else:

    # Load from cache
    with open(cache_file, 'r') as f:
      if debug:
        print(f'Reading {cache_file}')
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
catalog_json = json.dumps(catalog_list, indent=2)
print(catalog_json)
