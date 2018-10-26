#!/usr/bin/python

## The script checks for duplicate MACs in macList and prints any found.
## It uses glob to generate classesNames which is a list.
## classesNames is then iterated, each classes file is read and the MAC addresses are added to macList.
## The script checks macList for duplicates and prints any found.

# Imports
from sys import stdout
import sys
import glob
import collections

# Variables
classesNames = []
macList      = []

## CM New code doing this without a need for a shell script to generate a text file.
classesNames = (glob.glob("/root/IPAM/Classes/*.classes")) ## This creates a list containing the classes file names.

# Open each file name in classesNames and add the MAC address to macList
for file in classesNames:
	for line in open(file,'r'):
		if "host" in line:
			mac = line.split(" ")[4]
			#print mac,
			macList.append(mac)

## This code will find duplicate entries in macList
print ""
macList.sort()
duplicate = "false"
for i in range (len (macList) -1):
 	if macList[i] == macList[i+1]:
		duplicate = "true"
 		print "Duplicate: ",(macList[i])
if duplicate == "false":
	print "None"
else:
	print "Duplicate=Yes."
sys.exit(0) 
