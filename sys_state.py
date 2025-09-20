import logging
if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)


"""

Holds the whole system state, 

all the state machines and state variables live here!





"""

import hot_water_heat_sm
import threading
import relays
import requests
import settings
import datetime
import json
import time
from dataclasses import dataclass
import valves_and_temps

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
    shs=SysHeatState.from_JSON(main_state)
    logging.info(f"Server says:.....................    {shs.hot_water_currently_on=} ..........    {shs.heating_currently_on=}")
    return shs






class SystemState(threading.Thread):
    

    instance_count:int=0


    def __init__(self):
        if self.instance_count>0:
            raise Exception("Attempt to set up a duplicate SystemState- which must be a singleton!")
        

        super().__init__()
        
        self.instance_count+=1
        self.name="MainSystemStateThread"
        self.burn_relay=relays.boiler_heat_req
        self.burning_now=False
        self.burn_relay.off()
        self.burn_callback = lambda *args, **kwargs: self.fire_boiler_if_required(*args, **kwargs)
        self.manage_temperature_callback = lambda hot_water_state : self.manage_temperature(hw_state=hot_water_state)

        # Start monitoring the temperatures and valve states:
        self.valve_temp_states=valves_and_temps.ValveTempState.new_blank() # Continuously updates by the thread below by serial monitoring
        self.valve_temp_thread=valves_and_temps.ValvesTemps(self.valve_temp_states)
        self.valve_temp_thread.start()



        # These are the two threaded state machines that handle the two circuits
        self.heating=hot_water_heat_sm.HeatWaterSM(name="heating",
                                                   pump_relay=relays.heating_pump,
                                                   valve_relay=relays.heating_valve,
                                                   valve_state_fn=self.valve_temp_states.get_rad_valve_open)
        self.hot_water=hot_water_heat_sm.HeatWaterSM(name="hot water",
                                                     pump_relay=relays.hot_water_pump,
                                                     valve_relay=relays.hot_water_valve,
                                                     valve_state_fn=self.valve_temp_states.get_hw_valve_open,
                                                     control_while_on_callback=self.manage_temperature_callback)
        
        
        self.stop_requested=False
        self.stopped=False
        self.server_state:SysHeatState|None=None
        self.hot_water_overheat_condition=False
        self.old_hw_state:bool=False
        self.old_heat_state:bool=False

        # Start the two circuit state machines
        self.heating.start()
        self.hot_water.start()
        
        
        self.heating.add_subscriber(self.burn_callback)
        self.hot_water.add_subscriber(self.burn_callback)

    def manage_temperature(self,hw_state:hot_water_heat_sm.HeatWaterSM):


        assert isinstance(hw_state,hot_water_heat_sm.HeatWaterSM),f"Manage temperature called with hw_state not being the state engine, but {type(hw_state)}"

        if not hw_state.state=="On":
            raise ValueError("Attempt to manage temperature when the hw isn't on")

        logging.info("\nChecking hot water temperature, do we need head?")
        current_actual=self.server_state.hot_water_temperature
        if current_actual>settings.HOT_WATER_OFF_TEMPERATURE:
            logging.info("HW REACHED REQUIRED TEMPERATURE- SWITCHING OFF PUMP")
            hw_state.stop_pump() # Will stop the pump and indirectly this will indicate if burn is required
            return

        if current_actual<settings.HOT_WATER_ON_TEMPERATURE:
            logging.info("HW BELOW REQUIRED TEMPERATURE- SWITCHING ON PUMP")
            hw_state.start_pump() # Will stop the pump and indirectly this will indicate if burn is required
            return

        logging.info(f"How water is {current_actual}, which is between {settings.HOT_WATER_ON_TEMPERATURE} and {settings.HOT_WATER_OFF_TEMPERATURE} so no heat needed")



    def update_demands(self):
        """
            Takes all the state stuff and decides whether 
            heating or hot water is required to be on
            and whether the boiler should run
        """

        
        # Check if heat is currently called-for
        new_heat_state:bool=self.server_state.heating_currently_on
        new_hw_state:bool=self.server_state.hot_water_currently_on


        # logging.debug(f"###### OLD : {self.old_heat_state}   >>>>> {new_heat_state}")



        if not new_heat_state==self.old_heat_state:# We have a change in demand....
            self.old_heat_state=new_heat_state
            logging.info("State change detected for heating")
            if new_heat_state:
                self.heating.heat_please()
            else:
                logging.info("Switching off heating!!!!!!!!")
                self.heating.heat_off_please()

        if not new_hw_state==self.old_hw_state:
            self.old_hw_state=new_hw_state
            if new_hw_state:
                self.hot_water.heat_please()
            else:
                self.hot_water.heat_off_please()

        self.fire_boiler_if_required()
        
    def fire_boiler_if_required(self,**kwargs):
        """
            This just fires the boiler if that's appropriate

            Note: it get's called when a demand change is calculated
            but also as a result of being subscribed to state changes
            for the heating or hot water state machines!
        
        """
        # Master rule, hot water over temperature=>immediate shutdown 
        # logging.info(f"fire boiler being tested : {kwargs}")
        if self.hot_water_overheat_condition:
            self.burn_relay.off()
            logging.error(f"FORCED BOILER OFF DUE TO HOT WATER OVER-TEMPERATURE CONDITION")
            return # Will do nothing else
        
        hw_burn=self.hot_water.burn_wanted
        heat_burn=self.heating.burn_wanted
        burn_wanted:bool=hw_burn | heat_burn
        if burn_wanted==self.burning_now:
            return # we are already doing the right thing
        if burn_wanted:
            self.burn_relay.on()
        else:
            self.burn_relay.off()

        self.burning_now=burn_wanted



    def run(self):
        next_get_hw=time.time()
        while not self.stop_requested:
            if time.time()>next_get_hw:
                next_get_hw+=settings.SERVER_STATE_FETCH_INTERVAL_S
                self.server_state=get_main_system_state(settings.URL_TO_FETCH_SYSTEM_STATE)
                if self.server_state.hot_water_temperature>settings.HOT_WATER_SHUTDOWN_TEMPERATURE:
                    logging.error(f"Forced to enter overheat condition due to high temperature")
                    self.hot_water_overheat_condition=True

                if self.server_state.hot_water_last_temp_dt<datetime.datetime.now()-datetime.timedelta(minutes=10):
                    logging.error(f"Forced to enter overheat condition because our temperature reading is too old")
                    self.hot_water_overheat_condition=True

            
            self.update_demands() # Calculates if the burn relay should be set, 


            time.sleep(2.02)

        self.stopped=True


    def stop(self):
        

        # stop the two state machines
        self.heating.stop(block_timeout_s=4)
        self.hot_water.stop(block_timeout_s=4)
        

        self.stop_requested=True

        timeout=time.time()+20
        while time.time()<timeout:
            if self.stopped and self.heating.stopped and self.hot_water.stopped:
                logging.info(f"{self.name} now stopped gracefully")
                return
            time.sleep(0.93)

        raise Exception(f"Failed to stop {self.name} gracefully in 20 seconds")
    
    
def pause_timeout(timeout_s:float):
    endtime=time.time()+timeout_s
    while time.time()<endtime:
        time.sleep(1)


if __name__=="__main__":
    testsys=SystemState()
    testsys.start()
    pause_timeout(5)
    testsys.hot_water.heat_please()
    pause_timeout(60)
    testsys.hot_water.heat_off_please()
    pause_timeout(10)
    testsys.stop()
    time.sleep(4)
    print("finished")

