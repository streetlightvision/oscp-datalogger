import sqlite3
import sys
import json
import datetime
import time
import xml.etree.ElementTree as ET

from lib.CMS import CMS

def enum(*sequential, **named):
	enums = dict(zip(sequential, range(len(sequential))), **named)
	return type('Enum', (), enums)

State = enum('INIT', 'CONNECT_LOCAL_DB', 'GATHER_DATA', 'DISCONNECT_LOCAL_DB', 'BUILD_MESSAGES', 'CMS_CONNECT', 'CMS_SEND_MESSAGES', 'CMS_DISCONNECT', 'UPDATE_LOCAL_DB', 'SLEEP')

class OSCP:
	def __init__(self, config_file):
		print("-> OSCP Wrapper v0.1")
		with open(config_file) as data_file:
			config = json.load(data_file)

		if 'debug' in config:
			self.debug_flag = bool(config['debug'])
		else:
			self.debug_flag = True

		if 'push_interval' in config:
			self.push_interval = int(config['push_interval'])
		else:
			self.push_interval = 60

		if 'row_limit' in config:
			self.row_limit = int(config['row_limit'])
		else:
			self.row_limit = 1000

		self.cms = CMS(config)
		self.state = State.INIT
		self.highest_id = 0
		self.to_send = []

		self.state_arr = [
			self.init,
			self.connect_local_db,
			self.gather_data,
			self.disconnect_local_db,
			self.build_messages,
			self.cms_connect,
			self.cms_send_messages,
			self.cms_disconnect,
			self.update_local_db,
			self.sleep
		]

		if self.debug_flag == True:
			print('Debug: '+str(self.debug_flag))

	def run(self):
		print('Starting OSCP Gateway (Data Logger)...')
		running = True
		while running:
			self.state_arr[self.state]()

	def init(self):
		self.debug('Initializing...')
		self.debug('Loaded configuration file.')
		self.state = State.CONNECT_LOCAL_DB

	def connect_local_db(self):
		self.debug('Connecting to local database (sqlite)...')
		self.conn = sqlite3.connect('data.db', timeout=60)


		cursor = self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
		found_data = False
		found_info = False

		for row in cursor:
			if row[0] == 'oscp_data':
				found_data = True
			if row[0] == 'oscp_info':
				found_info = True
		if found_data == False:
			self.debug('Table `oscp_data` not found. Creating...')
			self.conn.execute("""CREATE TABLE "oscp_data" (
					`id`	INTEGER PRIMARY KEY AUTOINCREMENT,
					`controllerStrId`	TEXT NOT NULL,
					`idOnController`	TEXT NOT NULL,
					`meaning`	TEXT,
					`value`	TEXT NOT NULL,
					`time`	INTEGER NOT NULL
				)""")
			self.conn.commit()
		if found_info == False:
			self.debug('Table `oscp_info` not found. Creating...')
			self.conn.execute("""CREATE TABLE `oscp_info` (
					`id`	INTEGER PRIMARY KEY AUTOINCREMENT,
					`name`	TEXT NOT NULL,
					`value`	TEXT NOT NULL
				)""")
			self.conn.execute("INSERT INTO `oscp_info` (`name`, `value`) VALUES ('last_pushed', 0)")
			self.conn.commit()

		self.debug('Reading last `id` sent to CMS...')
		cursor = self.conn.execute("SELECT `value` FROM `oscp_info` WHERE `name`='last_pushed'")
		self.last_pushed = cursor.fetchone()[0]

		self.state = State.GATHER_DATA

	def gather_data(self):
		self.debug('Checking limits...')
		cursor = self.conn.execute("SELECT Count(id) as cnt FROM `oscp_data`")
		for row in cursor:
			count = row[0]
			if count > self.row_limit:
				command = "DELETE FROM `oscp_data` ORDER BY `id` LIMIT 0,"+str(count-self.row_limit)
				self.debug('Limit reached. Deleting older entries...')
				self.conn.execute(command)
				self.conn.commit()
		self.debug('Looking for new data...')
		cursor = self.conn.execute("SELECT `id`, `controllerStrId`, `idOnController`, `meaning`, `value`, `time` FROM `oscp_data` WHERE `id` > "+self.last_pushed)
		for row in cursor:
			if self.is_valid_entry(row) == True:
				self.to_send.append(row)
		self.state = State.DISCONNECT_LOCAL_DB

	def disconnect_local_db(self):
		if len(self.to_send) > 0:
			self.debug('Got new data!')
			self.state = State.BUILD_MESSAGES
		else:
			self.debug('No data to send!')
			self.state = State.SLEEP
		self.conn.close()
		self.debug('Disconnecting from local database (sqlite)')

	def build_messages(self):
		self.root = ET.Element("reporting")
		for entry in self.to_send:
			if int(entry[0]) > self.highest_id:
				self.highest_id = entry[0]
			value = ET.SubElement(self.root, "value",
				ctrlId=entry[1],
				id=entry[2],
				meaning=entry[3],
				date=entry[5]
				)
			value.text = entry[4]
		self.state = State.CMS_CONNECT
		del self.to_send[:]

	def cms_connect(self):
		result = self.cms.connect()
		if result == True:
			self.debug('Connected to CMS!')
			if self.cms.auth() == True:
				self.debug('Authenticated!')
				self.state = State.CMS_SEND_MESSAGES
			else:
				self.debug('Error authenticating with the CMS! Retrying in 10 seconds...')
				time.sleep(10)
		else:
			self.debug('Error connecting to CMS! Retrying in 10 seconds...')
			time.sleep(10)

	def cms_send_messages(self):
		self.debug('Sending messages to CMS')
		answer = self.cms.sendOSCP(ET.tostring(self.root).decode("utf-8"))
		error = False
		answer = ET.fromstring(answer)
		if self.debug == True:
			for entry in answer.findall('error'):
				error = True
				code = entry.get('code')
				self.debug('Got error code '+code+': '+entry.text)
			if error == True:
				self.debug("The entries that got an error won't be re-sent to the CMS.")

		self.state = State.CMS_DISCONNECT

	def cms_disconnect(self):
		self.debug('Disconnecting from CMS...')
		self.cms.getConnection().close()
		self.state = State.UPDATE_LOCAL_DB

	def update_local_db(self):
		self.debug('Writing last `id` sent to CMS...')
		updated = False
		while updated == False:
			try:
				self.conn = sqlite3.connect('data.db', timeout=60)
				self.conn.execute("UPDATE `oscp_info` SET `value` = "+str(self.highest_id)+" WHERE `name` = 'last_pushed'")
				self.conn.execute("DELETE FROM `oscp_data` WHERE `id` < "+str(self.highest_id)+"")
				self.conn.commit()
				self.conn.close()
				updated = True
			except:
				self.debug('Error updating database. Retrying in 10 seconds.')
				if self.conn != None:
					self.conn.close()
				time.sleep(10)

		self.state = State.SLEEP

	def sleep(self):
		self.debug('Sleeping for '+str(self.push_interval)+'s...')
		time.sleep(self.push_interval)
		self.state = State.CONNECT_LOCAL_DB

	def is_valid_entry(self, entry):
		# `id`, `controllerStrId`, `idOnController`, `meaning`, `value`, `time`

		if len(entry[1]) == 0:
			return False
		if len(entry[2]) == 0:
			return False
		if len(entry[3]) == 0:
			return False

		try:
			datetime.datetime.strptime(str(entry[5]), '%Y-%m-%dT%H:%M:%S.%fZ')
		except ValueError:
			self.debug('@@@@-> Invalid string format for `time` field!')
			return False

		return True

	def debug(self, string):
		if self.debug_flag == True:
			print(string)
