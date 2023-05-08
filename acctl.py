import sys
import os
import json
from urllib.parse import parse_qs
import hashlib

sys.path.append(os.path.dirname(__file__))
import acmod

auth_file=os.path.dirname(__file__) + "/auth.txt";
response_content_type="application/json;charset=utf-8";

# Return simple dictionary of current AC state values
def getvals():
   ss_data = acmod.ac_get_data()

   res = {}
   res['auto_on'] = ss_data['result']['smartMode']['enabled']
   res['run'] = ss_data['result']['acState']['on']
   res['run_mode'] = ss_data['result']['acState']['mode']
   res['auto_enabled'] = ss_data['result']['smartMode']['enabled']
   res['temp'] = ss_data['result']['measurements']['temperature']
   if ss_data['result']['smartMode']['lowTemperatureState']['on']:
      res['auto_mode'] = "heat"
      res['lo_temp'] = ss_data['result']['smartMode']['lowTemperatureThreshold']
      res['hi_temp'] = ss_data['result']['smartMode']['highTemperatureThreshold']
   elif ss_data['result']['smartMode']['highTemperatureState']['on']:
      res['auto_mode'] = "cool"
      res['lo_temp'] = ss_data['result']['smartMode']['lowTemperatureThreshold']
      res['hi_temp'] = ss_data['result']['smartMode']['highTemperatureThreshold']
   else:
      res['auto_mode'] = "off"
      try:
         res['lo_temp'] = ss_data['result']['smartMode']['lowTemperatureThreshold']
      except Exception as e:
         res['lo_temp'] = 21.6
      try:
         res['hi_temp'] = ss_data['result']['smartMode']['highTemperatureThreshold']
      except Exception as e:
         res['hi_temp'] = 21.8

   return res


def do_send_ok(app_res):
   ret_arr = { "status": "OK" }
   ret_js = json.dumps(ret_arr, indent = 3)
   status = '200 OK'
   response_header = [('Content-type', response_content_type)]
   app_res(status, response_header)
   return [bytes(ret_js, encoding='utf-8')]


def do_info(app_res):
   ret_arr = getvals()
   ret_arr["status"] = "OK"
   ret_js = json.dumps(ret_arr, indent = 3)
   status = '200 OK'
   response_header = [('Content-type', response_content_type)]
   app_res(status, response_header)
   return [bytes(ret_js, encoding='utf-8')]


def do_set_heat(app_res, in_args):
   ret_arr = getvals()
   try:
      b_on = int(in_args["on"][0]) != 0
   except Exception:
      b_on = ret_arr['auto_enabled']

   if (ret_arr['auto_mode'].lower() != "heat"):
      # if not in heat mode (cool or off) - turn off if running
      if (ret_arr['run']):
         ac_set_state(False, "heat", 26, "auto")
   acmod.ac_set_smartmode(b_on, "heat", ret_arr['lo_temp'], ret_arr['hi_temp'])
   return do_send_ok(app_res)   


def do_set_cool(app_res, in_args):
   ret_arr = getvals()
   try:
      b_on = int(in_args["on"][0]) != 0
   except Exception:
      b_on = ret_arr['auto_enabled']

   if (ret_arr['auto_mode'].lower() != "cool"):
      # if not in cool mode (heat or off) - turn off if running
      if (ret_arr['run']):
         ac_set_state(False, "cool", 20, "auto")
   acmod.ac_set_smartmode(b_on, "cool", ret_arr['lo_temp'], ret_arr['hi_temp'])
   return do_send_ok(app_res)   


def do_set_on(app_res):
   ret_arr = getvals()
   if (not ret_arr['auto_enabled']):
      if (ret_arr['auto_mode'].lower() == "off"):
         raise Exception("Cannot enable auto mode when selection is off")
      acmod.ac_set_smartmode(True, ret_arr['auto_mode'], ret_arr['lo_temp'], ret_arr['hi_temp'])


def do_set_off(app_res):
   ret_arr = getvals()
   if (ret_arr['run']):
      ac_set_state(False, ret_arr['run_mode'], 22, "auto")
   if (ret_arr['auto_mode'].lower() != "off"):
      acmod.ac_set_smartmode(False, ret_arr['auto_mode'], ret_arr['lo_temp'], ret_arr['hi_temp'])
   return do_send_ok(app_res)   


def do_set_temp(app_res, in_args):
   try:
      lo_temp = float(in_args["lo_temp"][0])
      hi_temp = float(in_args["hi_temp"][0])
   except Exception as e:
      raise Exception("Required temp parameter is missing")

   # Clamp temp range to 19-24 and make sure lo_temp and hi_temp more than 0.1 degree apart (i.e. 0.2)
   if (lo_temp < 19 or lo_temp > 24 or hi_temp < 19 or hi_temp > 24 or lo_temp + 0.1 >= hi_temp):
      raise Exception("Invalid temperature values specified")
   ret_arr = getvals()
   if (ret_arr['auto_mode'].lower() == "off"):
      raise Exception("Auto mode is off - unable to set temperature")
   acmod.ac_set_smartmode(ret_arr['auto_enabled'], ret_arr["auto_mode"], lo_temp, hi_temp)
   return do_send_ok(app_res)   


def application(app_env, app_res):
   try:
      try:
         with open(auth_file, 'r') as af:
            auth_hash = af.read().rstrip()
      except EnvironmentError:
         raise Exception("auth file missing")
         
      # parse GET or POST parameters
      if (app_env['REQUEST_METHOD'].upper() == 'GET'):
         in_args = parse_qs(app_env['QUERY_STRING'])
      elif (app_env['REQUEST_METHOD'].upper() == 'POST'):
         in_args = parse_qs(app_env['QUERY_STRING'])
         in_body_size = int(app_env.get('CONTENT_LENGTH', 0))
         in_body = app_env['wsgi.input'].read(in_body_size).decode()
         in_args_body = parse_qs(in_body)
         in_args.update(in_args_body)
      else:
         raise Exception("Unsupported method")

      try:
         auth_in = in_args["auth"][0]
      except Exception as e:
         raise Exception("auth")

      if (hashlib.md5(auth_in.encode('utf-8')).hexdigest() != auth_hash):
         raise Exception("auth")

      # get operator "op", default to nonexistent value
      op = in_args.get("op", ["none"])[0]
   
      if (op.lower() == "info"):
         return do_info(app_res)
      elif (op.lower() == "set_heat"):
         return do_set_heat(app_res, in_args)
      elif (op.lower() == "set_cool"):
         return do_set_cool(app_res, in_args)
      elif (op.lower() == "set_on"):
         return do_set_on(app_res)
      elif (op.lower() == "set_off"):
         return do_set_off(app_res)
      elif (op.lower() == "set_temp"):
         return do_set_temp(app_res, in_args)
      else:
         raise Exception("Unsupported operator")

      ret_arr["status"] = "OK"
      ret_js = json.dumps(ret_arr, indent = 3)
      status = '200 OK'
      response_header = [('Content-type', response_content_type)]
      app_res(status, response_header)
      return [bytes(ret_js, encoding='utf-8')]

   except Exception as e:
      ret_arr = { "status": "error", "error": str(e) }
      ret_js = json.dumps(ret_arr, indent = 3)
      status = '400 ERROR'
      response_header = [('Content-type', response_content_type)]
      app_res(status, response_header)
      return [bytes(ret_js, encoding='utf-8')]
      
