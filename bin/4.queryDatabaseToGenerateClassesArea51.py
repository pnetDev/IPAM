#!/bin/python

# CM Hardcoding Notice: Nothing hardcoded.

"""
CM 01-02-2018 This code does the following:
Runs this database query and generates the classes file.
"select IPADDR, MAC, SUBNET, SharedNetwork from IPAM where LEASED='Yes' and TYPE = 'Static'"
The naming convention of the file is:

<sharedNetwork><subnet><_mask>.classes


Log Changes Here:

CM 180207 Changed convention to <sharedNetwork><subnet>.classes
CM 180205 Added a counter to count number of IPs processed.

"""



import MySQLdb
import math
import re
import os
import glob
import datetime
Log="/root/IPAM/bin/ipam.Log"

def logWrite(logText):
        now =  datetime.datetime.now()
        currDate = str(now)
        #currDate = currDate.replace('-', '')
        logText = str(logText)
        file = open(Log,'a')
        file.write(currDate + " generateClasses \t")
        file.write(logText)
        file.write('\n')

print ""
print "Working...."
logWrite("Generating classes files")
## Remove /root/staticIPs/Classes/*
files = glob.glob('/root/staticIPs/debug/Classes/*')
# Doing this by shell script instead
#for f in files:
#    os.remove(f)

#db = MySQLdb.connect("localhost","root","D0xl1nk$","staticIPs" )
db = MySQLdb.connect("10.1.1.51","ipam","ipam$2o18$","docsis" )

cur = db.cursor()
baseDir="/root/IPAM/"
fileDir="Classes/"


row_count = cur.execute("select IPADDR, MAC, SUBNET, SharedNetwork from IPAM where MAC <> 'NULL' and TYPE <> 'Dynamic' and LEASED = 'Yes' or LEASED = 'leaseReserved' or LEASE_DATE  = 'leasePending' and TYPE = 'Static'")
#print row_count
noOfIp=0
for row in cur.fetchall():
	noOfIp = noOfIp + 1
	IP = row[0]
        MAC = row[1]
        subnet = row[2]
	sharedNetwork = row[3]
	newSubnet = subnet.replace('/','_')
	#print IP + "\t" + MAC + "\t" + subnet
	#print ('host ' + IP + ' {hardware ethernet ' + MAC + ';}')
        #print ('class "' + MAC + '" {match if hardware = 01:' + MAC + '; } ## IP:' + IP)
        #print ('pool {range ' + IP + ' ;deny unknown clients; allow members of "' + MAC + '";}\n\n\n')
	#fileName = "Classes/" + str(newSubnet) + "." + str(sharedNetwork) + ".classes"
	fileName = str(baseDir) + "Classes/" + str(sharedNetwork) + "." + str(newSubnet) + ".classes"
	file = open(fileName,'a')
        file.write('host ' + IP + ' {hardware ethernet ' + MAC + ';}\n')
        file.write('class "' + MAC + '" {match if hardware = 01:' + MAC + '; } ## IP:' + IP + '\n')
        file.write('pool {range ' + IP + ' ;deny unknown clients; allow members of "' + MAC + '";}\n\n\n')
        file.close()	
print str(noOfIp) + " IP addresses were processed."
print ""
print "Bash  verify: 'grep host /root/staticIPs/Classes/*.classes | wc'"
print "MySql verify: 'select count(IPADDR) from IPAM where LEASED='Yes';"
print ""
logString = str(noOfIp) + " host IPs were written."
logWrite(logString)
print "Done."
logWrite("Done.")
print ""
