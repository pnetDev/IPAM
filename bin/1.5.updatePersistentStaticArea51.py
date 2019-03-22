#!/usr/bin/python
import MySQLdb
import datetime

# CM Hardcoding Notice: Nothing hardcoded.

#This script will look up all IPs in the pesistentStatic table and update found IPs in IPAM with perssistentStatic = 1, sharedNetwork is set to reserved.

#Log Changes here
#180223 Had to mark 88.151.27.80/28 as Ai-Bridges as it overlaps with a Coolg subnet. 88.151.27.80/28 IPs are flagged as reserved so will never be touched.
#180219	sharedNetwork and subnet for persistentStatics will set to reserved.

Log="/pnetadmin/IPAM/bin/ipam.Log"

def logWrite(logText):
        now =  datetime.datetime.now()
        currDate = str(now)
        #currDate = currDate.replace('-', '')
        logText = str(logText)
        file = open(Log,'a')
        file.write(currDate + " flagPersistentStatic \t")
        file.write(logText)
        file.write('\n')

db = MySQLdb.connect("10.1.1.51","ipam","ipam$2o18$","docsis" )
#db = MySQLdb.connect("localhost","root","D0xl1nk$","staticIPs" )
cur = db.cursor()



sql = "(select ipADDR from persistentStatic)"
cur.execute(sql)
for static in cur.fetchall():
	static = static[0]
	logString = str(static) + " Flagged as persistentStatic"
	logWrite(logString)
	## Check is the IP already written in IPAM
	print static, "checking"
	sql = ("select IPADDR from IPAM where IPADDR = '" + str(static) + "'")
	cur.execute(sql)
	result =  cur.rowcount
        if result ==  0:
        	print static , "flagging as persistent"
		print static, "adding to IPAM"
		cur.execute("insert into IPAM (IPADDR, persistentStatic, LEASED) VALUES (%s,%s,%s)" , (static, '1','Yes'))
		db.commit()
	else:
		print static , "exists"
		cur.execute("update IPAM set persistentStatic = '1' where IPADDR = '" + static + "'")
		db.commit()
db.close()
