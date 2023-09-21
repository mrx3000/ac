#!/usr/bin/env python3

import sys
from urllib.request import urlopen
import json
import time    
from calendar import timegm
from datetime import datetime
import requests
import pickle

import acmod

BN = { True: "on", False: "off" }

TS_FILE_PATH = "/tmp/acts.dat"

now = datetime.now()
now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

b_sync = False
b_force = False

s_auto_mode = ""
b_mode = ""
b_sw_mode = ""

print(">>>>>>> [" + now_str + "]")
try:
   ss_data = acmod.ac_get_data()
except RuntimeError as e:
   print("! Getting data failed: " + str(e))
   sys.exit(-1)

if (not ss_data['result']['smartMode']['enabled']):
   print("- Not in auto mode")
   sys.exit(0)

if ('lastACStateChange' not in ss_data['result']):
   print("- Last state change too old - no change key")
   sys.exit(0)

# Sensibo reported values
b_on = ss_data['result']['acState']['on']
temp_cur = ss_data['result']['measurements']['temperature']
last_evt_sec = ss_data['result']['lastACStateChange']['time']['secondsAgo']
last_evt_reason = ss_data['result']['lastACStateChange']['reason'].lower()
b_mode = ss_data['result']['acState']['mode']

print("Run state: {}, temp: {}".format(BN[b_on], temp_cur))

s_auto_mode = ""
b_vsync = False      # verify with Tuya, possibly sync
b_sync = False       # Tuya confirmed, sync
b_force = False      # Non-verified, force on/off

temp_low = ss_data['result']['smartMode']['lowTemperatureThreshold']
temp_hi = ss_data['result']['smartMode']['highTemperatureThreshold']
if ss_data['result']['smartMode']['lowTemperatureState']['on']:
   s_auto_mode = "heat"
   temp_tgt = ss_data['result']['smartMode']['lowTemperatureState']['targetTemperature']
elif ss_data['result']['smartMode']['highTemperatureState']['on']:
   s_auto_mode = "cool"
   temp_tgt = ss_data['result']['smartMode']['highTemperatureState']['targetTemperature']
else:
   print("! Smart mode is undefined")
   sys.exit(-1)

print("Mode: {}, range: {} - {}, last evt: {} sec ago".format(s_auto_mode, temp_low, temp_hi, last_evt_sec))

# synchronization scope
for _x in range(1):
   if last_evt_sec < 300:
      print("- Last state chg too recent")
      break
   elif last_evt_sec > 36000:
      print("- Last state chg too old")
      break

   # if temp in range (or slightly out) - run state OK
   if (temp_cur - temp_hi < 0.1 and temp_low - temp_cur < 0.1):
      print("Run state OK")
      break

   # Desired run state
   # Offsets and range checked above, so here we
   # can simply compare with hi/lo threshold
   b_want_on = False
   if s_auto_mode == "heat":
      if temp_cur < temp_low:
         b_want_on = True
   elif s_auto_mode == "cool":
      if temp_cur > temp_hi:
         b_want_on = True

   # verify with the switch
   # spacing, ensure delay of 5-6 min between switch queries
   # Since the above conditions are quite common (i.e. room temp below
   # minimum for cooling mode at night), we will be relying more on
   # quering actual ac state. Save (limited) Tuya queries by introducing
   # mandatory delay
   try:
      tsf = open(TS_FILE_PATH, "rb")
      dts = pickle.load(tsf)
      tsf.close()
      tuya_last = dts['last_ts']
   except:
      print("- No Tuya ts file - assume too soon")
      tuya_last = now

      # write out initial file
      dts = { 'last_ts': now }
      tsf = open(TS_FILE_PATH, "wb")
      pickle.dump(dts, tsf)
      tsf.close()
      break

   tdelta = now - tuya_last
   if tdelta.seconds < 300:
      print("- Last Tuya access too recent, not proceeding")
      break

   try:
      dts = { 'last_ts': now }
      tsf = open(TS_FILE_PATH, "wb")
      pickle.dump(dts, tsf)
      tsf.close()
   except:
      print("! Unable to store last Tuya ts, aborting")
      sys.exit(-1)

   # actually access Tuya
   try:
      sw_state = acmod.ac_get_switch_state()
   except:
      print("! Tuya query failed")
      sys.exit(-1)
         
   b_sync = False
   b_force = False

   # Switch reported state out of sync with Sensibo
   if (b_on and sw_state != "on") or (not b_on and sw_state != "off"):
      print("+ Sync, run state reported: {}, sw reported: {}, auto mode: {}, sync to state {}".format(BN[b_on], sw_state, s_auto_mode, BN[not b_on]))

      # Patch current run state to the opposite
      try:
         acmod.ac_patch_state(b_on)
      except RuntimeError as e:
         print("! Patch failed: " + str(e))
         sys.exit(-1)
      b_on = not b_on

      b_sync = True

   # If desired run state is not the same as current (possibly just patched)
   # force the desired run state
   if (b_want_on != b_on):
      print("+ Force, run state: {}, run state wanted: {}, auto mode: {}, force to state {}".format(BN[b_on], BN[b_want_on], s_auto_mode, BN[b_want_on]))
      try:
         acmod.ac_set_state(b_want_on, s_auto_mode, temp_tgt, "auto")
      except RuntimeError as e:
         print("! Command on/off failed: " + str(e))
         sys.exit(-1)

      b_force = True

   if (b_sync or b_force):
      sys.exit(2)
   else:
      print("Run state verified OK")

# In cooling mode run fan periodically
# Attempting to proactively switch to the fan from autorun cool
# results in autorun shortly canceling the fan (and then fan restarting
# on the "soon after cooling" condition
if s_auto_mode == "cool":
   fan_min = 1
   #if (b_on and b_mode == "cool" and cur_temp <= off_temp) or ((not b_on) and last_evt_reason == "trigger" and last_evt_sec <= 120):
   if ((not b_on) and last_evt_reason == "trigger" and last_evt_sec <= 120):
      print("+ Fan on for {} min".format(fan_min))
      try:
         acmod.ac_set_state(True, "fan", temp_tgt, "low")
         acmod.ac_set_state_after(False, "fan", temp_tgt, "low", fan_min)
      except RuntimeError as e:
         print("! Fan on failed: " + str(e))
         sys.exit(-1)
