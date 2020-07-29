# -*- coding: utf-8 -*-
"""
Created on Mon May 25 14:42:18 2020
Obtains stock data from Yahoo Finance API.
@author: Santiago Ruiz de A
"""

import re
from urllib.request import urlopen, Request, URLError
import calendar
import datetime
import getopt
import sys
import time
import pandas as pd
import os


crumble_link = 'https://finance.yahoo.com/quote/{0}/history?p={0}'
crumble_regex = r'CrumbStore":{"crumb":"(.*?)"}'
cookie_regex = r'set-cookie: (.*?); '
quote_link = 'https://query1.finance.yahoo.com/v7/finance/download/{}?period1={}&period2={}&interval=1d&events={}&crumb={}'

def get_crumble(symbol):
    link = crumble_link.format(symbol)
    response = urlopen(link)
    text = response.read().decode("utf-8")
    mt = re.search(crumble_regex, text)
    if mt is not None:
        crumble_str = mt.group(1)
        return crumble_str
    
def download_quote(symbol, date_from, date_to, events):
    time_stamp_from = calendar.timegm(
        datetime.datetime.strptime(date_from, "%Y-%m-%d").timetuple())
    next_day = (datetime.datetime.strptime(date_to, "%Y-%m-%d") + 
        datetime.timedelta(days=1))
    time_stamp_to = calendar.timegm(next_day.timetuple())
    attempts = 0
    while attempts < 5:
        if get_crumble(symbol) is None: return None
        crumble_str = get_crumble(symbol)
        link = quote_link.format(symbol, time_stamp_from, time_stamp_to,
                                 events, crumble_str)
        r = Request(link)
        try:
            response = urlopen(r)
            text = response.read()
            print ("{} downloaded".format(symbol))
            return text
        except URLError:
            print ("{} failed at attempt # {}".format(symbol, attempts))
            attempts += 1
            time.sleep(2 * attempts)
    return b''    

def get_data(symbol_val, is_fresh, start=None, end=None, days=None):
    """ 
    Returns pandas dataframe of Date, Adj Close, and Volume from Yahoo Finance, 
    or None if not available.
    End date can be assumed to be today.
    Start date is automatically one calendar year ago.
    Days ex: 365 for the past calendar year.
    """
    symbol_val = symbol_val.replace('.', '-') # BRK.B -> BRK-B
    event_val = "history" # historical data
    ##Path will need to be fixed in order to use a main script.
    output_val = os.path.join('..\\','data' ,symbol_val + '.csv')

    # set begin and end date time strings
    if start is None and end is None:
        from_val, to_val = get_date(days)
    elif end is None:
        from_val = start
        to_val = get_date_string(datetime.datetime.now())
    else:
        from_val = start
        to_val = end

    # use old data if present and if is_fresh
    if not is_fresh and os.path.isfile(output_val):
        try:
            return pd.read_csv(output_val, index_col='Date', parse_dates=True, 
                               usecols=['Date', 'Adj Close', 'Volume'], 
                               na_values=['NaN']).dropna()[from_val: to_val]
        except Exception:
            print('Failed from {}. Now fetching {} fresh.'.format(output_val, 
                                                                  symbol_val))

    # Download data from Yahoo
    print ("downloading {}".format(symbol_val))
    csv = download_quote(symbol_val, from_val, to_val, event_val)
    if csv is not None:
        with open(output_val, 'wb') as f:
            f.write(csv)
        print ("{} written to {}".format(symbol_val, output_val))
        return pd.read_csv(output_val, index_col='Date', parse_dates=True, 
                           usecols=['Date', 'Adj Close', 'Volume'], 
                           na_values=['NaN']).dropna()[from_val: to_val]
    
def get_date(days):
    """ 
    Returns starting and ending date (like '2018-08-15') 
    given amount of days to go back 
    """
    if days is None: days = 365 # Defaulted to one calendar year
    now = datetime.datetime.now()
    past = now - datetime.timedelta(days=days)
    return get_date_string(past), get_date_string(now)

def get_date_string(datetime):
    return '{}-{}-{}'.format(datetime.year, datetime.month, datetime.day)