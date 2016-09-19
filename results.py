#!/usr/bin/env python
'''
'''
import pprint

import sys
import statistics

import pymongo

MONGO_URI = 'mongodb://YOUR_URI'


if __name__ == '__main__':

    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

    # the collection containing the crawler results
    results_collection = mongo_client['crawler_data']['results']

    # total records in the collection with starting point "Special:Random" that did not have
    # an issue with the http request at any point in the chain of links.
    valid_records = int(results_collection.count({'starting_url': 'Special:Random'}))

    # total records that map to philosophy
    total_successes = int(results_collection.count({'reaches_philosophy': True, 'starting_url': 'Special:Random'}))

    print "Total number of pages: %d" % valid_records
    print
    print "Percentage of pages that often lead to philosophy? %.1f%%" % (100 * float(total_successes) / float(valid_records))
    print
    print "What is the distribution of path lengths, discarding those paths that never reach the Philosophy page? "

    distro = {}
    for page in results_collection.find({'reaches_philosophy': True, 'starting_url': 'Special:Random'}):
        path_link_length = len(page['urls']) - 1
        distro[page['urls'][0]] = path_link_length

    print "Size: ", len(distro.values())
    print "Mean: %.2f" % statistics.mean(distro.values())
    print "Median: %d" % statistics.median(distro.values())
    print "Std: %.2f" % statistics.stdev(distro.values())
    print
