import time
import sqlite3
import datetime
from random import randint

while True:  # repeat indefinitely

    meaning = 'Occupancy'
    controllerStrId = 'Test'
    idOnController = 'PS01'
    value = str(randint(0, 50))  # get a random value as the sensor reading
    now = datetime.datetime.now().strftime(
        '%Y-%m-%dT%H:%M:%S.%fZ')  # get timestamp for 'now'

    print('Inserting value: '+value)
    print('Now: '+now)

    # prepare command to insert new row into `oscp_data` table
    command = """INSERT INTO `oscp_data`
		(`controllerStrId`,`idOnController`,`meaning`,`value`,`time`)
		VALUES
		('{controllerStrId}','{idOnController}','{meaning}',"{value}",'{time}');"""

    # open connection to sqlite database shared with the OSCP Data Logger
    conn = sqlite3.connect('../data.db', timeout=60)

    conn.execute(command.format(
        controllerStrId=controllerStrId,
        idOnController=idOnController,
        meaning=meaning,
        value=value,
        time=now))  # execute command setting values
    conn.commit()  # commit the changes
    conn.close()  # close connection with the database

    time.sleep(10)
