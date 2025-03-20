import logging
if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)


"""

Holds the whole system state, 

all the state machines and state variables live here!





"""

import simple_heat
import threading
import relays
import requests
import settings
import datetime
import json
import time
from dataclasses import dataclass

@dataclass
class SysHeatState:
    heating_currently_on:bool
    hot_water_currently_on:bool
    heating_boost_timeout:datetime.datetime
    hot_water_temperature:float
    hot_water_last_temp_dt:datetime.datetime
    hot_water_boost_requested:datetime.datetime

    @classmethod
    def from_JSON(cls,jsondict):
        return cls(jsondict["heating_currently_on"],
                   jsondict["hot_water_currently_on"],
                   datetime.datetime.fromisoformat(jsondict["heating_boost_timeout"]),
                   jsondict["hot_water_temperature"],
                   datetime.datetime.fromisoformat(jsondict["hot_water_last_temp_dt"]),
                   datetime.datetime.fromisoformat(jsondict["hot_water_boost_requested"]))



def get_main_system_state(url)->SysHeatState:
    r=requests.get(url)
    main_state=r.json()
    # logging.info(f"Found state: {main_state}")
    return SysHeatState.from_JSON(main_state)






class SystemState(threading.Thread):
    

    instance_count:int=0


    def __init__(self):
        if self.instance_count>0:
            raise Exception("Attempt to set up a duplicate SystemState- which must be a singleton!")
        

        super().__init__()
        
        self.instance_count+=1
        self.name="MainSystemStateThread"
        self.burn_relay=relays.boiler_heat_req
        self.burn_relay.off()

        self.heating=simple_heat.HeatingSM()
        self.stop_requested=False
        self.stoped=False
        self.server_state:SysHeatState|None=None
        self.hot_water_overheat_condition=False

    def update_demands(self):
        """
            Takes all the state stuff and decides whether 
            heating or hot water is required to be on
            and whether the boiler should run
        """
        ...

    def run(self):
        next_get_hw=time.time()
        while not self.stop_requested:
            if time.time()>next_get_hw:
                next_get_hw+=settings.HOT_WATER_FETCH_INTERVAL_S
                self.server_state=get_main_system_state(settings.URL_TO_FETCH_SYSTEM_STATE)
                if self.server_state.hot_water_temperature>settings.HOT_WATER_SHUTDOWN_TEMPERATURE:
                    logging.error(f"Forced to enter overheat condition due to high temperature")
                    self.hot_water_overheat_condition=True
                    self.update_demands()
                if self.server_state.hot_water_last_temp_dt<datetime.datetime.now()-datetime.timedelta(minutes=10):
                    logging.error(f"Forced to enter overheat condition because our temperature reading is too old")
                    self.hot_water_overheat_condition=True
                    self.update_demands()
                


            time.sleep(2.02)

        self.stopped=True


    def stop(self):
        self.stop_requested=True
        timeout=time.time()+20
        while time.time()<timeout:
            if self.stopped:
                logging.info(f"{self.name} now stopped gracefully")
                return
            time.sleep(0.93)

        raise Exception(f"Failed to stop thread {self.name} gracefully in 20 seconds")
    
    


if __name__=="__main__":
    testsys=SystemState()
    testsys.start()
    endtime=time.time()+100
    while time.time()<endtime:
        time.sleep(4)
        logging.info("testtick")
    testsys.stop()
    time.sleep(4)
    print("finished")

