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
	def __init__(self, dev=None):
		if dev!=None:
			self.dev=dev
			self.size=utils.get_dev_sector_count(dev)
			self.mapper='linear'
			self.offset=0
			self.start=0

class LinearTable:
	disks = []
	def __init__(size, dev=None, offset=None):
		disk=Disk()
		disk.start=0;
		disk.size=size;
		disk.mapper='error'
		if dev!=None:
			disk.mapper = 'linear'
			disk.offset = offset or 0
			disk.dev = dev
		disks.append(disk)

	def parse_text(text):
		disks = []
		lines = text.split('\n')
		for line in lines:
			line = line.split()
			if len(line) < 3:
				continue
			disk=Disk()
			disk.start = int(line[0])
			disk.size = int(line[1])
			disk.mapper = mapper = line[2]  # linear or error
			if mapper=='linear':
				disk.major_minor = major_minor = line[3]
				disk.dev = utils.get_devname_from_major_minor(major_minor)
				major_minor = major_minor.split(':')
				disk.major = int(major_minor[0])
				disk.minor = int(major_minor[1])
				disk.offset = int(line[4])
			elif mapper=='error':
				pass
			else:
				continue;
			disks.append(disk)
		self.disks = disks
	
	def _compute_starts(self):
		start=0;
		for disk in self.disks:
			disk.start = start
			start += disk.size

	@staticmethod
	def _format_disk(disk):
		return '%d %d %s %s %s' % (disk.start, disk.size, disk.mapper, disk.dev, disk.offset)

	def generate_text(self):
		_compute_starts(self);
		lines = [ _format_disk(disk) for disk in self.disks]
		return '\n'.join(lines)

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
		if isinstance(thedisk, Disk):
			self.disks.remove(thedisk)
		elif isinstance(thedisk, int):
			thedisk=self.disks[thedisk]
			self.disks.remove(thedisk)
		_compute_starts()





	

