from PyQt5 import QtCore, QtWidgets, QtNetwork
from qasync import QEventLoop, asyncSlot
from datetime import datetime

from client_ui import ClientUi
import pr_pb2 as pr

import pickle
import asyncio


class Client(QtWidgets.QMainWindow, ClientUi):
    def __init__(self, loop: QEventLoop):
        super().__init__()

        self.setup_ui(self)

        self.setObjectName("Client")
        self.resize(800, 530)

        self.socket = QtNetwork.QTcpSocket()

        self.requests_group.buttonClicked.connect(self.change_connection_type)
        self.connect_btn.clicked.connect(self.connect_to_server)
        self.disconnect_btn.clicked.connect(self.socket.disconnectFromHost)
        self.save_log_btn.clicked.connect(self.save_log)

        self.socket.connected.connect(self.handle_connection)
        self.socket.error.connect(self.handle_error)
        self.socket.disconnected.connect(self.handle_disconnection)
        self.socket.readyRead.connect(self.read_from_server)

        self.loop = loop

        self._connection_try = 0
        self._max_connection_tries = 4
        self._errors_to_reconnect = [-1, 0, 1, 2, 7]

    def save_log(self):
        filename = QtWidgets.QFileDialog(self).getSaveFileName()
        if filename[0] != '':
            with open(filename[0], 'w', encoding="utf-8") as file:
                file.write(self.log.toPlainText())

    def _read_proto_message(self) -> pr.WrapperMessage:
        message = pr.WrapperMessage()
        ms_size = int.from_bytes(self.socket.read(4), "littel")
        message.ParseFromString(self.socket.read(ms_size))
        message.ParseFromString(pickle.loads(self.socket.read(1000)))
        return message

    def change_connection_type(self):
        if self.requests_group.checkedButton().objectName() == "req_for_slow":
            self.request_timeout.setHidden(True)
            self.server_sleep_time.setHidden(False)
            self.reqtimeout_label.setText("Server sleep time")
        else:
            self.server_sleep_time.setHidden(True)
            self.request_timeout.setHidden(False)
            self.reqtimeout_label.setText("Request timeout")

    def change_input_state(self, state: bool):
        self.connect_btn.setEnabled(state)
        self.ip.setEnabled(state)
        self.port.setEnabled(state)
        self.request_timeout.setEnabled(state)
        self.server_sleep_time.setEnabled(state)
        self.reconnection_timeout.setEnabled(state)
        self.req_for_fast.setEnabled(state)
        self.req_for_slow.setEnabled(state)
        self.save_log_btn.setEnabled(state)

    def connect_to_server(self):
        if self.ip.text().count(".") != 3 or self.ip.text()[-1] == '.':
            QtWidgets.QMessageBox.warning(self, "Wrong input", "Enter right IP-address")
        elif 0 < len(self.port.text()) < 4:
            QtWidgets.QMessageBox.warning(self, "Wrong input", "Enter right port")
        else:
            port = self.port.text()
            if port == '':
                port = self.port.placeholderText()

            self.socket.connectToHost(
                self.ip.text(),
                int(port),
                QtCore.QIODevice.ReadWrite,
                QtNetwork.QAbstractSocket.IPv4Protocol
            )
            self._connection_try += 1

            self.log.append(f"Connection attempt {self._connection_try}...")
            self.change_input_state(False)

    async def wait_disconnection(self):
        while self.socket.state() == 3:
            await asyncio.sleep(0.1)

    def handle_connection(self):
        self._connection_try = 0

        port = self.port.text()
        if port == '':
            port = self.port.placeholderText()

        self.log.append(f"{datetime.now()}: Connected to {self.ip.text()}:{port}")
        self.connect_btn.setHidden(True)
        self.disconnect_btn.setHidden(False)
        self.send_to_server()

    @asyncSlot()
    async def handle_error(self):
        if self.socket.error() in self._errors_to_reconnect and self._connection_try < self._max_connection_tries:
            reconnection_timeout = self.reconnection_timeout.text()
            if reconnection_timeout == '':
                reconnection_timeout = 2000

            await self.wait_disconnection()
            self.connect_to_server()
        else:
            self.log.append(f"ERROR {self.socket.errorString()}")
            self.connect_btn.setHidden(False)
            self.disconnect_btn.setHidden(True)
            self.change_input_state(True)
            self._connection_try = 0

    def handle_disconnection(self):
        self.log.append(f"{datetime.now()}: Disconnected from {self.ip.text()}:{self.port.text()}")
        self.connect_btn.setHidden(False)
        self.disconnect_btn.setHidden(True)
        self.change_input_state(True)

    def send_to_server(self):
        if self.socket.state() == QtNetwork.QAbstractSocket.SocketState.ConnectedState:
            message = pr.WrapperMessage()

            if self.requests_group.checkedButton().objectName() == "req_for_fast":
                message.request_for_fast_response.SetInParent()
            else:
                if self.server_sleep_time.text() != "":
                    message.request_for_slow_response.time_in_seconds_to_sleep = int(self.server_sleep_time.text())
                else:
                    message.request_for_slow_response.time_in_seconds_to_sleep = 2

            self.socket.write(pickle.dumps(message.SerializeToString()))
            self.log.append(f"{datetime.now()}: Message sent")

    @asyncSlot()
    async def read_from_server(self):
        message = self._read_proto_message()
        if message.fast_response.current_date_time == "":
            data = message.slow_response.connected_client_count
        else:
            data = message.fast_response.current_date_time
        self.log.append(f"Received message: {data}")
        if self.requests_group.checkedButton().objectName() == "req_for_fast":
            if self.request_timeout.text() != "":
                await asyncio.sleep(int(self.request_timeout.text()) / 1000, self.loop)
            else:
                await asyncio.sleep(2, self.loop)
        self.send_to_server()
