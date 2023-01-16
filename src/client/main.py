import sys
import asyncio
from qasync import QEventLoop
from PyQt5 import QtWidgets
from client import Client

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = Client(loop)
    window.show()
    with loop:
        loop.run_forever()
