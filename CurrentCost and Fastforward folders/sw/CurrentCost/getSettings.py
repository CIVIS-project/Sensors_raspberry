import csv
import time
import httplib
import urllib
from parse import *
from shutil import copy


def getApartmentID():
	ack=False
	apartmentID="NULL"

	while not ack:
		ack, apartmentID=getApartmentIDfromFile()
		n=0
		while (apartmentID=="NULL" or apartmentID=="-1") and n<6:
			n+=1
			ContractID=raw_input("Enter the electricity contract ID: ")
			POD=raw_input("Enter the electricity POD code: ")
			apartmentID=getApartmentIDfromServer(POD, ContractID)
			print "ApartmentID: "+apartmentID
			try:
				if int(apartmentID)<0:
					apartmentID="-1"
					ack=False
				else:
					ack=True
					PositionID=-1
					while PositionID<1 or PositionID>5:
						print "Select the code number for the position of the apartment:"
						print "1. Storo"
						print "2. Lodrone"
						print "3. San Lorenzo in Banale"
						print "4. Dorsino - Andogno"
						try:
							PositionID=int(raw_input("5. Stenico\n"))
						except:
							print "Invalid integer"
					print PositionID
					backupSettings(apartmentID, ContractID, POD, PositionID)
			except:
				apartmentID="NULL"
				ack=False

			if not ack:
				print "Invalid data combination, please try again"
				if n==5:
					raise Exception('Impossible to continue with a not valid POD/ContractID combination')

			else:
				
				sendResp=collectSendApartmData(apartmentID)
				reply=search('<string>{:w}</string>', sendResp)[0]
				#print reply
				print "The collection of sensors data in CIVIS DB is "+reply
				if reply != "OK":
					raise Exception("Error while inserting data into CIVIS DB. Impossible to continue")
				conf=raw_input("Press enter to continue")
					
	return apartmentID



#####

def collectSendApartmData(apartmentID):
	kitTypeNumber=4	#The variety number of sensor kits available for the Trentino's Sensor Layer deployment
	dwellers=-1
	confirm=False
	while dwellers<0 or confirm==False:  #considers also the case of empty houses
		try:
			dwellers=int(raw_input("Insert the number of dwellers in the apartment: \n"))
		except:
			print "Invalid integer"	
		conf=raw_input("Press Y or y to confirm the dwellers are "+str(dwellers)+": \n")
		if (conf=="Y") or (conf=="y"):
			confirm=True

	PV=-1
	while PV<0 or PV>1:
		print "Select:"
		print "0. if no solar panel is present;"
		try:
			PV=int(raw_input("1. if solar panels are present\n"))
		except:
			print "Invalid integer"
	print "The possible kits installable in any apartment are the following"
	print "1. DSO data + amperometric clamps + thermometers"
	print "2. DSO data + amperometric clamps + smart plugs/other electricity sensors"
	print "3. DSO data + amperometric clamps + smart plugs/other electricity sensors + thermometers"
	print "4. DSO data + amperometric clamps + smart plugs/other electricity sensors + thermometers + smart camera"
	SensorType=["NULL" for col in range(36)]
	SensorLabel=["NULL" for col in range(36)]
	kitType=-1
	while kitType<1 or kitType>kitTypeNumber:
		try:
			kitType=int(raw_input("Insert the type code for the kit installed in the Apartment: "))
		except:
			print "Invalid integer"
		
		
		SensorType[0]="0"
		SensorLabel[0]="Consumo Elettrico"
		if PV==1:
			SensorType[8]="2"
			SensorLabel[8]="Produz. Elettrica"
		if kitType>=2:
			nSP=-1
			while nSP<1 or nSP>28:
				try:
					nSP=int(raw_input("Insert the number of Smart Plugs installed in the Apartment: "))
				except:
					print "Invalid integer"
			for k in range (1,min(nSP,7)+1):
				SensorType[k]="1"
				SensorLabel[k]=raw_input("Insert a label for the smart plug n."+str(k)+": ")
			if nSP>7:
				for k in range (1,nSP-6):
					SensorType[9+k]="1"
					SensorLabel[9+k]=raw_input("Insert a label for the smart plug n."+str(k+9)+": ")
			#implement here additional commands for other electricity sensors
				
		if (kitType==1 or kitType>=3):
			ThermNum=-1
			while ThermNum<1 or ThermNum>2:
				print "Select:"
				print "1. if only indoor thermometer is present;"
				try:
					ThermNum=int(raw_input("2. if also outdoor thermometer is present\n"))
				except:
						print "Invalid integer"
			SensorType[32]="32"
			SensorLabel[32]="Temp. Interna"
			if ThermNum==2:
				SensorType[33]="33"
				SensorLabel[33]="Temp. Esterna"
		if kitType==4:
			SensorType[31]="31"
			SensorLabel[31]="Contatore Gas"
		
	print SensorType
	print SensorLabel
	SensorTypeString=SensorLabelString=""
	for i in range(35):
		SensorTypeString=SensorTypeString+SensorType[i]+"\t"
		SensorLabelString=SensorLabelString+SensorLabel[i]+"\t"
	SensorTypeString=SensorTypeString+SensorType[35]
	SensorLabelString=SensorLabelString+SensorLabel[35]
	message=apartmentID+";"+str(kitType)+";"+str(PV)+";"+str(dwellers)+";"+SensorTypeString+";"+SensorLabelString
	print message

	stringSent=False
	while not stringSent:
		try:
			conn=httplib.HTTPConnection('production_server_address', timeout=6)		#production server
			#conn=httplib.HTTPConnection('development_server_address', timeout=6)			#development server
			headers={"Content-Type" : "application/text", "Accept-Charset" : "utf-8", "Accept" : "text/plain"}	#connects to server
			conn.request('POST', '/CivisEnergy/DataParser.svc/postApartmData', message, headers)			#posts message and headers
			r=conn.getresponse()											#gets response
			reply=r.read()
			conn.close()
			print reply
			stringSent=True 
		except:								#if something goes bad in the POST, 
			reply=raw_input('Problems in connection with CIVIS Server while sending electricity data. Press enter to retry')
	return reply


######

def getApartmentIDfromFile():
	ack=False
	ApartmentID="NULL"
	try:
		setting_file=open("/home/pi/sw/civis_config.txt", "r+")			#tries to open the config file and if successful selects the related path
		configfilepath="/home/pi/sw/civis_config.txt"
	except:
		try:
			setting_file=open("/home/pi/sw/backup/civis_config.txt", "r+")		#if the primary config file is not available, it tries to open the secondary config file
			try:
				copy("/home/pi/sw/backup/civis_config.txt", "/home/pi/sw/")	#if successful, tries to restore the primary config file
			except:
				print "Impossible to restore primary config file"
			configfilepath="/home/pi/sw/backup/civis_config.txt"			#selects the path of the accessible secondary config file
		except:
			raise Exception("Corrupted config files, impossible to recover")	#if both config files are corrupted, it is necessary to manually restore them
	try:
		copy("/home/pi/sw/civis_config.txt", "/home/pi/sw/backup/")   				#tries to backup the primary config file
	except:
		print "Impossible to backup primary config file"
	setting_file.close()   
	with open(configfilepath, "r+") as csvfile:						#opens the available config file as CSV
			csvreader=csv.reader(csvfile, delimiter="\t")
			for row in csvreader:
				if row[0]=="ID":
					ApartmentID=row[1] 					#selects the row containing the ID setting and associates this ID to the ApartmentID
	try:
		if int(ApartmentID)<0:
			ApartmentID="-1"
			ack=False
		else:
			ack=True
	except:
		ApartmentID="NULL"
		ack=False

	return ack, ApartmentID


#####

def getApartmentIDfromServer(POD, ContractID):
	
	ApartmentID="NULL"
	try:
		line=getInitialSettings("ApartmentID", POD, ContractID)
		ApartmentID=str(search('<string>{:d}</string>', line)[0])	#requests a value from the server
	except:
		print "Error while getting ApartmentID from server"
			
	return ApartmentID


#####

def getInitialSettings(setting, POD, ContractID):
	if setting=="ApartmentID":
		try:
			conn=httplib.HTTPConnection('production_server_address', timeout=6)	#production server
			#conn=httplib.HTTPConnection('development_server_address', timeout=6)		#development server
			base_url='/CivisEnergy/DataParser.svc/getInitialSettings'
			params=urllib.urlencode({'POD':POD,'ContractID':ContractID})
			conn.request('GET', base_url+'?'+params)		
			r=conn.getresponse()
			return r.read()
		except:
			print 'Warning: Problems in connection with CIVIS Server while getting initial settings'
			return "NULL"
	


######

def backupSettings(ApartmentID, ContractID, POD, PositionID):

	try:									
		setting_file=open("/home/pi/sw/civis_config.txt", "w")		#tries to backup the received value on the config files
		setting_file.write("ID\t"+ApartmentID+"\n")
		setting_file.write("ContractID\t"+ContractID+"\n")
		setting_file.write("POD\t"+POD+"\n")
		setting_file.write("PositionID\t"+str(PositionID)+"\n")
		setting_file.close()
		print "Settings correctly stored in primary config file"
	except:
		print "Impossible to save settings into primary config file"
		try:
			setting_file=open("/home/pi/sw/backup/civis_config.txt", "w")
			setting_file.write("ID\t"+ApartmentID)
			setting_file.write("ContractID\t"+ContractID+"\n")
			setting_file.write("POD\t"+POD+"\n")
			setting_file.write("PositionID\t"+PositionID+"\n")
			setting_file.close()
			print "Settings saved only in the secondary config file"
		except:
			print "Impossible to save ApartmentID into both config files"
	try:
		copy("/home/pi/sw/civis_config.txt", "/home/pi/sw/backup/civis_config.txt")
		raw_input("Settings correctly backed up in secondary config file. Press a key to continue...")
	except:
		print "Impossible to backup ApartmentID into secondary config file"

