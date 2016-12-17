import os
from lxml import html
import requests
from time import sleep
import csv
from urlparse import urlparse
import MySQLdb as db
import MySQLdb.cursors
con = db.connect('localhost', 'root',  'root', 'phish_tank', charset='utf8', cursorclass=MySQLdb.cursors.DictCursor)
con.autocommit(True)
cur = con.cursor()
con_read = db.connect('localhost', 'root',  'root', 'phish_tank', charset='utf8', cursorclass=MySQLdb.cursors.DictCursor)
con_read.autocommit(True)
cur_read = con_read.cursor()

DIR = os.path.dirname(os.path.realpath(__file__))


def get_wp_info(url):

    h = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36'
    }
    try:
        r = requests.get(url, headers=h, verify=False)
    except requests.exceptions.ConnectionError:
        return {'status': 'error', 'url': url}

    response = {}
    if r.status_code == 200:
        tree = html.fromstring(r.content)

        # Get our Word press Version
        meta_tags = tree.xpath('head//meta[@name="generator"]/@content')
        response = {
            'status': 'success',
            'wp_version': meta_tags[0] if meta_tags else 'No Version Found',
            'wp_plugins': []
        }

        # Grab all Word press plugins
        script_tags = tree.xpath('//script[@type="text/javascript"]/@src')
        found_plugins = []
        for tag in script_tags:
            if 'wp-content/plugins' in tag:
                segments = tag.split('/')
                plugin = segments[5]

                # If duplicate plugin skip
                if plugin in found_plugins:
                    continue

                found_plugins.append(plugin)
                version_segments = segments[len(segments) - 1].split('ver=')
                plugin_version = version_segments[1] if len(version_segments) > 1 else 'No Version Number'

                response['wp_plugins'].append({
                    'name': plugin,
                    'version': plugin_version
                })
    else:
        response = {'status': 'error', 'url': url}

    return response


def get_all_urls(url, parent_site_id):
    # Initial call
    site_urls = get_page_urls(url, parent_site=parent_site_id)

    # After db is primed loop through site pages and store them
    cur_read.execute('select id, parent_site_id, url, has_been_crawled from site_pages where parent_site_id = %s and has_been_crawled = 0', (parent_site_id,))
    data = cur_read.fetchone()
    while data:
        segments = urlparse(data['url'])
        page_url = '{}'.format(data['url'])
        if segments.scheme == '':
            page_url = '{}{}'.format(url, page_url)
        print "Parsing Page: {}".format(page_url)
        get_page_urls(page_url, parent_site=parent_site_id, page_id=data['id'])
        cur.execute('update site_pages set has_been_crawled = 1 where id = %s', (data['id'],))
        sleep(.01)
        data = cur_read.fetchone()


def get_page_urls(url, parent_site, page_id=0):
    h = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36'
    }
    try:
        r = requests.get(url, headers=h, verify=False)
    except requests.exceptions.ConnectionError:
        return {'status': 'error', 'url': url}

    response = {}
    if r.status_code == 200:
        tree = html.fromstring(r.content)

        # Get all links on page
        internal_links = []
        links = tree.xpath('//a/@href')
        for link in links:
            if link.startswith('http') and urlparse(url).netloc not in link:
                cur.execute('select id from external_links where url = %s', (link,))
                if not cur.fetchone():
                    cur.execute('insert into external_links (site_page_id, url) values (%s, %s)', (page_id, link))
                    # print "External: {}".format(link)
            else:
                if urlparse(link).path.startswith('/') and len(urlparse(link).path) > 1:
                    segments = urlparse(link)
                    try:
                        new_url = '{}'.format(urlparse(link).path.rstrip('/'),)
                    except UnicodeEncodeError:
                        continue

                    if urlparse(link).query != '':
                        new_url = '{}?{}'.format(new_url, urlparse(link).query)
                    if new_url not in internal_links:
                        internal_links.append(new_url)
                        cur.execute('select id from site_pages where url = %s', (new_url,))
                        if not cur.fetchone():
                            cur.execute('insert into site_pages (parent_site_id, url) values (%s, %s)', (parent_site, new_url))


def parse_websites(file):
    # Open our CSV file to write to
    with open('{}/data.csv'.format(DIR,), 'w+') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

        # Set our CSV Headers
        spamwriter.writerow(['Site', 'WordPress Version', 'Plugin Name', 'Plugin Version'])

        # Open url text file to read in line by line
        with open(file) as f:
            for line in f:
                # Query each url to get wordpress info
                url = "http://{}".format(line.rstrip())
                print "Parsing Site: {}".format(url,)
                response = get_wp_info(url)

                # If we get info write to the CSV
                if response['status'] == 'success':
                    # Write each plugin to row
                    for row in response['wp_plugins']:
                        spamwriter.writerow([line.rstrip(), response['wp_version'], row['name'], row['version']])

                # Write blank row between sites
                spamwriter.writerow(['', '', '', ''])

                all_urls = get_all_urls(url)

                return True


# parse_websites('{}/urls.txt'.format(DIR,))

get_all_urls('http://wpengine.com', parent_site_id=1)

print 'Done'
