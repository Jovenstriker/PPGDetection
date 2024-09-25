import threading
import serial
from datetime import datetime
import csv
from collections import deque
import time
import os
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import matplotlib.widgets as widgets

max_len = 200

class SerialPlotter:
    def __init__(self, port, baudrate=115200, max_len=max_len, plot_interval=1, csv_filename=None):
        self.ser = serial.Serial(port=port, baudrate=baudrate)
        self.max_len = max_len
        self.plot_interval = plot_interval
        self.csv_filename = csv_filename

        self._animation = None 

        # Initialize containers
        self.timestamps = deque(maxlen=self.max_len)
        self.adc1 = deque(maxlen=self.max_len)
        self.adc2 = deque(maxlen=self.max_len)
        self._last_timestamp = 0
        self._last_adc1 = 0
        self._last_adc2 = 0
        self._isChannel1 = True
        self.time_start = time.time()

        # Initialize plots
        self._fig, (self._ax1, self._ax2) = plt.subplots(ncols=1, nrows=2)
        self._line1, = self._ax1.plot(self.timestamps, self.adc1)
        self._line2, = self._ax2.plot(self.timestamps, self.adc2)
        self._ax1.set_title('ADC')
        self._ax2.set_xlabel('Time (s)')
        self._ax1.set_ylabel('ADC (a. u.)')
        self._ax2.set_ylabel('ADC (a. u.)')
        
        # Start background thread for reading data from serial port
        self._serial_thread = threading.Thread(target=self._read_serial)
        self._stop_event = threading.Event()
        
        # Initialize a button for stopping the data acquisition
        self._stop_button_ax = self._fig.add_axes([0.85, 0.025, 0.1, 0.04])
        self._stop_button = widgets.Button(self._stop_button_ax, 'Stop')
        self._stop_button.on_clicked(self._on_stop_button_clicked)
                
        # Data writing 
        if self.csv_filename:
            self.csvfile = open(self.csv_filename, 'a', newline='')
            self.csv_writer = csv.writer(self.csvfile)
        
    def start(self):
        # background thread
        self._serial_thread.start()

        # start animation
        self._animation = FuncAnimation(self._fig, self._update_plots, interval=self.plot_interval, cache_frame_data=False)
        
    def stop(self):
        self._stop_event.set()
        self._serial_thread.join()
        if self.csvfile:
            self.csvfile.close()
        
    def _read_serial(self):
        buffer = []
        while not self._stop_event.is_set():
            # Read data from serial port
            try:
                serial_byte = self.ser.readline()
                serial_line = serial_byte.decode('utf-8').strip()
            except UnicodeDecodeError:
                continue
            except ValueError:
                continue
            
            values = serial_line.split(',')  # Split the line by comma
            if len(values) != 2:
                continue

            value1, value2 = values
            try:
                value1 = int(value1)
                value2 = int(value2)
            except ValueError:
                continue  # Skip this iteration if conversion fails

            self._last_adc1 = value1
            self.adc1.append(self._last_adc1)

            self._last_adc2 = value2
            self.adc2.append(self._last_adc2)

            self._last_timestamp = time.time() - self.time_start
            self.timestamps.append(self._last_timestamp)

            # Write to csv
            if self.csv_filename:
                self.csv_writer.writerow([self._last_timestamp, self._last_adc1, self._last_adc2])
                self.csvfile.flush()
            
        # Write remaining data to file
        if buffer:
            self.csv_writer.writerows(buffer)
        if self.csvfile:
            self.csvfile.close()
            
    def _update_plots(self, frame):
        # Check if adc1 and adc2 are empty
        if not self.adc1 or not self.adc2 or len(self.adc1) != len(self.timestamps) or len(self.adc2) != len(self.timestamps):
            return
        
        # Update plot data
        self._line1.set_xdata(self.timestamps)
        self._line1.set_ydata(self.adc1)
        self._line2.set_xdata(self.timestamps)
        self._line2.set_ydata(self.adc2)
        self._ax1.relim()
        self._ax1.autoscale_view()
        self._ax2.relim()
        self._ax2.autoscale_view()
        
        # Set line color
        self._line1.set_color('r')
        self._line2.set_color('b')

        return self._line1, self._line2
    
    def _on_stop_button_clicked(self, event):
        self.stop()
        plt.close(self._fig)

if __name__ == '__main__':
     # Find the correct serial port for your device
    import serial.tools.list_ports
     
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        print(port)

    # Replace the serial port with the correct one for your device
    serial_port = '/dev/cu.usbserial-110'
    
    now = datetime.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')
    hour = now.strftime('%H')
    minute = now.strftime('%M')
    second = now.strftime('%S')

    date = '-'.join([year, month, day])
    filename = '-'.join([hour, minute, second])

    if not os.path.exists(f'CaffeineReadings/6-26Readings/{date}'):  # Use an f-string for formatting
        os.makedirs(f'CaffeineReadings/6-26Readings/{date}')
        print(f'Created folder {date}')

    serial_plotter = SerialPlotter(serial_port, max_len=max_len, csv_filename=f'CaffeineReadings/6-26Readings/{date}/{filename}.txt')  # Use f-string here as well
    serial_plotter.start()
    plt.show(block=True)

    # input('Press Enter to stop...\n')
    serial_plotter.stop() 