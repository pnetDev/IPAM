#!/usr/bin/python

# CM Hardcoding Notice: Nothing hardcoded.

"""
CM 29-01-2018 This is one function and does the following.
 Reads line by line dhcpd.leasesAllServersParsed
 Updates IPAM as follows for each IP address leased.
	o IPADDR=Leased IP
	o LeaseDate=Start of lease time
	o MAC=CPE MAC
	o ModemMac=Agent ID


## Log Changes Here
## 180219 IPs flagged as persistentStatic will never be recycled.  sql = ("SELECT IPADDR from IPAM where LEASED = 'NotLeased' and TYPE = 'Static' and SharedNetwork = '" + Network + "' and persistentStatic <> '1' order by IPADDR desc limit 1;")
## 180212 Started adding logging routines.
## 180209 Bug below fixed, uses Pytricia now to do longest prefix match.
## 180209 Now I have a bug, since omitting the first few IPs from a subnet. The leases written to the database don't match the leases read. To fix this need to read routing table into
pytricia and then find a new IP to assign to CPE once we know what the sharedNetwork is.
## 180208 For the Cisco MTAs with garbage agent IDs I am working out the Modem Mac from the router MAC.
## 180207 Converts MAC addresses to correct format, with leading zeros, in uppercase. 
## 180131 Checks that MAC and IP addresses are valid formats.
## CM This version will also write the agent.remoteID

"""

import pytricia
import MySQLdb
import math
import re
import subprocess
import datetime
import netaddr
from netaddr import EUI
pyt = pytricia
Log="/pnetadmin/IPAM/bin/ipam.Log"
now = datetime.date.today()
currDate = str(now)
currDate = currDate.replace('-', '')
print "Date is " + str(currDate)
currDate = str(currDate)
baseDir="/pnetadmin/IPAM/"
fileName="parsedFiles/dhcpd.leasesAllServersParsed"
leases=str(baseDir) + str(fileName)
routingTable=str(baseDir) + "parsedFiles/CCR1Routes.terse.txt"

def validate(IP):
        pieces = IP.split('.')
        if len(pieces) != 4: return False
        try: return all(0<=int(p)<256 for p in pieces)
        except ValueError: return False

def validate_mac(MAC):
        if re.match("[0-9a-f]{2}([-:])[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", MAC.lower()):
                #print "True"
		return True
        else:
                return False
		macCheck = False

def convertMac(MAC):
	MAC = MAC.replace('\n','')
	return ':'.join('{:0>2}'.format(i) for i in MAC.split(':'))

def incrementMAC(MAC,increment):
	mac_int = int(MAC.translate(None, ":.- "), 16)
	mac_int = mac_int - int(increment)
	mac_hex = "{:012x}".format(mac_int)
	MAC = mac_str = ":".join(mac_hex[i:i+2] for i in range(0, len(mac_hex), 2))
	return MAC
	
def logWrite(logText):
	now =  datetime.datetime.now()
	currDate = str(now)
	currDate = currDate.replace('-', '')
	logText = str(logText)
	file = open(Log,'a')
	file.write(currDate + " readLease \t")
	file.write(logText)
	file.write('\n')

## Read CCR routing table into pytricia.
import ipaddress
pyt = pytricia.PyTricia()

# Read in routes from "CCR1Routes.terse.txt" and add to pytricia trie
#print "Reading CCR1Routes.terse.txt"
print "Adding subnets to Pytricia"
logWrite("Adding subnets to Pytricia.")
for rawSubnets in open(routingTable,'r'):
        subnet = rawSubnets[rawSubnets.find(" dst-address=")+1:].split("=")[1].split(" ")[0]
        print "DEBUG: Adding " + subnet
        ## Extact the info from the route read from file above.
        # Write route to pytricia trie
        pyt[subnet] = subnet
        #print pyt.keys()
        ## IP validation
        checkSubnet = str(subnet).split('/')[0]
        print "DEBUG: Validating IP " + str(checkSubnet)


##===========================================================================================================##
#db = MySQLdb.connect("localhost","root","D0xl1nk$","staticIPs" )
db = MySQLdb.connect("10.1.1.51","ipam","ipam$2o18$","docsis" )
cur = db.cursor()
process = "Yes"


### CM Changed how this is done again.
leaseCount = 0
updateCount = 0
print "Working........"
logWrite("Reading leases.")
for binding in open(leases,'r'):
	leaseCount = leaseCount + 1
	## This file won't have blank lines so we don't need to check for blank lines.
	## We need to figure out is the line being read the leased IP or the MAC address.
	processBinding = binding.split(",")
	#print processBinding
	IP  = processBinding[0]
	leaseDate =  processBinding[2]
	MAC = processBinding[1]
	agentID = processBinding[3]
	## Data validation
        ipCheck = validate(IP)
        if ipCheck == True:
		ipCheck = True
		updateCount = updateCount + 1
        else:
		print IP + " IS NOT A VALID IP ADDRESS. I will now quit." 
		logWrite(IP + " is not a valid IP address.\n")
		subprocess.call(['bash','/root/staticIPs/trap.sh','IPAM IP PARSE ERROR',IP,"dhcpd.leasesAllServersParsed"])
		subprocess.call(['bash','/root/staticIPs/ipamLog.sh',IP,currDate,"Parse Error","dhcpd.leasesAllServersParsed",])
		print ""
		quit()
	macCheck = validate_mac(MAC)
	if macCheck == True:
		#print MAC + " validated."
		macCheck = True
	else:
		logWrite(MAC + " readLeases: not a valid MAC address.\n")
		print MAC + ",IS NOT A VALID MAC ADDRESS. I will now quit."
		subprocess.call(['bash','/root/staticIPs/trap.sh','IPAM MAC PARSE ERROR',MAC,"dhcpd.leasesAllServersParsed"])
		subprocess.call(['bash','/root/staticIPs/ipamLog.sh',MAC,currDate,"Parse Error","dhcpd.leasesAllServersParsed",])
		print ""
		quit()
	agentID = convertMac(agentID)
	macCheck = validate_mac(agentID)
	if macCheck == True:
		macCheck = True
	else:
		## Cisco MTAs don't have a valid agent ID. The string will be garbage, we need to convert these.	
                logString = "Cisco Option 82 Workaround " + agentID + " Modem MAC will be changed to CPE MAC " + str(MAC)
		logWrite(logString)
                print "DEBUG " + agentID + " Needs to be changed to CPE MAC"
                agentID = str(MAC)
	# Proper MAC format, uppercase with leading zeros.
	agentID = EUI(agentID)
	agentID = str(agentID).replace('-',':')
	MAC = EUI(MAC)
	MAC = str(MAC).replace('-',':')
	# Now we are ready to write the lease information to IPAM table.
	cur.execute("UPDATE IPAM SET LEASE_DATE = %s , LEASED = 'Yes' , MAC = %s , ModemMac = %s WHERE IPADDR = %s" , (leaseDate,MAC, agentID, IP))
	db.commit()
	## Check has the database been updated. We query the database to see was the entry added or not. If not find next free IP for the sharedNetwork.
	sql = "Select IPADDR from IPAM where IPADDR = '" + IP + "' and LEASED = 'Yes'"
	cur.execute(sql)
	result =  cur.rowcount
	if result ==  0:
		print ""
		logString = str(IP), str(MAC), str(agentID) + " Error not found. Most likely it's a reserved IP"
		logWrite(logString)
		print str(IP) + "," + str(MAC) + "," + str(agentID) + ",Error not found."
		# Longest prefix match to find out what subnet and sharedNetwork we are processing. 
		longestPrefixMatch = pyt[IP]
		# Figure out what sharedNetwork IP belongs to so we can prepare a new lease.
		print "PREFIX: Finding sharedNetwork for " + str(longestPrefixMatch) + "\t" + str(IP)
		sql = ("SELECT DISTINCT SharedNetwork from IPAM where SUBNET = '" + longestPrefixMatch + "'and SharedNetwork <> 'None'")
		print "PREFIX: " + sql
		cur.execute(sql)
		for sharedNetwork in cur.fetchall():
			Network = sharedNetwork[0]
		print "PREFIX: The shared network is " + str(Network)
		logString = "RESERVED IP CONVERSION: Finding sharedNetwork for " + str(longestPrefixMatch) + "\t" + str(IP) + str(Network)
                logWrite(logString)
		print "PREFIX: Finding free IP from " + str(Network)
		# Find the next free static IP address for sharedNetwork.
		sql = ("SELECT IPADDR from IPAM where LEASED = 'NotLeased' and TYPE = 'Static' and SharedNetwork = '" + Network + "' and persistentStatic <> '1' order by IPADDR desc limit 1;")
		print "PREFIX: " + sql
		cur.execute(sql)
		for free in cur.fetchall():
			freeIP = free[0]
			logString = str(freeIP) + " RESERVED IP CONVERSION: is a free static IP for " + str(Network)
			logWrite(logString)
			print freeIP + " PREFIX: is a free static IP for " + Network
			print "Updating database."
                	print "PREFIX: reset IP " + IP
			# Reset lease info for IP.
                	cur.execute("UPDATE IPAM SET LEASED =%s , LEASE_DATE='NULL', TYPE='Dynamic' , MAC='NULL', ModemMac='Null' WHERE IPADDR = %s" , ("NotLeased", IP))
                	db.commit()
			# freeIP is an IP address we can use for sharedNetwork. Update the database and set the lease time as leasePending.
			logString = "RESERVED IP CONVERSION: Writing new static lease " + freeIP, MAC ,agentID, Network
			logWrite(logString)
                	print "PREFIX: Writing new static lease " + freeIP + "\t" + agentID + "\t" + "\t" + Network
                	cur.execute("UPDATE IPAM SET LEASE_DATE = %s , LEASED = 'Yes' , MAC = %s , ModemMac = %s WHERE IPADDR = %s" , ("leasePending",MAC, agentID, freeIP))
			db.commit()
			#updateCount = updateCount - 1
print ""
print "Done."
print "Leases read    is " + str(leaseCount)
print "Leases written is:" + str(updateCount)
