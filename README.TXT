No license, experimental code, use at your own risk! 

This is a set of modules and applications to provide basic control
of a Sensibo device

acmod.py - Python module providing simplified api to certain AC control functions

acctl.py - Python module that can act as a web gateway (through Apache WSGI) to
           specific Sensibo AC control functions. Acts as a back end to 
           the web client.

acctl.html
acctl.js  - web client implementation of a simple "thermostat" style
            controller for the temperature. Uses Sensibo "smart mode"
            in lieu of AC own temperature sensing (allowing AC to be
            fully turned off at reaching the target temperature)

ac.py     - periodic script to trigger specific AC behaviors. In particular,
            - Helps in the cases of "runaway" AC (where Sensibo is out of sync
            with the unit). 
            - Implements "anti-mold" like functionality, running AC fan for a short
            period of time after AC compressor shuts off.

To use the web server component acctl.py you would need to place it into a
directory on your web server where WSGI is enabled.

Private information, including device ID, key and authentication hash for the
web client, should be stored in a file acpriv.py, which has to contain the 
following variables:

ss_url_v2_base="https://home.sensibo.com/api/v2/pods/<your device id>"
ss_url_v1_base="https://home.sensibo.com/api/v1/pods/<your device id>"
ss_key="<your device key>"
auth_hash="<md5 hash of the client passphrase>"

~                                              

