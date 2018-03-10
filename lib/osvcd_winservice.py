"""

 Author: Alex Baker
 Date: 7th July 2008
 Description : Simple python program to generate wrap as a service based on example on the web, see link below.

 http://essiene.blogspot.com/2005/04/python-windows-services.html

 Usage : python aservice.py install
 Usage : python aservice.py start
 Usage : python aservice.py stop
 Usage : python aservice.py remove

 C:\>python aservice.py  --username <username> --password <PASSWORD> --startup auto install

"""

import win32service
import win32serviceutil
import win32api
import win32con
import win32event
import win32evtlogutil
import os
import servicemanager
import sys

from osvcd import Daemon

class OsvcAgent(win32serviceutil.ServiceFramework):

    _svc_name_ = "OsvcAgent"
    _svc_display_name_ = "OpenSVC agent"
    _svc_description_ = "Orchestration, HA, inventoring, monitoring, config mgmt"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        sys.stop_agent = True
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        os.chdir(os.path.join(os.path.dirname(__file__), ".."))
        daemon = Daemon()

        while True:
            # Wait for service stop signal, if I timeout, loop again
            rc = win32event.WaitForSingleObject(self.hWaitStop, 5000)
            # Check to see if self.hWaitStop happened
            if rc == win32event.WAIT_OBJECT_0:
                # Stop signal encountered
                servicemanager.LogInfoMsg("%s - STOPPED"%self._svc_name_)
                daemon.stop()
                break
            else:
                #servicemanager.LogInfoMsg("%s - ALIVE"%self._svc_name_)
                daemon.loop()
                pass

def ctrlHandler(ctrlType):
    return True

if __name__ == '__main__':
    win32api.SetConsoleCtrlHandler(ctrlHandler, True)
    win32serviceutil.HandleCommandLine(OsvcAgent)

