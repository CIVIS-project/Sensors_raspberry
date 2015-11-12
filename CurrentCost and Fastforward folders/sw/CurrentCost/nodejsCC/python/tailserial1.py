import serial
import time
import sys
import httplib, urllib

try:
    	ser = serial.Serial("/dev/ttyUSB0", 57600)
except:
    	sys.stderr.write('Invalid CurrentCost Device')
while 1:
	cc_message=ser.readline()
	headers = { "Content-type":"application/xml", "Accept": "text/plain"}
      	print( cc_message ),
      	sys.stdout.flush()
	server_url="http://civis.cloud.reply.eu/Civis/DataParser.svc/postCurrentCostData"
	httpServ = httplib.HTTPConnection(server_url, 80)
	#httpServ.connect()
	httpServ.request("POST", cc_message, "", headers)
	response=httpServ.getresponse()
	if response.status == httplib.OK:
		print "Correctly sent"
		print response.read()
	else:
		print response.read()
	httpServ.close()
