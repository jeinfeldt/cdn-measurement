#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, time, subprocess, urllib
from threading import Thread
from subprocess import PIPE

# ---------- CONSTANTS ----------
cmd_wget = 'wget -q www.%s'
cmd_tcpdump_measure = 'tcpdump -i wlan0 -w testfile.pcap'
cmd_tcpdump_output = 'tcpdump -nn -r testfile.pcap \'tcp or udp\' | cut -f 5 -d " " | cut -f 1-4 -d "." | sort | uniq | head'
cmd_clean_index = 'rm -f index.html*'
cmd_clean_pcap = 'rm -f testfile.pcap'
cmd_pkill_thread = 'pkill tcpdump'
cmd_whois = 'whois %s'
tcpdump_trace_delay = 5

# ---------- PUBLIC MEASURMENT UTILITES ----------

def check_cdn_usage(site, cdn_list, verbose=False):
	'''matches cdn usage for a given page with a given cdn list'''
	result = ()
	# measure packages to given site
	_measure_packages(site)
	# read tcpdump destination ip adresses
	ips = _fetch_destination_ips()
	# fetch and lookup output destination ip adresses
	nodes = _lookup_reverse_dns(ips)
	# match resulting names with cdns
	result = _match_cdn_names(site, nodes, cdn_list)

	# debug output if verbose
	if verbose:
		_verbose(site, ips, nodes, result)

	# clean up
	_post_measurement()
	return result

# ---------- PRIVATE MEASURMENT UTILITES ----------

class _MeasureThread(Thread):
	'''Helper thread as listening via tcpdump blocks the script'''

	def __init__(self):
		''' Constructor'''
		Thread.__init__(self)
		self._process = None

	def run(self):
		'''Starts tcpdump listening'''
		self._process = subprocess.Popen(cmd_tcpdump_measure, shell=True)
		#self._process.wait()

	def stop(self):
		'''Stops tcpdump listening'''
		subprocess.call(cmd_pkill_thread, shell=True)

def _read_parameters(params):
	'''validates and reads input parameters for measurement'''
	# default values
	cdn_file = 'cdn-provider'
	site_file =  'popular-websites'
	# preparing input
	cdn_list = open(cdn_file, 'r').readlines()
	site_list = open(site_file, 'r').readlines()
	cdn_list = [cdn.strip() for cdn in cdn_list]
	site_list = [site.strip() for site in site_list]
	return (int(params[0]), params[1], site_list, cdn_list)

def _measure_packages(site):
	'''measures packages resulting in requesting given site'''
	# starting thread
	thread = _MeasureThread()
	thread.start()
	# fetching page
	time.sleep(tcpdump_trace_delay) # give tcpdump a little time
	wget = cmd_wget %(site)
	process = subprocess.Popen(wget, shell=True)
	process.wait()
	# finishing thread
	thread.stop()
	thread.join()

def _fetch_destination_ips():
	'''fetches destination ip adresses from tcpdump output'''
	process = subprocess.Popen(cmd_tcpdump_output, shell=True, stdout=PIPE)
	#process.wait()
	stdout, error = process.communicate() #fetching output ip adresses
	return [ip for ip in stdout.split('\n') if ':' not in ip and ip] #exclude ipv6 addresses and empty string

def _lookup_reverse_dns(ips):
	'''does a reverse DNS-Lookup using whois for given IPs. 
	Returns a list of the record content of org-name or OrgName'''
	nodes = []
	for ip in ips:
		process = subprocess.Popen(cmd_whois %(ip), shell=True, stdout=PIPE)
		process.wait()
		stdout, error = process.communicate() #fetching output ip adresses
		org_name = [line for line in stdout.split('\n') if 'org-name:' in line.lower() or 'orgname:' in line.lower()]
		if org_name:
			org_name = org_name[0].lower().strip('org-name:').strip('orgname:')
			nodes.append(org_name.strip())
	return nodes

def _match_cdn_names(site, nodes, cdn_list):
	'''matches given nodes with given cdn_list and returns a touple with:
	   the site, the matched cdns and the complete node trace as a list'''
	result = () # (page, [matched cdns], [nodes])
	matched_cdns = set() # using a set so no double entries
	for cdn_name in cdn_list:
		for node in nodes:
			if cdn_name.lower() in node.lower():
				matched_cdns.add(cdn_name)
	return (site, list(matched_cdns), nodes)

def _post_measurement():
	'''removes files generated during measurement'''
	subprocess.call(cmd_clean_index, shell=True)
	subprocess.call(cmd_clean_pcap, shell=True)

def _collect_result(page_result, complete_result):
	'''Collects all results during measurement'''
	# complete_result {cdn: (amount, [pages])}
	page, matched_cdns, nodes = page_result
	for cdn in matched_cdns:
		amount, pages = complete_result.get(cdn, (0, []))
		amount = amount + 1
		pages.append(page)
		complete_result[cdn] = (amount, pages)


# ---------- PRIVATE OUTPUT UTILITIES ----------

def _verbose(site, ips, nodes, result):
	''' prompts verbose output if mode active '''
	output_dic = {'site': site, 'ips': ips, 'nodes': nodes, 'result': result}
	output = ("\n----- Traced Destination IPs | tcpdump destination ips -----\n"
			  "{ips}\n"
			  "----- Node Organisation Names | org-name:, OrgName: -----\n"
			  "{nodes}\n"
			  "----- Result for page: {site} | page, matched cdns, nodes -----\n"
			  "{result}\n")

	print output.format(**output_dic)


def _write_measurment_results(result, total, file_name=None):
	'''prepares result and writes given output channel'''
	output_dic = {}
	lines = []
	output_header = "------------------ MEASUREMENT RESULT ------------------\n"
	output = "CDN: {cdn} | Usage: {amount}/{total} | Pages: {pages}\n"
	output_footer = "--------------------------------------------------------\n"

	if file_name:
		f = open(file_name, 'a')
		f.write(output_header)
		for cdn, value_tuple in result.iteritems():
			output_dic = {'cdn':cdn, 'amount':value_tuple[0], 'pages':value_tuple[1], 'total':total}
			f.write((output.format(**output_dic)))			
		f.write(output_footer)
		f.close()
	else:
		print output_header
		for cdn, value_tuple in result.iteritems():
			output_dic = {'cdn':cdn, 'amount':value_tuple[0], 'pages':value_tuple[1], 'total':total}
			print output.format(**output_dic)		
		print output_footer
def _help():
	print 'Script needs folowing parameters:'
	print '\t1: Amount of pages to read from file popular-websites'
	print '\t2: Name of the result file'

# ---------- START ----------

if __name__ == '__main__':

	# init
	page_result = () # (page, [matched cdns], [nodes])
	complete_result = {} # complete_result {cdn: (amount, [pages])}
	argv = sys.argv[1:]

	# reading input
	if len(argv) != 2:
		_help()
		sys.exit()
	total, output_file ,site_list, cdn_list = _read_parameters(argv)

	# measuring cdn usage for each page and collecting results
	print '--------- MEASUREMENT STARTED ---------'
	site_list = site_list[:total]
	for site in site_list:
		page_result = check_cdn_usage(site, cdn_list, False)
		_collect_result(page_result, complete_result)

	# writing result
	_write_measurment_results(complete_result, total, output_file)
