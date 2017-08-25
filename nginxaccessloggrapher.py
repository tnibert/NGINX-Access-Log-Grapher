#! /usr/bin/env python

"""
This script will graph the nginx access log for you.
You can configure the options via the constants at the top of the script.
Able to graph individual IP addressed accessing.
"""

__author__ = "Richard O'Dwyer/Tim Nibert"
__license__ = "MIT"

import re
from operator import itemgetter
import datetime
import matplotlib.pyplot as plt; plt.rcdefaults()
from datetime import timedelta
from collections import OrderedDict
import pandas as pd
from copy import deepcopy
from matplotlib import dates

IVAL=5                                                  # interval in minutes
ROLL=5                                                  # how many intervals to roll
IPSPLIT=True                                            # show graphs for individual IPs
TOTALTRAFFIC=True                                       # show graph for total traffic (all IPs)
IPVIEW=['127.0.0.1']               # fill this list with the ips you want to check, if empty we will show all IPs
FILENAME='example.log'
# graph types enabled:
GRAPHNORMAL=True
GRAPHROLLED=True
GRAPHCUMULATIVE=True
# add variables for a time range

#fig = plt.figure(figsize=(10,8))

def process_log(log):
    requests = get_requests(log)
    #files = get_files(requests)
    #totals = file_occur(files)
    totals = get_times(requests)
    return totals

def get_requests(f):
    log_line = f.read()
    pat = (r''
           '(\d+.\d+.\d+.\d+)\s-\s-\s' #IP address
           '\[(.+)\]\s' #datetime
           '"GET\s(.+)\s\w+/.+"\s' #requested file
           '(\d+)\s' #status
           '(\d+)\s' #bandwidth
           '"(.+)"\s' #referrer
           '"(.+)"' #user agent
        )
    requests = find(pat, log_line)
    return requests

def find(pat, text):
    match = re.findall(pat, text)
    if match:
        return match
    return False

def get_times(requests):
    """
    return list of times
    """
    timelist = []
    for req in requests:
        timelist.append((req[0], convertStrToDatetime(req[1])))     # tuple of (ip, time of request)
    return timelist

def convertStrToDatetime(dtstr):
    #03/Jul/2017:09:50:05 +1000
    # we will drop the +1000, so graph will be in UTC
    dtstr = dtstr.split(' ', 1)[0]
    return datetime.datetime.strptime(dtstr, "%d/%b/%Y:%H:%M:%S")

def generate_graph_dict(times):
    """
    param list of times, returned from process_log in this file
    returns ordered dictionary of form { time_slice_start : request_count }
    """
    #block is the amount of time that we tally over, set with IVAL global
    block = timedelta(minutes=IVAL)
    start = times[0]
    graphdict = OrderedDict()
    end = start + block

    # iterate through all times and tally up each request, if we reach end, move to next block
    for time in times:
        if start not in graphdict:
            graphdict[start] = 0
        if(time <= end):
            try:
                graphdict[start] += 1
            except:
                graphdict[start] = 1
        else:
            # if we haven't yet created a count for the time (eg if no entries in time range) set to 0, then seek start to next block
            while(time > end):
                start = end
                end = start + block
                graphdict[start] = 0
            graphdict[start] += 1

    return graphdict


def graphcumulative(graphdict, ip='full system'):
    dates = graphdict.keys()
    counts = graphdict.values()
    cp = deepcopy(graphdict)
    i = 1
    for date in dates[1:]:
        cp[date] = counts[i] + counts[i-1]
        counts[i] = cp[date]
        #print date
        #print i
        #print counts[i-1]
        #print counts[i]
        #print graphdict[date]
        i += 1
    graph(cp, 'Cumulative ' + ip)
        
def graph(graphdict, title='Graph'):
    x = graphdict.keys()
    y = graphdict.values()
    #print graphdict.keys()
    #plt.plot(x, y)

    fig, ax = plt.subplots(1)

    ax.xaxis_date()
    xfmt = dates.DateFormatter('%d-%m-%y %H:%M')
    ax.xaxis.set_major_formatter(xfmt)

    locs, labels = plt.xticks()
    plt.setp(labels, rotation=30, horizontalalignment='right')

    plt.plot(x,y)
    ax.set_title(title)

    #plt.show()

def graphrolling(graphdict, ip='full system'):
    #put graphdict into a dataframe
    data = { 'date':graphdict.keys(), 'count':graphdict.values() }
    df = pd.DataFrame(data, columns = ['date', 'count'])
    #print(df)
    df.index = df['date']
    del df['date']
    #print df

    #create roll
    dfb = pd.rolling_mean(df, ROLL)
    #print dfb

    ax = dfb.plot()
    ax.xaxis_date()
    xfmt = dates.DateFormatter('%d-%m-%y %H:%M')
    ax.xaxis.set_major_formatter(xfmt)
    titlestr = "Rolling Average on " + str(ROLL) + " count roll for " + ip
    ax.set_title(titlestr)

    plt.sca(ax)
    #plt.show()

def get_files(requests):
    #get requested files with req
    requested_files = []
    for req in requests:
        # req[2] for req file match, change to
        # data you want to count totals
        requested_files.append(req[2])
    return requested_files

def file_occur(files):
    # file occurrences in requested files
    d = {}
    for file in files:
        d[file] = d.get(file,0)+1
    return d

if __name__ == '__main__':

    #nginx access log, standard format
    log_file = open(FILENAME, 'r')

    # return tuple of times and ips
    timesandips = process_log(log_file)
    #print len(timesandips)

    if len(IPVIEW) == 0:
        ips = [x[0] for x in timesandips]
        uniqueips = list(set(ips))
        print uniqueips
        #try:
        #    input = raw_input
        #except NameError:
        #    pass
    else:
        uniqueips = IPVIEW

    # create graphs of total traffic
    if(TOTALTRAFFIC):
        times = [x[1] for x in timesandips]
        #print len(times)
        gd = generate_graph_dict(times)
        # display time intervals and number present
        #for k,v in gd.items():
        #    if(True):
        #        print str(k) + " " + str(v)
                #pass
        ivalstr = "On interval " + str(IVAL) + " minutes for full system"
        if(GRAPHNORMAL): graph(gd, ivalstr)
        if(GRAPHROLLED): graphrolling(gd)
        if(GRAPHCUMULATIVE): graphcumulative(gd)

    # create graphs by ip
    if(IPSPLIT):
        for ip in uniqueips:
            times = [x[1] for x in timesandips if x[0] == ip]

            gd = generate_graph_dict(times)
            #for k,v in gd.items():
            #    if(v > 0):
            #        print str(k) + " " + str(v)
                    #pass
            ivalstr = "On interval " + str(IVAL) + " minutes for " + ip
            if(GRAPHNORMAL): graph(gd, ivalstr)
            if(GRAPHROLLED): graphrolling(gd, ip)
            if(GRAPHCUMULATIVE): graphcumulative(gd, ip)

    plt.show()
