import logging

logging.basicConfig(level=logging.DEBUG)

from relays import *
import time



hot_water_valve.on()
time.sleep(3)
hot_water_pump.on()
time.sleep(3)
heating_valve.on()
time.sleep(3)
heating_pump.on()
time.sleep(3)
boiler_heat_req.on()

hot_water_pump.on()
time.sleep(2)
boiler_heat_req.on()

while True:
    time.sleep(5)
    logging.info("tick")