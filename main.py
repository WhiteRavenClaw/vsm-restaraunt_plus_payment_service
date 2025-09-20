import logging

import uvicorn

from vsm_restaurant.web import app

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(threadName)s [%(name)s] %(levelname)-8s %(message)s")
    uvicorn.run(app, host="0.0.0.0")
