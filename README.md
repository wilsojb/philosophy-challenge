## Overview: The "Getting to Philosophy" Challenge
If you go to any page on Wikipedia and keep clicking on the first link of the page (ignoring links in parenthesis and the ones in italic), you will usually eventually reach the Philosophy page. This is a python implementation of the challenge that uses [MongoDB](https://mlab.com) to cache previously visited pages in order to make aggregating results easier and to reduce the overall number of requests to Wikipedia. From [Wikepedia](https://en.wikipedia.org/wiki/Wikipedia:Getting_to_Philosophy),

> Clicking on the first link in the main text of a Wikipedia article, and then repeating the process for subsequent articles, usually eventually gets you to the Philosophy article. As of May 26, 2011, 94.52% of all articles in Wikipedia lead eventually to the article Philosophy. The remaining 100,000 (approx.) links to an article with no wikilinks or with links to pages that do not exist, or get stuck in loops (all three are equally probable). The median link chain length to reach philosophy is 23.

My stats differ from the main article, which is most likely due to slightly different assumptions about what the "first link" on the page should be. (E.g. some implementations ignore external links, etc.). As of this writing, this implementation finds 94.2% articles lead to the Philosophy page with a median link chain of 14.


## Installation

Best to start with a fresh virtual environment,

```bash
$ virtualenv env
New python executable in env/bin/python
Installing setuptools, pip, wheel...done.
```

Don't forget activate and then install all dependencies,

```bash
$ source env/bin/activate
(env)$ pip install -r requirements.txt
```

Make the scripts executable and take a look at the help menu,

```bash
(env)$ chmod +x results.py crawler.py
(env)$ ./crawler.py -h
usage: crawler.py [-h] -u URL [-l LIMIT] [-n RUNS] [-m MONGO] [-i]

Wikipedia philosophy crawler

optional arguments:
  -h, --help  show this help message and exit
  -u URL      the starting url
  -l LIMIT    page depth limit
  -n RUNS     run <n> times
  -m MONGO    mongo credentials
  -i          ignore caching
```

## Crawler

The bulk of the code is in crawler.py. To see the basic algorithm at work, run the following:

```bash
(env)$ ./crawler.py -u Art -i
{ 'errors': False,
  'message': 'Found in cache',
  'path_link_limit': 40,
  'reaches_philosophy': True,
  'starting_url': 'Art',
  'urls': ['Art',
          'Human_behavior',
          'Motion_(physics)',
          'Physics',
          'Natural_science',
          'Science',
          'Knowledge',
          'Awareness',
          'Conscious',
          'Quality_(philosophy)',
          'Philosophy']}
```

Significant speed improvements can be made by utilizing previously successful urls. Remove the '-i' to see this at work:

```bash
(env)$ ./crawler.py -u Art
Running with 1448 successful_urls
{ 'errors': False,
  'message': 'Found in cache',
  'path_link_limit': 40,
  'reaches_philosophy': True,
  'starting_url': 'Art',
  'urls': [u'Art',
          u'Human_behavior',
          u'Motion_(physics)',
          u'Physics',
          u'Natural_science',
          u'Science',
          u'Knowledge',
          u'Awareness',
          u'Conscious',
          u'Quality_(philosophy)',
          u'Philosophy']}
```

I've stored previously successful urls to a (free!) [MongoDB](https://mlab.com) instance. In order to generate the data stored there, I ran the following a few times between coffee breaks:

```bash
(env)$ ./crawler.py -u Special:Random -m <admin_username>:<admin_password> -n 50
```

You will need to set up your own MongoDB instance in order to cache previous successful urls or use results.py to see the aggregate results of the challenge. I recommend setting up two users: one with write permissions and one read-only user. You can change the <username>:<password> from the command like with "-m". This defaults to "read:read" when not specified (which was my "read-only" username/password for this exercise).


## Results

The data stored on the mongo instance should be all that's necessary to analyze the results. So I wrote a separate, smaller script to do just that:

```bash
(env)$ ./results.py
Total number of pages: 499

Percentage of pages that often lead to philosophy? 94.2%

What is the distribution of path lengths, discarding those paths that never reach the Philosophy page?
Size:  470
Mean: 14.32
Median: 14
Std: 4.04
```

## Credit
+ http://www.gyford.com/phil/writing/2015/03/25/wikipedia-parsing.php
+ http://matpalm.com/blog/2011/08/13/wikipedia-philosophy/
+ https://en.wikipedia.org/wiki/Wikipedia:Getting_to_Philosophy

## Contacts
 * <wilsojb@gmail.com>
