#!/usr/bin/python
import MySQLdb
import datetime


#This script will look up all IPs in the radreply.radius table and update found IPs in IPAM with TYPE and LEASED = PPPoE USER.

#Log Changes here

Log="/pnetadmin/IPAM/bin/ipam.Log"

def logWrite(logText):
        now =  datetime.datetime.now()
        currDate = str(now)
        #currDate = currDate.replace('-', '')
        logText = str(logText)
        file = open(Log,'a')
        file.write(currDate + " flagPPPoEUser \t")
        file.write(logText)
        file.write('\n')

db = MySQLdb.connect("localhost","radius","D0xl1nk$","radius" )
dbIPAM = MySQLdb.connect("10.1.1.51","ipam","ipam$2o18$","docsis" )
cur = db.cursor()
curIPAM = dbIPAM.cursor()


sql = "(select value from radreply)"
cur.execute(sql)
for static in cur.fetchall():
	static = static[0]
	logString = str(static) + " Flagged as PPPoE-USER"
	logWrite(logString)
	## Check is the IP already written in IPAM
	print static, "checking"
	sql = ("select IPADDR from IPAM where IPADDR = '" + str(static) + "'")
	curIPAM.execute(sql)
	result =  cur.rowcount
        if result ==  0:
        	print static , "flagging as PPPoE-USER"
		print static, "adding to IPAM"
		curIPAM.execute("insert into IPAM (IPADDR, TYPE, LEASED) VALUES (%s,%s,%s)" , (static, 'PPPoE-USER"','PPPoE-USER"'))
		dbIPAM.commit()
	else:
		print static , "exists"
		curIPAM.execute("update IPAM set TYPE = 'PPPoE-USER' where IPADDR = '" + static + "'")
		dbIPAM.commit()
dbIPAM.close()
db.close()
