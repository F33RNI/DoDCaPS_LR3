"""
This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain. We make this dedication for the benefit
of the public at large and to the detriment of our heirs and
successors. We intend this dedication to be an overt act of
relinquishment in perpetuity of all present and future rights to this
software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <https://unlicense.org>
"""

import math
import os
import sys
import threading
import time

import pyqtgraph as pg
from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem


def rotate2d(pos, rad):
    """
    Rotates point on angle
    :param pos: point
    :param rad: angle in radians
    :return:
    """
    x, y = pos
    s, c = math.sin(rad), math.cos(rad)
    return x * c - y * s, y * c + x * s


def ard_map(value, in_min, in_max, out_min, out_max):
    """
    Arduino's map function
    :return:
    """
    return out_min + (out_max - out_min) * ((value - in_min) / (in_max - in_min))


class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__()
        # Load GUI file
        uic.loadUi('LR3.ui', self)

        # System variables
        self.dump_file = None
        self.reader_running = False
        self.packets = []
        self.manual_timer = QtCore.QTimer()
        self.manual_timer.timeout.connect(self.manual_send)
        self.oscilloscope_timer = QtCore.QTimer()
        self.oscilloscope_timer.timeout.connect(self.oscilloscope)
        self.oscilloscope_timer.start(100)
        self.plot_timer = QtCore.QTimer()
        self.plot_timer.timeout.connect(self.update_plot_and_combos)
        self.plot_timer.start(500)

        # Connect GUI controls
        self.btn_load_data.clicked.connect(self.load_data)
        self.btn_stop_reading.clicked.connect(self.stop_reading)
        self.btn_add_row.clicked.connect(self.add_row)
        self.btn_remove_row.clicked.connect(self.remove_row)
        self.btn_send_start.clicked.connect(self.send_start)
        self.btn_send_stop.clicked.connect(self.send_stop)

        # Initialize table
        self.init_tables()

        # Initialize pyQtGraph charts
        self.init_charts()

        # Show GUI
        self.show()

    def init_tables(self):
        """
        Initializes table of packets and setup table (whitelist table)
        :return:
        """
        self.points_table.setColumnCount(5)
        self.points_table.verticalHeader().setVisible(False)
        self.points_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.points_table.setHorizontalHeaderItem(0, QtWidgets.QTableWidgetItem('Packet'))
        self.points_table.setHorizontalHeaderItem(1, QtWidgets.QTableWidgetItem('Time'))
        self.points_table.setHorizontalHeaderItem(2, QtWidgets.QTableWidgetItem('Src'))
        self.points_table.setHorizontalHeaderItem(3, QtWidgets.QTableWidgetItem('Dst'))
        self.points_table.setHorizontalHeaderItem(4, QtWidgets.QTableWidgetItem('Data'))
        header = self.points_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)

        self.setup_table.setColumnCount(2)
        self.setup_table.verticalHeader().setVisible(False)
        self.setup_table.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        self.setup_table.setHorizontalHeaderItem(0, QtWidgets.QTableWidgetItem('Source'))
        self.setup_table.setHorizontalHeaderItem(1, QtWidgets.QTableWidgetItem('Destination'))
        header = self.setup_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        self.setup_table.insertRow(0)
        self.setup_table.setItem(0, 0, QTableWidgetItem('*'))
        self.setup_table.setItem(0, 1, QTableWidgetItem('*'))

    def init_charts(self):
        """
        Initializes charts
        :return:
        """
        self.graphWidget.setBackground((255, 255, 255))
        # self.gui.graphWidget.getAxis('left').setPen(QtGui.QColor('black'))
        # self.gui.graphWidget.getAxis('left').setTextPen(QtGui.QColor('black'))
        # self.gui.graphWidget.getAxis('bottom').setPen(QtGui.QColor('black'))
        # self.gui.graphWidget.getAxis('bottom').setTextPen(QtGui.QColor('black'))
        self.graphWidget.getPlotItem().hideAxis('top')
        self.graphWidget.getPlotItem().hideAxis('left')
        self.graphWidget.getPlotItem().hideAxis('right')
        self.graphWidget.getPlotItem().hideAxis('bottom')
        self.graphWidget.showGrid(x=False, y=False, alpha=1.0)

        self.graphWidget_2.setBackground((255, 255, 255))
        self.graphWidget_2.showGrid(x=True, y=True, alpha=1.0)
        self.graphWidget_3.setBackground((255, 255, 255))
        self.graphWidget_3.showGrid(x=True, y=True, alpha=1.0)
        self.graphWidget_4.setBackground((255, 255, 255))
        self.graphWidget_4.showGrid(x=True, y=True, alpha=1.0)
        self.graphWidget_5.setBackground((255, 255, 255))
        self.graphWidget_5.showGrid(x=True, y=True, alpha=1.0)

    def add_row(self):
        """
        Adds row to the setup table
        :return:
        """
        row_number = self.setup_table.rowCount()
        self.setup_table.insertRow(row_number)
        self.setup_table.setItem(row_number, 0, QTableWidgetItem('00'))
        self.setup_table.setItem(row_number, 1, QTableWidgetItem('00'))

    # noinspection PyBroadException
    def remove_row(self):
        """
        Removes row from the setup table
        :return:
        """
        selected_items = self.setup_table.selectedItems()
        for selected_item in selected_items:
            try:
                self.setup_table.removeRow(self.setup_table.row(selected_item))
            except:
                pass

    def send_start(self):
        """
        Start timer for sending manual packets
        :return:
        """
        self.btn_send_start.setEnabled(False)
        self.btn_send_stop.setEnabled(True)
        self.manual_timer.start(self.spin_send_period.value())

    def send_stop(self):
        """
        Stops timer for sending manual packets
        :return:
        """
        self.btn_send_start.setEnabled(True)
        self.btn_send_stop.setEnabled(False)
        self.manual_timer.stop()

    def load_data(self):
        """
        Loads dump file
        :return:
        """
        if not self.reader_running:
            if os.path.exists(self.data_file.text()):
                print('Loading data...')
                self.dump_file = open(self.data_file.text(), 'rb')
                self.reader_running = True
                thread = threading.Thread(target=self.dump_reader)
                thread.start()
            else:
                print('File', self.data_file.text(), 'doesn\'t exist!')

    def stop_reading(self):
        """
        Stops reading data from dump file
        :return:
        """
        self.reader_running = False
        self.dump_file.close()

    def manual_send(self):
        """
        Sends sequence of packets defined on the form
        :return:
        """
        packet_time = 0
        if len(self.packets) > 0:
            packet_time = self.packets[len(self.packets) - 1][0] + self.spin_send_period.value()
        self.proceed_packet(packet_time, bytes.fromhex(self.line_send_src.text()),
                            bytes.fromhex(self.line_send_dst.text()), bytes.fromhex(self.line_send_data.text()))

    def dump_reader(self):
        """
        Reads dump from file
        :return:
        """
        # Clear table and data arrays
        # self.points_table.setRowCount(0)
        self.packets = []

        # Create temp buffers
        bytes_buffer = [b'\x00'] * 19
        bytes_buffer_position = 0
        previous_byte = b'\x00'
        packets_read = 0

        # Continue reading
        while self.reader_running:
            incoming_byte = self.dump_file.read(1)
            if incoming_byte is None or len(incoming_byte) == 0:
                self.reader_running = False
            else:
                bytes_buffer[bytes_buffer_position] = incoming_byte
                if bytes_buffer[bytes_buffer_position] == b'\xff' and previous_byte == b'\xff':
                    bytes_buffer_position = 0

                    packet_time = int.from_bytes(b''.join([bytes_buffer[1], bytes_buffer[0]]),
                                                 byteorder='big', signed=False)
                    source = bytes_buffer[6]
                    destination = bytes_buffer[7]
                    data = bytes_buffer[9]

                    self.proceed_packet(packet_time, source, destination, data)

                    packets_len = len(self.packets)
                    if packets_len > 1:
                        time_to_sleep = self.packets[packets_len - 1][0] - self.packets[packets_len - 2][0]
                        if time_to_sleep < 10:
                            time_to_sleep = 10
                        time.sleep(time_to_sleep / 1000)

                    packets_read += 1
                else:
                    previous_byte = bytes_buffer[bytes_buffer_position]
                    bytes_buffer_position += 1
                    if bytes_buffer_position >= 19:
                        bytes_buffer_position = 0

        self.dump_file.close()
        print('File reading stopped. Read', packets_read, 'packets')

    def proceed_packet(self, packet_time, source, destination, data):
        """
        Handles packet and adds it to the self.points_table and table according to the whitelist table
        :param packet_time: time mark of the packet
        :param source: source address
        :param destination: destination address
        :param data: payload
        :return:
        """
        # Create whitelists
        allowed_sources = []
        allowed_destinations = []
        for i in range(self.setup_table.rowCount()):
            allowed_sources.append(str(self.setup_table.item(i, 0).text()).lower())
            allowed_destinations.append(str(self.setup_table.item(i, 1).text()).lower())

        # Check is packet is allowed
        if (str(source.hex()).lower() in allowed_sources or '*' in allowed_sources) \
                and (str(destination.hex()).lower() in allowed_destinations or '*' in allowed_destinations):
            # Add packet to the list
            self.packets.append([packet_time, source, destination, data])

            # Add packet to the table
            position = self.points_table.rowCount()
            self.points_table.insertRow(position)
            self.points_table.setItem(position, 0, QTableWidgetItem(str(position)))
            self.points_table.setItem(position, 1, QTableWidgetItem(str(packet_time)))
            self.points_table.setItem(position, 2, QTableWidgetItem(str(source.hex())))
            self.points_table.setItem(position, 3, QTableWidgetItem(str(destination.hex())))
            self.points_table.setItem(position, 4, QTableWidgetItem(str(data.hex())))

    def oscilloscope(self):
        """
        Shows last 20 packets on the plots
        :return:
        """
        # Count packets and Initialize arrays
        packets_len = len(self.packets)
        points_x = [[], [], [], []]
        points_y = [[], [], [], []]
        if packets_len > 0:
            # Clear plots
            self.graphWidget_2.clear()
            self.graphWidget_3.clear()
            self.graphWidget_4.clear()
            self.graphWidget_5.clear()

            # Start position
            packets_position = packets_len - 1

            # Plot last 20 points
            while packets_position > 0 and (len(points_y[0]) < 20
                                            or len(points_y[1]) < 20
                                            or len(points_y[2]) < 20
                                            or len(points_y[3]) < 20):

                # Get channel source and destination from combobox
                ch1 = str(self.combo_ch1.currentText()).split('->')
                ch2 = str(self.combo_ch2.currentText()).split('->')
                ch3 = str(self.combo_ch3.currentText()).split('->')
                ch4 = str(self.combo_ch4.currentText()).split('->')

                if ch1[0] == self.packets[packets_position][1].hex() \
                        and ch1[1] == self.packets[packets_position][2].hex() and len(points_y[0]) < 20:
                    points_x[0].append(int(self.packets[packets_position][0]))
                    points_y[0].append(int(self.packets[packets_position][3].hex(), 16))

                if ch2[0] == self.packets[packets_position][1].hex() \
                        and ch2[1] == self.packets[packets_position][2].hex() and len(points_y[1]) < 20:
                    points_x[1].append(int(self.packets[packets_position][0]))
                    points_y[1].append(int(self.packets[packets_position][3].hex(), 16))

                if ch3[0] == self.packets[packets_position][1].hex() \
                        and ch3[1] == self.packets[packets_position][2].hex() and len(points_y[2]) < 20:
                    points_x[2].append(int(self.packets[packets_position][0]))
                    points_y[2].append(int(self.packets[packets_position][3].hex(), 16))

                if ch4[0] == self.packets[packets_position][1].hex() \
                        and ch4[1] == self.packets[packets_position][2].hex() and len(points_y[3]) < 20:
                    points_x[3].append(int(self.packets[packets_position][0]))
                    points_y[3].append(int(self.packets[packets_position][3].hex(), 16))

                packets_position -= 1

            # Draw plots
            self.graphWidget_2.plot(points_x[0], points_y[0], pen=pg.mkPen((255, 127, 0)),
                                    symbolBrush=(255, 127, 0), symbolSize=5)
            self.graphWidget_3.plot(points_x[1], points_y[1], pen=pg.mkPen((255, 127, 0)),
                                    symbolBrush=(255, 127, 0), symbolSize=5)
            self.graphWidget_4.plot(points_x[2], points_y[2], pen=pg.mkPen((255, 127, 0)),
                                    symbolBrush=(255, 127, 0), symbolSize=5)
            self.graphWidget_5.plot(points_x[3], points_y[3], pen=pg.mkPen((255, 127, 0)),
                                    symbolBrush=(255, 127, 0), symbolSize=5)

    def update_plot_and_combos(self):
        """
        Updates nodes plot and combo boxes
        :return:
        """
        # Create text lists of nodes and links
        nodes_text = []
        links_text = []
        for i in range(self.points_table.rowCount()):
            src = self.points_table.item(i, 2).text()
            dst = self.points_table.item(i, 3).text()
            links_text.append([src, dst])
            if src not in nodes_text:
                nodes_text.append(src)
            if dst not in nodes_text:
                nodes_text.append(dst)

        # Add links to comboBoxes
        for link_text in links_text:
            text_row = link_text[0] + '->' + link_text[1]
            if self.combo_ch1.findText(text_row) < 0:
                self.combo_ch1.addItem(text_row)
                self.combo_ch2.addItem(text_row)
                self.combo_ch3.addItem(text_row)
                self.combo_ch4.addItem(text_row)

        # Draw nodes with text and links
        if len(links_text) > 0:
            self.graphWidget.clear()
            nodes = []
            for i in range(len(nodes_text)):
                rotated = rotate2d((1, 1), math.radians(ard_map(i, 0, len(nodes_text), 0, 360)))
                nodes.append([rotated[0], rotated[1]])
                label = pg.TextItem(text=nodes_text[i], fill=(255, 245, 162), color=(0, 0, 0))
                label.setPos(rotated[0], rotated[1])
                self.graphWidget.addItem(label)

            links = []
            for i in range(len(nodes)):
                for k in range(len(nodes)):
                    if k != i:
                        link = [nodes[i], nodes[k]]
                        if link not in links and link[::-1] not in links and \
                                ([nodes_text[i], nodes_text[k]] in links_text
                                 or [nodes_text[k], nodes_text[i]] in links_text):
                            links.append(link)
            for link in links:
                self.graphWidget.plot([link[0][0], link[1][0]], [link[0][1], link[1][1]], pen=pg.mkPen((0, 255, 0)),
                                      symbolBrush=(255, 0, 0), symbolSize=5)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('fusion')
    win = Window()
    sys.exit(app.exec_())
