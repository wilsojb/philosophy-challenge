#!env/bin/python
'''
@createdOn: 20160331
@author: wilsojb@gmail.com
@credit: http://www.gyford.com/phil/writing/2015/03/25/wikipedia-parsing.php
@credit: http://matpalm.com/blog/2011/08/13/wikipedia-philosophy/
@credit: https://en.wikipedia.org/wiki/Wikipedia:Getting_to_Philosophy

'''

import argparse
import logging
import pprint
import os
import sys

import bs4
import requests
import pymongo

# global client. only initialized once.
_MONGO_CLIENT = None

def getMongoClient():
  global _MONGO_CLIENT
  if _MONGO_CLIENT is None:
    # a mongo instance set up using mlab.com. the data that gets pulled from here is used to
    # 'prime' the crawler with urls that will successfully map to the philosophy page.
    try:
      # args.mongo defaults to a 'read-only' user/pass == "read:read"
      mongo_uri = 'mongodb://YOUR_URI' % args.mongo
      mongo_connection = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
      _MONGO_CLIENT = mongo_connection['crawler_data']
    except Exception as e:
      logging.exception(e)
  return _MONGO_CLIENT


class Spider(object):

  @classmethod
  def getHtml(cls, url):
    '''
    Fetches HTML content (not the entire HTML page) and returns it.
    Returns a dict with three elements:
      'success' is either True or, if we couldn't fetch the page, False.
      'content' is the HTML if success==True, or else an error message.
      'url' is the url pointing to the returned content.
    '''
    error_message = ''
    complete_url = url
    if not url.startswith('http'):
      complete_url = 'http://en.wikipedia.org/wiki/' + url

    try:
      # The key benefit to passsing ?action=render to the get request
      # is that it strips away most of the formatting and other crud
      # that gets in the way of the actual parsing and link mining
      response = requests.get(complete_url, params={'action':'render'}, timeout=5)
      response.url = (response.url
        .replace('&action=render', '')
        .replace('?action=render', '')
        .replace('http://en.wikipedia.org/wiki/', '')
        .replace('https://en.wikipedia.org/wiki/', '')
        .replace('https://en.wikipedia.org/w/index.php?title=', ''))

    except requests.exceptions.ConnectionError as e:
      error_message = "Can't connect to domain."
    except requests.exceptions.Timeout as e:
      error_message = "Connection timed out."
    except requests.exceptions.TooManyRedirects as e:
      error_message = "Too many redirects."

    try:
      response.raise_for_status()
    except requests.exceptions.HTTPError as e:
      # 4xx or 5xx errors:
      error_message = "%s HTTP Error: %s" % (complete_url, response.status_code)
    except NameError:
      if error_message == '':
        error_message = "Something unusual went wrong."

    if error_message:
      return {'success': False, 'content': error_message, 'url': None}
    else:
      return {'success': True, 'content': response.text, 'url': response.url}


  @classmethod
  def findFirstLink(cls, html):
    '''
    Returns the first valid link on the page or 'None' if there
    was an error or it was unsuccessful.
    '''
    soup = bs4.BeautifulSoup(html, 'html.parser')

    # Let's ignore some common tags found on wikipedia pages.
    # The final implementation may or may not depend on these
    # tags being ignored, but not having them around certainly
    # helps the debugging process:
    #   1) 'hatnotes' contain italicized links to related content
    #   2) 'thumb' is the thumbnail image and description
    #   3) there can be several different types of tables that
    #      appear in wikipedia pages. none are useful for this exercise
    ignores = ['div.hatnote', 'div.thumb', 'table']

    for ignore in ignores:
      for tag in soup.select(ignore):
        tag.decompose()

    # keep a counter around to determine if we are looking
    # at text w/i parenthesis
    parentheticalCount = 0

    # for "well behaved" pages, the link I'm searching for
    # will be under a paragraph tag.
    for paragraph in soup.find_all(['p', 'ul', 'ol']):
      for child in paragraph.children:
        if child.__class__ == bs4.element.Tag:
          # bingo! Now, make sure you aren't in a set
          # of parenthesis before declaring victory
          if child.name == 'a':
            if parentheticalCount == 0:

              href = child['href']
              if not href.startswith('http'):
                href = 'http:'+href
              # wiki 'names' or full urls are allowed. this just adapts
              # one to the other when used reasonably.
              return (href.replace('&action=render', '')
                .replace('?action=render', '')
                .replace('http://en.wikipedia.org/wiki/', '')
                .replace('https://en.wikipedia.org/wiki/', '')
                .replace('https://en.wikipedia.org/w/index.php?title=', ''))

        # keep track of the parenthesis we find
        if child.__class__ == bs4.element.NavigableString:
          if '(' in child.string:
            parentheticalCount += child.string.count('(')
          if ')' in child.string:
            parentheticalCount -= child.string.count(')')
          if parentheticalCount < 0:
            # ouch! hard to parse...
            return None

    # no link found matching criteria
    return None


  def __init__(self, url, maxPages, successful_urls):
    super(Spider, self).__init__()
    self.num_path_links = 0
    self.successful_urls = {'Philosophy': ['Philosophy']}
    self.successful_urls.update(successful_urls)

    # wiki 'names' or full urls are allowed. this just adapts
    # one to the other when used reasonably.
    self.current_url = (url
      .replace('&action=render', '')
      .replace('?action=render', '')
      .replace('http://en.wikipedia.org/wiki/', '')
      .replace('https://en.wikipedia.org/wiki/', '')
      .replace('https://en.wikipedia.org/w/index.php?title=', ''))

    self.results = {
      'urls': [],
      'path_link_limit': int(maxPages),
      'starting_url': self.current_url,
      'message': '',
      'errors' : False,
      'reaches_philosophy': False,
    }


  def run(self):
    '''
    This applies the lookup strategy to a given url. This runs until either:
     a) The url matches a url that successfully maps to the Philosophy page.
     b) An error occurs with either the scraping or requesting
     c) The path_link_limit is reached. (This also catalogs an error)
    '''
    while self.current_url:
      if self.current_url in self.successful_urls:
        self.results['reaches_philosophy'] = True
        self.results['message'] = 'Found in cache'
        self.results['urls'].extend(self.successful_urls[self.current_url])
        break

      if self.num_path_links >= self.results['path_link_limit']:
        self.results['message'] = 'Path link limit reached'
        self.results['errors'] = True
        break

      html_result = Spider.getHtml(self.current_url)
      if html_result['success']:
        self.results['urls'].append(str(html_result['url']))
      else:
        self.results['message'] = 'Unable to get html content: ' + html_result['content']
        self.results['errors'] = True
        break

      self.current_url = Spider.findFirstLink(html_result['content'])
      self.num_path_links += 1
      if not self.current_url:
        self.results['errors'] = True
        self.results['message'] = 'Unable to find first link'



def getCachedUrls():
  mongo_db = getMongoClient()
  successful_urls = {}
  if mongo_db:
    for doc in mongo_db['results'].find({'reaches_philosophy' : True}):
      for idx, url in enumerate(doc['urls']):
        successful_urls[url] = doc['urls'][idx:]
    print "Running with %s successful_urls" % len(successful_urls.keys())
  return successful_urls


def main(args):
  # the set of known urls that map to the philosophy
  # page and the path they take.
  successful_urls = {}
  if not args.ignore:
    successful_urls = getCachedUrls()

  # for args.runs, repeat the entire experiement. this
  # option only really makes sense with "-u Special:Random"
  for _ in xrange(int(args.runs)):
    new_cache = {}

    s = Spider(args.url, args.limit, successful_urls)
    s.run()

    # if the run successfully reached philosophy, then
    # append it to the successful_urls set so the next run
    # will have better information to work with.
    if s.results['reaches_philosophy'] and not args.ignore:
      for idx, url in enumerate(s.results['urls']):
        new_cache[url] = s.results['urls'][idx:]

    # pretty print results
    pprint.pprint(s.results)

    # add to global cache
    successful_urls.update(new_cache)

    # try to store to mongo the results to mongo
    try:
      mongo_db = getMongoClient()
      if mongo_db and args.mongo != 'read:read':
        s.results['_id'] = s.results['urls'][0]
        _id = mongo_db['results'].insert(s.results)
        print 'New _id=', _id
    except pymongo.errors.OperationFailure:
      # happens when the user does not have permission to insert
      pass
    except pymongo.errors.ServerSelectionTimeoutError:
      # happens when the connection is invalid, or times out.
      pass
    except Exception as e:
      logging.exception(e)



if __name__ == '__main__':

  parser = argparse.ArgumentParser(description='Wikipedia philosophy crawler')

  parser.add_argument('-u', dest='url', action='store',
    help='the starting url', required=True)
  parser.add_argument('-l', dest='limit', action='store',
    help='page depth limit', default=40)
  parser.add_argument('-n', dest='runs', action='store',
    help='run <n> times', default=1)
  parser.add_argument('-m', dest='mongo', action='store',
    help='mongo credentials', default='read:read')
  parser.add_argument('-i', dest='ignore', action='store_true',
    help='ignore caching')

  args = parser.parse_args()

  try:
    main(args)
  except KeyboardInterrupt:
    pass
