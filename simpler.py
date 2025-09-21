import logging

if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)

import relays
import settings
from dataclasses import dataclass
import valves_and_temps
import datetime
import requests
import time

import threading

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
    try:
        r=requests.get(url)
        main_state=r.json()
        logging.info(f"Found state: {main_state}")
        shs=SysHeatState.from_JSON(main_state)
        logging.info(f"""Server says:.....................
                {shs.heating_currently_on=}
                {shs.hot_water_temperature=}
                {shs.hot_water_last_temp_dt=}
                {shs.hot_water_currently_on=}
                {shs.heating_currently_on=}""")
    except Exception as e:
        logging.error(f"Failed to fetch system state from {url}, assuming everything off: {e}")
        shs=SysHeatState(False,False,datetime.datetime.now(),-100.0,datetime.datetime.now()-datetime.timedelta(hours=1),datetime.datetime.now()-datetime.timedelta(hours=1))
    return shs

class SimpleState:
    def __init__(self,valid_states,starting_state):
        self.valid_states=valid_states
        self.state=starting_state

    def change_state(self,new_state):
        if new_state not in self.valid_states:
            raise ValueError(f"{new_state} is not one of the valid states ({self.valid_states})")
        self.state=new_state

    def __str__(self):
        return self.state

    def __eq__(self,other):
        if str(other) not in self.valid_states:
            raise ValueError(f"{other} is not one of the valid states ({self.valid_states})")
        return str(other)==str(self)

class MainState(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.name="HeatingPiMainThread"
        self.daemon=True
        self.heating=SimpleState(["OFF","OPENING_VALVE","HEATING"],"OFF")
        self.hot_water=SimpleState(["OFF","OPENING_VALVE","HEATING"],"OFF")   
        self.valve_temp_states=valves_and_temps.ValveTempState.new_blank() # Continuously updates by the thread below by serial monitoring
        self.valve_temp_thread=valves_and_temps.ValvesTemps(self.valve_temp_states)
        self.valve_temp_thread.start()

    def run(self):

        while True:
            # Fetch requirements from server
            server_state:SysHeatState=get_main_system_state(settings.URL_TO_FETCH_SYSTEM_STATE)

            # Calculate if we want to heat water
            heat_water= server_state.hot_water_temperature<settings.HOT_WATER_OFF_TEMPERATURE and server_state.hot_water_currently_on

            # Calculate if we want to heat radiators
            heat_radiators=server_state.heating_currently_on

            logging.info(f"Heating wanted: {heat_radiators}, Hotter water wanted: {heat_water}")

            logging.info(f"Valves and temps: {self.valve_temp_states}")

            # Update the hw_state
            if heat_water:
                match self.hot_water:
                    case "OFF":
                        # open the valve
                        relays.hot_water_valve.on()
                        logging.info("Hotter water demanded, starting to open valve")
                        self.hot_water.change_state("OPENING_VALVE")
                        

                    case "OPENING_VALVE":
                        # is the valve open
                        if self.valve_temp_states.hw_valve_open:
                            relays.hot_water_pump.on()
                            self.hot_water.change_state("HEATING")
                        

            else:
                match self.hot_water:
                    case "HEATING":
                        # We need to switch off the heating
                        relays.hot_water_valve.off()
                        relays.hot_water_pump.off()
                        self.hot_water.change_state("OFF")
                        

                    case "OPENING_VALVE":
                        # We want the heating to stop, so kill it
                        relays.hot_water_valve.off()
                        relays.hot_water_pump.off()
                        self.hot_water.change_state("OFF")
                        

            # Update the heating state
            if heat_radiators:
                match self.heating:
                    case "OFF":
                        # open the valve
                        relays.heating_valve.on()
                        self.heating.change_state("OPENING_VALVE")
                        logging.info(f"started opening heating valve\n\t because:\n\t\t{heat_radiators=}, {self.heating=}" )
                        

                    case "OPENING_VALVE":
                        # is the valve open
                        if self.valve_temp_states.rad_valve_open:
                            relays.heating_pump.on()
                            self.heating.change_state("HEATING")
                        

            else:
                match self.heating:
                    case "HEATING":
                        # We need to switch off the heating
                        relays.heating_valve.off()
                        relays.heating_pump.off()
                        self.heating.change_state("OFF")
                        logging.info("heating stopped")
                        

                    case "OPENING_VALVE":
                        # We want the heating to stop, so kill it
                        relays.heating_valve.off()
                        relays.heating_pump.off()
                        self.heating.change_state("OFF")
                        logging.info("Heating stopped early")
                        
            # Calculate if boiler should be burning

            boiler_required= (heat_water and self.hot_water=="HEATING") or (heat_radiators and self.heating=="HEATING")
            if boiler_required:
                relays.boiler_heat_req.on()
            else:
                relays.boiler_heat_req.off()

            logging.info("\n\n")
            time.sleep(7)

    def __str__(self):
        return f"""Heating: 
        Radiators demand: {self.heating}
        Hotter water damand: {self.hot_water}
        Valve temps: {self.valve_temp_states}
        Relays: 
            HW valve {relays.hot_water_valve}
            HW pump {relays.hot_water_pump}
            Heating valve {relays.heating_valve}
            Heating pump {relays.heating_pump}
            Boiler heat req {relays.boiler_heat_req}"""



if __name__=="__main__":
    t=MainState()
    t.start()
    while True:
        time.sleep(60)


                    

