import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
import h5py
from os import path
import requests
import json



def GetData(filepath='./',run_date=None):
    """ Downloads data from covidtracking.com and stores in a JSON file tagged
        with todays date.  If the JSON file already exists, we skip the download
        and just use the data in the cached json file.

        Args:
            filepath (string): Full path of where to save the json data file.

        Returns:
            python dictionary with the contents of the json file.
    """
    if run_date is None:
        today_str = datetime.date.today().strftime('%Y_%m_%d')
    else:
        today_str = run_date.strftime('%Y_%m_%d')
    filename = filepath + 'covidtracking_data_%s.json'%today_str

    json_text = None
    if(path.exists(filename)):
        #print('Reading data from file...')
        with open(filename) as json_file:
            all_data = json.load(json_file)
    else:
        #print('Downloading data...')
        url = 'https://covidtracking.com/api/v1/states/daily.json'
        r = requests.get(url)
        all_data = json.loads(r.text)

        with open(filename, 'w') as outfile:
            json.dump(all_data, outfile)

    return all_data

def ExtractDataFrame(json_data, start_date):
    """
    Extracts hospitalization and death data from the json object and stores it in a pandas
    DataFrame.  Missing data is filled with np.nan.

    Args:
        json_data (dict): The dictionary returned by the GetData function.
        start_date (date): The first day (inclusive) that we want to start
                           collecting data.   This is typically Jan. 22, 2020.
    """

    # A mapping from keys pandas dataframe we want to product to the keys the json dictionary
    keys = [('cum_positive','positive'),
            ('cum_total','total'),
            ('curr_hosp','hospitalizedCurrently'),
            ('cum_hosp','hospitalizedCumulative'),
            ('curr_icu','inIcuCurrently'),
            ('cum_icu','inIcuCumulative'),
            ('curr_vent','onVentilatorCurrently'),
            ('cum_vent','onVentilatorCumulative'),
            ('cum_death','death'),
            ('new_death','deathIncrease')]

    # will be array of tuples containing (state,date)
    indices = []

    # will contain the data (curr_hosp, cum_hosp, curr_icu, cum_icu, curr_vent, cum_vent)
    data = dict()

    # Initialize entries in the data dictionary to empty lists
    for key in keys:
        data[key[0]] = []

    # Will be a list of all the states in the json dictionary
    all_locations = []

    # Loop over the json data.  Each entry has a state and a name
    for entry in json_data:
        state = str(entry['state'])
        date = datetime.datetime.strptime(str(entry['date']), '%Y%m%d').date()

        all_locations.append(state)

        if(date>=start_date):
            indices.append((state, date))
            for key in keys:
                if(key[1] in entry.keys()):
                    if(entry[key[1]] is not None):
                        data[key[0]].append(entry[key[1]])
                    else:
                        data[key[0]].append(np.nan)
                else:
                    data[key[0]].append(np.nan)

    all_locations = np.unique(all_locations)

    # Create the dataframe using a multiindex [state,date] to define the rows
    index = pd.MultiIndex.from_tuples(indices, names=['state', 'date'])
    df = pd.DataFrame(data=data, index=index)
    df.sort_index(level=1,inplace=True)

    # For every state, go through and compute new_cases
    for state in df.index.unique(level=0):

        new_cases = np.zeros((df.loc[state]['cum_positive'].shape[0]))
        new_cases[1:] = np.diff(df.loc[state]['cum_positive'])
        df.loc[state,'new_cases'] = new_cases


    return df, all_locations


if __name__=='__main__':
    start_date = datetime.date(2020,2,1)
    json = GetData('./',start_date)
    df, locs = ExtractDataFrame(json, start_date)

    plt.figure(figsize=(10,5))
    state = 'AZ'
    plt.title('New Cases in reported %s'%state, fontsize=16)
    plt.plot(df.loc[state]['new_cases'], 'ob')
    plt.xlabel('Date',fontsize=16)
    plt.ylabel('New Cases',fontsize=16)

    ymin, ymax = plt.ylim()
    label_days = []
    for month in range(2,9):
        plt.plot([datetime.date(2020,month,1),datetime.date(2020,month,1)],[ymin,ymax],'--k')
        for day in [1,15]:
            label_days.append(datetime.date(2020,month,day))
    plt.xticks(label_days, rotation=25,fontsize=10)
    plt.xlim(datetime.date(2020,3,1), datetime.date(2020,8,1))
    plt.ylim(ymin,ymax)
    plt.show()
