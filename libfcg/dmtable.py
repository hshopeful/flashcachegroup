#!/usr/bin/env python

import os
from libfcg import utils

def get_error_table(sectors):
	table = '0 %d error' % sectors
	return table

def linear_map_table(disks):
	table = ''
	startSector = 0
	for disk in disks:
		sector = utils.get_dev_sector_count(disk)
		table +=  '%d %d linear %s 0\n' % (startSector, sector, disk)
		startSector += sector
	return table

def get_disks_in_linear_table(table):
	disks = []
	table_list = table.split('\n')
	for table_line_str in table_list:
		line = table_line_str.split()
		if len(line) == 5:
			disk = line[3]
			try:
				major, minor = [int(x) for x in disk.split(':')]
				disk = utils.get_devname_from_major_minor(disk)
			except Exception, e:
				pass
			disks.append(disk)
	return disks

def insert_disk_to_linear_table(disk, table):
	new_table = ''
	sector = utils.get_dev_sector_count(disk)
	lines = table.strip().split('\n')
	for i in range(len(lines)):
		line_str = lines[i]
		line = line_str.strip().split()
		start, offset = map(int, line[0:2])
		map_type = line[2]
		if map_type == 'error' and offset >= sector:
			new_disk_line = '%d %d linear %s 0\n' % (start, sector, disk)	
			new_table += new_disk_line
			if offset > sector:
				new_err_line = '%d %d error\n' %(start+sector, offset-sector)
				new_table += new_err_line
		else:
			new_table += line_str
			new_table += '\n'
	return new_table

class Disk:
	start=None
	size=None
	mapper=None
	dev=None
	offset=None
	major_minor=None
	major=None
	minor=None
	def __str__(self):
		return '%d %d %s %s %d' % (self.start, self.size, self.mapper, self.dev, self.offset)
	def __repr__(self):
		return __str__(self)
	def parse_line(line):
		line = line.split()
		if len(line) < 3:
			return False
		self.start = int(line[0])
		self.size = int(line[1])
		self.mapper = mapper = line[2]  # linear or error
		if mapper=='linear':
			self.major_minor = major_minor = line[3]
			self.dev = utils.get_devname_from_major_minor(major_minor)
			major_minor = major_minor.split(':')
			self.major = int(major_minor[0])
			self.minor = int(major_minor[1])
			self.offset = int(line[4])
		elif mapper=='error':
			pass
		else:
			return False
		return True
	@staticmethod
	def from_line(line):
		disk = new Disk()
		ok = disk.parse_line(line)
		return ok and disk
	@staticmethod
	def create_linear_mapping(dev, size=None, offset=None):
		self=Disk()
		self.start   = 0
		self.size    = size or utils.get_dev_sector_count(dev)
		self.mapper  = 'linear'
		self.dev     = dev
		self.offset  = offset or 0
	@staticmethod
	def create_error_mapping(size):
		self=Disk()
		self.start   = 0
		self.size    = size
		self.mapper  = 'error'


class LinearTable:
	disks = []
	def __init__(size=None):
		if size!=None:
			self.disks = [Disk.create_error_mapping(size)]

	def parse_text(text):
		disks = []
		lines = text.split('\n')
		for line in lines:
			line = line.split()
			if len(line) < 3:
				continue
			disk=Disk.from_line(line)
			if disk:
				disks.append(disk)
		self.disks = disks

	@staticmethod
	def from_text(text):
		table = LinearTable()
		table.parse_text(text)
		return table
	
	def _compute_starts(self):
		start=0;
		for disk in self.disks:
			disk.start = start
			start += disk.size

	def __str__(self):
		_compute_starts(self);
		return '\n'.join(map(str, self.disks))

	def insert_disk(newdisk):
		for i in range(len(self.disks)):
			disk = self.disks[i]
			# find the first free space (mapper=='error') that is big enough
			if disk.mapper!='error' or disk.size<newdisk.size:
				continue
			newdisk.start=disk.start
			if disk.size>newdisk.size:
				disk.size -= newdisk.size
				disk.start += newdisk.size
				self.disks.insert(i, newdisk)
			elif disk.size == newdisk.size:
				self.disks[i]=newdisk
			_compute_starts()
			return True
		return False 	# no enough space

	def remove_disk(self, thedisk):
		length = len(self.disks)
		for i in range(length):
			disk = self.disks[i]
			if disk.mapper=='linear' and disk.start==thedisk.start and disk.size==thedisk.size:
				break;
		if i==length:  
			return False         # not found
		
		disk.mapper='error'
		disk.dev=None
		disk.major_minor=None
		disk.major=None
		disk.minor=None

		j = i+1
		while j<length:
			next=self.disks[j]
			if self.disks[j].mapper=='error':
				disk.size+=next.size
				self.disks.remove(next)
			else:
				j++

		_compute_starts()







	

