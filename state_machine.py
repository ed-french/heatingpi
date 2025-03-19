import logging
if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)
import threading
import time


class StateMachine(threading.Thread):
    def __init__(self,*,name:str,states:list[str],initial_state:str,subscribers:list[callable],interval_s=0.4):
        """
            name is the name of the statemachine thread - very useful for debugging
            states is a list of strings representing all the valid state names
            initial_state must be a valid string state name from the list
            subscribers is a list of callables, these receive three parameters:
                subscriber(state_machine=self,new_state=new_state,reason=reason,type="STATE_CHANGE")
                or type="TIMEOUT" if it's called because the state exceeded its timeout


        
        """
        super().__init__()
        self.name=name
        self.valid_states=states
        self._state=initial_state
        self.subscribers=subscribers
        self.initial_state:str=initial_state
        self.last_change_reason:str=""
        self.last_change_time:int=0
        self.stop_requested=False
        self.stopped=False
        self.interval_s=interval_s
        self.timeout_set=False
        self.timeout_time=0
        self.previous_state="undefined"

        self.set_state(new_state=initial_state,reason="")

        
    @property
    def state(self):
        return self._state


    
    def set_state(self,*,new_state:str,reason:str="",timeout_s:float=-1):
        """
            new_state must be a valid state name string
            reason, just a string that's available to see why the last state change happened, useful for debugging
            timeout_s if this is set to 1s or more, then, if the state hasn't changed again and
            that timeout is reached all the subscribers will get called with a "timeout" event

        """


        # tell subscribers
        if new_state not in self.valid_states:
            raise ValueError(f"New state of {new_state} for {self.name} because of {reason} is not one of the allowed states: {self.valid_states}")
        
        # Deal with the timeouts
        if timeout_s>0.99: # timeouts must be greater than 1 to count!
            self.timeout_time=time.time()+timeout_s
            self.timeout_set=True
        else:
            self.timeout_set=False

        self.previous_state=self.state
        self._state=new_state
        self.last_change_reason=reason
        for subscriber in self.subscribers:
            subscriber(state_machine=self,new_state=new_state,reason=reason,type="STATE_CHANGE")
        self.last_change_time=time.time()
        logging.info(f"{self.name} from >>>>> {self.previous_state} >>>>>> {self.state} because {reason}")


        
    def stop(self):
        self.stop_requested=True
        logging.debug(f"{self.name}->stop requested")
        end_time=time.time()+10 # Wait 10 seconds
        while time.time()<end_time:
            time.sleep(1)
            if self.stopped:
                logging.debug(f"{self.name}->stopped cleanly")
                return # stopped cleanly

        raise Exception(f"Failed to stop {self.name} 10 seconds after stop requested")

    def step(self):
        logging.error(f"State machine {self.name} failed to implement a 'step' method, so nothing happens each loop!")


    def run(self):
        while not self.stop_requested:
            self.step() # This is the overridden method called every interval
            if self.timeout_set and time.time()>self.timeout_time:
                for subscriber in self.subscribers:
                    subscriber(state_machine=self,new_state=self.state,reason="timeout",type="TIMEOUT")
                self.timeout_set=False

            time.sleep(self.interval_s)
        self.stopped=True


if __name__=="__main__":

    def timeout_noticer(*,state_machine:StateMachine,new_state:str,reason:str,type:str):
        logging.info(f"NOTICED EVENT:{state_machine=}, {new_state=}, {reason=}, {type=}")
        

    testsm=StateMachine(name="bob",states=["off","on"],initial_state="off",subscribers=[timeout_noticer])
    testsm.start()
    end_at=time.time()+5
    while time.time()<end_at:
        time.sleep(0.2)

    testsm.set_state(new_state="on",reason="5 seconds done",timeout_s=2)

    end_at=time.time()+5
    while time.time()<end_at:
        time.sleep(0.2)
    testsm.stop()

