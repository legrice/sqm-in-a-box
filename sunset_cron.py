#!/usr/bin/python
import os, shutil

basepath = os.path.expanduser('~/sqm-in-a-box/')

configfile = '/tmp/config.ini'
if not os.path.exists(configfile):
	if os.path.exists(basepath + 'config.ini'):
		shutil.copy(basepath + 'config.ini', '/tmp/')

logpath = basepath + 'logs/'
if not os.path.isdir(logpath):
	os.makedirs(logpath)

sqm_logfile = basepath +'logs/sqm.log'
	
datapath = basepath + 'data/'
if not os.path.isdir(datapath):
	os.makedirs(datapath)

import configparser, sys
from distutils.util import strtobool

config = configparser.ConfigParser()
config.read(configfile)

debug = config["debug"]
debugmode = config.get('debug', 'debugmode')

import logging
# set up logging to file - see previous section for more details
if debugmode == 'debug':
	logging.basicConfig(level=logging.DEBUG,
					format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
					datefmt='%Y-%m-%d %H:%M',
					filename=sqm_logfile)
	# define a Handler which writes INFO messages or higher to the sys.stderr
	console = logging.StreamHandler()
	console.setLevel(logging.DEBUG)
else:
	logging.basicConfig(level=logging.INFO,
					format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
					datefmt='%Y-%m-%d %H:%M',
					filename=sqm_logfile)
	# define a Handler which writes INFO messages or higher to the sys.stderr
	console = logging.StreamHandler()
	console.setLevel(logging.INFO)

# set a format which is simpler for console use
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
console.setFormatter(formatter)
# add the handler to the root logger
logging.getLogger('').addHandler(console)

logger = logging.getLogger('set_cron')

try:
	gps = config["gps"]
	timezone = config.get('gps', 'timezone')
	latitude = config.getfloat('gps', 'latitude')
	longitude = config.getfloat('gps', 'longitude')
	elevation = config.getfloat('gps', 'elevation')
	location_description = config.get('gps', 'location_description')

	station = config["station"]
	apikey = config.get('station', 'apikey')
	station_id = config.get('station', 'station_id')
	has_internet = strtobool(config.get('station', 'has_internet'))
	is_mobile = strtobool(config.get('station', 'is_mobile'))
	mobile_frequency = config.get('station', 'mobile_frequency')
	has_gps = strtobool(config.get('station', 'has_gps'))
	station_name = config.get('station', 'name')
	configured = strtobool(config.get('station', 'configured'))

	sqm = config["sqm"]
	sqm_serial = config.get('sqm', 'serial')
	sqm_type = config.get('sqm', 'type')
	connection = config.get('sqm', 'connection')
	sqm_address = config.get('sqm', 'sqm_address')
	tcp_port = config.get('sqm', 'tcp_port')
	usb_port = config.get('sqm', 'usb_port')
	instrument_id = config.get('sqm', 'instrument_id')

	mail = config["mail"]
	smtp_server = config.get('mail', 'smtp_server')
	smtp_port = int(config.get('mail', 'smtp_port'))
	mailbox_username = config.get('mail', 'mailbox_username')
	mailbox_password = config.get('mail', 'mailbox_password')
	frequency = config.get('mail', 'frequency')

	logger.debug('Read values from config.ini')
except KeyError as e:
    logger.warn("Error reading the configuration section {}".format(e))

import datetime
from datetime import datetime, timedelta
import pytz
import tzlocal

tz = pytz.timezone(timezone)

now = datetime.now(tz)
logger.debug('now: ' + str(now))

nowplus5min = now + timedelta(seconds=300)
logger.debug('nowplus5min: ' + str(nowplus5min))

today = datetime.today()
logger.debug('Today: ' + str(today))

from skyfield.nutationlib import iau2000b

DAYLENGTH_CENTER_HORIZON = 0.0
DAYLENGTH_TOP_HORIZON = 0.26667
DAYLENGTH_TOP_HORIZON_APPARENTLY = 0.8333
DAYLENGTH_CIVIL_TWILIGHT = 6.0
DAYLENGTH_NAUTICAL_TWILIGHT = 12.0
DAYLENGTH_ASTRONOMICAL_TWILIGHT = 18.0

def daylength(ephemeris, topos, degrees):
    """Build a function of time that returns the daylength.

    The function that this returns will expect a single argument that is a 
    :class:`~skyfield.timelib.Time` and will return ``True`` if the sun is up
    or twilight has started, else ``False``.
    """
    sun = ephemeris['sun']
    topos_at = (ephemeris['earth'] + topos).at

    def is_sun_up_at(t):
        """Return `True` if the sun has risen by time `t`."""
        t._nutation_angles = iau2000b(t.tt)
        return topos_at(t).observe(sun).apparent().altaz()[0].degrees > -degrees

    is_sun_up_at.rough_period = 0.5  # twice a day
    return is_sun_up_at

from skyfield import api
from skyfield.api import Loader
load = Loader(basepath + '/skyfield/skyfield-data/')

ts = load.timescale()
planets = load('de421.bsp')

from skyfield import almanac

loc = api.Topos(latitude, longitude, elevation_m=elevation)

t0 = ts.utc(datetime.now(tz))
t1 = ts.utc(tz.normalize(datetime.now(tz) + timedelta(1)))

#center_time, center_up = almanac.find_discrete(t0, t1, daylength(planets, loc, DAYLENGTH_CENTER_HORIZON))
#print('Sunrise Sunset center of sun is even with horizon:')
#print(center_time.utc_iso(), center_up)

#astro_twil_time, astro_twil_up = almanac.find_discrete(t0, t1, daylength(planets, loc, DAYLENGTH_ASTRONOMICAL_TWILIGHT))
twil_time, twil_up = almanac.find_discrete(t0, t1, daylength(planets, loc, DAYLENGTH_CENTER_HORIZON))
#print('Astronomical twilight:')
#print('Civil twilight:')
logger.debug('Civil Twilight: ' + str(twil_time.utc_iso()) + ', ' + str(twil_up))
logger.debug(type(twil_up))

    
import numpy as np
result = np.where(twil_up == False)
logger.debug(result)
logger.debug('Sunset Index: ' + str(result[0][0]))
logger.debug('type(result[0][0].item()): ' + str(type(result[0][0].item())))
logger.debug('result[0][0].item() == 1: ' + str(result[0][0].item() == 1))

astro_times = twil_time.utc_iso()
if result[0][0].item() == 1:
    sunset_utc_time = astro_times[1]
    sunrise_utc_time = astro_times[0]
else:
    sunset_utc_time = astro_times[0]
    sunrise_utc_time = astro_times[1]

logger.debug('UTC Sunset time in ISO8601 format: ' + sunset_utc_time)
logger.debug('UTC Sunrise time in ISO8601 format: ' + sunrise_utc_time)

import dateutil.parser
sunset_date = dateutil.parser.parse(sunset_utc_time)
sunrise_date = dateutil.parser.parse(sunrise_utc_time)

logger.debug('UTC Sunset time in datetime format: ' + str(sunset_date))
logger.debug('UTC Sunrise time in datetime format: ' + str(sunrise_date))

sunset_localtime = sunset_date.astimezone(tz)
sunrise_localtime = sunrise_date.astimezone(tz)

logger.debug('Local Sunset time: ' + str(sunset_localtime))
logger.debug('Local Sunrise time: ' + str(sunrise_localtime))
    
config.set('suntimes', 'next_sunrise', str(sunrise_localtime))
config.set('suntimes', 'next_sunset', str(sunset_localtime))

timestr = now.strftime("%Y%m%d_%H%M%S")
sqmdatafile = timestr + '_' + instrument_id + '.dat'

if not os.path.isfile(datapath + sqmdatafile):
    with open(datapath + sqmdatafile, 'w+') as datafile:
        datafile.write('utc_now.isoformat; now.isoformat; temperature; counts; frequency; mpsas; moon_phase_deg; moon_elev_deg; moon_illum latitude; logitude; elevation\n')
        datafile.close()
	os.symlink(datapath + sqmdatafile, datapath + 'tmpsymlink')
	os.rename(datapath + 'tmpsymlink', datapath + 'latest.dat')

config.set('sqm', 'sqmdatafile', sqmdatafile)

logger.debug('datapath: ' + datapath)
logger.debug('sqmdatafile: ' + sqmdatafile)

import requests, zlib

checksum = hex(zlib.crc32( sqm_serial + sqm_type + instrument_id + apikey))[2:]
logger.debug('checksum: ' + checksum)

params = (
    ('action', 'getstationid'),
    ('device_serial', sqm_serial),
    ('instrument_id', instrument_id),
    ('device_type', sqm_type),
    ('apikey', apikey),
    ('checksum', checksum),
)

res = requests.get('http://darkskynz.org/sqminabox/api.php', params=params, headers={'User-Agent': 'Unihedron SQM-LE and Raspberry Pi'})

if res.status_code == '200':
    station_id = res.content

# Writing our configuration file to 'config.ini'
with open(configfile, 'wb') as thisconfigfile:
    config.write(thisconfigfile)
    thisconfigfile.close()
    shutil.copy(configfile, basepath + 'config.ini')

if now < sunset_localtime + timedelta(seconds=300) and now > sunset_localtime - timedelta(seconds=300):
    next_set_cron = sunrise_localtime
elif now < sunrise_localtime + timedelta(seconds=300) and now > sunrise_localtime - timedelta(seconds=300):
    next_set_cron = sunset_localtime
else:
    #next_set_cron = sunrise_localtime
    next_set_cron = sunset_localtime
    
logger.debug('next_set_cron: ' + str(next_set_cron))

jobhour = sunset_localtime.hour
jobminute = sunset_localtime.minute

import getpass
current_user = getpass.getuser()

from crontab import CronTab
my_cron = CronTab(user=current_user)

#    my_cron.env['MAILTO'] = 'justin@darkskynz.org'
exists_query_gps = exists_query_sqm = exists_sunrise_cron = exists_sunset_cron = exists_startup_cron = exists_send_data = exists_get_updates = exists_git_pull = False

for job in my_cron:
	if "Query GPS" in str(job):
		exists_query_gps = True
	if "Query SQM" in str(job):
		exists_query_sqm = True
	if "Sunrise cron" in str(job):
		exists_sunrise_cron = True
	if "Sunset cron" in str(job):
		exists_sunset_cron = True
	if "Startup cron" in str(job):
		exists_startup_cron = True
	if "Send data" in str(job):
		exists_send_data = True
	if "Get updates" in str(job):
		exists_get_updates = True
	if "git pull code updates" in str(job):
		exists_git_pull = True

if exists_query_gps == True:
	for job in my_cron.find_comment('Query GPS'):
		job.clear()
		if is_mobile == True:
			job.minute.every(5) # every 5th minute
		else:
			job.hour.on(sunset_localtime.hour)
			job.minute.on(sunset_localtime.minute)
			job.enable(True)
		job.enable(has_gps)
	logger.debug('job: ' +str(job))
	logger.debug('Query GPS cron job modified successfully')
elif exists_query_gps == False:
	get_gps = my_cron.new(command='python /home/' + current_user + '/sqm-in-a-box/get_gps_coordinates.py', comment="Query GPS")
	get_gps.minute.every(1)
	get_gps.enable(False)
	logger.debug('Query GPS job created successfully')

if exists_query_sqm == True:
	for job in my_cron.find_comment('Query SQM'):
		job.clear()
		if has_gps == True:
			if is_mobile == True:
				job.minute.every(5) # every 5th minute
			else:
				job.minute.every(1) # every minute
		job.enable(True)
		logger.debug('job: ' + str(job))
		logger.debug('Query SQM job modified successfully')
	my_cron.write()
elif exists_query_sqm == False:	
	get_sqm = my_cron.new(command='python /home/' + current_user + '/sqm-in-a-box/get_sqm_reading.py', comment="Query SQM")
	get_sqm.minute.every(1)
	get_sqm.enable(True)
	my_cron.write()
	logger.debug('Query SQM job created successfully')

if exists_startup_cron == False:
	startup_cron = my_cron.new(command='python /home/' + current_user + '/sqm-in-a-box/startup.py', comment="Startup cron")
	startup_cron.every_reboot()
	my_cron.write()
	logger.debug('Startup cron job created successfully')

if exists_get_updates == False:
	get_updates = my_cron.new(command='python /home/' + current_user + '/sqm-in-a-box/startup.py', comment="Startup cron")
	get_updates.hour.every(1)
	get_updates.enabled(has_internet)
	my_cron.write()
	logger.debug('Get update cron job created successfully')

if exists_git_pull == False:
	update_git_cron = my_cron.new(command='cd /home/' + current_user + '/sqm-in-a-box/ && git pull && https://darkskynz.org/sqminabox/api.php?action=update_processed&apikey=' + apikey, comment="git pull code updates")
	update_git_cron.hour.on(12)
	update_git_cron.minute.on(0)
	update_git_cron.enable(False)
	my_cron.write()
	logger.debug('git pull code updates cron job created successfully')

if exists_sunrise_cron == True:
	for job in my_cron.find_comment('Sunrise cron'):
		job.hour.on(sunrise_localtime.hour)
		job.minute.on(sunrise_localtime.minute)
		job.enable(True)
		logger.debug('sunrise_localtime.hour: ' + str(sunrise_localtime.hour))
		logger.debug('sunrise_localtime.minute: ' + str(sunrise_localtime.minute))
		logger.debug('job: ' +str(job))
		logger.debug('Sunrise cron job modified successfully')
	my_cron.write()
elif exists_sunrise_cron == False:
	sunrise_cron = my_cron.new(command='python /home/' + current_user + '/sqm-in-a-box/sunrise_cron.py', comment="Sunrise cron")
	sunrise_cron.minute.on(30)
	sunrise_cron.hour.on(5)
	sunrise_cron.enable(True)
	logger.debug('Sunrise cron job created successfully')

if exists_sunset_cron == True:
	for job in my_cron.find_comment('Sunset cron'):
		job.hour.on(sunset_localtime.hour)
		job.minute.on(sunset_localtime.minute)
		job.enable(True)
		logger.debug('sunset_localtime.hour: ' + str(sunset_localtime.hour))
		logger.debug('sunset_localtime.minute: ' + str(sunset_localtime.minute))
		logger.debug('job: ' +str(job))
		logger.debug('Sunset cron job modified successfully')
	my_cron.write()
elif exists_sunset_cron == False:
	sunset_cron = my_cron.new(command='python /home/' + current_user + '/sqm-in-a-box/sunset_cron.py', comment="Sunset cron")
	sunset_cron.minute.on(nowplus5min.minute)
	sunset_cron.hour.on(nowplus5min.hour)
	sunset_cron.enable(True)
	logger.debug('Sunset cron job created successfully')

if exists_send_data == True:
	for job in my_cron.find_comment('Send data'):
		job.clear()
		job.enable(True)
		if frequency == 'daily':
			job.minute.on(0)
			job.hour.on(9)
		elif frequency == 'weekly':
			job.minute.on(0)
			job.hour.on(9)
			job.dow.on('MON')
		elif frequency == 'monthly':
			job.minute.on(0)
			job.hour.on(9)
			job.day.on(1)
		else:
			job.enable(False)
	my_cron.write()
	logger.debug('Send data cron job modified successfully')
elif exists_send_data == False:
	send_data_cron = my_cron.new(command='python /home/' + current_user + '/sqm-in-a-box/send_data.py', comment="Send data")
	send_data_cron.enable(True)
	if frequency == 'daily':
		send_data_cron.minute.on(0)
		send_data_cron.hour.on(9)
	elif frequency == 'weekly':
		send_data_cron.minute.on(0)
		send_data_cron.hour.on(9)
		send_data_cron.dow.on('MON')
	elif frequency == 'monthly':
		send_data_cron.minute.on(0)
		send_data_cron.hour.on(9)
		send_data_cron.day.on(1)
	else:
		send_data_cron.enable(False)
	logger.debug('Send data cron job created successfully')

my_cron.write()
