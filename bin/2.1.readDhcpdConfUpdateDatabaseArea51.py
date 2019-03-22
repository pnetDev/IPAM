#!/usr/bin/python

'''
CM 29-01-18 This script is one function and does the following:
Parses the file dhcpdSubnets.confParsed for the following
        o Subnet and Mask
        o SharedNeworkName
Writes this info to the list networkList. The list is then sorted by prefix.
networkList contains prefix, subnet, fullSubnet, sharedNetwork  (prefix is /25 /26 etc. subnet is 88.151.30.128 etc. fullSubnet is 88.151.30.128/25 etc. sharedNetwork is MishBridged etc)
networkList is then iterated and the database is updated with the sharedNetwork name for the IP. Because the list is sorted by prefix the subnets are processed in the order of shortest to longest prefix. This means nothing can be overwritten and sharedNetwork name is correct for each IP address.

##### CHANGE LOG #######
# 180831 New version. Read subnets to a list 'networkList' and then sort by prefix. Broadcast and Network address written for each subnet.
'''

import ipaddress
import MySQLdb
import math
import re
import subprocess
import datetime
import netaddr
#import pytricia
from netaddr import *

## Variables
#db = MySQLdb.connect("localhost","root","D0xl1nk$","staticIPs" )
Log="/pnetadmin/IPAM/bin/ipam.Log"
db = MySQLdb.connect("10.1.1.51","ipam","ipam$2o18$","docsis" )
cur = db.cursor()
networkList = []
sharedNetwork="notRead"
skip=0
baseDir="/pnetadmin/IPAM/"
fileName="parsedFiles/dhcpdSubnets.confParsed"
dhcpdConfs=str(baseDir) + str(fileName)

## CM The idea of this script is to read dhcpdSubnets.confParsed and generate another list with the longest prefix first.
## This will solve the problem of a /28 being read before a /23. When this happens the SharedNetwork name for a subnet is wrong.

# The format of dhcpdSubnets.confParsed is like this.
# This is an example of a /28 and a /23 from which the /28 was 'carved'

'''
shared-network K13-Bundle3 {
        subnet 37.128.195.192 netmask 255.255.255.240 {
        subnet 81.31.215.0 netmask 255.255.255.0 {
        subnet 88.151.27.96 netmask 255.255.255.224 {
shared-network Forth-Casa {
        subnet 37.128.194.0 netmask 255.255.254.0 {
        subnet 88.151.24.64 netmask 255.255.255.224 {
'''
# If this was parsed as read in the order in dhcpdSubnets.confParsed the /28 SharedNetwork name will be overwritten by the /23 SharedNetwork name.

## Functions
def logWrite(logText):
        now =  datetime.datetime.now()
        currDate = str(now)
        #currDate = currDate.replace('-', '')
        logText = str(logText)
        file = open(Log,'a')
        file.write(currDate + " parseDhcpd.conf \t")
        file.write(logText)
        file.write('\n')

def validate(IP):
        pieces = IP.split('.')
        if len(pieces) != 4: return False
        try: return all(0<=int(p)<256 for p in pieces)
        except ValueError: return False
        #usage
        #result = validate(subnet)

## Open dhcpdSubnets.confParsed and write prefix, subnet, fullSubnet, sharedNetwork to networkList.append, the list is then sorted by prefix.
for subnetShared in open(dhcpdConfs,'r'):
        process = "Yes"
        if not subnetShared.strip():
                process = "No"
        #print "DEBUG subnetShared " + subnetShared
        if subnetShared.split()[0] == "shared-network":
            	sharedNetwork = subnetShared.split()[1]
                print ""
                print "DEBUG: Found network " + sharedNetwork
                logString = ("SharedNetwork " + str(sharedNetwork))
                #logWrite(logString)
        if subnetShared.split()[0] == "subnet":
        	subnet = subnetShared.split()[1]
                mask = subnetShared.split()[3]
                #print subnet, mask
                ## Convert the mask to a prefix
                prefix = IPAddress(mask).netmask_bits()
                fullSubnet = str(subnet) + "/" + str(prefix)
                print "Network is " + fullSubnet
		networkList.append([prefix, subnet, fullSubnet, sharedNetwork])
			

networkList.sort()  ## Now the list is sorted by prefix. /23 processed before /28

## Iterate through list networkList, the list has been sorted so iteration is from shortest prefix to longest prefix.
for line in  networkList:
	skip = 0 ## This is our counter so we can reserve the first X addresses of a network. 
	prefix = line[0]
	subnet = line[1]
	fullSubnet = line[2]
	sharedNetwork = line[3]
	print prefix, subnet, fullSubnet, sharedNetwork
	ip = IPNetwork(fullSubnet)
        network = ip.network
        broadcast = ip.broadcast
        print "Network Info:", fullSubnet, network, broadcast
	## Write the network ID and broadbcast address to database
	cur.execute("UPDATE IPAM SET LEASE_DATE ='NoLease' , TYPE='NetAddress', sharedNetwork = %s WHERE IPADDR = %s" , (sharedNetwork,network))
        cur.execute("UPDATE IPAM SET LEASE_DATE ='NoLease' , TYPE='Broadcast', sharedNetwork = %s WHERE IPADDR = %s" , (sharedNetwork,broadcast))
	db.commit()
	## Iterate the range of the subnet
	fullSubnet = unicode(fullSubnet)
	range = (ipaddress.ip_network(fullSubnet).hosts())
	for IP in range:
		skip = skip + 1
		IP = str(IP)
		IP, " checking is this a GiAddr"
                sql = "select TYPE from IPAM where IPADDR = '" + str(IP) + "'"
		cur.execute(sql)
		for type in cur.fetchall():
			TYPE = type[0]
		if TYPE == 'GIADDR':
			print IP, " is a GiAddr"
			logString = IP, " is a GiAddr"
			logWrite(logString)
			continue
		logString =  IP, sharedNetwork, fullSubnet, "writing to dbase"
		logWrite(logString)
		print IP, sharedNetwork, fullSubnet, "writing to dbase"
		if skip < 4:
                	cur.execute("UPDATE IPAM SET LEASE_DATE ='NoLease' , SharedNetwork = %s , TYPE='Reserved' WHERE IPADDR = %s" , (sharedNetwork, IP))
                        continue
                else:
                        cur.execute("UPDATE IPAM SET LEASE_DATE ='NoLease' , SharedNetwork = %s , TYPE='Static' WHERE IPADDR = %s" , (sharedNetwork, IP))
                        db.commit()

## CM 180831 There is no need to parse the classes info. We already know what is static from above code. This is legacy code which I'm leaving in place to remind me. 

quit ()
'''
print ""
print "Parsing classes."
logWrite("Parsing classes.")

for binding in open("dhcpd.confParsed",'r'):
                process = "Yes"
                if not binding.strip():
                        process = "No"
                print "Debug " + binding.split()[1]
                if binding.split()[0] == "shared-network" and process == "Yes":
                        #print binding.split()
                        sharedNetwork = binding.split()[1]
                        #print "" + "\t" + str(sharedNetwork)

                if binding.split()[0] == "include" and process == "Yes":
                        logString =  str(binding)
                        logWrite(logString)
                        print "debug CLASSES " + str(binding) + "Network " + str(sharedNetwork)
                        line = binding.split()[1]
                        path = line.split('/')
                        #print "path " + str(path)
                        fileName = path[3]
                        print "debug FILENAME " + str(fileName)
                        #print "fileName " + str(fileName)
                        #print "Found classes file for " + sharedNetwork
                        #print "The fileName is " + str(fileName)
                        ## Remove " and ; from fileName
                        fileName = fileName.replace(";", "")   ## Remove ';' from fileName
                        fileName = fileName.replace('"', '')   ## Remove '"' from fileName
                        #print "The actual fileName is " + str(fileName)
                        #print "Debug: This is the CLASSES section"
                        #print "Found " + str(fileName) + " file for " + sharedNetwork
                        openFileName = "/root/staticIPs/dhcp/" + str(fileName)
                        for host in open(openFileName,'r'):
                    		process = "Yes"
                                if not host.strip():
                                        process = "No"
                                if process == "Yes":
                                        #print host.split()
                                        if host.split()[0] == "pool":
                                                IP = host.split()[2]
                                                IP = IP.replace(";", "")
                                                ## Validate IP
                                                ipCheck = validate(IP)
                                                if ipCheck == True:
                                                        print "DEBUG The CLASSES IP is " + IP + " for " + sharedNetwork + " in " + openFileName
                                                        cur.execute("UPDATE IPAM SET LEASE_DATE ='NoLease' , SharedNetwork = %s , TYPE='Static' WHERE IPADDR = %s" , (sharedNetwork, IP))
                                                        db.commit()
                                                else:
                                                        print "ERROR " + IP + " CLASSES IS NOT A VALID IP ADDRESS. I will now quit. " + sharedNetwork + "," + openFileName
                                                        #subprocess.call(['bash','/root/staticIPs/trap.sh','IPAM IP PARESE ERROR',IP,"dhcpd.confAll"])
                                                        isubprocess.call(['bash','/root/staticIPs/ipamLog.sh',IP,currDate,"Parse Error","dhcpd.confAll",])
                                                        print ""

                        classes = True
                else:
                        classes = False

db.close()
'''
logWrite("Done.")




