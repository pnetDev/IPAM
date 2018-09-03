#!/usr/bin/python

# CM Hardcoding Notice: Nothing hardcoded. 
"""
This script reads "dynamicRanges.txt" to get the names of the  *.dyn files. 
It then reads each *.dyn file, figures out the IP range and flags IPs which are from a .dyn range in the IPAM table as TYPE 'Dynamic'

Log Changes here:

"""

import ipaddress
import MySQLdb
import math
import re
import subprocess
import datetime
import netaddr
from netaddr import IPAddress

#db = MySQLdb.connect("localhost","root","D0xl1nk$","staticIPs" )
db = MySQLdb.connect("10.1.1.51","ipam","ipam$2o18$","docsis" )
cur = db.cursor()

debug = "Debug"
baseDir="/root/IPAM/"
fileDir=str(baseDir) + "dhcp/"
fileName="parsedFiles/dynamicRanges.txt"
dynamics=str(baseDir) + str(fileName)
 
def logWrite(logText):
        now =  datetime.datetime.now()
        currDate = str(now)
        #currDate = currDate.replace('-', '')
        logText = str(logText)
        file = open('ipam.Log','a')
        file.write(currDate + " parseDynamic \t")
        file.write(logText)
        file.write('\n')

def validate(IP):
        pieces = IP.split('.')
        if len(pieces) != 4: return False
        try: return all(0<=int(p)<256 for p in pieces)
        except ValueError: return False
        #usage
        #result = validate(subnet)
        #print result

now = datetime.date.today()
currDate = str(now)
currDate = currDate.replace('-', '')
print "Date is " + str(currDate)


print "Parsing dynamicRanges.txt"
logWrite("Parsing dynamicRanges.txt")
for sharedNetwork in open(dynamics,'r'):
	process = True
	print debug, sharedNetwork
        sharedNetwork = sharedNetwork.split("/")[3].split(".")[0]
        print sharedNetwork
        fileName = str(fileDir) + str(sharedNetwork) + ".dyn"
        for binding in open(fileName,'r'):
		if "#" in binding:
			process = False
		if process == True:
                	rangeStart = binding.split(" ")[2]
                	rangeEnd  =  binding.split(" ")[3]
                	## We have to split rangeStart IP in quads
                	splitIP=rangeStart.split(".")
                	quad0Start = splitIP[0]
                	quad1Start = splitIP[1]
                	quad2Start = splitIP[2]
                	quad3Start = splitIP[3]
                	splitIP = rangeEnd.split(".")
                	quad0End = splitIP[0]
                	quad1End = splitIP[1]
                	quad2End = splitIP[2]
                	quad3End = splitIP[3].replace(";", "")   ## Remove ';' from rangeEnd
                	startIP = int(quad3Start)
                	endIP   = int(quad3End)
                	print "DEBUG DYNAMIC PARSE " + str(startIP) + str(endIP)
                	print str(rangeStart) + "\t" + str(rangeEnd)
                	print str(startIP) + "\t" + str(endIP)


                	hosts = endIP - startIP
                	print "loop will be " + str(hosts)
                	print "DEBUG DYNAMIC PARSE "  + "\t" + str(binding.split()[1]) + "\t" + str(binding.split()[2]) + "\t" + str(sharedNetwork)
			logString = str(rangeStart), str(rangeEnd), str(sharedNetwork)
			logWrite(logString)
                	## Update the datebase for each IP
               	 	for check in range(hosts + 1):
                        	nextIP = startIP
                        	IP = str(quad0Start) + "."  + str(quad1Start) + "." + str(quad2Start) + "." + str(nextIP)
                        	ipCheck = validate(IP)
                        	if ipCheck == True:
                                	print IP + "," + sharedNetwork + "," "Dynamic"
					logString = "    " + IP, sharedNetwork + " Dynamic"
					logWrite(logString)
                                	startIP = startIP + 1
                                	## Update the database with IP type
                                	cur.execute("UPDATE IPAM SET TYPE=%s , SharedNetwork = %s  WHERE IPADDR = %s" , ("Dynamic",sharedNetwork, IP))
                                	db.commit()
                        	else:
                                	print "ERROR " + IP + " DYNAMIC IS NOT A VALID IP ADDRESS. I will now quit. " + sharedNetwork
                                 	#subprocess.call(['bash','/root/staticIPs/trap.sh','IPAM IP PARESE ERROR',IP,"dhcpd.confAll"])
                                 	subprocess.call(['bash','/root/staticIPs/ipamLog.sh',IP,currDate,"Parse Error","*.dyn",])
                                 	print ""

db.close()
