#This script has been developed in Concept Reply for enabling the possibility of managing CurrentCost EnvirNET with Raspberry Pi
#It creates aggregated statistics and energy calculations that can be exported periodically towards other Platforms.
#It makes use of 2 external libraries (serial.py and parse.py) released under GNU licence. All rights are of respective proprietaries/developers.
 
import serial
import time
import sys
import os
from parse import *
import subprocess
import types
import math
from datetime import datetime, timedelta
from file_tail import *
import redis
from getSettings import *
from init_time import *
from log2file import *

envir_logfile="/home/pi/sw/CurrentCost/envir_log.txt"
logfile=open(envir_logfile, "a")
logfile.close()

c= ntplib.NTPClient()				#NTP client for periodic synch ot Raspberry time
try:
	apartmentID=getApartmentID()
	
except:
	log2file("Error during elaborations for validating contract data or accessing config files", envir_logfile)
	#raise Exception("Error during elaborations for validating contract data or accessing config files")


print "Assigned Apartment ID: "+apartmentID

redis_connection=False

while redis_connection==False:
	try:
		print "Connecting to Redis Server"
		redis_DB = redis.StrictRedis(host='localhost', port=6379, db=0)
		redis_connection=redis_DB.ping()
		redis_connection=True
		print "Connection to Redis Server successful"
	except:
		print "Impossible to connect to Redis DB. Trying to restart the service..."
		try:
			os.system('sudo /etc/init.d/redis-server restart')
		except:
			print "Impossible to restart the Redis Server"
			log2file("ERROR: Impossible to restart the Redis Server", envir_logfile)
			redis_connection=False

#-------------------------------------------------------------------------------------
#redis_DB.flushdb()	#clears the DB. THIS LINE MUST BE REMOVED BY FINAL SOFTWARE  ||
#-------------------------------------------------------------------------------------

N=10			#number of channels in CurrentCost EnvirNET
line="\n"		#variable that will contain the line read by EnvirNET serial port
meas=0			#variable counting the number of successfull readings from EnvirNET
sensor_id=0		#variable that will store the sensorID number at each iteration (value assigned by CurrentCost)
sensor_number=0		#variable that will identify the sensor/channel number at each iteration (it can vary from 0 to 9)
buffer_lenght=50 	#defines the lenght of the sensors measures buffer, before sending them to file/server. Do not use values too much higher than 50/100
			#with buffer_lenght=50, data are stored and accumulated every 300-400seconds for each sensor
temp_buffer_lenght=100	#defines the lenght of the temperature measures buffer

temp=[0.0 for col in range(temp_buffer_lenght)]					#variable containing last temperature samples coming from EnvirNET built-in sensor
temp_ind=0		#index pointing at last temperature reading in the buffer defined above

curr_reading=[[0.0 for col in range(buffer_lenght)] for row in range(N)] 	#creates N=10 vectors (in 1 matrix) for containing last M=buffer_luenght power readings for each of 
										#N=10 sensors/channels available in the EnvirNET. Each row is treated as a circular list
cur_read_ind=[0 for col in range(N)]						#N=10 indexes pointing at last readings for each of 10 possible sensors in the circular lists defined above


prev_reading=[0.0 for col in range(N)]						#N=10 values containing the previous power reading for each channel/sensor

c= ntplib.NTPClient()				#NTP client for periodic synch ot Raspberry time
tz_cyclevalue=275				#sets every how many cycles the timezone will be recalculated
ntp_cyclevalue=150				#sets every how many cycles the NTP server will be interrogated
tz_iter=tz_cyclevalue
ntp_iter=0

ntp_synched="0"		#describes the status of the clock

# Values for ntp_synched:
# 0="start (undefined) status"; the clock could have mantained last value or be returned to 1970, Jan 1 
# 1="date/hour synched with NTP service; 
# 2="date/hour loaded from time config file, but not synched with NTP service; 
# 3="data not synched with NTP service, date/time should be roughly ok, because synched clock synched and no reboot occurred in the meanwhile"

if redis_DB.llen("ClockFlag")>0:
	redis_DB.lpop("ClockFlag")
redis_DB.rpush("ClockFlag", ntp_synched)

ntp_synched=init_clock(c, ntp_synched)
redis_DB.lpop("ClockFlag")
redis_DB.rpush("ClockFlag", ntp_synched)

print "NTP synchronization: "+str(ntp_synched)
#--------------------------------------------------------------------------------------------#
### do not move the following assignation block before the clock initialization procedure ####
#--------------------------------------------------------------------------------------------#
#prev_timestamp will contain the timestamp associated to the second last samples of each sensor/channel
prev_timestamp=[datetime.now() for col in range(N)]
#curr_timestamp will contain the timestamp associated to last/current samples of each sensor/channel
curr_timestamp=[datetime.now() for col in range(N)]

cycle_lower_tstmp=[datetime.now() for col in range(N)]				#timestamp for the starting moment of last cycle time interval, for each sensor/channel
cycle_upper_tstmp=[datetime.now() for col in range(N)]				#timestamp for the end moment of last cycle time interval, for each sensor/channel
cycle_energy=[0.0 for col in range(N)]						#N=10 values accumulating the energy associated to each sensor in the last cycle period
sample_period=[0.0 for col in range(N)]						#N=10 values calculating the last Envirnet sample period for each channel
total_energy=[0.0 for col in range(N)]						#N=10 values accumulating the total energy associated to each sensor from beginning of monitoring

start_time=datetime.now()


try:
    	ser = serial.Serial("/dev/ttyUSB0", 57600)			#reads a line from serial port via USB0 port. If the CC cable is plugged in another port, ttyUSB0 value must be updated. 57600 is the default baud rate
except:
	log2file("ERROR: Invalid CurrentCost Device", envir_logfile)
    	sys.stderr.write('Invalid CurrentCost Device')


while True: 
	
	try:
		#This section is for periodic calculation of clock timezone
		if tz_iter==tz_cyclevalue:  #it corresponds more or less to 10minutes with normal Envirnet Data elaboration times
			tz_iter=0
			try:	
				#Calculation of timezone offset
				offset =time.timezone if (time.localtime().tm_isdst==0) else time.altzone
				offset=-offset/3600.0
				rest=int(abs(offset*4)%4)
				if rest==0:
					timezone='{:=+#03,d}'.format(int(offset))+":00"
				elif rest==1:
					timezone='{:=+#03,d}'.format(int(offset))+":15"
				elif rest==2:
					timezone='{:=+#03,d}'.format(int(offset))+":30"
				elif rest==3:
					timezone='{:=+#03,d}'.format(int(offset))+":45"
				print "Current timezone: "+timezone
			
			except:
				print 'Problems in calculating local timezone'
				timezone="+00:00" #defines a GMT timezone in the case of problems in calculating timezone, to make it possible to continue the execution of the script without great problems
		tz_iter+=1
	
		changed_clock=0
		#This section is for periodic synch of the clock with NTP server
		if ntp_iter==ntp_cyclevalue:  #it corresponds more or less to 5-6minutes with normal Envirnet Data elaboration times
			ntp_iter=0
			ntp_synched, changed_clock=ntp_synch(c, ntp_synched)
			redis_DB.lpop("ClockFlag")
			redis_DB.rpush("ClockFlag", ntp_synched)
		ntp_iter+=1
		print "NTP iter:" + str(ntp_iter)
		print "ntp_synched: "+ntp_synched

		if changed_clock:	#this flag will go to "1" only when passing from state "2" to state "1". State "3" is considered to be a reliable value, so no changed_clock is logged
			#this routine manages the case of clock changed by NTP service. The cycle needs to be closed prematurely and a new one must be started
			for i in range(N):
				cur_read_ind[i]=0
				cycle_lower_tstmp[i]=cycle_upper_tstmp[i]		#the current interrupted cycle for sensor #i has started when previous cycle finished
				cycle_upper_tstmp[i]=prev_timestamp[i]			#the current interrupted cycle finished with last received sample for all sensors
				print "Durata ultimo ciclo: ", (cycle_upper_tstmp[i]-cycle_lower_tstmp[i]).total_seconds(), " for sensor: ", i
				print cycle_lower_tstmp[i]
	
				#in this section the message about consumption to be forwarded is formatted
				if cycle_energy[i]!=0:		#in this cycle the message is formatted keeping in count that values are referred to ntp_synched=2 even if now this value is changed to 1
					message=apartmentID+"\t"+cycle_lower_tstmp[i].strftime('%Y-%m-%dT%H:%M:%S')+timezone+"\t"+cycle_upper_tstmp[i].strftime('%Y-%m-%dT%H:%M:%S')+timezone+"\t"+str(i)+"\t"+str(cycle_energy[i])+"\t"+cycle_upper_tstmp[i].strftime('%a')+"\t2\t1"	#different columns are divided by tabs. The last value means "real time value"
					print message
					
					cycle_energy[i]=0
	
					#checking that all is ok with Redis server
					try:
						redis_DB.ping()
						print "\nRedis is connected\n"
					except:
						print "\nRedis was not connected... trying to connect again\n"
						try:
							os.system('sudo /etc/init.d/redis-server restart')
							redis_DB = redis.StrictRedis(host='localhost', port=6379, db=0)
						except:
							print "Impossible to connect to Redis DB"
					#in this section the message about average consumption in the interrupted cycle is pushed into a Redis List
					redis_DB.rpush("cycle_energy"+str(i), message)
					print(redis_DB.lrange("cycle_energy"+str(i), 0, -1))
	except:
		log2file("WARNING: Problems while performing periodic NTP and Timezone operations", envir_logfile)
		print "Problems while performing periodic NTP and Timezone operations"

#----Starting here the analysis of fresh data from Envirnet

	try:
		print "---------------Press Ctrl+Z to terminate--------------------------------\n" 
		line=ser.readline()  		#reads another line from EnvirNET
		print line
		sys.stdout.flush()
	except:
		log2file("ERROR: Error in reading serial port with Current Cost", envir_logfile)
		print 'Error in reading serial port with Current Cost'
		time.sleep(30)
		
	
	try:
		logfilesize=os.stat(envir_logfile).st_size
		if logfilesize>50000000:	#clears the log if it reaches 50MB
			logfile=open(envir_logfile, "w")
			logfile.close()
		#line="\xef<msg><src>CC128-v1.44</src><dsb>00079</dsb><time>09:46:00</time><tmpr>  .0</tmpr><sensor>2</sensor><id>03277</id><type>1</type><ch1><watts>00008</watts></ch1></msg>"

		if search('<watts>{:d}</watts>', line)!=None:   	#parses for <watts> tag, which is contained only in "real time output from Watt-sensors"
			try:
				sensor_number =search('<sensor>{:d}</sensor>', line)[0]			#parses the line in search of a channel number	
				i=sensor_number
				curr_timestamp[i]=datetime.now()					#associates to current_timestamp the Raspberry datatime
				local_time = search('<time>{:tt}</time>', line)[0] 			#parses the line in search of a timestamp 
        			temp[temp_ind] = search('<tmpr>{:f}</tmpr>', line)[0]   		#parses the line in search of a temperature
				sensor_id= search('<id>{:d}</id>', line)[0]				#parses the line in search of a sensor ID
				reading = search('<watts>{:d}</watts>', line)[0]			#parses the line in search of instantaneous power measure
				j=cur_read_ind[i]
				curr_reading[i][j]=reading						#stores the reading in the proper cell of the defined matrix
				meas+=1
        			print "Reading OK: time:", curr_timestamp[i].strftime('%Y/%m/%d %H:%M:%S'), " temp=",temp[temp_ind],", sensor n.=", sensor_number, ", sensor ID=", sensor_id, ", instant. pwr=", reading,"W, misurazione n.=" ,meas, "\n"
				line="\n"
				print cur_read_ind
				
				#Energy calculations on "Watt-sensors"
				s=total_energy[i]
				s1=cycle_energy[i]						#Wh consumed in last cycle
				sample_period[i]=(curr_timestamp[i]-prev_timestamp[i]).total_seconds()
				s1=s1+(reading+prev_reading[i])*sample_period[i]/2/60/60  	#adding consumption in the last 'sample_period' seconds to cycle_energy[i]
				s=s+(reading+prev_reading[i])*sample_period[i]/2/60/60  	#adding consumption in the last 'sample_period' seconds to total_energy[i]
				total_energy[i]=s
				print "Energy consumption from", start_time, " (Wh): ", s
				print "Enegy consumption in last cycle (Wh): ", s1
				prev_timestamp[i]=curr_timestamp[i]
				prev_reading[i]=reading
				
					
				if j<buffer_lenght-1:
					cur_read_ind[i]+=1
					cycle_energy[i]=s1
				else:
					cur_read_ind[i]=0
					cycle_energy[i]=s1
					cycle_lower_tstmp[i]=cycle_upper_tstmp[i]		#stores the value of the timestamp when the last cycle has started for sensor #i
					cycle_upper_tstmp[i]=curr_timestamp[i]			#stores the value of the timestamp when the last cycle ends for sensor #i
					print "Durata ultimo ciclo: ", (cycle_upper_tstmp[i]-cycle_lower_tstmp[i]).total_seconds(), " for sensor: ", i
					print cycle_lower_tstmp[i]

					#in this section the message about consumption to be forwarded is formatted
					message=apartmentID+"\t"+cycle_lower_tstmp[i].strftime('%Y-%m-%dT%H:%M:%S')+timezone+"\t"+cycle_upper_tstmp[i].strftime('%Y-%m-%dT%H:%M:%S')+timezone+"\t"+str(i)+"\t"+str(s1)+"\t"+cycle_upper_tstmp[i].strftime('%a')+"\t"+ntp_synched+"\t1"	#different columns are divided by tabs. The last value means "real time value"
					print message

					cycle_energy[i]=0
				
					#checking that all is ok with Redis server
					try:
						redis_DB.ping()
						print "\nRedis is connected\n"
					except:
						print "\nRedis was not connected... trying to connect again\n"
						try:
							os.system('sudo /etc/init.d/redis-server restart')
							redis_DB = redis.StrictRedis(host='localhost', port=6379, db=0)
						except:
							print "Impossible to connect to Redis DB"
							log2file("ERROR: Impossible to connect to Redis DB after its restart", envir_logfile)
							time.sleep(30)

					#in this section the message about average consumption in the cycle is pushed into a Redis List	
					redis_DB.rpush("cycle_energy"+str(i), message)
					print(redis_DB.lrange("cycle_energy"+str(i), 0, -1))
			except:
				print 'Invalid data sent by Envirnet during transmission of real time output from sensors'	
				log2file("ERROR: Invalid data sent by Envirnet during transmission of real time output from sensors", envir_logfile)
				time.sleep(30)
			
	except:
		log2file("ERROR: Invalid data format sent by Envirnet, it does not contain text or parsable data: "+line, envir_logfile)
		print 'ERROR: Invalid data format sent by Envirnet, it does not contain text or parsable data'
		time.sleep(60)
    	