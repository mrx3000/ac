import sys
from urllib.request import urlopen
import json
import time    
from calendar import timegm
from datetime import datetime
import requests
import logging
from tuya_connector import TuyaOpenAPI, TUYA_LOGGER

import acpriv

tgt_temp_cool=20
tgt_temp_heat=26

def ac_get_data():
   req_params = { "apiKey": acpriv.ss_key, "fields": "measurements,smartMode,acState,lastACStateChange" }
   ret_js = requests.get(acpriv.ss_url_v2_base, params=req_params)
   ret_arr = json.loads(ret_js.text)
   if ret_arr['status'] != "success":
      raise RuntimeError("return is not success")
   return ret_arr

# Set AC run state and mode
def ac_set_state(b_on, s_mode, s_temp, s_fan):
   req_params = { "apiKey": acpriv.ss_key }
   req_data = { "acState": { "on": b_on, "mode": s_mode, "targetTemperature": s_temp, "fanLevel": s_fan }}
   ret_js = requests.post(acpriv.ss_url_v2_base + "/acStates", params=req_params, json=req_data)
   ret_arr = json.loads(ret_js.text)
   if ret_arr['status'] != "success":
      raise RuntimeError("return is not success")

def ac_set_state_after(b_on, s_mode, s_temp, s_fan, i_delay):
   req_params = { "apiKey": acpriv.ss_key }
   req_data = { "minutesFromNow": i_delay, "acState": { "on": b_on, "mode": s_mode, "targetTemperature": s_temp, "fanLevel": s_fan }}
   ret_js = requests.put(acpriv.ss_url_v1_base + "/timer", params=req_params, json=req_data)
   ret_arr = json.loads(ret_js.text)
   if ret_arr['status'] != "success":
      raise RuntimeError("return is not success")

# Given AC run state, flip it to the opposite
def ac_patch_state(b_on):
   req_params = { "apiKey": acpriv.ss_key }
   req_data = { "currentAcState": {"on": b_on}, "newValue": not b_on, "reason": "StateCorrectionByUser"}
   ret_js = requests.patch(acpriv.ss_url_v2_base + "/acStates/on", params=req_params, json=req_data)
   ret_arr = json.loads(ret_js.text)
   if ret_arr['status'] != "success":
      raise RuntimeError("return is not success")

def ac_set_smartmode(b_on, s_mode, i_lo_temp, i_hi_temp):
   req_params = { "apiKey": acpriv.ss_key }
   if (s_mode == "cool"):
      req_data = { "enabled": b_on,
                   "lowTemperatureThreshold": i_lo_temp,
                   "lowTemperatureState": { "on": False },
                   "highTemperatureThreshold": i_hi_temp,
                   "highTemperatureState": { "on": True, "mode": "cool", "fanLevel": "auto", "targetTemperature": tgt_temp_cool }
                 }
   elif (s_mode == "heat"):
      req_data = { "enabled": b_on,
                   "lowTemperatureThreshold": i_lo_temp,
                   "lowTemperatureState": { "on": True, "mode": "heat", "fanLevel": "auto", "targetTemperature": tgt_temp_heat },
                   "highTemperatureThreshold": i_hi_temp,
                   "highTemperatureState": { "on": False }
                 }
   else:
      raise ValueError("Unsupported mode " + str(s_mode))
   ret_js = requests.post(acpriv.ss_url_v2_base + "/smartmode", params=req_params, json=req_data)
   ret_arr = json.loads(ret_js.text)
   if ret_arr['status'] != "success":
      raise RuntimeError("return is not success")


def ac_ctl_smartmode(b_on):
   req_params = { "apiKey": acpriv.ss_key }
   req_data = { "enabled": b_on }
   ret_js = requests.put(acpriv.ss_url_v2_base + "/smartmode", params=req_params, json=req_data)
   ret_arr = json.loads(ret_js.text)
   if ret_arr['status'] != "success":
      raise RuntimeError("return is not success")


def ac_get_switch_state():
   TUYA_LOGGER.setLevel(logging.ERROR)
   tapi = TuyaOpenAPI(acpriv.tuya_url, acpriv.tuya_id, acpriv.tuya_key)
   tapi.connect()

   res = tapi.get("/v1.0/iot-03/devices/{}/status".format(acpriv.tuya_device_id))
   want_codes = { 'cur_current': 'current' }
   map_res = dict(map(lambda e: ( want_codes[e['code']], e['value'] ), 
               filter(lambda v: v['code'] in want_codes.keys(), res['result'])))

   vcur = map_res['current'];
   if (vcur > 2000):
      return "on"
   elif (vcur > 300):
      return "fan"
   else:
      return "off"

