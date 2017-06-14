import subprocess
import re
import sqlite3
import datetime
import time
import json

CONST_MEGA = 1000000
CONST_KILO = 1000

if_re = re.compile('^(\S*)[\s\S]*RX bytes:(\d*).*TX bytes:(\d*)')
if_list = []
interfaces = False
header = False
buffer = ""

log = []

prev_eth0_in = -1
prev_eth0_out = -1
prev_rf0_in = -1
prev_rf0_out = -1

curr_run = 3

def getNow():
	return datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

def add_data_point(conn, controller, meaning, value, time):
	print(meaning, value, time)
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
	printf('// IoTR Resource Usage Monitor v0.1')
	printf('/////////////////////////////////////')

	controllerStrId = config['controllerStrId']

	# main loop
	while True:
		# save timestamp so it's possible to run precisely every mns
		begin = datetime.datetime.now()

		if curr_run == 3:
			curr_run = 0
			cmd = subprocess.Popen('free | awk \'/^Mem:/{print $3}\'', shell=True, stdout=subprocess.PIPE)
			for line in cmd.stdout:
				line = line.decode()
				mem_usage = float(line)/CONST_KILO
				now = getNow()
				result = ['mem', mem_usage, now]
				log.append(result)

			cmd = subprocess.Popen('top -bn 1 | awk \'{print $9}\' | tail -n +8 | awk \'{s+=$1} END {print s}\'', shell=True, stdout=subprocess.PIPE)
			for line in cmd.stdout:
				line = line.decode()
				cpu_usage = float(line)
				now = getNow()
				result = ['cpu', cpu_usage, now]
				log.append(result)

		cmd = subprocess.Popen('netstat -ie', shell=True, stdout=subprocess.PIPE)
		for line in cmd.stdout:
			if header == False:
				header = True
			else:
				line = line.decode()
				if line != '\n':
					buffer = buffer + line
				else:
					now = getNow()
					re_match = if_re.findall(buffer)
					result = []
					for iface in re_match:
							for entry in iface:
									result.append(entry)
					result.append(now)
					log.append(result)
					buffer = ""

		# open connection to sqlite database shared with the OSCP Data Logger
		conn = sqlite3.connect('../data.db', timeout=60)
		for entry in log:
			if entry[0] == config['eth_iface']:
				# store received bytes
				add_data_point(conn, controllerStrId, 'eth0.in',  float(entry[1])/CONST_MEGA, entry[3])
				add_data_point(conn, controllerStrId, 'eth0.out', float(entry[2])/CONST_MEGA, entry[3])
				add_data_point(conn, controllerStrId, 'eth0.total', (float(entry[1])+float(entry[2]))/CONST_MEGA, entry[3])

				if prev_eth0_in == -1: # if first run, just log how much it has until now
					prev_eth0_in = float(entry[1])
					prev_eth0_out = float(entry[2])
				else: # if has previous entry, calculate delta as 5mns aggregation
					delta_in = float(entry[1]) - prev_eth0_in
					delta_out = float(entry[2]) - prev_eth0_out
					prev_eth0_in = float(entry[1])
					prev_eth0_out = float(entry[2])
					add_data_point(conn, controllerStrId, 'eth0.in.5mns',  float(delta_in)/CONST_KILO,  entry[3])
					add_data_point(conn, controllerStrId, 'eth0.out.5mns', float(delta_out)/CONST_KILO, entry[3])
					add_data_point(conn, controllerStrId, 'eth0.total.5mns', (float(delta_in)+float(delta_out))/CONST_KILO, entry[3])
			elif entry[0] == config['rf_iface']:
				# store received bytes
				add_data_point(conn, controllerStrId, 'rf0.in',  float(entry[1])/CONST_MEGA, entry[3])
				add_data_point(conn, controllerStrId, 'rf0.out', float(entry[2])/CONST_MEGA, entry[3])
				add_data_point(conn, controllerStrId, 'rf0.total', (float(entry[1])+float(entry[2]))/CONST_MEGA, entry[3])

				if prev_rf0_in == -1: # if first run, just log how much it has until now
					prev_rf0_in = float(entry[1])
					prev_rf0_out = float(entry[2])
				else: # if has previous entry, calculate delta as 5mns aggregation
					delta_in = float(entry[1]) - prev_rf0_in
					delta_out = float(entry[2]) - prev_rf0_out
					prev_rf0_in = float(entry[1])
					prev_rf0_out = float(entry[2])
					add_data_point(conn, controllerStrId, 'rf0.in.5mns',  float(delta_in)/CONST_KILO,  entry[3])
					add_data_point(conn, controllerStrId, 'rf0.out.5mns', float(delta_out)/CONST_KILO, entry[3])
					add_data_point(conn, controllerStrId, 'rf0.total.5mns', (float(delta_in)+float(delta_out))/CONST_KILO, entry[3])
			elif entry[0] == 'mem':
				add_data_point(conn, controllerStrId, 'memory_in_use',  entry[1],  entry[2])
			elif entry[0] == 'cpu':
				add_data_point(conn, controllerStrId, 'cpu_in_use',  entry[1],  entry[2])

		conn.commit()  # commit the changes
		conn.close()  # close connection with the database

		log = []
		header = False
		end = datetime.datetime.now()
		diff = end-begin
		time.sleep(int(config['refresh_interval'])-diff.seconds-diff.microseconds/1000000) # sleep for 5mins minus time it took to run
		curr_run += 1