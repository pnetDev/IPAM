#!/usr/bin/python

## This is python version of bash script and is super fast.

# Imports
import sys
import glob
import collections

# Variables
classesNames = []
macList      = []

baseDir="/root/IPAM/"
fileName="parsedFiles/classesNames.txt"
classList=str(baseDir) + str(fileName)
## Open "classesNames.txt" which contains a list of the classes file names.
for fileName in open(classList,'r'):
	fileName = fileName.replace("\n","")
	classesNames.append(fileName)

# Open each file name in classesNames and add the MAC address to macList
for file in classesNames:
	file = str(baseDir) + "Classes/" + str(file)
	#print file
	for line in open(file,'r'):
		if "host" in line:
			mac = line.split(" ")[4]
			#print mac
			macList.append(mac)

## This code will find duplicate entries in macList
print ""
macList.sort()
duplicate = "false"
my_list = [20,30,20,30,40,50,15,11,20,40,50,15]
for i in range (len (macList) -1):
 	if macList[i] == macList[i+1]:
		duplicate = "true"
 		print "Duplicate: ",(macList[i])
if duplicate == "false":
	print "None"
else:
	print "Yes"
sys.exit(0)
