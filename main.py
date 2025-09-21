import logging
if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG)


from flask import Flask, request

import sys_state as ss



app=Flask(__name__)


@app.route("/")
def index():
    return f"Heating currently: {ss.heating}"

@app.route("/heat_on")
def heat_on():
    ss.heating.heat_please()
    return "Heating going on now"

@app.route("/heat_off")
def heat_off():
    ss.heating.heat_off_please()
    return "Heating going off now"









if __name__=="__main__":

    app.run(host="0.0.0.0",port=8181)