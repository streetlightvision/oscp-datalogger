# OSCP DataCollect

## Summary

The OSCP DataCollect is an application that reads a SQLite database, and sends the available data to any SLV CMS instance set in the configuration file using the Open Smart City Protocol (OSCP).

## Configuration

The configuration is read from a json file (currently _config.json_). Ex:

	{
		"debug" : true,
		"host" : "localhost",
		"port" : 8080,
		"path" : "/reports",
		"username" : "admin",
		"password" : "password",
		"refresh_interval" : 10
	}
	
## Running

Just run the command below on the directory where datalogger.py is present:

	python3.5 datalogger.py
	
By running that, the SQLite database (_data.db_) will be created automatically.

## Details

### Data to send
The application looks for new data on the table _oscp\_data_, and if it was not set as sent before, it is sent to the CMS indicated by the configuration files.  
The table _oscp\_info_ has a row named `last_pushed` that indicate what was the last `id` to be sent to the CMS.

#### Table _oscp\_data_

	CREATE TABLE "oscp_data" (
					`id`	INTEGER PRIMARY KEY AUTOINCREMENT,
					`controllerStrId`	TEXT NOT NULL,
					`idOnController`	TEXT NOT NULL,
					`meaning`	TEXT,
					`value`	TEXT NOT NULL,
					`time`	INTEGER NOT NULL
				)
				
The fields _controllerStrId_ and _idOnController_ are the ones set for the device on the SLV CMS.  
The _meaning_ field defines which property of the given device is being written to (e.g.: LampLevel, SensorCO).  
The _value_ field defines the value of the property being set (e.g.: 10.0).  
The _time_ field, is a timestamp with the format `%Y-%m-%dT%H:%M:%S.%fZ`.

## Adding new data

To add new data to the SQLite database, you can use a query like this:

	INSERT INTO `oscp_data` 
			(`controllerStrId`,`idOnController`,`meaning`,`value`,`time`) 
			VALUES 
			('{controllerStrId}','{idOnController}','{meaning}',"{value}",'{time}');
			
Replacing the appropriate fields as indicated above.

## Examples

Check the _examples_ directory for examples.