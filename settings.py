

URL_TO_FETCH_SYSTEM_STATE="http://192.168.1.125/systemstate"

HOT_WATER_SHUTDOWN_TEMPERATURE=64

HOT_WATER_OFF_TEMPERATURE=47 # if it's above this the hot water will stop heating
HOT_WATER_ON_TEMPERATURE=45 # If it falls below this the hot water will heat
if HOT_WATER_OFF_TEMPERATURE-HOT_WATER_ON_TEMPERATURE<1.9:
    raise ValueError(f"{HOT_WATER_OFF_TEMPERATURE=} must always be 2degC above {HOT_WATER_ON_TEMPERATURE} for stability")



SERVER_STATE_FETCH_INTERVAL_S=100

FAKE_WAIT_FOR_VALVE_TIME_S=10