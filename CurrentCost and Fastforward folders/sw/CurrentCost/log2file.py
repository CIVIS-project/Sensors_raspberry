import time
import sys
from datetime import datetime
from time import strftime

def log2file(log_message, log_file):
	
	try:
		logfile=open(log_file, "a")
		logfile.write(datetime.now().strftime('%Y/%m/%d %H:%M:%S')+" "+log_message+"\n")
	except:
		print "Impossible to log event"
	try:
		logfile.close()
	except:
		print "Impossible to close log file"

	

