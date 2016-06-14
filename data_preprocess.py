#!/usr/bin/env python
#-*- coding:utf-8 -*-

import time
import codecs
import re
import hashlib
from gremlin_rest import GremlinClient
import sys
reload(sys)
sys.setdefaultencoding( "utf-8" )

class DataPreProcess(object):
	
	def __init__(self, server, file_path):
		self.server = server
		self.file_path = file_path
		
	def flow_import(self):
		vertices = {'ip':{},'domain':{},'url':{}}
		edges = []
		
		try:
			file = codecs.open(self.file_path, 'r', encoding='utf-8')
		except StandardError, e:
			print e
		
		lines = file.readlines()
		lines.pop(0)
		
		for line in lines:
			line = line.strip().split()
			vertices['ip'][line[0]] = {'location': line[9], 'country': line[11]}
			vertices['ip'][line[1]] = {'location': line[10], 'country': line[12]}
			
			timeArray = time.strptime(line[4],"%Y/%m/%dT%H:%M:%S")
			format_time = time.strftime("%Y/%m/%d %H:%M:%S", timeArray)
			
			hash_val = hashlib.md5(''.join(line[0:9])).hexdigest()
			edges.append({'label':'access', 'src':line[0], 'dst': line[1], 'src_port': line[5], 'dst_port': line[6], 'time': format_time, 'pkg_num':line[2], 'bytes':line[3], 'protocol':line[8], 'TCP_flag':line[7], 'hash':hash_val})
		
		self.check_exist(vertices, edges)
		
		return vertices, edges
	
	def jsp_import(self):
		vertices = {'ip':{},'domain':{},'url':{}}
		edges = []
		
		try:
			file = codecs.open(self.file_path, 'r', encoding='utf-8')
		except StandardError, e:
			print e
			
		lines = file.readlines()
		lines.pop(0)
		
		for line in lines:
			line = line.strip().split('\t')
			vertices['ip'][line[2]] = {}
			vertices['ip'][line[3]] = {}
			
			res = line[8]
			pattern_host = re.compile(r'(Host:)(.*?)(\\)')
			try:
				host = pattern_host.search(res).group(2).strip()
			except StandardError, e:
				print e
			vertices['domain'][host] = {}
			
			pattern_dir = re.compile(r'(\/)(.*?)(HTTP)')
			try:
				url = host+'/'+pattern_dir.search(res).group(2).strip()
			except StandardError, e:
				print e			
			vertices['url'][url] = {}
			
			timeArray = time.strptime(line[6],"%Y%m%d%H%M%S")
			format_time = time.strftime("%Y/%m/%d %H:%M:%S", timeArray)
			hash_val = hashlib.md5(''.join(line[0:9])).hexdigest()
			edges.append({'label':'attack', 'src':line[2], 'dst': line[3], 'src_port': line[4], 'dst_port': line[5], 'time': format_time, 'in&out_port':line[0], 'evt_name':line[1], 'device_name':line[7], 'return_val':line[8], 'hash':hash_val})
			edges.append({'label':'ip2host', 'src':line[3], 'dst':host, 'hash':hashlib.md5(line[3]+host).hexdigest()})
			edges.append({'label':'url2host', 'src':url, 'dst':host, 'time':format_time, 'hash':hashlib.md5(url+host).hexdigest()})
			edges.append({'label':'ip2url', 'src':line[2], 'dst':url, 'time':format_time, 'hash':hashlib.md5(line[2]+url).hexdigest()})
			
			
		self.check_exist(vertices, edges)
		
		return vertices, edges
		
	def check_exist(self, vertices, edges):
		client = GremlinClient(self.server)
		
		for type in vertices.keys():
			if type == 'ip':
				label = "IP_ADD_SCHEME_TRACE"
			elif type == 'domain':
				label = "DOMAIN_NAME_SCHEME_TRACE"
			elif type == 'url':
				label = "URL_ADD_SCHEME_TRACE"
			for key in vertices[type].keys():
				resp = client.run_script('g.V().has(name, val).count()', name = label, val = key) 
				if str(resp).strip('[]') != '0':
					vertices[type].pop(key)

#		for edge in edges:
#			resp = client.run_script('g.E().has("hash" val)', val = edge['hash']) 
#			if str(resp).strip('[]') != '0':
#				edges.remove(edge)

		return vertices, edges

def main():
#	test = DataPreProcess('http://10.1.1.48:8182', 'F:\\FLOW-20160513-dip.txt')
#	vertices, edges = test.flow_import()
#	for i in edges:
#		print i

	test = DataPreProcess('http://10.1.1.48:8182', 'F:\\fghk-2787-jsp.txt')
	vertices, edges = test.jsp_import()
	test.check_exist(vertices, edges)
	for i in vertices['ip']:
		print i
	
	
if __name__ == '__main__':
	main()