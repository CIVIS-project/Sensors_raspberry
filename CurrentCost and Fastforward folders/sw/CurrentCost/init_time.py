import ntplib
import os
from datetime import datetime
from time import ctime
from time import gmtime, strftime

def load_temp_clock(ntp_synched):

	#loads last valid date and time if present
	time_file=open("/home/pi/sw/time_config.txt", "r+")		#opens time config files for setting on boot last temporary stored value, if available
	temp_date_time=time_file.read()
	print temp_date_time
	if temp_date_time!="":
		try:
			os.system('sudo date -s "'+ temp_date_time+'"')
			print "Temporary date and time correctly set"
			ntp_synched="2"
		except:
			print "Impossible to set temporary initial date and time"
	time_file.close()
	return ntp_synched

def ntp_synch(c, ntp_synched):
	changed_clock=0		#this flag will go to "1" only when passing from state "2" to state "1". State "3" is considered to be a reliable value, so no changed_clock is logged
	try:
		response=c.request('time.nist.gov')
		print ctime(response.tx_time)
		try:									
			time_file=open("/home/pi/sw/time_config.txt", "w")		#tries to backup the received date/time value on the time config files
			time_file.write(ctime(response.tx_time))
			time_file.close()
			print "Time data correctly stored in its config file"
		except:
			print "Impossible to save NTP date/time into restore time config file"
		os.system('sudo date -s "'+ ctime(response.tx_time)+'"')
		if ntp_synched=="2":
			changed_clock=1
		ntp_synched="1"
	except:
		print 'Warning: impossible to synch the clock with NTP server'
		if ntp_synched!="0":
			try:									
				time_file=open("/home/pi/sw/time_config.txt", "w")		#tries to save the current date/time value in the time config files
				time_file.write(datetime.now().strftime('%a %b %d %H:%M:%S %Y'))
				time_file.close()
				print "Time data correctly stored in its config file"
			except:
				print "Impossible to save Local date/time into restore time config file"
		if ntp_synched=="1":
			ntp_synched="3"

	return ntp_synched, changed_clock

def init_clock(c, ntp_synched):
	ntp_synched=load_temp_clock(ntp_synched)
	ntp_synched, changed_clock=ntp_synch(c, ntp_synched)
	return ntp_synched
