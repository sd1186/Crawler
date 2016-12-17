import os
from lxml import html
import requests
import re
from time import sleep


class Crawler(object):

    BASE_URL = 'http://urlfind.org'
    BASE_QUERY_PARAM = '/?wp_plugins'

    def get_urls(self):
        """
        Get Url list on the page
        Navigate to those sub pages and append the list of sites to a file
        :return:
        """
        url = '{}{}'.format(self.BASE_URL, self.BASE_QUERY_PARAM)

        page = requests.get(url)
        tree = html.fromstring(page.content)

        # Truncate file first
        current_dir = os.path.dirname(os.path.realpath(__file__))
        f = open('{}/urls.txt'.format(current_dir,), 'w+')
        f.close()

        # Open file to append to
        f = open('{}/urls.txt'.format(current_dir,), 'a')

        sub_page_urls = tree.xpath('body//table//td//a/@href')
        for sub_page_url in sub_page_urls:
            # sub_page_url = '/?wp_plugins=wp-stats'  # Test URL

            url2 = '{}{}'.format(self.BASE_URL, sub_page_url)

            # Stream the incoming page in chunks so we don't kill our memory
            sub_page = requests.get(url2, stream=True)
            for chunk in sub_page.iter_content(chunk_size=1024):
                if chunk:
                    # Use Regex to find all anchors that contain the query param site
                    # We don't use lxml here because it crashes on the malformed html and when using the HTMLParser it dies on the page comments even when ignoring them and
                    # using the recover flag
                    # There's probably a cleaner regex pattern we can use here, but this is fast enough
                    matches = re.findall('(site=)(.*)(</a>)', chunk)
                    for m in matches:
                        # We want to split on the second item returned in the matches, because that's the section beteween site= and the ending anchor tag
                        # We split on the closing start anchor tag >, to isolate the text between that and the ending anchor tag and grab that as index 1 in the list
                        site = m[1].split('>')[0][:-1]
                        # Append the URL to the urls file
                        f.write("{}\n".format(site,))

                        # Output for terminal, just used for terminal feedback
                        print site

            # Give CPU a break after each sub page write
            print 'Take a break CPU :)'
            sleep(.01)

        # Close our file IO
        f.close()

# Instantiate our class and start getting urls
c = Crawler()
c.get_urls()

# Let's us know when the script is complete
print 'Done'


