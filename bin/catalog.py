import os
import json

import util

debug = True
update = False


def getAllInstruments(update, data_dir, categories=None):
  """Calls getAllInstruments() and returns a list of instrument dicts.

  Caches the result in catalog.instruments.json unless update=True.

  If categories is not None, filters instruments to only those in the given
  list of categories.
  """
  cache_dir = os.path.join(data_dir, 'madrigal')
  cache_file = os.path.join(cache_dir, 'instruments.json')

  if update or not os.path.exists(cache_file):

    # Create the main object to get all needed info from Madrigal
    if debug:
      print(f"Calling madrigalWeb.madrigalWeb.MadrigalData('{config['madrigalUrl']})'")
    madrigalData = util.madrigalData(debug=debug)

    # Get all instruments from Madrigal
    if debug:
      print(f'Calling getAllInstruments: {config['madrigalUrl']}')
    instruments = madrigalData.getAllInstruments()

    instruments = util.to_dicts(instruments)

    # Cache
    util.write_json(cache_file, instruments)

  else:

    # Load from cache
    instruments = util.read_json(cache_file, debug=debug)

  if debug:
    print(f'Found {len(instruments)} instruments')

  if categories is not None:
    # Filter instruments by category
    instruments = [instrument for instrument in instruments if instrument['category'] in categories]

  if debug:
    print(f'Found {len(instruments)} instruments with category in {categories}')

  for instrument in instruments:
    cache_file = os.path.join(cache_dir, "instruments", f"{instrument['code']}.json")
    if debug:
      print(f'Writing {cache_file}')
    util.write_json(cache_file, instrument)

  return instruments


def hapi_catalog(instruments, data_dir):
  catalog = []
  # If mnemonic is unique, use it as id?
  for instrument in instruments:
    dataset = {
      'id': instrument['code'],
      'title': instrument['name'],
      'x_category': instrument['category'],
      'x_mnemonic': instrument['mnemonic'],
    }
    catalog.append(dataset)

  catalog_file = os.path.join(data_dir, 'hapi', 'catalog.json')
  util.write_json(catalog_file, catalog)

  return catalog


config = util.config()

instruments = getAllInstruments(update, config['dataDir'], config['categories'])

catalog = hapi_catalog(instruments, config['dataDir'])

catalog_json = json.dumps(catalog, indent=2)
#print(catalog_json)
