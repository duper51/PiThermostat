#!/usr/bin/env python3
import Adafruit_DHT
import logging
from threading import Thread
import time
import json
import RPi.GPIO as GPIO
import requests
import configparser

sense_thread = None
connect_thread = None
running = True
config = configparser.ConfigParser()

def verify_config():
  config.read('config.ini')
  if 'uuid' in config['settings'] and 'api_key' in config['settings']:
    return True
  else:
    return False

def main():
  logging.basicConfig()
  verify_config()
  GPIO.setmode(GPIO.BCM)
  GPIO.setwarnings(False)
  GPIO.setup(17, GPIO.OUT)
  sense_obj = TempSensor(4)
  connection = Connector(sense_obj)
  sense_thread = Thread(target=sense_obj.runner_thread, name='sense-thread')
  sense_thread.start()
  connect_thread = Thread(target=connection.update_current_temp, name='connect-thread')
  connect_thread.start()

  while True:
    print("Temp: {0:0.1F}, humid: {1:0.1F}, shouldRun: {2}".format(sense_obj.temp, sense_obj.humid, connection.should_be_on(sense_obj.temp)))
    status = connection.should_be_on(sense_obj.temp)
    if status is not None:
      if status:
        GPIO.output(17, GPIO.HIGH)
      else:
        GPIO.output(17, GPIO.LOW)
    time.sleep(1)    

def cleanup():
  GPIO.cleanup()  

class TempSensor:
  def __init__(self, pin):
    self.temp = None
    self.humid = None
    self.current_rough_avg = None
    self._pin = pin
    while self.temp is None and self.humid is None:
      self._update()

  def _update(self):
    humidity_tmp, temp_tmp = Adafruit_DHT.read_retry(Adafruit_DHT.AM2302, self._pin)
    if self.current_rough_avg is not None:
      self.current_rough_avg = temp_tmp
    if temp_tmp is not None and humidity_tmp is not None and (abs(self.current_rough_avg - self.temp) < 2):
      self.temp = (temp_tmp * 9 / 5) + 32
      self.humid = humidity_tmp
    self.current_rough_avg = (self.current_rough_avg + temp_tmp)/2

  def runner_thread(self):
    global running
    while running:
      self._update()

class Connector:
  def __init__(self, sensor):
    self.low_temp_setting = 0
    self.high_temp_setting = 1
    self._current_avg = None
    self._sense_obj = sensor
    self._uuid = config['settings']['uuid']

  def get_temp(self):
    return (self.low_temp_setting, self.high_temp_setting)

  def should_be_on(self, temp):
    if temp < self.low_temp_setting:
      return True
    if temp > self.high_temp_setting:
      return False
    # return none if no change should be made to setting
    return None
  def update_current_temp(self):
    global running, sense_obj
    run = 6
    while running:
      try:
        self._make_call("updateTemp", {"current_temp": self._sense_obj.temp, "current_humid": self._sense_obj.humid}, "POST")
        resp = self._make_call("")
        self.low_temp_setting = resp['settings']['temp_setting']
        self.high_temp_setting = self.low_temp_setting +  resp['settings']['threshold']
        if run >= 6:
           print(str(self._make_link_call()))
           run = 0
        time.sleep(20)
        run += 1
      except Exception as e:
        print("Caught exception in update thread")
        print(e)

  def _make_call(self, endpoint, body=None, method="GET"):
    base_url = "https://temp-api.duper51.me/temperature/" + self._uuid + "/"
    url = base_url + endpoint
    headers = {'x-api-key': config['settings']['api_key'],
               'Content-Type': 'application/json'}
    r = None
    if (method=="GET"):
      r = requests.get(url, headers=headers)
    elif (method=="POST"):
      r = requests.post(url, headers=headers, data=json.dumps(body))
    elif (method=="PUT"):
      r = requests.put(url, headers=headers, data=json.dumps(body))
    if(r.status_code == 200):
      return r.json()
    else:
      print("API Call Failed")
      print(str(r))

  def _make_link_call(self):
    base_url = "https://temp-api.duper51.me/link/" + self._uuid
    headers = {'x-api-key': config['settings']['api_key'],
               'Content-Type': 'application/json'}
    r = requests.post(base_url, headers=headers, data=headers['x-api-key'])
    if(r.status_code == 200):
      return r.json()
    else:
      print("API Call Failed")
      print(str(r))


if __name__ == "__main__":
  try:
    main()
  except Exception as e:
    print("uncaught exception in main, cleaning and closing")
    raise
  finally:
    GPIO.output(17,GPIO.LOW)
    GPIO.cleanup()
    running = False
    print("finally block reached")
