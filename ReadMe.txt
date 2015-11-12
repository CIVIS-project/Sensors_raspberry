The folder "sw", contained in "CurrentCost and Fastforward folders", was originally positioned on the Raspberry at the path:

/home/pi 

It contains all the developed software (in python and C languages)to run CIVIS EU Project applications for managing 
CurrentCost and FastForward data. Some additional standard libraries could be needed on the Raspberry depending on the 
software present or missing at the moment of installation.

-----
The folder "OEM folders" contains the files, modified for CIVIS EU Project, useful for modify the behaviour of the 
OpenEnergyMonitor (OEM) main branch code published by the OpenEnergyMonitor foundation.
Latest OEM SD card image for Raspberry can be downloaded at: http://openenergymonitor.org/files/emonSD-17Jun2015.img.zip
Previous image can be found at: http://openenergymonitor.org/files/emonSD-13-03-15.zip 
In particular the files contain modifications for collecting data from OEM thermometers and send them towards 
CIVIS EU Project servers.

The folder "boot" within "OEM folders" contains the modified "emonhub.conf" file to be put in the /boot folder on the 
Raspberry Pi.

The "emonhub" folder contained within "OEM folders" substitutes the original "emonhub" folder contained in the root
directory of the Raspberry.

---

In order to correctly work, the  production_server_address string must be substituted with the effective CIVIS server
address in currentcost.py and getSettings.py files.

