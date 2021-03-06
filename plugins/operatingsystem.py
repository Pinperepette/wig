from collections import Counter
from classes.plugin import Plugin
import json, pprint

class OperatingSystem(Plugin):

	def __init__(self, cache, results):
		super().__init__(results)
		self.cache = cache
		self.results = results

		self.category = "Operating System"
		self.os = Counter()
		self.packages = Counter()
		self.oss = []
		self.use_profile = False
		self.os_files = [
			'data/os/centos.json',
			'data/os/debian.json',
			'data/os/fedora.json',
			'data/os/freebsd.json',
			'data/os/openbsd.json',
			'data/os/opensuse.json',
			'data/os/redhat.json',
			'data/os/scientific.json',
			'data/os/ubuntu.json',
			'data/os/debian_specific.json',
			'data/os/ubuntu_specific.json'
		]
		self.matched_packages = set()


	def load_extra_data(self, extra_file):
		all_items = self.get_all_items()

		with open(extra_file) as f:
			items = json.load(f)
			for package in items:
				for version in items[package]:
					os_list = items[package][version]
					if package in all_items:
						if version in all_items[package]:
							all_items[package][version].extend(os_list)
						else:
							all_items[package][version] = os_list
					else:
						all_items[package] = {version: os_list}

		self.set_items(all_items)


	def find_match(self, response):
		headers = response.headers

		if 'server' in headers:
			line = headers['server']

			if "(" in line:
				os = line[line.find('(')+1:line.find(')')]
				line = line[:line.find('(')-1] + line[line.find(')')+1: ]
			else:
				os = False

			if os: self.oss.append(os.lower())

			for part in line.split(" "):
				try:
					pkg,version = list(map(str.lower, part.split('/')))

					self.packages[pkg] += 1
					os_list = self.db[pkg][version]

					for i in os_list:
						if len(i) == 2:
							os, os_version = i
							weight = 1
						elif len(i) == 3:
							os, os_version, weight = i

						self.matched_packages.add( (os, os_version, pkg, version) )
						self.os[(os, os_version)] += weight

				except Exception as e:
					continue

		if 'X-Powered-By' in headers:
			line = headers['X-Powered-By']
			try:
				pkg,version =  list(map(str.lower, line.split('/')))
				for i in self.db[pkg][version]:
					if len(i) == 2:
						os, os_version = i
						weight = 1
					elif len(i) == 3:
						os, os_version, weight = i
					
					self.matched_packages.add( (os, os_version, pkg, version) )
					self.os[(os, os_version)] += weight
			except Exception as e:
				pass


	def find_results(self, results):
		if len(results) == 0: return

		prio = sorted(results, key=lambda x:x['count'], reverse=True)
		max_count = prio[0]['count']
		relevant = []
		for i in prio:
			if i['count'] == max_count:
				if len(relevant) > 0  and i[0] == "": continue
				self.add_results([{'version': i['version'], 'count': i['count']}], i['os'])
			else:
				break

	def finalize(self):
		# if an os string 'self.oss' has been found in the header
		# prioritize the identified os's in self.os

		# iterate over the list of os strings found
		for os in self.oss:
			# iterate over the fingerprinted os's
			for key in self.os:
				if os in key[0].lower():
					self.os[key] += 100

		# add OS to results: self.os: {(os, version): weight, ...}
		r = []
		for p in self.os:
			r.append({'version': p[1], 'os': p[0], 'count': self.os[p]})

		self.find_results(r)
		

	def run(self):

		# load all fingerprints
		self.data_file = 'data/os/os_fingerprints_static.json'
		self.load_data()
		for os_file in self.os_files:
			self.load_extra_data(os_file)
	
		def lower_key(in_dict):
			if type(in_dict) is dict:
				out_dict = {}
				for key, item in in_dict.items():
					out_dict[key.lower()] = lower_key(item)
				return out_dict
			elif type(in_dict) is list:
				return [lower_key(obj) for obj in in_dict]
			else:
				return in_dict

		self.db = lower_key(self.get_all_items())

		responses = self.cache.get_responses()
		for response in responses:
			self.find_match(response)

		self.finalize()

def get_instances(host, cache, results):
	return [
		OperatingSystem(cache, results)
	]
