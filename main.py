import logging
if __name__=="__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format="%(asctime)s [%(threadName)s] %(levelname)s %(name)s: %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")


from flask import Flask, request

import simpler

main_state=simpler.MainState()
main_state.start()


app=Flask(__name__)


@app.route("/")
def index():
    # returns the state string as a text/plain response
    response=app.response_class(
        response=str(main_state),
        status=200,
        mimetype="text/plain"
    )
    return response











if __name__=="__main__":


    app.run(host="0.0.0.0",port=8181)