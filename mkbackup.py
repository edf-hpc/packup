#!/usr/bin/env python

# This file is part of HPCStats
#
# Copyright (C) 2013 EDF SA
# Contact:
#       CCN - HPC <dsp-cspit-ccn-hpc@edf.fr>
#       1, Avenue du General de Gaulle
#       92140 Clamart
#
# Authors: Bruno Agneray
#
# This program is free software; you can redistribute in and/or
# modify it under the terms of the GNU General Public License,
# version 2, as published by the Free Software Foundation.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# On Debian systems, the complete text of the GNU General
# Public License can be found in `/usr/share/common-licenses/GPL'.

#import config
import subprocess
import pp
import sys
import os
import grp
import pwd
import time
import signal
import datetime
import glob
import tempfile
import getopt

def main():
   backupFlag = True
   targetDir = ''
   try:
      opts, args = getopt.getopt(sys.argv[1:], "hr:", ["help", "restore"])
   except getopt.GetoptError:
      usage()
      sys.exit(2)
   output = None
   verbose = False
   for o, a in opts:
      if o == "-v":
         verbose = True
      elif o in ("-h", "--help"):
         usage()
         sys.exit()
      elif o in ("-r", "--restore"):
         backupFlag = False
         targetDir = a
      else:
         assert False, "Unexpected option"
   return backupFlag, targetDir

def secondsToStr(t):
    return "%d-%02d:%02d.%03d" % \
        reduce(lambda ll,b : divmod(ll[0],b) + ll[1:],
            [(t*1000,),1000,60,60])

def usage():
   print 'Ce script effectue les sauvegardes automatiques du repertoire /home ou les restaurations si l\'option est indiquee :'
   print 'mkbackup.py [ -h  | --help ] [ ( -r | --restore ) targetDir ]'
   

def backupFiles (path, listFiles, bckDir, bckOpt):
   """Backup file list with dar"""
   timeStamp=datetime.datetime.now().strftime("%Y%m%d-%H:%M")
   dirName=os.path.basename(path)
   targetDir='%s%s' % (bckDir, path)
   newBckFile='%s/%s_%s_full' % (targetDir, dirName, timeStamp)
   oldestBckFile=''
   
   # create target directory
   try:
      os.makedirs(targetDir)
   except OSError:
      pass
   
   # check for previous full backup
   bckList=glob.glob('%s/%s*_full*' % (targetDir, dirName))
   
   if len(bckList) >= 1:
      # keep most recent and remove older
      oldestBckFile=bckList[-1]
   
   # create the file list file from listFiles
   tf_name = tempfile.mktemp()
   tf_handle = open(tf_name, 'w')
   
   for file in listFiles:
     tf_handle.write("%s\n" % file)
   
   tf_handle.close()

   # create new full backup
   try:
      process = subprocess.call('dar -c %s -R %s %s -[ %s' % (newBckFile, path, bckOpt, tf_name), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
      os.unlink(tf_name)
   except:
      return 1
   
   if oldestBckFile != '': # previous backup found out
      oldestBckFileDec = oldestBckFile.replace('_full', '')
      try:
         process = subprocess.call('dar -+ %s -A %s -@ %s -ad %s' % (oldestBckFileDec.replace (".1.dar", ""), oldestBckFile.replace(".1.dar", ""), newBckFile, bckOpt), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
      except:
         return 1
      os.unlink(oldestBckFile)
   
   return 0

def restoreDir(path, dirName, bckDir, targetDir):
   """Backup directory with dar"""
   bckPath='%s%s/%s' % (bckDir, path, dirName)
   bckFile=''
   
   # check for last full backup
   bckList=glob.glob('%s/%s*_full*' % (bckPath, dirName))
   
   if len(bckList) >= 1:
      # keep most recent and remove older
      BckFile=bckList[-1]
      info = os.lstat(BckFile)
      BckFile=BckFile.replace('.1.dar', '')

   # Create directory for restoration
   try:
      os.makedirs('%s/%s' % (targetDir, dirName))
      os.chown('%s/%s' % (targetDir, dirName), info.st_uid, info.st_gid)
   except OSError:
      pass
   
   
   # restore full backup
   try:
      process  = subprocess.call('dar -x %s -w -R %s/%s' % (BckFile, targetDir, dirName),  stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
   except:
      return 1
   
   return 0



def backupDir(path, dirName, bckDir, bckOpt):
   """Backup directory with dar"""
   timeStamp=datetime.datetime.now().strftime("%Y%m%d-%H:%M")
   targetDir='%s%s/%s' % (bckDir, path, dirName)
   newBckFile='%s/%s_%s_full' % (targetDir, dirName, timeStamp)
   oldestBckFile=''
   
   info = os.lstat('%s/%s' % (path,dirName))

   # create target directory
   try:
      os.makedirs(targetDir)
   except OSError:
      pass
   
   os.chown(targetDir, info.st_uid, info.st_gid)

   # check for previous full backup
   bckList=glob.glob('%s/%s*_full*' % (targetDir, dirName))
   
   if len(bckList) >= 1:
      # keep most recent and remove older
      oldestBckFile=bckList[-1]

   # create new full backup
   try:
      process  = subprocess.call('dar -R %s/%s -c %s -D %s' % (path, dirName, newBckFile, bckOpt),  stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
      os.chown('%s.1.dar' % newBckFile, info.st_uid, info.st_gid)
   except:
      return 1
   
   if oldestBckFile != '': # previous backup found out
      oldestBckFileDec = oldestBckFile.replace('_full', '')
      try:
         process = subprocess.call('dar -+ %s -A %s -@ %s -ad %s' % (oldestBckFileDec.replace (".1.dar", ""), oldestBckFile.replace(".1.dar", ""), newBckFile, bckOpt), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
         os.chown(oldestBckFileDec, info.st_uid, info.st_gid)
      except:
         return 1
      os.unlink(oldestBckFile)
   
   return 0


if __name__ == "__main__":
   start_time = time.time()
   configFile='/usr/local/etc/mkbackup.conf'
   backupFlag, targetDir = main()
   process_list=[]
   server_list=[]
   
   try: 
      execfile(configFile)
   except IOError:
      print 'Configuration file %s not found' % config
      sys.exit(3)
   
   myhost = os.uname()[1]
   
   # Launch ppserver on all node
   for server in Servers.split(','):
      if not server.startswith(myhost): # No need to launch ppserver on localhost
         process = subprocess.Popen('ssh %s ppserver -p %s -w %d -t 60' % (server, Port, Workers), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
         process_list.append(process)
         server_list.append("%s:%d" % (server, Port))
   
   # List of all the nodes in your cluster
   
   job_server = pp.Server(ppservers=tuple(server_list)) 
   
   jobs = []
   
   for path in SrcDir.split(','):
      if os.path.exists(path):
         dirList=os.listdir(path)
         list_file=[]
         for dirName in dirList:
            # Save directories
            srcDir='%s/%s' % (path, dirName)
            if os.path.isdir(srcDir):
               if backupFlag == True:
                  jobs.append(job_server.submit(backupDir, (path, dirName, BckDir, BckOpt), (), ("commands", "datetime","glob","grp","os","pwd","subprocess","time",)))
               else:
                  jobs.append(job_server.submit(restoreDir, (path, dirName, BckDir, targetDir), (), ("commands", "datetime","glob","grp","os","pwd","subprocess","time",)))
            else:
               list_file.append(srcDir)
         if backupFlag == True:
            if list_file != []: # Backup files
               jobs.append(job_server.submit(backupFiles, (path, list_file, BckDir, BckOpt), (), ("commands","datetime","glob","grp","os","pwd","subprocess","tempfile","time",)))
            else:
               jobs.append(job_server.submit(restoreDir, (os.path.dirname(path), os.path.basename(path), BckDir, targetDir), (), ("commands","datetime","glob","grp","os","pwd","subprocess","tempfile","time",)))
      else:
         print 'Directory %s does not exist' % srcDir 
   
   # Clean ssh subprocess
   job_server.wait()
   
   # parallel python stats
   # job_server.print_stats()
   
   if backupFlag == True:
      print 'Duree d\'execution des sauvegardes : %s' % secondsToStr(time.time() - start_time)
   else:
      print 'Duree d\'execution des restorations : %s' % secondsToStr(time.time() - start_time)
   
