import logging
if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)

import serial
import time

from dataclasses import dataclass

import threading
import json

PORT='/dev/ttyACM0'


@dataclass
class ValveTempState:
    OutHW:float
    RetHW:float
    OutRad:float
    RetRad:float
    hw_valve_open:bool
    rad_valve_open:bool
    oil_flowing:bool

    @classmethod
    def new_blank(cls):
        return cls(-10,-10,-10,-10,False,False,False)
    
    def update(self,**new_vals):
        for key,val in new_vals.items():
            setattr(self,key,val)

    def get_hw_valve_open(self):
        return self.hw_valve_open
    
    def get_rad_valve_open(self):
        return self.rad_valve_open

class ValvesTemps(threading.Thread):
    def __init__(self,shared_state:ValveTempState):
        super().__init__()
        self.name="ValvesTempsDaaemon"
        self.state:ValveTempState=shared_state
        self.last_reading_time=time.time()
        self.stopped=False
        self.stop_requested=False



    def get_live_state(self):
        return self.state
    
    def stop(self):
        self.stop_requested=True
        timeout=time.time()+10 # 10 second timeout on blocking shutdown
        while True:
            if time.time()>timeout:
                logging.error("ValvesTemps failed to stop properly :-(")
                return
            if self.stopped:
                logging.info("ValvesTemps closed properly")
                return
            time.sleep(0.5)




    def run(self):
        with serial.Serial(PORT,115200,timeout=1) as ser:
            ser.flush()
            nl:str=""
            while not self.stop_requested:
                x=ser.read(1) # reading single bytes at a time to overcome line end inconsistencies!
                if x==b'\r' or  x==b'\n': # we finished a line 
                    
                    if nl.startswith("{"):
                        # Assume this is a valid line with the json state:
                        # logging.info(f"{nl}\n")
                        self.state.update(**json.loads(nl))
                    else:
                        # logging.debug(f"F>>>>>>>>>>>>DEBUG >>>>>>>>\n\t{nl[:20]}\n\n")
                        ...
                    nl=""
                else:
                    nl+=x.decode("ascii")



if __name__=="__main__":
    shared_state=ValveTempState.new_blank()
    scanner=ValvesTemps(shared_state=shared_state)
    scanner.start()
    while True:
        print(shared_state)
        time.sleep(2)


