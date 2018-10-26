#!/bin/bash
source /root/.bashrc
clear
currDate=$(date +%y%m%d%H%M)
Log=/root/IPAM/bin/ipam.Log
## Copy new classes file and restart dhcp.
echo "$currDate Calling /root/7.5.copyClassesRestartDHCP75.sh on 10.1.1.75" >> $Log
echo "$currDate Calling /root/7.6.copyClassesRestartDHCP66.sh on 10.1.1.66" >> $Log
echo "$currDate Calling /root/7.7.copyClassesRestartDHCP68.sh on 10.1.1.68" >> $Log
echo "$currDate Calling /root/7.copyClassesRestartDHCP233.sh on 10.1.1.233" >> $Log
ssh -q 10.1.1.75  /root/7.5.copyClassesRestartDHCP75.sh
ssh -q 10.1.1.66  /root/7.6.copyClassesRestartDHCP66.sh
ssh -q 10.1.1.68  /root/7.7.copyClassesRestartDHCP68.sh
ssh -q 10.1.1.233  /root/7.copyClassesRestartDHCP233.sh
echo "$currDate IPAM Execution Complete."   >> $Log
exit
