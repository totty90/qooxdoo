#!/usr/bin/env python
# -*- coding: utf-8 -*-

################################################################################
#
#  qooxdoo - the new era of web development
#
#  http://qooxdoo.org
#
#  Copyright:
#    2007-2009 1&1 Internet AG, Germany, http://www.1und1.de
#
#  License:
#    LGPL: http://www.gnu.org/licenses/lgpl.html
#    EPL: http://www.eclipse.org/org/documents/epl-v10.php
#    See the LICENSE file in the project's top-level directory for details.
#
#  Authors:
#    * Daniel Wagner (d_wagner)
#
################################################################################

import os
import re

##
# Reads a log file generated by an automated test run (simulation) of a qooxdoo
# application. The log file's contents can be extracted, grouped, filtered and
# returned as a Python data structure using the getSimulationData() method. 
#
# @param logFile {str} File system location of the log file to be processed
# @param ignore {list} List of strings that will be evaluated as regular 
# expressions. Any line matching one of these will not be logged.
class SimulationLogParser:
  def __init__(self, logFile, ignoreStrings=None):
    if not logFile:
      raise Exception("No log file specified!")
    
    if not(os.path.exists(logFile)):
      raise Exception("Specified log file does not exist!")
    
    self.log = open(logFile, "r")
    
    self.ignore = []
    if ignoreStrings:
      for string in ignoreStrings:
        try:
          reg = re.compile(string)
          self.ignore.append(reg)
        except Exception:
          pass
    
    self.simulationsList = None


  ##
  # Returns the log file's data as a list of simulation results.
  #  
  # @return {list} The simulation result list
  def getSimulationData(self):
    if not self.simulationsList:
      simulationDict = self.getSimulationDict(self.log)
      self.simulationsList = self.parseLogDict(simulationDict)
    return self.simulationsList

  
  ##
  # Reads "qxSimulator" log entries from a file object and groups them by 
  # simulation.
  #
  # @param log {file} The simulation log
  # @return {dict} Dictionary where the keys are simulation IDs and the values
  # are simulation log entries  
  def getSimulationDict(self, log):
    logs = {}
    logre = re.compile('.*browserSideLog - qxSimulator_(\d*): (.*)')
    logre2 = re.compile('qxSimulator_(\d+):[ "\+\']+(.*)')
  
    # group log entries by date
    for line in log:
      found = logre.match(line)
      if not found:
        found = logre2.match(line)
      
      if found:
        if found.group(1) in logs.keys():
          if not (found.group(2) + "\n") in logs[found.group(1)]:
            logs[found.group(1)].append(found.group(2) + "\n")
        else:
          logs[found.group(1)] = [found.group(2) + "\n"]
    log.close
    
    return logs


  ##
  # Iterates over a simulation log dictionary as returned by getSimulationDict()
  # and extracts relevant information. Returns a list of dictionaries, each
  # containing the results of of one simulation.
  #
  # @param logs {dict} Simulation log dictionary
  # @return {list} List of simulation result dictionaries
  def parseLogDict(self, logs):
    simulationsList = []
    
    agentre = re.compile('(?s).*<p>User agent: (.*?)</p>')
    platre = re.compile('(?s).*<p>Platform: (.*?)</p>')
    datere = re.compile('from (.*)</h1>')
    errorre = re.compile('with warnings or errors: (\d*?)</p>')
    durationre = re.compile('<p>Test run finished in: (.*)</p>')
    
    for k in sorted(logs.iterkeys()):    
      simulationDict = {
        "browser" : "Unknown",
        "user_agent" : "Unknown",
        "platform" : "Unknown",
        "selenium_version" : "Unknown",
        "failed" : True,
        "start_date" : "1970-01-01_00-00-00",
        "end_date" : "1970-01-01_00-00-00",
        "net_duration" : "unknown",
        "logentries" : []
      }
      
      entry = "".join(logs[k])
  
      agent = agentre.search(entry)
      if (agent):
        simulationDict["browser"] = self.getBrowser(agent.group(1))
        simulationDict["user_agent"] = agent.group(1)
        
      platma = platre.search(entry)
      if (platma):
        simulationDict["platform"] = platma.group(1)
  
      duration = durationre.search(entry)
      if (duration):
        simulationDict["net_duration"] = duration.group(1)
      
      errors = errorre.search(entry)
      if errors:
        simulationDict["failed"] = False
        
      logentryData = self.getLogentryList(logs[k])    
      simulationDict["logentries"] = logentryData
      
      dateMatch = datere.search(entry)
      if dateMatch:
        rawDate = dateMatch.group(1)
        stringDate = rawDate.replace(" ", "_")
        stringDate = stringDate.replace(":", "-")
        simulationDict["start_date"] = stringDate
              
      simulationsList.append(simulationDict)
    
    return simulationsList


  ##
  # Processes a list of simulation log entries and returns relevant messages 
  # as a list of dictionaries.
  #
  # @param logEntries {list} A list containing one or more log file entries
  # @return {list} A list of log entry dictionaries  
  def getLogentryList(self, logEntries):
    logentryList = []  
    for entry in logEntries:
      ignore = False
      if len(self.ignore) > 0:
        for reg in self.ignore:
          found = reg.search(entry)
          if found:
            ignore = True
            continue
      if ignore:
        continue
      
      if 'level-' in entry or "testResult" in entry:
        entryDict = {
          "level" : "info",
          "message" : entry
        }
        if "level-error" in entry or "testResult failure" in entry or "testResult error" in entry:
          entryDict["level"] = "error"
        elif "level-warn" in entry:
          entryDict["level"] = "warn"
        elif "level-info" in entry:
          entryDict["level"] = "info"
        elif "level-debug" in entry:
          entryDict["level"] = "debug"
        
        logentryList.append(entryDict)
    return logentryList


  ##
  # Tries to determine the name and version of a browser from the user agent
  # string. Supports Firefox, Opera, IE, Chrome and Safari.
  #
  # @param agent {str} A user agent string
  # @return{str} Browser name and version number, i.e. "Firefox 3.5.2"
  def getBrowser(self, agent):
    browser = False
    regFF = re.compile('.*(Firefox|Namoroka)\/([\d\.]*)')
    match = regFF.match(agent)
    if (match):
      browser = match.group(1) + " " + match.group(2)
  
    if (not(browser)):
      regOp = re.compile('.*(Opera)\/([\d\.]*)')
      match = regOp.match(agent)
      if (match):
        regOpTen = re.compile('.*(Opera).*Version\/([\d\.]+)$')
        matchTen = regOpTen.match(agent)
        if matchTen:
          browser = matchTen.group(1) + " " + matchTen.group(2)
        else:
          browser = match.group(1) + " " + match.group(2)
  
    if (not(browser)):
      regIe8Comp = re.compile('.*MSIE 7\.0.*(Trident)')
      match = regIe8Comp.match(agent)
      if (match):
        browser = "Internet Explorer 8 in IE7 compatibility mode"
  
      regIe8Std = re.compile('.*MSIE 8\.0.*(Trident)/')
      match1 = regIe8Std.match(agent)
      if (match1):
        browser = "Internet Explorer 8 in standards mode"
  
      if (not(browser)):
        regIe = re.compile('.*MSIE ([\d\.]*)')
        match2 = regIe.match(agent)
        if (match2):
          browser = "Internet Explorer " + match2.group(1) 
  
    if (not(browser)):
      regCh = re.compile('.*(Chrome)\/([\d\.]*)')
      match = regCh.match(agent)
      if (match):
        browser = match.group(1) + " " + match.group(2)
  
    if (not(browser)):
      regSa = re.compile('.*Version\/([\d\.]+).*(Safari)')
      match = regSa.match(agent)
      if (match):
        browser = match.group(2) + " " + match.group(1)
        
    if (not(browser)):
      browser = agent
  
    return browser
