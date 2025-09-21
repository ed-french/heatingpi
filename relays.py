import logging
if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)

from gpiozero import LED
from enum import Enum
import time


class RelayIs(Enum):
    OFF = 0
    ON = 1




class Relay:
    pin_mapping={1:37,
                 2:35,
                 3:33,
                 4:31,
                 5:29,
                 6:23,
                 7:21,
                 8:19}
    instances=[]

    def __init__(self,name:str,relay_number:int,initial_state=RelayIs.OFF):



        self.state:RelayIs=initial_state
        self.name=name
        self.pin=self.pin_mapping[relay_number]
        self.output=LED(f"BOARD{self.pin}")
        self.set_value(initial_state)
        self.initial_state=initial_state

        
        Relay.instances.append(self)

    def on(self):
        self.set_value(RelayIs.ON)
        logging.info(f">>>>>>> Switched: {self.name} on")

    def off(self):
        self.set_value(RelayIs.OFF)
        logging.info(f">>>>>>> Switched: {self.name} off")

    def is_on(self)->bool:
        # interrogated to see if the pump is on, so that burn requirement can be determined
        return self.output.value==RelayIs.ON

    def set_value(self,value):
        if value == RelayIs.OFF:
            self.output.off()
            logging.info(f">>>>>>> Switched: {self.name} off")

        else:
            self.output.on()
            logging.info(f">>>>> Switched {self.name} on")

    def __str__(self):
        return f"Relay {self.name} = {self.output.value==RelayIs.ON}"

    @classmethod
    def reset_all(cls):
        for rel in cls.instances:
            rel.set_value(rel.initial_state)






boiler_heat_req=Relay("boiler_heat_req",1)
hot_water_valve=Relay("hot_water_valve",2)
hot_water_pump=Relay("hot_water_pump",3)
heating_valve=Relay("heating_valve",4)
heating_pump=Relay("heating_pump",5)

if __name__=="__main__":
    end_time=time.time()+10
    while time.time()<end_time:
        boiler_heat_req.on()
        time.sleep(3)
        hot_water_valve.on()
        time.sleep(3)
        hot_water_pump.on()
        time.sleep(3)
        heating_valve.on()
        time.sleep(3)
        heating_pump.on()
        time.sleep(0.5)
        boiler_heat_req.off()
        time.sleep(0.5)
        hot_water_valve.off()
        time.sleep(0.5)
        hot_water_pump.off()
        time.sleep(0.5)
        heating_valve.off()
        time.sleep(0.5)
        heating_pump.off()
        time.sleep(0.5)
    print("Finished, resetting all to off...")

    Relay.reset_all()






