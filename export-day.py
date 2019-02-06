# script for exporting a single day of data from local_store.db as a tap separated file
# 2019-02-06 A. Keller

import sqlite3
import os, sys, configparser, argparse
import time,datetime

def validdate(date_str):
    try:
        datetime.datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise ValueError("Incorrect date format, should be YYYY-MM-DD")


def execute_query(date_str,storage_location):

    table_name = 'message'
    start_date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
    end_date = start_date + datetime.timedelta(days=1)
    date_str2 = end_date.strftime('%Y-%m-%d')

    file_header = [
       "Daytime",
       "runtime",
       "spoven",
       "toven",
       "spcoil",
       "tcoil",
       "spband",
       "tband",
       "spcat",
       "tcat",
       "tco2",
       "pco2",
       "co2",
       "flow",
       "curr",
       'countdown',
       "statusbyte"]

    columns = [
       "time(timestamp) as Daytime",
       "runtime",
       "spoven",
       "toven",
       "spcoil",
       "tcoil",
       "spband",
       "tband",
       "spcat",
       "tcat",
       "tco2",
       "pco2",
       "co2",
       "flow",
       "curr",
       'printf("%d", countdown) as countdown',
       "statusbyte"]

    units = [
        "hh:mm:ss",
        "s",
        "degC",
        "degC",
        "degC",
        "degC",
        "degC",
        "degC",
        "degC",
        "degC",
        "degC",
        "kPa",
        "ppm",
        "lpm",
        "A",
        "s",
        "-"]

    query =  "SELECT " + ','.join(map(str, columns)) + " FROM " + table_name 
    query += " WHERE timestamp >= '" + date_str + "' AND timestamp < '" + date_str2 + "' AND runtime > 0"

    print >>sys.stderr, 'query = {0}'.format(query)

    conn = sqlite3.connect(storage_location)
    c = conn.cursor()

    # Creating file header
    print date_str                          # line 1 is the measurement date
    print "\t".join(map(str, file_header))  # column headers
    print "\t".join(map(str, units))        # units

    for row in c.execute(query):
        print "\t".join(map(str, row))
    conn.close()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Read the local_store.db file and extract the data for an specific date')
    parser.add_argument('--usedate', required=False, dest='DATE',
                        help='Use this date for generating the datafile (DATE=Today if omitted). Format: YYYY-MM-DD')
    parser.add_argument('--inifile', required=False, dest='INI', default='config.ini',
                        help='Path to configuration file (config.ini if omitted)')
    parser.add_argument('DB', nargs='?', default='local_store.db',
                        help='Database name (local_store.db if omitted')

    args = parser.parse_args()

    if args.DATE:
        date = args.DATE
        validdate(date)
    else:
        date = time.strftime("%Y-%m-%d")
        # date = "2019-02-03"

    config_file = args.INI
    if os.path.exists(config_file):
        config = configparser.ConfigParser()
        config.read(config_file)
        storage_location = eval(config['GENERAL_SETTINGS']['STORAGE_LOCATION']) + '/' + args.DB
    else:
        storage_location = args.DB
        print >>sys.stderr, 'Could not find the configuration file {0}'.format(config_file)

    if os.path.exists(storage_location):
        print >>sys.stderr, 'Using {0} as database file'.format(storage_location)
        print >>sys.stderr, 'Using {0} as date for the query'.format(date)
        execute_query(date,storage_location)
    else:
        print >>sys.stderr, 'Could not find the database at {0}'.format(storage_location)

