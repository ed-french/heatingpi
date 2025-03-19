import logging
if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)



from state_machine import StateMachine
import time







class HeatingSM(StateMachine):
    def __init__(self):
        super().__init__(name="Heating",
                         states=["Initialising","Heating Off","Waiting Valve Open","Heating On","Waiting Valve Closed"],
                         initial_state="Initialising",
                         subscribers=[])
        self.demanding_heat:bool=False
    


    def step(self):
        # logging.debug("tick:"+self.state)
        match self.state:
            case "Initialising":
                logging.info("Setting pump and valve to default state, probably a repeat but harmless")
                self.stop_pump()
                self.close_valve()
                logging.info("Initialising to off as not requiring heat at the moment")
                self.demanding_heat=False
                self.set_state(new_state="Heating Off",reason="Initialised",timeout_s=-1)
                return
            
            case "Heating Off":
                return # Nothing to do here, external code will call the state change

            case "Waiting Valve Open":
                logging.info("Checking if valve has finished opening...")
                # fake it on time of 4 seconds
                if self.last_change_time<time.time()-4:
                    self.start_pump()
                    self.set_state(new_state="Heating On",reason="heat valve now open")
                    return
                
            case "Heating On":
                return # Nothing to do here, external code will change the state to off sometime
            
            case "Waiting Valve Closed":
                logging.info("Checking if valve has closed")
                if self.last_change_time<time.time()-4:
                    self.stop_pump()
                    self.set_state(new_state="Heating Off",reason="heat valve now closed")
                    return
                
            case _:
                raise ValueError(f"Somehow the state of {self.name} is {self.state} which isn't one of the valid ones!")


    def open_valve(self):
        logging.info("Opening valve")
        return
    
    def close_valve(self):
        logging.info("Closing valve")
        return
    
    def start_pump(self):
        logging.info("Starting pump")

    def stop_pump(self):
        logging.info("Stopping pump")

        
    def heat_please(self):
        # Actions to be done depend on the current state:

        match self.state:
            case "Heating Off":
                self.open_valve()
                self.set_state(new_state="Waiting Valve Open",reason="heat requested")
                return
            case "Waiting Valve Open":
                logging.info("Ignoring heat please as we're already switching on the heat")
                return
            case "Heating On":
                logging.info("Ignoring heat request, it's already on")
                return
            case "Waiting Valve Closed":
                self.start_opening_valve()
                self.set_state(new_state="Waiting Valve Open",reason="heat requested")
                return

            case _:
                raise ValueError(f"In {self.name}, we didn't expect to see a state of {self.state} when heat was requested")
            

                


        

    def heat_off_please(self):
                # Actions to be done depend on the current state:

        match self.state:
            case "Heating Off":
                logging.info("Ignoring heat off request as it's already off")
                return
            case "Waiting Valve Open":
                self.close_valve()
                self.set_state(new_state="Waiting Valve Closed",reason="heat request cancelled")
                return
            case "Heating On":
                self.close_valve()
                self.set_state(new_state="Waiting Valve Closed",reason="heat request cancelled")
                return
            case "Waiting Valve Closed":
                logging.info("Nothing to do, heating is already going off")
                return

            case _:
                raise ValueError(f"In {self.name}, we didn't expect to see a state of {self.state} when heat was cancelled")



def pause(time_s):
    enddy=time.time()+time_s
    while time.time()<enddy:
        time.sleep(1)



if __name__=="__main__":
    heat=HeatingSM()
    heat.start()
    pause(6)
    heat.heat_please()
    pause(6)
    heat.heat_off_please()
    pause(6)

    heat.stop()