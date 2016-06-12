#!/usr/bin/python
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import urllib, sys

# CONSTANTS
BASE_URL = "http://www.alexa.com/topsites/global;"
SITES_PER_PAGE = 25

# PUBLIC FUNCTIONS
def retrieve_pages(amount):
	'''Fetches the amount of requested pages from alexa.com as a list'''
	max_index = _calculate_index(amount, SITES_PER_PAGE)
	result = []
	# alex loop , only 25 entries per page
	for index in range(0, max_index):
		# progress
		_update_progess(index+1, max_index)
		# analyzing alexa page
		raw_page = _fetch_page(BASE_URL + str(index))		
		sites = _scan_page(raw_page)
		result = result + sites
	return result
	
# PRIVATE FUNCTIONS
def _fetch_page(alexa_url):
	'''Fetches given alexa url via urllib'''
	filehandle = urllib.urlopen(alexa_url)
	return filehandle.read()

def _scan_page(alexa_page):
	'''Fetches listed top pages from the given page'''
	soup = BeautifulSoup(alexa_page, 'html.parser')
	all_li = [li for li in soup.find_all('li') if li.get('class') is not None and 'site-listing' in li.get('class')]
	return [str(li.a.string) for li in all_li]

def _write_result(site_list, file_name, seperator):
	'''Writes the list of the pages to file concatenated by seperator'''
	f = open(file_name, 'w')
	[f.write(element+seperator) for element in site_list] 
	f.close()

def _calculate_index(amount, sites_per_page):
	'''Calculates the max index based on listings per page'''
	return amount/sites_per_page

def _update_progess(current, end):
	'''Progess bar for measurment'''
	sys.stdout.write("processed %s/%s pages" % (str(current), str(end)))
	sys.stdout.flush()
	sys.stdout.write("\r")

def _help():
	'''Console help output'''
	print 'Following parameters are necessary:'
	print '1. amount of pages to fetch (max 500)'
	print '2. name for an outputfile'

# MAIN
if __name__ == '__main__':
	
	# guard clause for args
	argv = sys.argv[1:]
	if len(argv) != 2:
		_help()
		sys.exit()

	# reading args
	amount_pages, output_file = int(argv[0]), argv[1]

	# fetches requested alexa top sites
	print 'fetching top %s sites on alexa...' %(amount_pages)
	top_sites = retrieve_pages(amount_pages)

	# writing result file
	_write_result(top_sites, output_file, '\n')
	print ''
	print top_sites
	print 'got it! writing file...'
	print 'all done'