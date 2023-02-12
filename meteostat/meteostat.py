#!/usr/bin/env python3
# coding=utf8

#############################################################################################################################
#TODO LIST
#############################################################################################################################
# check what is needed in file header
# make github project 
# select right open source model, add copyright notice, write readme.md (I like MIT most)
# pip package
# go live

import configparser
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from dateutil import parser
import urllib.parse
import datetime
import time
import json 
import http.client
import argparse

argParser = argparse.ArgumentParser()
argParser.add_argument("cfg", type=str, help="config.ini file")
args = argParser.parse_args()
configFile = args.cfg


class Meteostat:
    def __init__(self):
        #read config file
        config = configparser.ConfigParser()
        try:
            with open(configFile) as f:
                config.read_file(f)
                self.rapidApiKey = config['METEOSTAT']['RapidApiKey']
                self.rapidApiHost = config['METEOSTAT']['RapidApiHost']
                self.pointData = config['METEOSTAT']['PointData']
                self.latitude = config['METEOSTAT']['Latitude']
                self.longitude = config['METEOSTAT']['Longitude']
                self.altitude = config['METEOSTAT']['Altitude']
                self.pointLocation = config['METEOSTAT']['PointLocation']
                self.stationId = config['METEOSTAT']['StationId']
                self.stationLocation = config['METEOSTAT']['StationLocation']
                self.timeZone = urllib.parse.quote(config['METEOSTAT']['TimeZone'], safe='')
                numberOfRequestsPerDay = int(config['METEOSTAT']['NumberOfRequestsPerDay'])
                self.sleepTimeSeconds = (24*60*60)/numberOfRequestsPerDay
                self.influxdbUrl = config['INFLUXDB']['InfluxDbUrl']
                self.influxdbToken = config['INFLUXDB']['InfluxDbToken']
                self.influxdbOrg = config['INFLUXDB']['InfluxDbOrg']
                self.influxdbBucket = config['INFLUXDB']['InfluxDbBucket']
        except:
            print('Config file (' + configFile + ') not found or property does not exist')
            raise

    def run(self):
        print("Running ...")
        while True:
            
            #today plus next 5 days
            start = datetime.datetime.now() - datetime.timedelta(days=0)
            end = start + datetime.timedelta(days=5)

            conn = http.client.HTTPSConnection("meteostat.p.rapidapi.com")
            
            headers = {'X-RapidAPI-Key': self.rapidApiKey, 'X-RapidAPI-Host': self.rapidApiHost}
            
            if self.pointData == False:
                conn.request("GET", "/stations/hourly?station=" + self.stationId + "&start="  + start.strftime("%Y-%m-%d") + "&end=" + end.strftime("%Y-%m-%d") + "&tz=" + self.timeZone, headers=headers)
            else:
                conn.request("GET", "/point/hourly?lat=" + str(self.latitude) + "&lon=" + str(self.longitude) + "&start="  + start.strftime("%Y-%m-%d") + "&end=" + end.strftime("%Y-%m-%d") + "&alt=" + str(self.altitude) + "&tz=" + self.timeZone, headers=headers)
            res = conn.getresponse()
            meteostatdata = res.read()
            meteostatJson=json.loads(meteostatdata.decode("utf-8"))

            #prepare points to write to influx
            point = Point("Weather")
            
            if self.pointData == False:
                point.tag("Station", self.stationLocation)
            else:
                point.tag("Station", self.pointLocation)
                
            point.measurement("Weather")

            #reading the json dict and write to influx
            for i in meteostatJson['data']:
                point.time(parser.parse(i["time"]))
                for key, value in i.items():
                    # only write key value pair when a value is available
                    if type(value) != type(None): 
                        point.field(key, value) 
                with InfluxDBClient(url=self.influxdbUrl, token=self.influxdbToken, org=self.influxdbOrg) as client:
                    write_api = client.write_api(write_options=SYNCHRONOUS)
                    write_api.write(bucket=self.influxdbBucket, record=point)
        
            print("Weather data posted to influx ...")
            print("Sleep for " +  str((self.sleepTimeSeconds/60)) + " minutes ...")
            time.sleep(self.sleepTimeSeconds)
        

if __name__ == '__main__':
    meteostat = Meteostat()
    meteostat.run()