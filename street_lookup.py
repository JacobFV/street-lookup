import os
import re
import csv
import sys
import time
import random
import requests
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import display

### ========================================
### ======== USER INTERFACE HERE ===========
### ========================================

ZIP = '75165'  # make empty ('') if there is no definite zip
data = [
    ('Ennis St.', (200, 214), None),
    ('Peters St.', (97, 119), None),
    ('Coats St.', (None, None), None),
    ('E Ross St.', (1002, 1201), None),
    ('Saddlers St.', (303, 305), None),
    ('E Parks Ave.', (600, 799), None),
    ('Bradshaw St.', (None, None), None),
    ('Bradshaw Ct.', (None, None), None),
    ('Thompson St.', (None, None), None),
    ('Henderson St.', (None, None), None),
]

### ========================================
### ======== END USER INTERFACE ============
### ========================================


# Structure data
header = ['street', 'situs', 'filename']
data = pd.DataFrame(data=data, columns=header)

if len(ZIP) != 0:
    data['street'] = data['street'].apply(lambda s: f'{s} {ZIP}')

# download data for streets with no csv
for row in data.itertuples():
    if row.filename is None:
        filename = f'/tmp/file{time.time()}.csv'
        print(f'looking up {row.street}')
        r = requests.get(
                url='https://esearch.elliscad.com/Search/SearchResultDownload', 
                params={'keywords': row.street})
        with open(filename, 'w') as csv_file:
            csv_file.write(r.text)
        data.at[row.Index, 'filename'] = filename
        
# format csv into text and validate
valid_cities = ['Waxahachie', 'Ennis', 'Pecan Hill', 'Rockett', 'Ike', 
                'Palmer', 'Boyce', 'Rockett', 'Red Oak', 'Reagor Springs',
                'Howard', 'Garrett', 'Alma', 'Bardwell', 'Nash', 'Forreston', 
                'Italy', 'Avalon', 'Byrd']

remove_name_keys = ['llc', 'l/e', 'ltd', 'c/e', 
                    'trust', 'trist', 'trustee',
                    'company', 'owner', 'owners',
                    'property', 'properties', ]

all_names = []
street = None
def validate(name, addr, situs, situs_range=(None, None)):

    split_addr = addr.split()
    
    # remove records w/o a number
    if not split_addr[0].isnumeric():
        return False, f'No street number for \"{addr}\"'
    
    number = int(split_addr[0])
    
    # validate situs against number
    if number != situs:
        return False, f'Situs number ({situs}) does not equal number ({number}) ' + \
                      f'extracted from address: {address}'
    
    # remove records whose number is out of range
    situs_low, situs_high = situs_range
    if situs_low is not None:
        if row.situs < situs_low:
            return False, f'Situs number ({situs}) not in the specified range [{situs_low}, {situs_high}]'
        if row.situs > situs_high:
            return False, f'Situs number ({situs}) not in the specified range [{situs_low}, {situs_high}]'
    
    # remove redundant names
    # this catches finding "John Jr McDonald" inside "John & Michael McDonald"
    for row_name in all_names:
        sub_matches = 0
        name_splits = name.split()
        name_splits = [w for w in name_splits if len(w) > 2]
        for part in name_splits:
            if part in row_name:
                sub_matches += 1
        if sub_matches / len(name_splits) >= 0.75:  # 2 for first and last name
            return False, f'Duplicate resident \"{name}\" matches \"{row_name}\"'
    all_names.append(name)
    
    # remove non-resident records
    for key in remove_name_keys:
        if key in name.lower():
            return False, f'\"{name}\" is not a resident'
    
    # remove records that don't belong to this street
    # This code assumes the first address record has the correct street
    # this_street = split_addr[1]
    # if street is None:
    #     street = this_street
    # elif street != this_street:
    #     return False, f'address \"{addr}\" not on street \"{street}\"'
    
    # remove records not in TX
    if split_addr[-2] != 'TX':
        return False, f'Address not in Texas {addr}'

    # make sure address is in a valid city
    if not any(valid_city.lower() in addr.lower() for valid_city in valid_cities):
        return False, f'This address is not in a valid city: {addr}'
    
    return True, 'valid'

def format_name(name):
    splits = name.split()

    if 'etal' in name.lower():  # 'VALDEZ JACOB ETAL'
        if len(splits) == 3 and splits[-1].lower() == 'etal':
            return f'{splits[1]} {splits[0]}'.title()
        else:
            return name
    elif len(splits) == 2:  # 'VALDEZ JACOB'
        return f'{splits[1]} {splits[0]}'.title()
    elif len(splits) == 3:  # 'GATTIN ANTHONY CHARLES'
        return f'{splits[1]} {splits[2]} {splits[0]}'.title()
    elif '&' in splits:
        if splits[0] in splits[1:]:
            return f'{splits[0]} Family'.title()
        else:
            return ' '.join(splits[1:]+[splits[0]]).title()
    else:
        return name

def format_addr(addr, default_zip=75165):
    addr = addr.title()
    addr = re.sub('(\r|\n) ', '\r', addr)
    addr = re.sub('Tx', 'TX', addr)
    if not addr[-5:].isnumeric():
        addr = f'{addr} {default_zip}'
    return addr


## main code
all_names_and_addresses = list()
for row in data.itertuples():  
    
    i = row.Index
    # street = row.street
    situs_range = row.situs
    filename = row.filename
    
    street = None
    names_and_addresses = list()
    
    df = pd.read_csv(filename)
    display(df.head(5))
    
    df = df[['Owner Name', 'Address', 'Street Number']]
    df.columns = ['name', 'addr', 'situs']
    
    for row in df.itertuples():
        
        name = format_name(row.name)
        addr = format_addr(row.addr)
        situs = row.situs
        
        valid, err = validate(name, addr, situs, situs_range)
        if not valid: 
            logging.error(err)
            logging.info(f'skipping invalid record: {row}')
            continue
            
        names_and_addresses.append(f'{name} \n{addr}\n')
    all_names_and_addresses.append(names_and_addresses)
        
output_str = str()
for names_and_addresses in all_names_and_addresses:

    for name_and_address in names_and_addresses:
        output_str += name_and_address + "\n"
    output_str += 32 * "_" + "\n"
    
with open('/tmp/output.txt', 'w') as f:
    f.write(output_str)
    
!xdg-open /tmp/output.txt