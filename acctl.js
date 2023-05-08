var BG_OFF = "#eeeeee";
var BG_COOL = "#aaddff";
var BG_HEAT = "#ffbb77";

var page_visible = true;
var vals_loaded = false;
var submit_delay = 2000;
var info_interval = 15000;
var info_delay = 1000;

var submit_id = 0;
var cur_temp = 0;
var lo_temp = 19;
var hi_temp = 20;
var auto_mode = "off";
var run_mode = "off";
var run = false;
var auto_enabled = false;
var auth = null;

var auto_mode_new = auto_mode;

var url_info = "acctl.py?op=info";

var url_set_temp = "acctl.py?op=set_temp";
var url_set_heat = "acctl.py?op=set_heat";
var url_set_cool = "acctl.py?op=set_cool";
var url_set_off = "acctl.py?op=set_off";


function init_page()
{
   auth = getCookie("auth");
   if (!auth || auth == "") {
      open_modal();
   }

   srv_get_info();

   document.addEventListener( 'visibilitychange' , function() {
      if (document.hidden) {
         page_visible = false;
      } else {
         page_visible = true;
         setTimeout(srv_get_info, info_delay);
      }
   }, false );

   setInterval(srv_get_info, info_interval);
}


function srv_get_info()
{
   if (!page_visible) return;
   if (!auth) return;

   var xhr = new XMLHttpRequest();

   xhr.open('POST', url_info, true);
   xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
   xhr.responseType = 'json';

   req_params = new URLSearchParams();
   req_params.set('auth', auth);
   params_str = req_params.toString();

   xhr.onload = function() {
      var status = xhr.status;
      var ret = xhr.response;

      if (status != 200 || ret['status'] != 'OK') {
         handle_error(ret);
         return;
      }

      cur_temp = ret["temp"];
      lo_temp = ret['lo_temp'];
      hi_temp = ret['hi_temp'];
      auto_mode = ret['auto_mode'];
      run_mode = ret['run_mode'];
      run = ret['run'];
      auto_enabled = ret['auto_enabled'];
      vals_loaded = true;

      auto_mode_new = auto_enabled ? auto_mode : "off";

      update_set_temp();
      update_cur_temp();
      update_mode_switch();
      update_frame_bg();
   }

   xhr.send(params_str);
}


function srv_set_mode()
{
   var xhr = new XMLHttpRequest();
   var url = url_set_temp;
   var b_on = false;

   tmode = auto_enabled ? auto_mode : "off";
   // change in effective mode
   if (auto_mode_new != tmode) {
      switch(auto_mode_new) {
      case "heat":
         url = url_set_heat;
         b_on = true;
         break;
      case "cool":
         url = url_set_cool;
         b_on = true;
         break;
      case "off":
         url = url_set_off;
         break;
      default:
         break;
      }
   }

   xhr.open('POST', url, true);
   xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
   xhr.responseType = 'json';

   // alwaus send temperature
   req_params = new URLSearchParams();
   req_params.set('auth', auth);
   req_params.set('lo_temp', lo_temp.toFixed(1));
   req_params.set('hi_temp', hi_temp.toFixed(1));
   if (b_on)
      req_params.set('on', '1');
   params_str = req_params.toString();

   xhr.onload = function() {
      var status = xhr.status;
      var ret = xhr.response;

      if (status != 200 || ret['status'] != 'OK') {
         handle_error(ret);
         return;
      }
      
      auto_mode = auto_mode_new;

      // launch info reload
      setTimeout(srv_get_info, info_delay);
   }

   xhr.send(params_str);
}



function submit_mode()
{
   submit_id = 0;
   //alert("Submit lo: " + lo_temp.toFixed(1) + ", high: " + hi_temp.toFixed(1));
   srv_set_mode()
}


function update_mode_switch()
{
   tmode = auto_enabled ? auto_mode : "off";
   switch (tmode) {
   case "heat":
      document.getElementById('radio-heat').checked = true;
      break;
   case "cool":
      document.getElementById('radio-cool').checked = true;
      break;
   case "off":
   default:
      document.getElementById('radio-off').checked = true;
      break;
   }
}


function update_cur_temp()
{
   document.getElementById('temp_cur_text').innerHTML = "&nbsp;" + cur_temp.toFixed(1) + "&deg;";
}


function update_set_temp()
{
   temp_str = lo_temp.toFixed(1) + "&deg;-" + hi_temp.toFixed(1) + "&deg;";
   document.getElementById('temp_set_text').innerHTML = temp_str;
}


function update_frame_bg()
{
   color = BG_OFF;

   if (run_mode == "cool" && run) {
      color = BG_COOL;
   } else if (run_mode == "heat" && run) {
      color = BG_HEAT;
   }
   document.getElementById('frame').style.backgroundColor = color;
}


function click_up()
{
   if (!vals_loaded) return;
   if (submit_id) clearTimeout(submit_id);

   lo_temp += 0.1;
   hi_temp += 0.1;
   update_set_temp();

   submit_id = setTimeout(submit_mode, submit_delay);
}


function click_down()
{
   if (!vals_loaded) return;
   if (submit_id) clearTimeout(submit_id);

   lo_temp -= 0.1;
   hi_temp -= 0.1;
   update_set_temp();

   submit_id = setTimeout(submit_mode, submit_delay);
}


function switch_mode(item)
{
   if (!vals_loaded) return;
   if (submit_id) clearTimeout(submit_id);

   auto_mode_new = item.value;
   submit_id = setTimeout(submit_mode, submit_delay);
}


function open_modal()
{
   document.getElementById('auth_dialog').style.display = "block";
}

function close_modal()
{
   auth = document.getElementById('auth_value').value;
   setCookie("auth", auth, 365);
   document.getElementById('auth_dialog').style.display = "none";
   setTimeout(srv_get_info, 500);
}

function handle_error(ret)
{
   if (!ret || !ret['status'] || ret['status'] != "error") {
      alert("Unknown error");
      return;
   }

   // on auth errors re-request auth value
   if (ret['error'] == "auth") {
      open_modal();
      return;
   }

   alert(ret['error']);
}

function setCookie(name,value,days) {
    var expires = "";
    if (days) {
        var date = new Date();
        date.setTime(date.getTime() + (days*24*60*60*1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "")  + expires + "; path=/";
}

function getCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for(var i=0;i < ca.length;i++) {
        var c = ca[i];
        while (c.charAt(0)==' ') c = c.substring(1,c.length);
        if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
    }
    return null;
}

function eraseCookie(name) {   
    document.cookie = name +'=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';
}

