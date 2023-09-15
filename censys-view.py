import argparse
import sys
import pandas as pd
import re
from censys.search import CensysHosts
from collections.abc import MutableMapping

def _flatten_dict_gen(d, parent_key, sep):
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, MutableMapping):
            yield from flatten_dict(v, new_key, sep=sep).items()
        else:
            yield new_key, v


def flatten_dict(d: MutableMapping, parent_key: str = '', sep: str = '.'):
    return dict(_flatten_dict_gen(d, parent_key, sep))

ipregex = re.compile(r'(?:(?:\d|[01]?\d\d|2[0-4]\d|25[0-5])\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d|\d)(?:\/\d{1,2})?')

def create_iplist(input):
    iplist = []
    for line in input:
        line = line.strip()

        match_ipregex = ipregex.match(line)

        if match_ipregex:
            iplist.append(line)

        elif not match_ipregex:
            pass
    return(iplist)

def create_results_dataframe(ip_list):
    df_list = []
    for ip in ip_list:
        result = get_individual_ip_result(ip)
        df_list.append(result)

    concatenated_df = pd.concat(df_list)
    return(concatenated_df)

def get_individual_ip_result(ip):
    h = CensysHosts()
    d = h.view(ip.strip())
    d = pd.json_normalize(d)
    d = flatten_dict(d)
    df = pd.DataFrame.from_dict(d)
    df = df.explode('services') 
    df = df.reset_index(drop=True)
    serv = [x for x in df['services']]
    res = pd.concat([df.drop('services', axis=1), pd.json_normalize(serv)], axis=1)
    res = res.reset_index(drop=True)
    if 'labels' in res.columns:
        res = res.drop('labels', axis =1)
    else:
        pass
    return(res)

def write_csv(df, csv_path):
    df.to_csv(str(csv_path))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", nargs="?", action="store", help="OPTIONAL - name of file containing IPs of interest; if not provided, reads from STDIN")
    parser.add_argument("--outputname", "-o", action="store", help="optional output path - default is censys_output.csv")

    args = parser.parse_args()

    if (args.input_file):
        with open(args.input_file, 'r') as file:
            iplist = create_iplist(file)
    else:
        data = sys.stdin.readlines()
        iplist = create_iplist(data)

    try:
        results = create_results_dataframe(iplist)
    except:
        print("There was an error creating the results DataFrame")
    
    if(args.outputname):
        path = args.outputname
    else:
        path = 'censys_output.csv'

    write_csv(results, path)

if __name__ == '__main__':
    main()