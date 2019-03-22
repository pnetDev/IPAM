#!/usr/bin/python

#### CM Hardcoding Notice: This script hard codes the GiAddrs. This should be done via .giaddr files names, similar to .dyn or a database table.  This needs to be reviewed.
""" 
CM 29-01-18 This script is one function and does the following:
Creates a duplicate of table IPAM as IPAM<currentDate>
Drops all data from IPAM
Reads "CCR1Routes.terse.txt" and creates an entry for each IP address with the fields set as follows:
 	o IPADDR=IPAddress
	o LEASED=NotLeased
	o SUBNET=Subnet
	o SharedNetwork=None
	o daysNotLeases=0	

##### CHANGE LOG #######
# 180906 The shell script has dumped IPAM_PREVIOUS. This script will drop IPAM_PREVIOUS. Copy IPAM as IPAM_PREVIOUS and drop IPAM.
# 180831 First 4 IPs were not being reserved. Skip counter wasn't being reset. Fixed this.
# 180831 New version. Read subnets to a list 'networkList' and then sort by prefix. Used to use pytricia but this is no longer needed.
# 180228 When dropping IPAM we don't drop the data for persistentStatic.
# 180222 Code cleanup.
# 180221 Need to mark the IPs which are GiAddrs for a bridgedNetwork to GIADDR. These IPs will never be used for leases.
# 180218 Setting first 4 IPs of a network to TYPE 'RESERVED'
# 180219 Default value of persistentStatic is 0
# 180219 We update IPAM with the info from persistentStatic table and add the IP if it doesn't exist.
# 180208 Does not write net address, first 5 usable IPs and broadbcast address
# 180202 Now using module 'Pytrica' to carry out longest prefix match and  'ipaddress' to work out the start and end IP of a subnet. 
# 180201 Have a solution for overlapping routes. If the IP alredy exists we just update the sharedNetwork and subnet.
# 180130 New code to validate the IP address format.
# 171212 We duplicate the IPAM table to IPAMTABLE<CurrDate>.  Streamlined the code, removed elements that were from an older project. 
## CM No ipam software suitable so I have written my own script which lookup up the CCR1 routing table.

"""
import netaddr
from netaddr import *
import MySQLdb
import math
import re
import datetime
import subprocess
#import pytricia
import ipaddress
from ipaddress import *
import re
#pyt = pytricia.PyTricia()
from sys import stdout
networkList = []
Log="/root/IPAM/bin/ipam.Log"
baseDir="/root/IPAM/"
fileName="parsedFiles/CCR1Routes.terse.txt"
routingTable=str(baseDir) + str(fileName)

def logWrite(logText):
        now =  datetime.datetime.now()
        currDate = str(now)
        logText = str(logText)
        file = open(Log,'a')
        file.write(currDate + " parseRoutes \t")
        file.write(logText)
        file.write('\n')

def validate(checkSubnet):
        pieces = checkSubnet.split('.')
        if len(pieces) != 4: return False
        try: return all(0<=int(p)<256 for p in pieces)
        except ValueError: return False
	#usage
	#result = validate(subnet)
	#print result

## Determine the date, result is yyyymmdd
now = datetime.date.today()
currDate = str(now)
currDate = currDate.replace('-', '')

subnetPosition = 0
subnet = "0"
subnets = "0"
print ""
print "Working...."

#db = MySQLdb.connect("localhost","root","D0xl1nk$","staticIPs" )
db = MySQLdb.connect("10.1.1.51","ipam","ipam$2o18$","docsis" )
cur = db.cursor()

## Build sql query
sqlCopy = "CREATE TABLE IPAM" + str(currDate) + " LIKE IPAM"
sqlPopulateCopy = "INSERT IPAM" + str(currDate) + " SELECT * FROM IPAM"
#dropCopy = "DROP TABLE IF EXISTS IPAM" + str(currDate)

## Create a duplicate of IPAM
logWrite("Creating a copy of IPAM")
print "Creating a copy of IPAM as IPAM" + str(currDate) + " and populating it."

cur.execute(sqlCopy)
cur.execute(sqlPopulateCopy)
#cur.execute(dropCopy)

# Delete data from  IPAM, apart form persistentStatics
logWrite("Deleting IPAM")
cur.execute("delete from IPAM where persistentStatic <> 1")

# Read in routes from "CCR1Routes.terse.txt"
print "Populating database with IP information read from CCR1 routing table."
for rawSubnets in open(routingTable,'r'):
	subnet = rawSubnets[rawSubnets.find(" dst-address=")+1:].split("=")[1].split(" ")[0]
	logString = subnet + " added to networkList"
	logWrite (logString)
	networkAddress = subnet.split('/')[0]
	prefix = subnet.split('/')[1]
	#print "DEBUG: Adding ", prefix, networkAddress
	networkList.append([prefix, subnet, networkAddress])
	## IP validation
	checkSubnet = str(subnet).split('/')[0]
	print "DEBUG: Validating IP " + str(checkSubnet)
	result = validate(checkSubnet)
	if result == False:
		logWrite("Errors in CCR routing table.")
		print "Errors found in CCR1 routing table. IPAM aborted and trap sent."
		subprocess.call("/root/staticIPs/sendTrap.sh")
		quit ()
		exit

## CM Iterate through networkList and update the database. We just need to know range of addresses per subnet. 
## Its an iteration within an iteration.
networkList.sort() # Now the list is sorted by prefix. In order shortest to longest prefix.
for net in networkList:
	skip = 0
	prefix = net[0]
	subnet = net[1]
	fullSubnet = net [2]
	ipInfo = IPNetwork(subnet) ## This contains the list of usable IPs in the subnet.
        network = ipInfo.network
	broadcast = ipInfo.broadcast
	subnet = unicode(subnet)
        print "Network Info:", subnet, network, broadcast
	db.commit()
	#ip = IPNetwork(subnet)
	range = (ipaddress.ip_network(subnet).hosts())
	for ip in range:
		skip = skip + 1
		logString = "WRITING", ip, subnet
		logWrite(logString)
		print "WRITING", ip, subnet
		## We have to check here that the IP address doesn't already exist. If it does we update with the subnet info in this iteration.
                ipCheck="select IPADDR from IPAM where IPADDR = '" + str(ip) + "'"
                cur.execute(ipCheck)
                result =  cur.rowcount
                if result ==  0:
                        #print "Writing IP " + ip
                        cur.execute("insert into IPAM  (IPADDR, LEASED, SUBNET, SharedNetwork, daysNotLeased, persistentStatic) VALUES (%s, 'NotLeased', %s, 'None', '0','0')" , (ip,subnet))
			if skip < 5:
				print "DEBUG: Skip is < 5", ip, "RESERVED"
				logString = ip, " flagged as RESERVED"
				logWrite(logString)
                        	cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'RESERVED' WHERE IPADDR = %s" , ('0', ip))
				db.commit()
                        else:
				cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'Static' WHERE IPADDR = %s" , ('0', ip))
                        db.commit()
                else:
                        #stdout.write("\r%s" % ip)
                        logString =  "Found duplicate IP ", ip, subnet , "and updated subnet prefix."
			logWrite(logString)
                        print "Found duplicate IP ", ip, subnet , "and updated subnet prefix."
                        cur.execute("UPDATE IPAM SET SUBNET = %s, TYPE = 'Static' WHERE IPADDR = %s" , (subnet,ip))
			db.commit()

## =====================================================================================================## 

## Now we have populated the database with the IP address and subnet. Next script will read dhcpd.leases and update the status of each address
print ""
## These are IPs which are GIADDRs on Bridged CMTSs and can't be used for leases. 
## Knock-Bridged
logWrite("Marking GiAddr Knock-Bridged IPADDR as GIADDR")
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '185.11.65.2'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '185.11.65.3'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '185.11.65.4'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '185.11.65.5'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '185.11.66.130'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '185.11.66.131'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '185.11.66.132'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '185.11.66.133'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '31.186.32.2'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '31.186.32.4'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '31.186.32.5'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '31.186.32.7'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '31.186.37.2'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '31.186.37.3'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '31.186.37.4'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '31.186.37.5'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '88.151.26.2'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '88.151.26.3'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '88.151.26.4'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Knock-Bridged' WHERE IPADDR = %s" , ('0', '88.151.26.5'))
# Tknock4
logWrite("Marking GiAddr Tknock-Bridged IPADDR as RESERVED")
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Tknock-Bridged' WHERE IPADDR = %s" , ('0', '81.31.213.196'))
logWrite("Marking GiAddr Mish-Bridged IPADDR as RESERVED")
db.commit()
## Mish
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Mish-Bridged' WHERE IPADDR = %s" , ('0', '37.128.198.130'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Mish-Bridged' WHERE IPADDR = %s" , ('0', '81.31.213.4'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Mish-Bridged' WHERE IPADDR = %s" , ('0', '37.128.196.15'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Mish-Bridged' WHERE IPADDR = %s" , ('0', '37.128.197.194'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Mish-Bridged' WHERE IPADDR = %s" , ('0', '37.128.198.131'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Mish-Bridged' WHERE IPADDR = %s" , ('0', '37.128.197.195'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Mish-Bridged' WHERE IPADDR = %s" , ('0', '37.128.198.133'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Mish-Bridged' WHERE IPADDR = %s" , ('0', '37.128.196.4'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Mish-Bridged' WHERE IPADDR = %s" , ('0', '37.128.197.196'))
cur.execute("UPDATE IPAM SET daysNotLeased = %s, TYPE = 'GIADDR', SharedNetwork = 'Mish-Bridged' WHERE IPADDR = %s" , ('0', '81.31.213.8'))
db.commit()
db.close()
logWrite("IPs written to IPAM, prefix known, persistentStatics known, sharedNetwork not known yet.")
print "DONE."
print ""
## Now we have populated the database with the IP address and subnet, marked RESERVED and GIADDR addresses. 
## Next script will read dhcpd.leases and update the status of each address
