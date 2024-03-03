#!/usr/bin/env python3

import sys
from urllib.request import urlopen
import json
import time    
from calendar import timegm
from datetime import datetime
import requests

import acmod

tgt_temp_heat=26
tgt_temp_cool=20

now = datetime.now()
now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

#
# Resync loop
# Both iteratons must result in b_sync == True to update state
#
b_sync = False
b_force = False

b_auto_mode = ""
b_mode = ""

for loop in range(2):
   if (loop > 0):
      # sleep 10 seconds and retest, must require sync both times
      time.sleep(10)
      
   print(">>>>>>> " + now_str + " [" + str(loop) + "]")
   try:
      ss_data = acmod.ac_get_data()
   except RuntimeError as e:
      print("Getting data failed: " + str(e))
      sys.exit(-1)

   if (not ss_data['result']['smartMode']['enabled']):
      print("Not in auto mode")
      break

   if ('lastStateChange' not in ss_data['result']):
      print("Last state change too old - no change key")
      break

   b_on = ss_data['result']['acState']['on']
   cur_temp = ss_data['result']['measurements']['temperature']
   last_evt_sec = ss_data['result']['lastStateChange']['secondsAgo']
   #last_evt_reason = ss_data['result']['lastACStateChange']['reason'].lower()

   print("On: " + str(b_on))
   print("Temp Now: " + str(cur_temp))

   b_auto_mode = ""
   b_sync = False
   b_force = False

   b_mode = ss_data['result']['acState']['mode']

   if ss_data['result']['smartMode']['lowTemperatureState']['on']:
      print("Smart mode is: Heat")
      b_auto_mode = "heat"
      on_temp = ss_data['result']['smartMode']['lowTemperatureThreshold']
      off_temp = ss_data['result']['smartMode']['highTemperatureThreshold']
   elif ss_data['result']['smartMode']['highTemperatureState']['on']:
      print("Smart mode is: Cool")
      b_auto_mode = "cool"
      on_temp = ss_data['result']['smartMode']['highTemperatureThreshold']
      off_temp = ss_data['result']['smartMode']['lowTemperatureThreshold']
   else:
      print("Smart mode is: Undefined")
      break

   print("Temp On: " + str(on_temp))
   print("Temp Off: " + str(off_temp))

   print("Last event " + str(last_evt_sec) + " sec ago")
   if last_evt_sec < 300:
      print("Last state chg too recent")
      break
   elif last_evt_sec > 7000:
      print("Last state chg too old")
      break
   #elif last_evt_reason != "trigger":
   #   print("Last event not in auto mode")
   #   break

   if b_auto_mode == "heat":
      mode_temp = tgt_temp_heat
      if not b_on:
         temp_diff = cur_temp - off_temp
         if temp_diff > 0.4:
            b_sync = True
      else:
         if last_evt_sec > 1500 and cur_temp < off_temp:
            b_sync = True
   elif b_auto_mode == "cool":
      mode_temp = tgt_temp_cool
      if not b_on:
         # Current temperature well below off (low) limit
         # Assume runaway cooling mode
         if (off_temp - cur_temp) > 0.3:
            b_sync = True
   
         # AC off, above on (upper) limit
         # Assume failed smart mode start
         if (cur_temp - on_temp > 0.1):
            b_force = True
      else:
         # linearly adjust thold from on_temp + 0.5 immediately (delayed by 500 sec)
         # to off temp itself at 1hr
         # If current temperature is above thold, assume "underrun" (not actually cooling)
         temp_thold = off_temp + (on_temp + 0.5 - off_temp) * ((3600 - last_evt_sec) / 3300)
         print("Temp thold: " + str(temp_thold))
         if last_evt_sec > 500 and cur_temp >= temp_thold:
            b_sync = True

         # AC on, below off (lower) limit
         # Assume failed smart mode stop
         if (off_temp - cur_temp) > 0.2:
            b_force = True

   if not (b_sync or b_force):
      print("Run state OK")
      break

if b_sync:
   print("Need to sync, current on: " + str(b_on) + ", auto mode: " + str(b_auto_mode))

   # patch current state to the opposite
   try:
      acmod.ac_patch_state(b_on)
   except RuntimeError as e:
      print("Patch failed: " + str(e))
      sys.exit(-1)

   # actually apply current state
   try:
      acmod.ac_set_state(b_on, b_auto_mode, mode_temp, "auto")
   except RuntimeError as e:
      print("Command on/off failed: " + str(e))
      sys.exit(-1)

   print ("Flipped state and applied state: " + str(b_on))
   sys.exit(2)

if b_force:
   print("Need to force, current on: " + str(b_on) + ", auto mode: " + str(b_auto_mode))

   # apply opposite state
   b_on = not b_on;

   try:
      acmod.ac_set_state(b_on, b_auto_mode, mode_temp, "auto")
   except RuntimeError as e:
      print("Command on/off failed: " + str(e))
      sys.exit(-1)

   print ("Force applied state: " + str(b_on))
   sys.exit(2)

# In cooling mode run fan periodically
# Attempting to proactively switch to the fan from autorun cool
# results in autorun shortly canceling the fan (and then fan restarting
# on the "soon after cooling" condition
if b_auto_mode == "cool":
   #if (b_on and b_mode == "cool" and cur_temp <= off_temp) or ((not b_on) and last_evt_reason == "trigger" and last_evt_sec <= 120):
   #if ((not b_on) and last_evt_reason == "trigger" and last_evt_sec <= 120):
   # XXX XXX need to figure out how to run once!!!
   if ((not b_on) and last_evt_sec <= 120):
      print("Fan is off - will turn on")
      try:
         acmod.ac_set_state(True, "fan", tgt_temp_cool, "low")
         acmod.ac_set_state_after(False, "fan", tgt_temp_cool, "low", 1)
      except RuntimeError as e:
         print("Fan on failed: " + str(e))
         sys.exit(-1)
