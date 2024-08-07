# A class for an Xsens main device and attached sensors.
import sys
from math import sqrt
from io import StringIO
from pathlib import Path
from time import time, sleep
from datetime import datetime
# from scipy.spatial.transform import Rotation as _rot
import numpy as np
import os.path

# Xsens Device API documentation provided with SDK download:
# https://www.movella.com/support/software-documentation
import xsensdeviceapi as xda
# https://osc4py3.readthedocs.io/en/latest/
from osc4py3 import oscbuildparse
from osc4py3.as_eventloop import osc_process, osc_send, osc_terminate

import sensors as ss
import xda_callback as xc
from utils import log

class XdaDevice():
    """XdaDevice class for Xsens Dongle or Xsens Station. Class
    objects contain all the necessary attributes for handling live
    data recording.
    """
    
    def __init__(self, main_device, log_path, threshold=30):
        """Parameters
        --------------
        main_device : str
            'dongle' or 'station'
        log_path : str
            File path for saving log files.
        threshold : int
            Default 30 m/s**2 threshold for total acceleration 'hit'.
        Attributes
        ------------
        control : XsControl pointer
            create_control_object sets a poitner to an XsControl
            object.
        port : XsPortInfoArray
            open_device mehtod sets an XsPortInfoArray object.
        main_device : XsDevice pointer
            open_device sets a pointer to an XsDevice object.
        callback : XsCallback
            XsCallback object for handling incoming sensor data.
        channel : int
            Hardcoded 11 for Biodata Sonata. Available channels
            are 11,12,13, ..., 23, 24 and 25. See the documents.
        update_rate : int
            Hardcoded 100 for Biodata Sonata. Recommended
            wireless update rates are
            60Hz for 11 - 20 MTw sensors
            80Hz for     10    MTw sensors
            100Hz for   6 - 9   MTw sensors and
            120Hz for   1 - 5   MTw sensors.
        sensors : Sensor
            Sensor object for using Sensor class send_data
            and status functions.
        log_path : str
            File path for saving log files.
        serial : str
            main_device parameter defines serial: 'dongle' sets serial to
            'AW-DNG2' and 'station' sets serial to ' AW-A2'.
        recording : Bool
            A Boolean representing the recording status of the device.
        acc_threshold : int
            Default is 30 m/s**2 for a total acceleration 'hit'.
        """
        
        self.control = None
        self.port = None
        self.device = None
        self.callback = None
        self.channel= 11 # 11 for Biodata Sonate
        self.update_rate = 60 # 100 for Biodata Sonate
        self.sensors = ss.Sensors()
        self.log_path = log_path

        if main_device == 'dongle':
            self.serial = 'AW-DNG2'
        elif main_device == 'station':
            self.serial = 'AW-A2'
        else:
            self.serial == 'unknown device'

        self.recording = False
        self.acc_threshold = threshold
        self.saveLog = False #Toggle recording data to log
        self.resetOri = False
        
    def create_control_object(self):
        """create_control_object creates an XsControl object for
        the main device and prints out the Xsens Device API
        version if successful.
        """
        
        log('program_status', 'Creating an XsControl object...', append = False)
        self.control = xda.XsControl()
        xdaVersion = xda.XsVersion()
        xda.xdaVersion(xdaVersion)

        if self.control == 0: return

        log('program_status', 'XsControl object created successfully.\n' +
            f'Xsens Device API version: {xdaVersion.toXsString()}')
    
    def open_device(self):
        """open_device finds the main device, opens the port it is
        connected to, sets the device to the XsControl object and
        sets a callback handler to it as well as sets the device to
        self.device while printing information about the steps
        to terminal and the dashboard.
        """
        
        log('program_status', 'Scanning for ports with Xsens devices...')
        self.port = xda.XsScanner_scanPorts()

        if len(self.port) > 0:
            for port in self.port:
                log('program_status', 'The following port with a connected Xsens device was found:')
                log('program_status', f'{port.portName()} with baud rate {port.baudrate()} Bd' +
                    f'and device ID {port.deviceId()}')
        else:
            log('program_status', 'No Xsens device found. Aborting\n')
            sys.exit(1)

        log('program_status', 'Checking the type of the connected Xsens device...')
        
        for port in self.port:
            if self.serial == 'AW-DNG2':
                if port.deviceId().isAwinda2Dongle():
                    log('program_status', f'Device {port.deviceId()} is of type {self.serial}')
                else:
                    log('program_status', f'{self.serial} device not found. Aborting.\n')
                    sys.exit(1)

            elif self.serial == 'AW-A2':
                if port.deviceId().isAwinda2Station():
                    log('program_status', f'Device {port.deviceId()} is of type {self.serial}')
                else:
                    log('program_status', f'{self.serial} device not found. Aborting.\n')
                    sys.exit(1)

        log('program_status', 'Opening device port...\n')

        for port in self.port:
            if not self.control.openPort(port.portName(), port.baudrate()):
                log('program_status', 'Unable to open device port. Aborting.\n')
                sys.exit(1)

            self.device = self.control.device(port.deviceId())
            log('program_status', f'Port {port.portName()} for {self.serial} {port.deviceId().toXsString()} opened')

        try:
            self.callback = xc.XdaCallback()
            self.device.addCallbackHandler(self.callback)
        except Exception as e:
            log('program_status', 'Callback handler setup failed. Aborting\n')
            sys.exit(1)
    
    def configure_device(self):
        """configure_device sets the device to configuration mode,
        enables device radio, sets device live data recording
        options and counts the connected sensors as well as sets
        the sensor IDs to the dashboard sensor status panel, while
        printing information about all the steps to the dashboard
        and terminal.
        """
        
        try:
            self.device.gotoConfig()
        except Exception as e:
            log('program_status', f'{e}. {self.serial} {self.device.deviceId()} ' +
                'Failed to go to config mode. Aborting.\n')
            sys.exit(1)

        self.device.enableRadio(self.channel)
        self.device.setOptions(xda.XSO_Orientation, xda.XSO_None)

        log('program_status', f'{self.serial} {self.device.deviceId()}' +
            f' update rate set to {self.update_rate} Hz and radio' +
            f' enabled on channel {self.channel}\n')

        log('program_status', f'Connecting the sensors to {self.serial} {self.device.deviceId()}...\n')

        # Wait for 5 seconds for the sensors to connect.
        sleep(5)
        log('program_status', f'{self.device.childCount()} sensors' +
            f' connected to {self.serial} {self.device.deviceId()}')

        try:
            self.sensors.sensors = self.device.children()
        except Exception as e:
            log('program_status', f'{e} Failed to set sensors connected to {self.serial}' +
                f' {self.device.deviceId()} to XdaDevice instance sensor list. Aborting.\n')
            self.device.disableRadio()
            sys.exit(1)

        try:
            self.sensors.status(ids=True)
        except Exception as e:
            log('program_status',
                f'{e} Failed to set sensor ids to the dashboard sensor status panel. Aborting.\n')
            self.device.disableRadio()
            sys.exit(1)

        try:
            self.sensors.set_ids()
        except Exception as e:
            log('program_status', f'{e} Failed to set sensor ids to the scaling dictionary. Aborting.\n')
            self.device.disableRadio()
            sys.exit(1)        
    
    def go_to_recording_mode(self):
        """go_to_recording_mode sets the device and connected
        sensors to measurement mode, confirms that the sensors
        are in measurement mode and creates an mtb log file for
        MTManager. XDA library function startRecording() does not
        work without an mtb log file. However, the mtb log file
        remains empty of data, unless by some miracle it works on
        your machine. Finally, go_to_recording_mode attempts to
        start recording with the main device. Information about
        all the steps is printed to the dashboard and terminal.
        """
        
        try:
            self.device.gotoMeasurement()
        except Exception as e:
            log('program_status', f'Failed to set {self.serial}' +
                f' {self.device.deviceId()} to measurement mode. Aborting.\n')
            self.device.disableRadio()
            sys.exit(1)

        for sensor in self.device.children():
            if not sensor.isMeasuring(): continue
            log('program_status', f'Sensor {sensor.deviceId()} connected' +
                f' to {self.serial} {self.device.deviceId()} set to measurement mode\n')

        log('program_status', f'Creating a log file for {self.serial}' +
            f' {self.device.deviceId()} and starting recording...\n')

        logPath = str(Path(f'{self.log_path}\{self.device.deviceId()}_log.mtb'))

        if (not os.path.exists(self.log_path)):
            log('program_status', f'Creating a log directory for {self.serial}' +
                f' {self.device.deviceId()} at {logPath}')
            
            os.mkdir(self.log_path)

        if self.device.createLogFile(logPath) != xda.XRV_OK:
            log('program_status', 'Failed to create a log file for' +
                f' {self.serial} {self.device.deviceId()}. Aborting.\n')
            self.device.disableRadio()
            sys.exit(1)

        try:
            self.device.startRecording()
            log('program_status', f'{self.serial} {self.device.deviceId()} is' +
                ' recording from the connected sensors')
        except Exception as e:
            log('program_status', f'{e}. {self.serial} {self.device.deviceId()}' +
                ' failed to start recording. Aborting.\n')
            self.device.disableRadio()
            sys.exit(1)

        log('program_status', 'Use the "Recording on/off" button to stop')
    
    def recording_loop(self, timeout=0.2):
        """recording_loop takes care of live data recording and
        sending it to dashboard plots as well as to Open Sound
        Control environment. It also creates a txt log file and
        checks status of the sensors connected to the main
        device. The function prints information about all the
        steps to the dashboard and terminal.
        Parameters
        --------------
        timeout : float
            Number of seconds before next possible registration of a
            threshold surpassing total acceleration value.
        """
        
        timer = 0
        data_out = StringIO()
        samplingRate = -1
        lastTime = -1
        #last_valid_value = [[0 for x in range(3)] for y in range(self.sensors.nSensors)]
        #last_output_value = [[0 for x in range(3)] for y in range(self.sensors.nSensors)]
        #interpolation_start = [[0 for x in range(3)] for y in range(self.sensors.nSensors)]
        #delta = [[0 for x in range(3)] for y in range(self.sensors.nSensors)]
        #deltaOut = [[0 for x in range(3)] for y in range(self.sensors.nSensors)]
        #north_gimbal_lock = [False for y in range(self.sensors.nSensors)]
        #south_gimbal_lock = [False for y in range(self.sensors.nSensors)]
        #interpolation_active = [False for y in range(self.sensors.nSensors)]
        #interpolation_timer = [0 for y in range(self.sensors.nSensors)]
        

        while self.recording:
            # osc_msg = [self.sensors.nDancers]
            # message = oscbuildparse.OSCMessage('/xsens-nDancers', None, osc_msg)           
            # osc_send(message, 'OSC_client')

            # try: osc_process()      
            # except AttributeError: print("osc packet skipped")

            # osc_msg = [self.sensors.nSensors]
            # message = oscbuildparse.OSCMessage('/xsens-nSensors', None, osc_msg)           
            # osc_send(message, 'OSC_client')

            # try: osc_process()      
            # except AttributeError: print("osc packet skipped")

            osc_msg = []

            if self.resetOri:
                self.sensors.resetOrientations()
                self.resetOri = False

            if self.callback.packet_available():
                packet = self.callback.get_next_packet()
                 
                if packet.containsStoredDeviceId():
                    sensor_id = f'{packet.deviceId()}'
                    # Set ID for OSC and txt log as xy whre x is dancer 
                    # number and y is sensor number: 1 for left, 2 for 
                    # right and 3 for torso.
                    dancer = self.sensors.locations[sensor_id][1]
                    sensor = self.sensors.locations[sensor_id][2]
                    osc_id = dancer * 10 + sensor
                    osc_msg.append(osc_id)

                if packet.containsCalibratedData():
                    acc = packet.freeAcceleration() / 100.0
                    acc_value = acc
                    acc_value = [round(val, 5) for val in acc_value]
                    tot_acc = [sqrt(acc[0]**2 + acc[1]**2 + acc[2]**2)]
                    check_threshold = tot_acc[0] > self.acc_threshold

                    if check_threshold and time() - timer > self.acc_threshold:
                        tot_acc.append(1)
                        timer = time()
                    else:
                        tot_acc.append(0)

                    osc_msg.append(float(acc_value[0]))
                    osc_msg.append(float(acc_value[1]))
                    osc_msg.append(float(acc_value[2]))
                    osc_msg.append(float(round(tot_acc[0], 5)))
                    osc_msg.append(float(tot_acc[1]))
                    self.sensors.send_data(sensor_id, 'acc', acc_value)
                    self.sensors.send_data(sensor_id, 'tot_a', tot_acc)

                    gyr = packet.calibratedGyroscopeData()
                    gyr_value = [gyr[0], gyr[1], gyr[2]]
                    rot_value = self.sensors.scale_data(sensor_id, 'rot',
                        [sqrt(gyr[0]**2 + gyr[1]**2 + gyr[2]**2)]
                    )

                    gyr_value = [round(val, 5) for val in gyr_value]
                    osc_msg.append(float(gyr_value[0]))
                    osc_msg.append(float(gyr_value[1]))
                    osc_msg.append(float(gyr_value[2]))
                    osc_msg.append(float(round(rot_value[0], 5)))
                    self.sensors.send_data(sensor_id, 'gyr', gyr_value)
                    self.sensors.send_data(sensor_id, 'rot', rot_value)

                    mag = packet.calibratedMagneticField()
                    mag_value = mag 
                    osc_msg.append(float(round(mag_value[0], 5)))
                    osc_msg.append(float(round(mag_value[1], 5)))
                    osc_msg.append(float(round(mag_value[2], 5)))
                    self.sensors.send_data(sensor_id, 'mag', mag_value)

                if packet.containsOrientation():
                    euler = packet.orientationEuler()
                    
                    #2pi ,pi ,2pi
                    euler_value = [
                        np.pi * float(euler.x()) / 180.0 + 1.0,
                        np.pi * float(euler.y()) / 180.0,
                        np.pi * float(euler.z()) / 180.0 + 1.0
                    ]
                                
                    q1 = packet.orientationQuaternion()
                    #repack quaternion in our reference frame
                    q1 = [
                        float(q1[0]),
                        -float(q1[1]),
                        float(q1[3]),
                        float(q1[2])
                    ]
                   
                    osc_msg.append(float(euler_value[0]+np.pi))
                    osc_msg.append(float(euler_value[1]+np.pi))
                    osc_msg.append(float(euler_value[2]+np.pi))
                    
                    osc_msg.append(float(q1[0]))
                    osc_msg.append(float(q1[1]))
                    osc_msg.append(float(q1[2]))
                    osc_msg.append(float(q1[3]))
                   
                    self.sensors.send_data(sensor_id, 'ori',
                        [(euler_value[0]), (euler_value[1]), (euler_value[2])]
                    )

                message = oscbuildparse.OSCMessage(f'/xsens{dancer}{sensor}', None, osc_msg)
                osc_send(message, 'OSC_client')

                try: osc_process()      
                except AttributeError: print("osc packet skipped")

                if self.saveLog:
                    # Write data to a line in data_out.
                    osc_str = [f'{elem}: ' for elem in osc_msg]
                    for index, val in enumerate(osc_str):
                        data_out.write(osc_str[index])
                    data_out.write('\n')   

                if sensor == 1 and dancer == 1:
                    '''
                    dT = -1
                    localTime = time.time()
                    if lastTime>0:
                        dT = localTime - lastTime
                    lastTime = localTime

                    if dT>0:
                        osc_msg = []
                        mfccs = self.sensors.calculate_mfcc(1.0/dT)

                        for mfcc_ in mfccs:
                            for val in mfcc_:
                                osc_msg.append(round(float(val),5))

                        message = oscbuildparse.OSCMessage('/xsens-mfcc', None, osc_msg)                             
                        osc_send(message, 'OSC_client')

                        try: osc_process()      
                        except AttributeError: print("osc packet skipped")
                    '''
                    
                    # CORRELATIONS

                    # osc_msg = []
                    # correlations = self.sensors.calculate_correlation_self()

                    # for corr_value in correlations:
                    #     osc_msg.append(round(float(corr_value[1]), 5))       

                    # message = oscbuildparse.OSCMessage(f'/xsens{dancer}{sensor}-correlation-self', None, osc_msg)
                    # osc_send(message, 'OSC_client')

                    # try: osc_process()      
                    # except AttributeError: print("osc packet skipped")

                    # FFT

                    # osc_msg = []
                    # osc_msg_fft_stats = []
                    # ffts = self.sensors.calculate_fft()
                   
                    # for fft in ffts:
                    #     for val in fft:
                    #         osc_msg.append(round(float(val),5))       

                    #     idxMax =  1 + np.argmax(fft[1:])
                    #     energyAtIdx = fft[idxMax]

                    #     if (energyAtIdx < 0.35):
                    #         idxMax = 0

                    #     #assemble for statistics
                    #     totalEnergy = abs(fft[1:].sum())
                        
                    #     if totalEnergy > 0.999 and energyAtIdx > 0.35:
                    #         stats = []
                    #         for i, bin in enumerate(fft[1:]):
                    #             stats.extend( [i+1] * int(bin * 10) )
                                
                    #         if len(stats) > 0 and idxMax > 0:
                    #             osc_msg_fft_stats.append(round(float(np.std(stats) / len(fft)), 5))
                    #         else:
                    #             osc_msg_fft_stats.append(round(float(0), 5))
                            
                    #         osc_msg_fft_stats.append(round(float(idxMax) / len(fft), 5))
                    #     else:
                    #         osc_msg_fft_stats.append(round(float(0), 5))
                    #         osc_msg_fft_stats.append(round(float(0), 5))

                    # message = oscbuildparse.OSCMessage('/xsens-fft', None, osc_msg)
                    # osc_send(message, 'OSC_client')

                    # try: osc_process()      
                    # except AttributeError: print("osc packet skipped")

                    # message = oscbuildparse.OSCMessage('/xsens-fft-stats', None, osc_msg_fft_stats)                           
                    # osc_send(message, 'OSC_client')

                    # try: osc_process()      
                    # except AttributeError: print("osc packet skipped")

                    # CORRELATIONS OTHERS

                    osc_msg = []
                    correlations = self.sensors.calculate_correlation_others()

                    for corr_value in correlations:
                        osc_msg.append(round(float(corr_value[1]), 5))       

                    message = oscbuildparse.OSCMessage(f'/xsens{dancer}{sensor}-correlation-others', None, osc_msg)
                    osc_send(message, 'OSC_client')

                    try: osc_process()      
                    except AttributeError: print("osc packet skipped")

            # Check sensor status and set it to the dashboard.
            self.sensors.status(self.sensors.sensors)
            
        # Recording stopped from the dashboard button.
        osc_terminate()
        self.sensors.status(self.sensors.sensors, finished=True)
        
        if self.saveLog:
            log_file = Path(f'{self.log_path}\{datetime.now().strftime("%d.%m.%Y-%H.%M.%S")}.txt')
            log_data = data_out.getvalue()

            with open(log_file, 'w') as log_handle:
                log_handle.write(log_data)

            log('program_status', f'Data from the recording was written to {log_file}')

        # Try to stop recording.
        log('program_status', f'Closing {self.serial} {self.device.deviceId()}...')
        
        try:
            self.device.stopRecording()
            log('program_status', f'{self.serial} {self.device.deviceId()} recording stopped...')
        except Exception as e:
            log('program_status', f'{e}. Failed to stop {self.serial}' +
                f' {self.device.deviceId()} recording. Aborting.\n')
            self.device.disableRadio()
            sys.exit(1)

        # Try to close the mtb log file required by startRecording().
        if not self.device.closeLogFile():
            log('program_status', f'Failed to close {self.serial}' +
                f' {self.device.deviceId()} log file. Aborting.\n')
            self.device.disableRadio()
            sys.exit(1)

        log('program_status', '... and log file closed.')
        
        # Try to remove the callback handler from the main device.
        try:
            self.device.clearCallbackHandlers()
            log('program_status', f'{self.serial} {self.device.deviceId()} callback handler removed')
        except Exception as e:
            log('program_status', f'{e}. Failed to remove callback handler' +
                f' from {self.serial} {self.device.deviceId()}. Aborting\n')
            self.device.disableRadio()
            sys.exit(1)

        # Try to close the radio, port and XsControl object.
        try:
            self.device.disableRadio()
            log('program_status', f'{self.serial} {self.device.deviceId()} radio disabled')
            log('program_status', 'All devices closed. Closing the ports...')
            
            for port in self.port:
                self.control.closePort(port.portName())
                log('program_status', f'Port {port.portName()} closed')

            log('program_status', 'All ports closed. Closing the XsControl object...')
            self.control.close()
            log('program_status', 'XsControl object closed')
        except Exception as e:
            log('program_status', f'{e}. Aborting.\n')
            self.device.disableRadio()
            sys.exit(1)

        # Succesful exit.
        log('program_status', 'Successful exit. Ready for restart\n')