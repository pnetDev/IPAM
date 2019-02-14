#!/bin/bash
source /root/.bashrc
clear
echo ""
echo "This version does not change dhcp config and stops after generating classes files from the database."
echo "This version runs on the database on the LIVE DATABASE 10.1.1.51"
echo "#########################################"
echo "Press a key to continue"
read key
echo ""


## CM 29-01-18 This is a bash script and does the following to prepare the info to populate the database staticIPs on 10.1.1.24.
## It does the follows:
## Gets the CCR1 routing table and removes routes which doesn't need to be processed and saves as ASCII CCR1Routes.terse.txt
## Gets dhcpd.leases files from all servers and parses for IP address, CPE Mac, Lease start time, ModemMac.
## Gets dhcpd.conf from all DHCP servers and parses for SharedNetwork name, IP ranges.


## Log Changes here

## CM 181218 Code cleanup. Removed redundant 'commented-out' lines.
## CM 181214 Added functions which will check the error status of the python scripts. If there is an error this script is aborted. 
## CM 180906 Current database is backed up to IPAM/dbaseBackups/IPAM$currDate. Table IPAM_PREVIOUS is dropped. Table IPAM is copied as IPAM_PREVIOUS. Table IPAM is dropped.
## CM 180903 Files generated by this script are copied to parsedFiles. Files copied from dhcp servers are copied to dhcp. Code cleanup. Directories are absolute.
## CM 180306 Files previously copied from DHCP servers are renamed with current dates before being copied from the DHCP servers.
## CM 180302 There are private routes in dhcpd.conf which aren't routes on CCR1. These are ignored when 'dhcpdSubnets.confParsed' is created.
## CM 180223 Need to skip '88.151.27.80/28' This is a reserved subnet for AiBridges and IPAM is reading this as Coolg
## CM 180218 Calls /root/7.5.copyClassesRestartDHCP75.sh on 10.1.1.24 before script ends.
## CM 180207 Not finding 10.1.10.0 in dhcpd.confParsed
## CM 180207 Removed CCR1 route filtering because we were missing P2P management subnets.
## CM 180130 Gets the *.dyn files so the database can be updated for Dynamic ranges

basename=$0
trapserver=10.1.1.7
baseDir=/root/IPAM
parsedFiles=$baseDir/parsedFiles
dhcp=$baseDir/dhcp
classes=$baseDir/Classes
scriptDir=$baseDir/bin

## Error checking funtions
checkExecution () {
        # $ is the pythonFile name
        if [ $? -eq 0 ] ; then
          pyScript=$1
          error=false
        else
          # Redirect stdout from echo command to stderr.
          #echo "$basename $pyScript Python Script exited with error." >&2
          #echo "Ending script"
          trapString="$string Python Script exited with error. $basename aborted."
          echo Sending Trap
          trap $trapString
          echo EXIT
          exit
        fi
}

trap () {
   echo "Sending trap $trapString"
   #snmptrap -v2c -c public 10.1.1.70 0 .1.3.6.1.4.1.1141.4.182 1 s "$trapString"
}


## Get the CCR routing table
log=$baseDir/leaseAnalysis.log
currDate=$(date +%y%m%d%H%M)
echo ""
echo ""
Log=$baseDir/bin/ipam.Log
echo "=====================================================" >> $Log
echo "" >> $Log
echo $currDate Starting launcher bash script >> $Log
echo Backing up IPAM as /root/IPAM/dbaseBackups/IPAM51.$currDate
echo $currDate Getting CCR1 Routing table....
echo $currDate Getting CCR1 Routing table.... >> $Log

## Comment in SCP line below if routes change on CCR1
scp -q pnetadmin@10.1.1.63://CCR1Routes.IPAM.txt $parsedFiles/CCR1Routes.IPAM.txt
cp $parsedFiles/CCR1Routes.IPAM.txt  $parsedFiles/CCR1Routes.terse.raw.txt
grep -v "#" $parsedFiles/CCR1Routes.terse.raw.txt  | grep -v "/32" | grep -v 88.151.27.80/28 > $parsedFiles/CCR1Routes.terse.txt  ## We don't want /32 routes, we don't want 88.151.27.80/28

#echo "Temp Exit"
#exit

## Get the lease files from all DHCP servers
echo $currDate Getting lease files... >> $Log
## Rename previous files
cp $dhcp/dhcpd.leases66  $dhcp/dhcpd.leases66$currDate
cp $dhcp/dhcpd.leases68  $dhcp/dhcpd.leases68$currDate
cp $dhcp/dhcpd.leases75  $dhcp/dhcpd.leases75$currDate
cp $dhcp/dhcpd.leases233 $dhcp/dhcpd.leases233$currDate

## Get the lease files from dhcp servers.
scp root@10.1.1.66://var/lib/dhcpd/dhcpd.leases $dhcp/dhcpd.leases66 >  /dev/null
scp root@10.1.1.68://var/lib/dhcpd/dhcpd.leases $dhcp/dhcpd.leases68 >  /dev/null
scp root@10.1.1.75://var/lib/dhcpd/dhcpd.leases $dhcp/dhcpd.leases75 >  /dev/null
scp root@10.1.1.233://var/db/dhcpd.leases 	$dhcp/dhcpd.leases233 > /dev/null

## Rename the classes files from last session
echo "$currDate Backing up previously generated classes files." >> $Log
cd $classes
rename classes classes$currDate *.classes

## Get the dhcpd.conf from all DHCP servers
echo $currDate Getting dhcpd.conf files... >> $Log
## Rename previous files.
cp $dhcp/dhcpd.conf66  $dhcp/dhcpd.conf66$currDate
cp $dhcp/dhcpd.conf68  $dhcp/dhcpd.conf68$currDate
cp $dhcp/dhcpd.conf75  $dhcp/dhcpd.conf75$currDate
cp $dhcp/dhcpd.conf233 $dhcp/dhcpd.conf233$currDate

## Get dhcpd.confs from dhcp servers
scp root@10.1.1.66://etc/dhcp/dhcpd.conf $dhcp/dhcpd.conf66 > /dev/null
scp root@10.1.1.68://etc/dhcp/dhcpd.conf $dhcp/dhcpd.conf68 > /dev/null
scp root@10.1.1.75://etc/dhcp/dhcpd.conf $dhcp/dhcpd.conf75 > /dev/null
scp root@10.1.1.233://etc/dhcpd.conf $dhcp/dhcpd.conf233 > /dev/null

## Get the *.dyn files from all DHCP servers.
echo $currDate Getting *.dyn files... >> $Log
echo "Getting the .dyn files"
cd $dhcp
rename .dyn .dyn$currDate *.dyn
scp -q root@10.1.1.66://etc/dhcp/*.dyn /$dhcp/
scp -q root@10.1.1.68://etc/dhcp/*.dyn /$dhcp/  
scp -q root@10.1.1.75://etc/dhcp/*.dyn /$dhcp/
scp -q root@10.1.1.233://etc/dhcp/*.dyn /$dhcp/

## Concatenate dhcpd.conf and dhcpd.leases and parse for format phyton script will use
echo $currDate Concatenating dhcpd.conf and dhcpd.leases >> $Log
echo "Preparing the dynamic list" >> $Log
mv $parsedFiles/dynamicRanges.txt $parsedFiles/dynamicRanges.txt$currDate
echo "Parsing dhcpd.confAllServers and writing to dhcpd.confParsed." >> $Log
cat $dhcp/dhcpd.conf68 $dhcp/dhcpd.conf66 $dhcp/dhcpd.conf75 $dhcp/dhcpd.conf233 > $parsedFiles/dhcpd.confAllServers
grep .dyn $parsedFiles/dhcpd.confAllServers | grep -v "#" > $parsedFiles/dynamicRanges.txt

# CAT leases file to 1 single file
cd $parsedFiles

## Backup previous file.
cp $parsedFiles/dhcpd.leasesAllServers $parsedFiles/dhcpd.leasesAllServers$currDate

# Strange issue doing a normal 'cat' on the leases files so doing it this way, horrible way to do it I know.
more $dhcp/dhcpd.leases66 > $parsedFiles/dhcpd.leasesAllServers
$scriptDir/parseLeasesCM.csv.py > $parsedFiles/parsedLeases66
more $dhcp/dhcpd.leases68 > $parsedFiles/dhcpd.leasesAllServers
$scriptDir/parseLeasesCM.csv.py > $parsedFiles/parsedLeases68
more $dhcp/dhcpd.leases75 > $parsedFiles/dhcpd.leasesAllServers
$scriptDir/parseLeasesCM.csv.py > $parsedFiles/parsedLeases75
more $dhcp/dhcpd.leases233 > $parsedFiles/dhcpd.leasesAllServers
$scriptDir/parseLeasesCM.csv.py > $parsedFiles/parsedLeases233

# Calculate the active leases for a handy report.
leased66=$(wc $parsedFiles/parsedLeases66 | awk {'print ($1) } ')
leased68=$(wc $parsedFiles/parsedLeases68 | awk {'print ($1) } ')
leased75=$(wc  $parsedFiles/parsedLeases75 | awk {'print ($1) } ')
leased233=$(wc  $parsedFiles/parsedLeases233 | awk {'print ($1) } ')

echo ""
echo "Leases Report" >> $Log
echo "=============" >> $Log
echo ""
echo 66 = $leased66 >> $Log
echo 68 = $leased68 >> $Log
echo 75 = $leased75 >> $Log
echo 233 = $leased233 >> $Log
echo "=========================" >> $Log
total=$((leased66+leased68+leased75+leased233))

echo "Concatanating the parsed leases files as dhcpd.leasesAllServersParsed" >> $Log
cp  $parsedFiles/dhcpd.leasesAllServersParsed $parsedFiles/$dhcpd.leasesAllServersParsed$currDate
cat  $parsedFiles/parsedLeases66  $parsedFiles/parsedLeases68  $parsedFiles/parsedLeases75  $parsedFiles/parsedLeases233 >  $parsedFiles/dhcpd.leasesAllServersParsed
echo "Parsing dhcpd.confAllServers and writing to dhcpd.confParsed." >> $Log
cp $parsedFiles/dhcpd.confParsed $parsedFiles/dhcpd.confParsed$currDate
cat $parsedFiles/dhcpd.confAllServers | grep 'shared\|range\|agent.remote-id\|classes'  > $parsedFiles/dhcpd.confParsed

## Prepare file used to parse subnets and shared network.
cp $parsedFiles/dhcpdSubnets.confParsed $parsedFiles/dhcpdSubnets.confParsed$currDate
cat $parsedFiles/dhcpd.confAllServers | grep 'shared\|subnet'  | grep -v "#" | grep -v 172.31.0.0 | grep -v 192.168.254.0 | grep -v 172.31.1.0 | grep -v 84.203.223.0 > $parsedFiles/dhcpdSubnets.confParsed

## Get the *.classes files from all dhcp servers and save to $dhcp
echo Getting the classes files from all DHCP servers. >> $Log
#cat parsedLeases66 parsedLeases68 parsedLeases75 parsed24 > dhcpd.leasesAllServersParsed
#Rename syntax rename .classes .classes180213 *.classes
cd $dhcp
echo Appending $currDate to existing classes files. >> $Log
rename .classes .classes$currDate *.classes

scp -q root@10.1.1.66://etc/dhcp/*.classes  $dhcp/
scp -q root@10.1.1.68://etc/dhcp/*.classes  $dhcp/
scp -q root@10.1.1.75://etc/dhcp/*.classes  $dhcp/
scp -q root@10.1.1.233://etc/dhcp/*.classes $dhcp/

echo "Sleeping for 3"
sleep 3

echo "Total Leased: $total"
echo ""
echo "Leases Report"
echo "============="
echo ""
echo 66 = $leased66
echo 68 = $leased68
echo 75 = $leased75
echo 233 = $leased233

echo "Total Leased: $total"
echo ""

### Call Python Scripts, with error checking. 
echo $currDate Calling Python scripts  >> $Log
## Update database staticIPs with routes.
string="1.updateDatabaseWithCCR_RoutesArea51.py"
echo Updating database with CCR1 routes. 
$scriptDir/1.updateDatabaseWithCCR_RoutesArea51.py ; checkExecution $string
sleep 2

## Flag the persistentStatic IPs so these will never be recycled.
string="1.5.updatePersistentStaticArea51.py"
$scriptDir/1.5.updatePersistentStaticArea51.py ; checkExecution $string

## Update database with dhcpd.conf shared-networks
string="2.1.readDhcpdConfUpdateDatabaseArea51.py"
echo Updating database dhcpd.conf shared-networks.
$scriptDir/2.1.readDhcpdConfUpdateDatabaseArea51.py ; checkExecution $string ## CM 180831 New version, now subnets don't need to hardcoded and Pytricia isn't needed.
sleep 2

## Update database IPs which are to be set to TYPE Dynamic
string="2.5.parseDynamicArea51.py"
echo Updating database with dynamic ranges
$scriptDir/2.5.parseDynamicArea51.py ; checkExecution $string
sleep 2

## Update database with leases. Reassign any leases which are part of a reserved range. First 4 usable addresses of a subnet are reserved.
string="3.readLeaseUpdateDatabaseArea51.py"
echo Updating database with leases.
$scriptDir/3.readLeaseUpdateDatabaseArea51.py ; checkExecution $string
sleep 2

## Check for IPs leased yesterday and not today
echo "Checking for IPs leased yesterday and not today."
string="/3.5.compareTodaysLeasesToYesterdayArea51.py"
$scriptDir/3.5.compareTodaysLeasesToYesterdayArea51.py ; checkExecution $string
sleep 2

## Convert Dynamic Leases to Static.
string="3.6.convertDynamicLeasesArea51.py"
echo "Converting Dynamic Leases to Static"
#echo "SKIPPING: Converting Dynamic Leases to Static"
$scriptDir/3.6.convertDynamicLeasesArea51.py ; checkExecution $string
sleep 5

## Generating Classes files.
string="4.queryDatabaseToGenerateClassesArea51.py"
echo "Generating Classes Files."
$scriptDir/4.queryDatabaseToGenerateClassesArea51.py ; checkExecution $string
echo "The following Classes files were generated."
grep host $baseDir/Classes/*.classes | wc

echo "Checking for Duplicate leases in Classes files."
python $scriptDir/findDuplicateMacs.py
echo ""
echo ""
echo "Leases Report" >> $Log
echo "============="  >> $Log
echo "" 
echo 66 = $leased66  >> $Log
echo 68 = $leased68  >> $Log
echo 75 = $leased75  >> $Log
echo 233 = $leased233  >> $Log
echo "========================="  >> $Log
total=$((leased66+leased68+leased75+leased233))
echo "Total Leased: $total"  >> $Log
echo 

###############
## CM We exit before changing anything on DHCP servers.
echo "Exit after generating classes files."
echo "Execute 'copyClassesRestartDHCP.sh' to complete the process if no duplicates were found."
exit
###############

## Copy new classes file and restart dhcp.
#echo "$currDate Calling /root/7.5.copyClassesRestartDHCP75.sh on 10.1.1.75" >> $Log
#echo "$currDate Calling /root/7.6.copyClassesRestartDHCP66.sh on 10.1.1.66" >> $Log
ssh 10.1.1.75  /root/7.5.copyClassesRestartDHCP75.sh
ssh 10.1.1.66  /root/7.6.copyClassesRestartDHCP66.sh
ssh 10.1.1.68  /root/7.7.copyClassesRestartDHCP68.sh
ssh 10.1.1.233  /root/7.copyClassesRestartDHCP233.sh
echo "$currDate IPAM Execution Complete"   >> $Log
exit
