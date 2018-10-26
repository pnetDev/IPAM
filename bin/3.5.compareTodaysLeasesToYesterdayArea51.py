#!/usr/bin/python

# CM Hardcoding Notice: Nothing hardcoded.

"""

 CM 30-01-2018 this script is one function and does the following.
	o Checks if the leases found in IPAM<currDate> are in IPAM and takes the following action.
		o If the lease is in IPAM<currDate> and IPAM no action taken.
		o If the lease is in IPAM<currDate> and not in IPAM the following action is taken
			> daysNotLeased in incremented by 1 in IPAM
	o Seaches IPAM for daysNotLeased > 7 and does the following if any are found matching to condition
		o IP info is reset 
			> LEASED="NotLeased"
			> LEASE_DATE="NotLeased"
			> daysNotLeased=0
			> MAC='NULL'
			> ModemMac='NULL'


 Log Changes here
180829 CM New logic needed. If the CPE MAC has a lease on 2 networks. Remove the older lease. We were having problems of duplicate MACs in classes files when a modem is moved
#      to another sector. To overcome this, I use this logic.
#      Check was it leased yesterday. Note the shared network.
#      Is there another active lease for the MAC. If yes do not preserve the other lease.
#      If there is no other active lease for MAC. Preserve the lease.
180306 CM Also need to write the CPE MAC and flag as reserved lease, otherwise won't be written to classes file.
"""

import MySQLdb
import math
import re
import datetime
Log="/root/IPAM/bin/ipam.Log"

def logWrite(logText):
        now =  datetime.datetime.now()
        currDate = str(now)
        #currDate = currDate.replace('-', '')
        logText = str(logText)
        file = open(Log,'a')
        file.write(currDate + " compareYesterday \t")
        file.write(logText)
        file.write('\n')

print 
print "Working...."

#db = MySQLdb.connect("localhost","root","D0xl1nk$","staticIPs" )
db = MySQLdb.connect("10.1.1.51","ipam","ipam$2o18$","docsis" )
cur = db.cursor()

# Now we have to figure out if the leases in PAMbackup are in IPAM and alter database based on these conditions.
# Thanks to Ray we can do this with one query
# select IPAM.IPADDR,IPAM.LEASED AS TODAY ,IPAM20180126.LEASED AS YESTERDAY from IPAM join IPAM20180126 on IPAM.IPADDR = IPAM20180126.IPADDR where IPAM.LEASED <> IPAM20180126.LEASED;



now = datetime.date.today()
currDate = str(now)
currDate = currDate.replace('-', '')
print "Date is " + str(currDate)

## Build our sql query
IP = "Null"

#sql = "select IPAM.IPADDR,IPAM.LEASED,IPAM.daysNotLeased AS TODAY ,IPAM" + str(currDate) + ".LEASED AS YESTERDAY from IPAM join IPAM" + str(currDate) + " on IPAM.IPADDR = IPAM" + str(currDate) + ".IPADDR where IPAM.LEASED <> IPAM" + str(currDate) + ".LEASED"

sql = "select IPAM.IPADDR,IPAM.LEASED AS LeasedTODAY ,IPAM" + str(currDate) +".LEASED AS YESTERDAY,IPAM" + str(currDate) +".MAC,IPAM" + str(currDate) +".TYPE as TypeYesterday from IPAM join IPAM" + str(currDate) +" on IPAM.IPADDR = IPAM" + str(currDate) +".IPADDR where IPAM.LEASED <> IPAM" + str(currDate) +".LEASED and IPAM.LEASED <> 'leasePending' and IPAM" + str(currDate) +".LEASED = 'Yes' and  IPAM" + str(currDate) +".TYPE = 'Static'"

sqlDaysLeased = "select IPADDR, daysNotLeased from IPAM where IPADDR = '" + str(IP) + "'"
resetIP =  "UPDATE IPAM SET LEASED = 'NotLeased', daysNotLeased = '0', LEASE_DATE = 'notLeased'  WHERE IPADDR = '" + str(IP) + "'"
incrementDays = "UPDATE IPAM SET daysNotLeased = daysNotLeased + 1 where IPADDR = '" + str(IP) + "'"
expiredLease = "SELECT IPADDR from IPAM where daysNotLeased > 7"
daysNotLeasedQuery = "SELECT daysNotLeased from IPAM where IPADDR='" +  str(IP) + "'"

#print sql
#print sqlToday
#
print "Checking for IPs leased yesterday and not today."
foundLease = 0
preserve = "Yes"
row_count = cur.execute(sql)
for row in  cur.fetchall():
	print row[0], row[1] ,row[2], row[3]
	IPADDR = row[0]
	leasedToday = row[1]
	MAC = row[3]
	print MAC,IPADDR, leasedToday
	#print IP, MAC, 
	if leasedToday == "NotLeased":
		print MAC, IPADDR, " Checking for other leases for this mac."
		logString = MAC, IP, " Checking for other leases for this mac."
		logWrite(logString)
		sql = "select SharedNetwork from IPAM where MAC = '" + str(MAC) + "'"
		results = cur.execute(sql)
		print MAC, results, " Leases found."
		logString = MAC, results, " Leases found."
		logWrite(logString)
		if results > 1:
			logString =  MAC, IPADDR, "Another active lease found will not preserve this lease."
			logWrite(logString)
			print MAC, IPADDR, "Another active lease found will not preserve this lease."
			preserve = "No"
		if preserve <> "No":
			foundLease = foundLease + 1
			print MAC, IP + " incrementing daysNotLeased by 1 and setting LEASED as leaseReserved."
			logString  = MAC + IP + " incrementing daysNotLeased by 1 and setting LEASED as leaseReserved"
			logWrite(logString)
			cur.execute("UPDATE IPAM SET daysNotLeased = daysNotLeased + 1 , LEASED = %s , MAC = %s WHERE IPADDR = %s" , ("leaseReserved", MAC, IP))
			db.commit()	
	
## Report on leases found if any
if foundLease > 0:
	print "Found " + str(foundLease) + " leases and daysNotLeased has been incremented."
	logString =  "Found " + str(foundLease) + " leases and daysNotLeased has been incremented."
	logWrite(logString)
	print ""
else:
	print "All IPs leased yesterday have been leased today."
	logWrite("All IPs leased yesterday have been leased today.")

## Now we reset IPs with daysNotLeased > 7


#print "Starting reset for loop"
row_count = cur.execute(expiredLease)
for row in  cur.fetchall():
	IP = row[0]
	print IP + " Resetting to not leased state in IPAM."
	logString = str(IP) + " Resetting to not leased state in IPAM."
	logWrite(logString)
	cur.execute("UPDATE IPAM SET LEASED = %s ,LEASE_DATE =%s, daysNotLeased = %s, MAC = 'NULL', ModemMac = 'NULL' WHERE IPADDR = %s" , ("NotLeased","notLeased","0", IP))
	db.commit()

print "Report of IPs with daysNotLeased > 1"
print "------------------------------------"
sql = "SELECT IPADDR, daysNotLeased from IPAM where daysNotLeased > 1"
cur.execute(sql)
for row in  cur.fetchall():
	IP = row[0]
	daysNotLeased = row[1]
	print IP + "\t" + str(daysNotLeased)
	logString =  IP + "\t" + str(daysNotLeased)
	logWrite(logString)

db.close()
print "Done."
logWrite("Done.")
print ""
