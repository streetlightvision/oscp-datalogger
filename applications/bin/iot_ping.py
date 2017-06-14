import subprocess
import re
import sqlite3
import datetime
import time
import json

ping_re = re.compile('min\/avg\/max\/\S* = \S*\/(\S*)\/\S*\/\S*')
buffer = ""

log = []

def add_data_point(conn, controller, meaning, value, time):
		# prepare command to insert new row into `oscp_data` table
		command = """INSERT INTO `oscp_data`
				(`controllerStrId`,`idOnController`,`meaning`,`value`,`time`)
				VALUES
				('{controllerStrId}','controllerdevice','{meaning}',"{value}",'{time}');"""

		conn.execute(command.format(
				controllerStrId=controller,
				meaning=meaning,
				value=value,
				time=time))  # execute command setting values



if __name__ == '__main__':
	with open('../etc/config.json') as data_file:
		config = json.load(data_file)

	printf('/////////////////////////////////////')
	printf('// IoT SLV CMS Ping v0.1')
	printf('/////////////////////////////////////')

	controllerStrId = config['controllerStrId']
	# main loop
	while True:
		if config['ipv6'] == True:
			command = 'ping6 -U -c4 '+config['host']
		else:
			command = 'ping -U -c4 '+config['host']

		cmd = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
		for line in cmd.stdout:
			line = line.decode()
			buffer = buffer + line

		re_match = ping_re.findall(buffer)

		now = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

		conn = sqlite3.connect('../data.db', timeout=60)
		add_data_point(conn, controllerStrId, 'ping.avg',  re_match[0], now)
		conn.commit()  # commit the changes
		conn.close()  # close connection with the database

		print('ping.avg',  re_match[0], now)

		log = []
		header = False
		time.sleep(config['refresh_interval'])