"""
setup necessary variables to run icehms
"""



import os
import sys
import re
import exceptions
import Ice


#Find The installation root and setup some paths 
intree = False
if os.environ.has_key("ICEHMS_ROOT"):
    root = os.environ["ICEHMS_ROOT"]
else:
    #See if we are started form sourcetree
    root = os.path.realpath(os.path.dirname(__file__))
    root = os.path.normpath(os.path.join(root, "../../../"))
    if os.path.isdir(os.path.join(root, "icefg")) and os.path.isdir(os.path.join(root, "slices")):
        print "Looks like we are in source tree"
        intree = True
    else:
        tmp = os.path.join(sys.prefix, "share", "icehms")
        if os.path.isdir(tmp): # look like icehms has been installed ealier, try that
            root = tmp
        else:
            print "Error: IceHMS libraries not found, set ICEHMS_ROOT environment variable"
            sys.exit(1)

print "icehms root is ", root

sysSlicesPath = os.path.join(root, "slices") # system slice files
icecfgpath = os.path.join(root, "icecfg", "icegrid.cfg" ) #configuration ice
iceboxpath = os.path.join(root, "icecfg", "icebox.xml" ) #configuration icestorm

#setup ice database path

if os.environ.has_key("ICEHMS_DB"):
    db_dir = os.environ["ICEHMS_DB"]
else:
    if intree:
        nodeData = os.path.join(root, "db", "node") # node registry
        registryData = os.path.join(root, "db", "registry") #registry database path
    else:
        if os.name == "nt":
            appdata = os.environ["APPDATA"]
            db_dir = os.path.join(appdata, "icehms", "db")
        else:
            db_dir = os.path.join(os.path.expanduser("~"), ".icehms", "db") # This is not a config so do not use .config
nodeData = os.path.join(db_dir, "node")
registryData = os.path.join(db_dir, "registry")

#setup ice registry address 
if os.environ.has_key("ICEHMS_REGISTRY"):
    IceRegistryServer = os.environ["ICEHMS_REGISTRY"]
else:
    print "ICEHMS_REGISTRY environment variable not set, using localhost:12000"
    IceRegistryServer = 'tcp -p 12000 ' #we let Ice chose the network interface



#dynamic compiling Ice slice files
slicedirs = []

slicedirs.append(sysSlicesPath) #append system path

#do we have user slices
icehms_user = ""
if os.environ.has_key("ICEHMS_USER"):
    icehms_user = os.environ["ICEHMS_USER"]
elif  os.environ.has_key("HOME") and os.path.isdir(os.path.join(os.environ["HOME"], ".icehms")):
    icehms_user = os.path.join(os.environ["HOME"], ".icehms")
if icehms_user:
    userslices = os.path.join(icehms_user, "slices")
    if os.path.isdir(userslices):
        for d in os.walk(userslices):
            slicedirs.append(os.path.join(icehms_user, d[0]))

#now find application slices
if os.environ.has_key("ICEHMS_SLICES"):
    icehms_slices = os.environ["ICEHMS_SLICES"]
    icehms_slices = icehms_slices.split(";")
    for path in icehms_slices:
        if os.path.isdir(path):
            slicedirs.append(path)

# Read slice files in current diretory, usefull for small projects
slicedirs.append(".")

#print "Loading slice files from ", slicedirs

for path in slicedirs:
    for icefile in os.listdir(path):
        if re.match("[^#\.].*\.ice$", icefile):
            #print 'icehms.__init__.py: trying to load slice definition:', icefile
            icefilepath = os.path.normpath(os.path.join(path, icefile))
            try:
                Ice.loadSlice("", ["--all", "-I" + path, "-I" + sysSlicesPath, icefilepath])
            except exceptions.RuntimeError, e:
                print 'icehms.__init__.py: !!! Runtime Error !!!, on loading slice file:', icefile
        else:
            #print 'icehms.__init__.py: not loading non-slice file:', icefile
            pass


#commodity imports

import hms # only to be able to write "from icehms import hms"

from holon import * # from icehms import holon, Message
from agentmanager import * # from icehms import agentmanager
from icemanager import * # from icehms import icemanager

