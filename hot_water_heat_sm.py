import logging
if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)



from state_machine import StateMachine
import time

import relays

import settings




class HeatWaterSM(StateMachine):
    def __init__(self,*,name:str,pump_relay:relays.Relay,valve_relay:relays.Relay):
        super().__init__(name=name,
                         states=["Initialising","Off","Waiting Valve Open","On","Waiting Valve Closed"],
                         initial_state="Initialising",
                         subscribers=[])
        self.demanding_heat:bool=False
        self.pump_relay=pump_relay
        self.valve_relay=valve_relay
        
    
    @property
    def burn_wanted(self)->bool:
        return self.state=="On"


    def step(self):
        # logging.debug("tick:"+self.state)
        match self.state:
            case "Initialising":
                logging.info(f"{self.name} Setting pump and valve to default state, probably a repeat but harmless")
                self.stop_pump()
                self.close_valve()
                logging.info(f"{self.name} Initialising to off as not requiring heat at the moment")
                self.demanding_heat=False
                self.set_state(new_state="Off",reason="Initialised",timeout_s=-1)
                return
            
            case "Off":
                return # Nothing to do here, external code will call the state change

            case "Waiting Valve Open":
                logging.info(f"{self.name}: Checking if valve has finished opening...")



                # FAKE FOR NOW
                if self.last_change_time<time.time()-settings.FAKE_WAIT_FOR_VALVE_TIME_S:
                    self.start_pump()
                    self.set_state(new_state="On",reason=f"{self.name} valve now open")
                    return
                
            case "On":
                return # Nothing to do here, external code will change the state to off sometime
            
            case "Waiting Valve Closed":
                logging.info(f"{self.name}:Checking if valve has closed")


                # FAKE FOR NOW
                if self.last_change_time<time.time()-settings.FAKE_WAIT_FOR_VALVE_TIME_S:
                    self.stop_pump()
                    self.set_state(new_state="Off",reason=f"{self.name}: valve now closed")
                    return
                

                
            case _:
                raise ValueError(f"Somehow the state of {self.name} is {self.state} which isn't one of the valid ones!")


    def open_valve(self):
        logging.info(f"{self.name} Opening valve")
        self.valve_relay.on()
        return
    
    def close_valve(self):
        logging.info(f"{self.name} Closing valve")
        self.valve_relay.off()
        return
    
    def start_pump(self):
        logging.info(f"{self.name} Starting pump")
        self.pump_relay.on()

    def stop_pump(self):
        logging.info(f"{self.name} Stopping pump")
        self.pump_relay.off()

        
    def heat_please(self):
        # Actions to be done depend on the current state:

        match self.state:
            case "Off":
                self.open_valve()
                self.set_state(new_state="Waiting Valve Open",reason=f"{self.name}:heat requested")
                return
            case "Waiting Valve Open":
                logging.info(f"{self.name}:Ignoring heat please as we're already switching on the heat")
                return
            case "On":
                logging.info(f"{self.name}: Ignoring heat request, it's already on")
                return
            case "Waiting Valve Closed":
                self.start_opening_valve()
                self.set_state(new_state="Waiting Valve Open",reason=f"{self.name}:heat requested")
                return

            case _:
                raise ValueError(f"In {self.name}, we didn't expect to see a state of {self.state} when hot water was requested")
            

                


        

    def heat_off_please(self):
                # Actions to be done depend on the current state:

        match self.state:
            case "Off":
                logging.info(f"{self.name}:Ignoring heat off request as it's already off")
                return
            case "Waiting Valve Open":
                self.close_valve()
                self.set_state(new_state="Waiting Valve Closed",reason=f"{self.name}:heat request cancelled")
                return
            case "On":
                self.close_valve()
                self.set_state(new_state="Waiting Valve Closed",reason=f"{self.name}:heat request cancelled")
                return
            case "Waiting Valve Closed":
                logging.info(f"{self.name}:Nothing to do, heating is already going off")
                return

            case _:
                raise ValueError(f"In {self.name}, we didn't expect to see a state of {self.state} when heat was cancelled")



def pause(time_s):
    enddy=time.time()+time_s
    while time.time()<enddy:
        time.sleep(1)






if __name__=="__main__":
    heating=HeatWaterSM(name="heating",pump_relay=relays.heating_pump,valve_relay=relays.heating_valve)
    
    heating.start()
    pause(6)
    heating.heat_please()
    pause(6)
    heating.heat_off_please()
    pause(6)

    heating.stop()