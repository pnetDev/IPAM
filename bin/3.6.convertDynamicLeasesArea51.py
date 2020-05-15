#!/usr/bin/python

# CM Hardcoding Notice: No hardcoding used. Fixed this by using a list.


"""
 CM 29-01-2018 This is one function and does the following.
 Finds dynamic leases in IPAM
 Finds next free static lease for above shared network
 Resets dynamic lease
 Creates static lease
 Sends trap if there is no free static lease available.
 Log Changes here
181101 Added a counter to report the number of dynamic conversions.
180801 As discussed with Ray. If a CPE has a dynamic lease any exisiting static entry must be deleted/reset. 
180226 Same as below for '81.31.215.192/26' needs to be marked 'Slieveboy-BSR7'
180226 Have to mark 37.128.195.192/28 as K13-Bundle3. I need to rewrite '2.readDhcpdConfUpdateDatabaseArea51.py' as its not correctly identifying shared networks.
       I will need to fix this as I don't like the system being less automated. It goes against design principles. But have to do it for now to keep making progress.
180223 Had to mark 88.151.27.80/28 as Ai-Bridges as it overlaps with a Coolg subnet. Doing it here because this is the last script to write to DB
180221 Need to was to see what the dynIP was for a conversion so it's easier to debug.
180222 Code cleanup.
180219 IPs flagged as persistentStatic will never be recycled. sql = "select IPADDR from IPAM where TYPE='Static' and LEASED='NotLeased' and SharedNetwork='" + sharedNetwork + "' and persistentStatic <> '1' order by IPADDR desc limit 1" 
"""
import MySQLdb
import math
import re
import subprocess
import datetime

now = datetime.date.today()
currDate = str(now)
currDate = currDate.replace('-', '')
currDate = str(currDate)
Log="/pnetadmin/IPAM/bin/ipam.Log"
#db = MySQLdb.connect("localhost","root","D0xl1nk$","staticIPs" )
db = MySQLdb.connect("10.1.1.51","ipam","ipam$2o18$","docsis" )

cur = db.cursor()
process = "Yes"

def logWrite(logText):
        now =  datetime.datetime.now()
        currDate = str(now)
        logText = str(logText)
        file = open(Log,'a')
        file.write(currDate + " convDynamic \t")
        file.write(logText)
        file.write('\n')

leaseCount = 0
dynamicConversionCounter = 0
print "Working........"
print "Finding dynamic leases"
sql = "select IPADDR,MAC,ModemMac,SharedNetwork,TYPE,LEASE_DATE from IPAM where TYPE='Dynamic' and LEASED='Yes';"

cur.execute(sql)
for lease in cur.fetchall():
        IP = lease[0]
        MAC = lease[1]
        Modem = lease[2]
        sharedNetwork = lease[3]

## We need to check if this MAC address already has a static lease, if so we reset the static lease.
## Search IPAM to see if there is a static entry and a lease for this MAC. Example for 98:FC:11:55:FD:59
## select * from IPAM where MAC = '98:FC:11:55:FD:59' and TYPE = "Static" and LEASED ="Yes";
## If no results take no action.
## If there is a result, mark the static lease as NotLeased and reset lease data, the old static lease won't be written when the classes files are written.
## UPDATE IPAM SET LEASED ='NotLeased' , MAC = "NULL", ModemMac = "NULL", daysNotLeased = "0", LEASE_DATE = "NULL" WHERE MAC = '98:FC:11:55:FD:59' and TYPE = "Static";

	#print "Code needed here to check does " + MAC + " have a static lease and if so reset it"
	sql = "select MAC, IPADDR from IPAM where MAC='" + MAC + "'  and TYPE = 'Static' and LEASED ='Yes';"
	result = cur.execute(sql)
	if result == 1:
		for duplicateLease in cur.fetchall():
                	MAC = duplicateLease[0]
                	IP =  duplicateLease[1]
		print MAC, IP + " DUPLICATE MAC BUG FIX: convertDynamicLeases	Dynamic and Static found resetting static lease"
		logString = MAC, IP + " DUPLICATE MAC BUG FIX: convertDynamicLeases	Dynamic and Static found resetting static lease"
        	logWrite(logString)
		cur.execute("UPDATE IPAM SET LEASED ='NotLeased' , LEASE_DATE=%s , MAC='NULL', ModemMac='Null',  LEASE_DATE = 'NULL'  WHERE MAC = %s and IPADDR = %s" , ("NULL",MAC,IP))		
		db.commit()

# ROL added in the following to allow multiplr .dyn files in sharedNetwork e.g. Knock-BridgedX_31_186_32_0_27.dyn
# note the "X" must follow the SharedNetName and the only "." must precede the dyn.
#
        if sharedNetwork.find('X') > 0:
            sharedNetwork = sharedNetwork[:sharedNetwork.find('X')]
	    print "New X shared network name ", sharedNetwork
        LEASE_DATE = lease[5]
	print IP, MAC, Modem, LEASE_DATE, sharedNetwork + " Dynamic"
	logString =  IP, MAC, Modem, LEASE_DATE, sharedNetwork + " Dynamic"
	logWrite(logString)
	## Process the first found IP
	print IP, sharedNetwork  + " DYN IP CONVERSION: finding next free IP."
	logString = IP, sharedNetwork  + " DYN IP CONVERSION: finding next free IP."
	logWrite(logString)
#
# ROL added in the followng so that there may be a preferred Subnet to use within a shared Network to allocat static IP from
#
	sql1 = "select prefSubnet from preferredSubnet where SharedNetwork='" + sharedNetwork + "' "
        cur.execute(sql1)
        ispreference =  cur.rowcount
        if ispreference == 0:
	    sql = "select IPADDR from IPAM where TYPE='Static' and LEASED='NotLeased' and SharedNetwork='" + sharedNetwork + "' and persistentStatic <> '1' and TYPE <> 'Reserved' order by IPADDR desc limit 1"
	    cur.execute(sql)
            result =  cur.rowcount
        else:
            for preference in cur.fetchall():
                prefSubnet = preference[0]
	    sql = "select IPADDR from IPAM where SUBNET='" + prefSubnet + "' and TYPE='Static' and LEASED='NotLeased' and SharedNetwork='" + sharedNetwork + "' and persistentStatic <> '1' and TYPE <> 'Reserved' order by IPADDR desc limit 1"
            cur.execute(sql)
            result =  cur.rowcount
#
# ROL if we cannot get an IPADDR in preferred subnet then use any subnet
#
            if result == 0:
                sql = "select IPADDR from IPAM where TYPE='Static' and LEASED='NotLeased' and SharedNetwork='" + sharedNetwork + "' and persistentStatic <> '1' and TYPE <> 'Reserved' order by IPADDR desc limit 1"
                cur.execute(sql)
                result =  cur.rowcount

        print "Row result is " + str(result)
        if result == 0:
                print "Error no free Static ip in " + sharedNetwork
		logString = "Error no free Static ip in " + sharedNetwork
		logWrite(logString)
                #subprocess.call(['bash','/root/staticIPs/trapNoStatic.sh',sharedNetwork])
                #quit ()
        for free in cur.fetchall():
                freeIP = free[0]
		print freeIP + " DYN IP CONVERSION: Is the next free IP for " + str(sharedNetwork)
		logString =  freeIP + " DYN IP CONVERSION: Is the next free IP for " + str(sharedNetwork)
		logWrite(logString)
		print IP + " Reset"
		logString = IP + " DYN IP CONVERSION: Reset"
		logWrite(logString)
		cur.execute("UPDATE IPAM SET LEASED ='NotLeased' , SharedNetwork = %s , LEASE_DATE='NULL', TYPE='Dynamic' , MAC='NULL', ModemMac='Null' WHERE IPADDR = %s" , (sharedNetwork, IP))
		db.commit()
		print "Replacing " + IP + " with " + freeIP,MAC,sharedNetwork
		logString = " DYN IP CONVERSION: Replacing " + IP + " with " + freeIP,MAC,sharedNetwork
		logWrite(logString)
		cur.execute("UPDATE IPAM SET LEASED ='leasePending' , SharedNetwork = %s , LEASE_DATE='leasePending', TYPE='Static' , MAC = %s, ModemMac=%s, wasDyn = %s WHERE IPADDR = %s" , (sharedNetwork, MAC, Modem, IP, freeIP))
		dynamicConversionCounter = dynamicConversionCounter + 1
		db.commit()
print "Done."
print dynamicConversionCounter, "Dynamic IPs converted."
logString=str(dynamicConversionCounter) + " Dynamic IPs converted."
logWrite(logString)
logWrite("Done.")
#logWrite("Marking 88.151.27.80/28 as Ai-Bridges")
## CM I don't like doing this but have too because 88.151.27.80/28 is for AI Bridges and DHCP knows nothing about the subnet, and a Coolg subnet overlaps.
## This fixes the problem. We just overwite the whole subnet and mark the addreses as static. They will never be used.
#logWrite("Correctly identifying the following SharedNetworks, bug in '2.readDhcpdConfUpdateDatabaseArea51.Pytricia.py' needs to be fixed.")
#logWrite("Applying Pytricia LPM bug fix for 88.151.27.80/28, 37.128.195.192/28, 81.31.215.192/26, 37.128.196.128/27, 37.128.196.176/28, 37.128.196.192/27, 88.151.28.224/27")
#logWrite("Applying Pytricia LPM bug fix for 88.151.29.0/26, 88.151.29.64/27, 88.151.29.112/28, 88.151.29.128/25, 88.151.29.96/28, 88.151.25.160/27")
#logWrite("Applying Pytricia work around for M10k-Bun3_H_temp")

## CM 180831 No need to hardcode anymore as I rewrote the way dhcpd.conf is parsed using a list and sorting the list by prefix. Also non dhcp subnets are now delcared in dhcpd.conf.
#Leaving the code here to jog my memory.
'''
cur.execute("update IPAM set SharedNetwork = 'AIBridgesSE' , TYPE = 'Reserved' where SUBNET  = '37.128.195.248/29'")
cur.execute("update IPAM set SharedNetwork = 'RhodePropertiesGlue' , TYPE = 'Reserved' where SUBNET  = '37.128.195.244/30'")
cur.execute("update IPAM set SharedNetwork = 'Ai-Bridges' , TYPE = 'Reserved' where SUBNET  = '88.151.27.80/28'")
cur.execute("update IPAM set SharedNetwork = 'K13-Bundle3' where SUBNET  = '37.128.195.192/28'")
cur.execute("update IPAM set SharedNetwork = 'Slieveboy-BSR7' where SUBNET  = '81.31.215.192/26'")
## CM 180302 These need to be manually set also until I fix LPM for reading dhcpd.conf
cur.execute("update IPAM set SharedNetwork = 'M10k-Bun4_EV' where SUBNET  = '37.128.196.128/27'")
cur.execute("update IPAM set SharedNetwork = 'Clara4-uBR' where SUBNET  = '37.128.196.176/28'")
cur.execute("update IPAM set SharedNetwork = 'Clara4-uBR' where SUBNET  = '37.128.196.192/27'")
cur.execute("update IPAM set SharedNetwork = 'Clara4-uBR' where SUBNET  = '88.151.28.224/27'")
cur.execute("update IPAM set SharedNetwork = 'White-Casa5' where SUBNET  = '88.151.29.0/26'")
cur.execute("update IPAM set SharedNetwork = 'Tknock1-Bundle1' where SUBNET  = '88.151.29.64/27'")
cur.execute("update IPAM set SharedNetwork = 'MtGab-uBR' where SUBNET  = '88.151.29.112/28'")
cur.execute("update IPAM set SharedNetwork = 'White-Casa4' where SUBNET  = '88.151.29.128/25'")
cur.execute("update IPAM set SharedNetwork = 'M10k-Bun4_EV' where SUBNET  = '88.151.29.96/28'")
cur.execute("update IPAM set SharedNetwork = 'Forth-Bridged' where SUBNET  = '88.151.25.160/27'")
## Temp for for M10k-Bun3_H_temp dynamic range
cur.execute("update IPAM set SharedNetwork = 'M10k-Bun3_H' where SUBNET  = '88.151.26.192/27'")
'''
db.commit()
db.close()		
