#This script has been developed in Concept Reply for enabling the possibility of managing CurrentCost EnvirNET with Raspberry Pi
#It creates aggregated statistics and energy calculations that can be exported periodically towards other Platforms.
#It makes use of 2 external libraries (serial.py and parse.py) released under GNU licence. All rights are of respective proprietaries/developers.

#IMPORTANT: In order to correctly work all the sensors sending strings to this gateway must report the RealTime_Transm flag as the last value of the string
#To switch from development server to production server, the "post_server" variable must be change in this file, analogous changes must be made in 2 rows of getSettings.py file
#and an address must be also changed into the HiReply software.
 

import time
import os
import sys
import urllib
#import urllib2
import httplib
import subprocess
import types
import redis
from log2file import *

class Gateway():

	logfilepath="/home/pi/sw/CurrentCost/gateway_log.txt"
	
	def redis_access_ok(self):
		try:
			self.redis_DB.ping()
			print "\nRedis is connected\n"
		except:
			print "\nRedis was not correctly loaded... trying to connect again\n"
			try:
				os.system('sudo /etc/init.d/redis-server restart')
				self.redis_DB = redis.StrictRedis(host='localhost', port=6379, db=0)
			except:
				print "Impossible to connect to Redis DB"

	def gateway(self):
		post_server='production_server_address'   	#production server
		#post_server='development_server_address' 		#development server
		logfile=open(self.logfilepath, "a")
		logfile.close()
		N=10			#number of channels in CurrentCost EnvirNET
		i=0
		iter=0			#iteration number between 0 and 10000
		L1=L2=L3=0		#numbers of elements into the redis tails
		try:
			self.redis_DB = redis.StrictRedis(host='localhost', port=6379, db=0)
		except:
			log2file("Error while connecting to redis DB", self.logfilepath)
		time_out=4	#timeout for waiting connection to civis server	
		while True: 
			ack=ack1=ack2=ack3=False
			iter+=1
			print "iteration #", iter
			if iter==10000:
				iter=0
			self.redis_access_ok()  #periodically checks connection to Redis server
			L1=0
			for i in range (0,N):
				L1=L1+self.redis_DB.llen("cycle_energy"+str(i))
			L2=self.redis_DB.llen("Gas_measure_tail")
			L3=self.redis_DB.llen("OEM_data")
			L=L1+L2+L3	#total amount of elements into the gateway-related redis tails	
			if L>0:
				try:
					print "connected to server: "+post_server+"\n"
					conn=httplib.HTTPConnection(post_server, timeout=time_out)
				#-------Section dedicated to CurrentCost measures forwarding
					try:
						print "Electricity"
						for i in range (0,N):
							L1=self.redis_DB.llen("cycle_energy"+str(i))			#for each Envir channel, checks if the related list 
							print "Lunghezza tail redis: "+str(L1)
							if  L1 != 0:							#if REDIS DB is not empty
								message=self.redis_DB.lpop("cycle_energy"+str(i))		#pops the last element in the selected Redis list
								print "Il messaggio e': \n"+message
		
								try:
									
									headers={"Content-Type" : "application/text", "Accept-Charset" : "utf-8", "Accept" : "text/plain"}	#connects to server
									conn.request('POST', '/CivisEnergy/DataParser.svc/postEnvirData', message, headers)			#posts string and headers
									r=conn.getresponse()											#gets response
									print r.read()
									#time.sleep(1)
									
									ack1=True
									#post_to_server("10.41.5.101:49780/postEnvirData", message)
									#response=urllib2.urlopen('http://civis.cloud.reply.eu/CivisEnergy/DataParser.svc/postEnvirData', message).read()
									i+=1													
									if i==N:				#loops among all available Redis lists/channels (N=10: 0-9)
										i=0
								except:									#if something goes bad in the POST, 
									message=message[:-2]+"\t0"					#the real-time flag is modified
									self.redis_DB.rpush("cycle_energy"+str(i), message)		# and the message is pushed again the element in the tail 
									ack1=False
									print "Failed to send: "+message
									print 'Warning: Problems in contacting CIVIS Server while sending electricity data'
									log2file("Error: problems in contacting CIVIS Server while sending electricity data", self.logfilepath)
									
					except:
						print 'error while forwarding CurrentCost data to server: perhaps network problems?'
						log2file("Error: while forwarding CurrentCost data to server: perhaps network problems?", self.logfilepath)
						time.sleep(2)
						
					
				#-------Section dedicated to Gas measures forwarding
				
					try:
						print "Gas"
						L2=self.redis_DB.llen("Gas_measure_tail")				 
						print "Lunghezza tail redis: "+str(L2)				#if the gas measures list
						if  L2 != 0:							#in REDIS DB is not empty
							message=self.redis_DB.lpop("Gas_measure_tail")		#pops the last element in the selected Redis list
							print "Il messaggio e': \n"+message
							
							try:
								headers={"Content-Type" : "application/text", "Accept-Charset" : "utf-8", "Accept" : "text/plain"}	#connects to server
								conn.request('POST', '/CivisEnergy/DataParser.svc/postGasData', message, headers)			#posts string and headers
								r=conn.getresponse()											#gets response
								print r.read() 
								#time.sleep(1)
								ack2=True
							except:								#if something goes bad in the POST, 
								message=message[:-2]+"\t0"				#the real-time flag is modified
								self.redis_DB.rpush("Gas_measure_tail", message)	#and the gateway pushes again the element in the list
								print "Failed to send: "+message
								ack2=False
								print 'Warning: Problems in contacting CIVIS Server while sending gas data'
								log2file("Error: problems in contacting CIVIS Server while sending gas data", self.logfilepath)
					except:
						print 'error while forwarding FastForward data to server: perhaps network problems?'
						log2file("Error: while forwarding FastForward data to server: perhaps network problems?", self.logfilepath)
						time.sleep(2)
				
				#-------Section dedicated to OEM data forwarding
				
					try:
						print "Temperature"
						print "Lunghezza tail redis: "+str(L3)				#checks if the temperature measures list
						if  L3 != 0:							#in REDIS DB is not empty
							message=self.redis_DB.lpop("OEM_data")			#pops the last element in the selected Redis list
							print "Il messaggio e': \n"+message
							
							try:
								headers={"Content-Type" : "application/text", "Accept-Charset" : "utf-8", "Accept" : "text/plain"}	#connects to server
								conn.request('POST', '/CivisEnergy/DataParser.svc/post_OEMData', message, headers)			#posts string and headers
								r=conn.getresponse()											#gets response
								print r.read() 
								#time.sleep(1)
								ack3=True
							except:								#if something goes bad in the POST,
								message=message[:-2]+"\t0"				#the real-time flag is modified
								self.redis_DB.rpush("OEM_data", message)		#and the gateway pushes again the element in the list
								print "Failed to send: "+message	
								ack3=False
								print 'Warning: Problems in contacting CIVIS Server while sending OEM data'
								log2file("Error: problems in contacting CIVIS Server while sending OEM data", self.logfilepath)
					except:
						print 'error while forwarding OEM data to server: perhaps network problems?'
						log2file("Error: while forwarding OEM data to server: perhaps network problems?", self.logfilepath)
						time.sleep(2)
					conn.close()
				except:
					print 'Warning: Problems in connection with CIVIS Server... timeout after '+str(time_out)+' seconds.'
					log2file("Warning: Problems in connection with CIVIS Server... timeout after "+str(time_out)+" seconds.", self.logfilepath)
					time.sleep(3)
			ack=(ack1 or ack2 or ack3)
			print ack

			if L==0:
				sleepTime=6
			elif L>0 and L<10:
				if ack:
					sleepTime=2.5
				else:
					sleepTime=60
			elif L>10 and L<50:
				if ack:
					sleepTime=1
				else:
					sleepTime=30
			else:
				if ack:
					sleepTime=0.4
				else:
					sleepTime=30

			time.sleep(sleepTime)
			logfilesize=os.stat(self.logfilepath).st_size
			if logfilesize>50000000:	#clears the log if it reaches 50MB
				logfile=open(self.logfilepath, "w")
				logfile.close()
				
			
x=Gateway()
x.gateway()		
					
					
			