from time import sleep
import sys
import logging

import Ice

from icehms import Holon, run_holon

class TestHolon(Holon):
    def __init__(self, name, logLevel=logging.INFO):
        Holon.__init__(self, name, logLevel=logLevel)
    def run(self):
        self.logger.info("I am "+ self.name)
        while not self._stopev:
            listprx = self._icemgr.find_holons("::mymodule::KHolon")
            tmp = self._icemgr.find_holons("::hms::myproject::CustomHolon")
            listprx += tmp
            if listprx:
                for prx in listprx:
                    try:
                        self.logger.info( "Calling %s of type %s custom method which returns: %s", prx.get_name(), prx.ice_id(), prx.customMethod() )
                        self.logger.info(prx)
                    except Ice.Exception as why:
                        self.logger.info("Exception while querying proxy: %s", why)
            else:
                self.logger.info("No KHolon found")
            sleep(1)


if __name__ == "__main__":

    holon = TestHolon("MyServerHolon")
    run_holon(holon)
 

