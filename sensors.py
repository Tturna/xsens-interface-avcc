# https://dearpygui.readthedocs.io/en/latest/
import dearpygui.dearpygui as dpg
from librosa.feature.spectral import mfcc
import numpy as np

def dancers(number_of_dancers=3, number_of_sensors=3):
    """dancers creates a list of dictionary of dictionaries for 
    sensor data of each Biodata Sonata dancer.
    Parameters
    --------------
    number_of_dancers : int
        Number of dancers. Default value is three.
    number_of_sensors : int
        Number of sensors per dancer. Default value is three.
    Returns
    -------
    dancers: list
        A list of dictionaries of dictionaries for sensor data of each dancer.
        Each dancer has a sensor dictionary with a key for every sensor.
        Each value in the dictionary is a sensor data dictionary with a key
        for each data label.
    """

    # These loops could be combined for possibly simpler code. (Tturna 2024.6.17)
    dancers = []

    for dancer_index in range(number_of_dancers):
        dancers.append({})
        for sensor_num in range(1, number_of_sensors + 1):
            dancers[dancer_index][f'snsr_{sensor_num}'] = {}

    labels = ['tot_a', 'b_tot_a', 'rot', 'ori_p', 'ori_r', 'ori_y', 'acc_x', 'acc_y', 'acc_z', 'gyr_x','gyr_y','gyr_z', 'mag_x', 'mag_y', 'mag_z']
    
    # Length of data plots' x-axes is 500, initialise data as zeros.
    for dancer1_idx, dancer1 in enumerate(dancers):
        for i in range(1, number_of_sensors + 1):
            for label in labels:
                dancer1[f'snsr_{i}'][label] = [0] * 500

            #dancer[f'snsr_{i}']['correlation_acc']={}
            #for j in range(1, number_of_sensors+1):
            #    if i!=j:
            #        dancer[f'snsr_{i}']['correlation_acc'][f'snsr_{j}'] = [0] * 500

        for i in range(1, number_of_sensors):
            for j in range(i + 1, number_of_sensors + 1):
                sensor1 = f'snsr_{i}'
                sensor2 = f'snsr_{j}'

                for label in labels:
                    for sens in [sensor1, sensor2]:
                        if f'correlation_{label}' in dancer1[sens]: continue

                        dancer1[sens][f'correlation_{label}'] = {}

                        for jj in range(1, number_of_sensors + 1):
                            dancer1[sens][f'correlation_{label}'][f'snsr_{jj}'] = [0] * 500

                        for dancer2_idx in range(len(dancers)):
                            if dancer2_idx == dancer1_idx: continue
                            dancer1[sens][f'correlation_{label}'][f'dancer_{dancer2_idx + 1}'] = [0] * 500
    return dancers

class Sensors:
    # locations[x][1]: dancers 1, 2 and 3. This seems to be the dancer number. (Tturna 2024.6.16)
    # locations[x][2]: 1 for left, 2 for right, 3 for torso. This is the sensor number I guess.
    locations = {
        '00B4F11A' : ['left', 1, 1], # dancer 1 left etc.
        '00B4F114' : ['right', 1, 2],
        # '00B4F118' : ['right', 1, 2],
        '00B4F115'  : ['torso', 1, 3],
        '00B4F11B'  : ['left', 2, 1],
        '00B4F116'  : ['right', 2, 2],
        '00B4F119'  : ['torso', 2, 3],
        '00B4F11C'  : ['left', 3, 1],
        '00B4F107'  : ['right', 3, 2],
        '00B4F11D'  : ['torso', 3, 3],
        #'00B42D56' : ['left', 2, 1],
        #'00B42D32' : ['right', 2, 2],
        #'00B42D44' : ['torso', 2, 3],
        #'00B42D54' : ['left', 3, 1],
        #'00B42D4E' : ['right', 3, 2],
        #'00B42B48' : ['torso', 3, 3]
    }

    correlation_others_combos = [
        (12, 22)
    ]

    def __init__(self):
        """Parameters
        --------------
        axes : list
            A list of characters for the used axes. Default is 'x', 'y' and 'z'.
        sensors : list
            XdaDevice instance method configure_device appends
            a list of XsDevice pointers to sensors connected to the
            main device.
        locations : dict
            Sensor IDs are the keys and locations are the values.
        labels: list
            List of tuples containing sensor data labels.
        minmax : list
            List of dictionaries with sensor ID and min/max values
            for data scaling.
        dancers : list
            List of dictionaries of dictionaries for each dancers'
            sensor data.
        """
        
        self.axes  = ['x', 'y', 'z']
        self.sensors = None
        self.labels = [
            ('acc','Acceleration'), ('tot_a', 'Total Acceleration'),
            ('ori', 'Orientation'), ('gyr', 'Gyroscope'), 
            ('rot', 'Rate of Turn'), ('mag', 'Magnetometer')
        ]
        self.minmax = [
            {
                'id': None, 'acc_min':[0, 0, 0], 'gyr_min':[0, 0, 0],
                'mag_min':[0, 0, 0], 'ori_min':[0, 0, 0], 'tot_a_min':[0],
                'rot_min':[0], 'acc_max':[1, 1, 1], 'gyr_max':[1, 1, 1],
                'mag_max':[1, 1, 1], 'ori_max':[1, 1, 1], 'tot_a_max':[1],
                'rot_max':[1]
            }
            for _ in range(9)
        ]
        self.dancers = dancers()
        self.nSensors = len(self.dancers[0])
        self.nDancers = len(self.dancers)
    
    def resetOrientations(self):
        for i, sensor in enumerate(self.sensors):
            sensor.resetOrientation(4)

    def set_ids(self):
        """set_ids sets sensor IDs to the dashboard and to
        self.minmax dictionary list used for data scaling.
        """
        
        for i, sensor in enumerate(self.sensors):
            sensor_id = f'{sensor.deviceId()}'        
            w = Sensors.locations[sensor_id][1]
            k = Sensors.locations[sensor_id][2]
            self.minmax[i]['id'] = sensor_id

            for j in range(6):
                dpg.configure_item(
                    f'dncr{w}_snsr{k}_{self.labels[j][0]}',
                    label = f'{sensor_id} {self.labels[j][1]}'
                )
    
    def scale_data(self, sensor_id, data_type, value):
        """scale_data scales sensor data to the unit interval."""
        
        scaled_data = []
        sensor = [
            sensor for sensor in self.minmax if sensor['id'] == sensor_id
        ][0]

        for i, val in enumerate(value):
            minimum = sensor[f'{data_type}_min'][i]
            maximum = sensor[f'{data_type}_max'][i]

            if val < minimum:
                sensor[f'{data_type}_min'][i] = val
            elif val > maximum:
                sensor[f'{data_type}_max'][i] = val

            # Cast numpy.float64 value to Python's native float.
            scaled_data.append(float((val - minimum) / (maximum - minimum)))

        return scaled_data
    
    def send_data(self, sensor_id, data_type, value):
        """send_data sends sensor data and IDS to the dashboard plots."""
        
        s_idx = Sensors.locations[sensor_id][2]
        d_idx = Sensors.locations[sensor_id][1] - 1
        sensor_key = f'snsr_{s_idx}'

        # Set xyz coordinate data to their plots.
        if data_type in ['acc', 'gyr', 'mag']:
            for i, val in enumerate(value):
                data_label = f'{data_type}_{self.axes[i]}'

                self.dancers[d_idx][sensor_key][data_label].append(val)
                cutoff = len(self.dancers[d_idx][sensor_key][data_label]) - 500

                if cutoff > 0:
                    del self.dancers[d_idx][sensor_key][data_label][0]

                dpg.configure_item(
                    f'{data_type}{d_idx}_{s_idx}{self.axes[i]}',
                    y = self.dancers[d_idx][sensor_key][data_label]
                )
        # Set Euler angles data to its plot.
        elif data_type == 'ori':
            self.dancers[d_idx][sensor_key][f'{data_type}_p'].append(value[0])
            self.dancers[d_idx][sensor_key][f'{data_type}_r'].append(value[1])
            self.dancers[d_idx][sensor_key][f'{data_type}_y'].append(value[2])

            for pry in ['p', 'r', 'y']:
                data_label = f'{data_type}_{pry}'
                cutoff = len(self.dancers[d_idx][sensor_key][data_label]) - 500

                if cutoff > 0:
                    del self.dancers[d_idx][sensor_key][data_label][0]

                dpg.configure_item(
                    f'{data_type}{d_idx}_{s_idx}{pry}',
                    y = self.dancers[d_idx][sensor_key][data_label]
                )
        # Set rate of turn data to its plot.
        elif data_type == 'rot':
            self.dancers[d_idx][sensor_key][f'{data_type}'].append(value[0])
            cutoff = len(self.dancers[d_idx][sensor_key][f'{data_type}']) - 500

            if cutoff > 0:
                del self.dancers[d_idx][sensor_key][f'{data_type}'][0]

            dpg.configure_item(
                f'{data_type}{d_idx}_{s_idx}',
                y = self.dancers[d_idx][sensor_key][f'{data_type}']
            )
        # Set total acceleration and binary value data to their plot.
        elif data_type == 'tot_a':
            self.dancers[d_idx][sensor_key][f'{data_type}'].append(value[0])
            self.dancers[d_idx][sensor_key][f'b_{data_type}'].append(value[1])
            cutoff = len(self.dancers[d_idx][sensor_key][f'{data_type}']) - 500

            if cutoff > 0:
                del self.dancers[d_idx][sensor_key][f'{data_type}'][0]

            dpg.configure_item(
                f'{data_type}{d_idx}_{s_idx}',
                y = self.dancers[d_idx][sensor_key][f'{data_type}']
            )

            cutoff = len(self.dancers[d_idx][sensor_key][f'b_{data_type}']) - 500

            if cutoff > 0:
                del self.dancers[d_idx][sensor_key][f'b_{data_type}'][0]

            if self.dancers[d_idx][sensor_key][f'b_{data_type}'] == 0:
                dpg.configure_item(
                    f'b_{data_type}{d_idx}_{s_idx}',
                    y = self.dancers[d_idx][sensor_key][f'b_{data_type}']
                )
            elif self.dancers[d_idx][sensor_key][f'b_{data_type}'] == 1:
                # TODO: Make sure the line below with "dancers.dancers" is not a bug (Tturna 2024.6.16)
                dpg.configure_item(
                   f'b_{data_type}{d_idx}_{s_idx}',
                   y = self.dancers.dancers[d_idx][sensor_key][f'b_{data_type}']
                )

    def calculate_mfcc(self, fs):
        mfccAll = []

        for dancer in self.dancers:
            for i in range(1, self.nSensors + 1):
                sensor1 = f'snsr_{i}'

                for label in dancer[sensor1]:
                    if (label == 'tot_a' or
                        label == 'b_tot_a' or
                        label == 'rot' or
                        ('correlation' in label)):
                        continue

                    lenVec1 = len(dancer[sensor1][label])
                    
                    #if it's an angle measure take the cosine before doing fft to eliminate discontinuity
                    if lenVec1 < 32: continue

                    if 'ori' in label: 
                        cc = mfcc(y = np.cos(2 * np.asarray(dancer[sensor1][label][lenVec1 - 32:lenVec1])),
                                  sr = fs,
                                  n_fft = 32,
                                  n_mfcc = 13)
                    elif 'mag' in label:
                        cc = mfcc(y = np.cos(2 * np.pi * (1.0 + np.asarray(dancer[sensor1][label][lenVec1-32:lenVec1]))),
                                  sr = fs,
                                  n_fft = 32,
                                  n_mfcc = 13)
                    else:
                        cc = mfcc(y = dancer[sensor1][label][lenVec1 - 32:lenVec1],
                                  sr = fs,
                                  n_fft = 32,
                                  n_mfcc = 13)

                    mfccAll.append(np.abs(cc))
        return mfccAll

    def calculate_fft(self):
        fftAll = []

        for dancer in self.dancers:
            for i in range(1, self.nSensors + 1):
                sensor1 = f'snsr_{i}'

                for label in dancer[sensor1]:
                    if (label == 'tot_a' or
                        label == 'b_tot_a' or
                        label == 'rot' or
                        ('correlation' in label)):
                        continue

                    lenVec1 = len(dancer[sensor1][label])
                    
                    #if it's an angle measure take the cosine before doing fft to eliminate discontinuity
                    if lenVec1 < 32: continue

                    if 'ori' in label: 
                        fft = np.fft.rfft(np.cos(2 * np.asarray(dancer[sensor1][label][lenVec1 - 32:lenVec1])))
                    elif 'mag' in label:
                        fft = np.fft.rfft(np.cos(2 * np.pi * (1.0 + np.asarray(dancer[sensor1][label][lenVec1 - 32:lenVec1]))))
                    else:
                        fft = np.fft.rfft(dancer[sensor1][label][lenVec1 - 32:lenVec1])

                    fftAll.append(np.abs(fft))
        return fftAll

    def calculate_correlation_self(self):
        out_correlations = []
        #CORRELATIONS BETWEEN DIFFERENT SENSORS - SAME DANCER
        for dancer in self.dancers:
            for i in range(1, self.nSensors):
                for j in range(i + 1, self.nSensors + 1):                
                    sensor1 = f'snsr_{i}'
                    sensor2 = f'snsr_{j}'
                    
                    for label in dancer[sensor1]:
                        if (label == 'tot_a' or
                            label == 'b_tot_a' or
                            label == 'rot' or
                            ('correlation' in label)):
                            continue
                        
                        lenVec1 = len(dancer[sensor1][label])
                        lenVec2 = len(dancer[sensor2][label])

                        if lenVec1 < 32 or lenVec2 < 32: continue

                        correlation = np.corrcoef(dancer[sensor1][label][lenVec1 - 32:lenVec1],
                                                  dancer[sensor2][label][lenVec2 - 32:lenVec2])
                        corrVal = 0

                        if not (np.isnan(correlation[1][0])):
                            corrVal = correlation[1][0]

                        out_correlations.append([label,corrVal])
                        dancer[sensor1][f'correlation_{label}'][sensor2].append(corrVal)
                        cutoff = len(dancer[sensor1][f'correlation_{label}'][sensor2]) - 500

                        if cutoff> 0:
                            del dancer[sensor1][f'correlation_{label}'][sensor2][0]
        return out_correlations

    def calculate_correlation_others(self):
        out_correlations = []

        for (sensor1_label, sensor2_label) in Sensors.correlation_others_combos:
            if sensor1_label == sensor2_label: continue

            dancer1_idx = round(sensor1_label / 10)
            dancer1 = self.dancers[dancer1_idx - 1]
            sensor1_idx = sensor1_label % 10
            sensor1 = f'snsr_{sensor1_idx}'

            dancer2_idx = round(sensor2_label / 10)
            dancer2 = self.dancers[dancer2_idx - 1]
            sensor2_idx = sensor2_label % 10
            sensor2 = f'snsr_{sensor2_idx}'

            for label in dancer1[sensor1]:
                if (label == 'tot_a' or
                    label == 'b_tot_a' or
                    label == 'rot' or
                    ('correlation' in label)):
                    continue
                
                lenVec1 = len(dancer1[sensor1][label])
                lenVec2 = len(dancer2[sensor2][label])

                if lenVec1 < 32 or lenVec2 < 32: continue

                correlation = np.corrcoef(dancer1[sensor1][label][lenVec1 - 32:lenVec1],
                                            dancer2[sensor2][label][lenVec2 - 32:lenVec2])
                
                corrVal = 0
                if not (np.isnan(correlation[1][0])):
                    corrVal = correlation[1][0]

                out_correlations.append([label,corrVal])
                dancer1[sensor1][f'correlation_{label}'][f'dancer_{dancer2_idx + 1}'].append(corrVal)
                cutoff = len(dancer1[sensor1][f'correlation_{label}'][f'dancer_{dancer2_idx + 1}']) - 500

                if cutoff> 0:
                    del dancer1[sensor1][f'correlation_{label}'][f'dancer_{dancer2_idx + 1}'][0]
        return out_correlations

    def status(self, ids=False, finished=False):
        """status sets and checks the measurement status of
        the sensors.
        """
        
        for i, sensor in enumerate(self.sensors):
            if ids:
                dpg.set_value(f'snsr_id{i}', f'{sensor.deviceId()}')
            if finished:
                dpg.set_value(f'sensor_{i}', 'Finished')
            elif not sensor.isMeasuring():
                dpg.set_value(f'sensor_{i}', 'Error!')
            else:
                dpg.set_value(f'sensor_{i}', 'Measuring')

def plot_log(file_path, dancers, axes):
    """plot_log plots a txt log file from the dashboard file dialog.
    One line in the txt log file written by XdaDevice class
    method recording_loop contains the data from a single
    data packet sent by a sensor.
    """
    
    locations = Sensors.locations
    
    # TODO: Surely this doesn't have to be so hard coded. (Tturna 2024.6.16)
    with open(file_path, 'r') as log_handle:
        sensor_id = None
        for line in log_handle.readlines():
            split = line.split()

            if split[0] == '11:':
                sensor_id = '00B4F115'
            elif split[0] == '12:':
                sensor_id = '00B4F116'
            elif split[0] == '13:':
                sensor_id = '00B4F11D'
            elif split[0] == '21:':
                sensor_id = '00B42D56'
            elif split[0] == '22:':
                sensor_id = '00B42D32'
            elif split[0] == '23:':
                sensor_id = '00B42D44'
            elif split[0] == '31:':
                sensor_id = '00B42D54'
            elif split[0] == '32:':
                sensor_id = '00B42D4E'
            elif split[0] == '33:':
                sensor_id = '00B42B48'

            split = line.split(': ')
            acc_value = [float(val) for val in split[1:4]]
            tot_a_value = [float(split[4]), 0]
            gyr_value = [float(val) for val in split[5:8]]
            rot_value = [float(split[8])]
            mag_value = [float(val) for val in split[9:12]]
            euler_value = [float(val) for val in split[12:15]]

            send_log_data(sensor_id, 'acc', acc_value, dancers, locations, axes)
            send_log_data(sensor_id, 'tot_a', tot_a_value, dancers, locations, axes)
            send_log_data(sensor_id, 'gyr', gyr_value, dancers, locations, axes)
            send_log_data(sensor_id, 'rot', rot_value, dancers, locations, axes)
            send_log_data(sensor_id, 'mag', mag_value, dancers, locations, axes)
            send_log_data(sensor_id, 'ori', euler_value, dancers, locations, axes)
            
def send_log_data(sensor_id, data_type, value, dancers, locations, axes):
    """send_log_data sends sensor data from a logfile to the dashboard
    plots.
    """    
    
    s_idx = locations[sensor_id][2]
    d_idx = locations[sensor_id][1] - 1    
    sensor_key = f'snsr_{s_idx}'

    # Set xyz coordinate data to their plots.
    if data_type in ['acc', 'gyr', 'mag']:
        for i, val in enumerate(value):
            data_label = f'{data_type}_{axes[i]}'
            dancers[d_idx][sensor_key][data_label].append(val)
            cutoff = len(dancers[d_idx][sensor_key][data_label]) - 500

            if  cutoff > 0:
                del dancers[d_idx][sensor_key][data_label][0]

            dpg.configure_item(
                f'{data_type}{d_idx}_{s_idx}{axes[i]}',
                y = dancers[d_idx][sensor_key][data_label]
            )
    # Set Euler angles data to its plot.
    elif data_type == 'ori':
        dancers[d_idx][sensor_key][f'{data_type}_p'].append(value[0])
        dancers[d_idx][sensor_key][f'{data_type}_r'].append(value[1])
        dancers[d_idx][sensor_key][f'{data_type}_y'].append(value[2])
        data_label = f'{data_type}_{pry}'

        for pry in ['p', 'r', 'y']:
            cutoff = len(dancers[d_idx][sensor_key][data_label]) - 500

            if cutoff > 0:
                del dancers[d_idx][sensor_key][data_label][0]

            dpg.configure_item(
                f'{data_type}{d_idx}_{s_idx}{pry}',
                y = dancers[d_idx][sensor_key][data_label]
            )
    # Set rate of turn data to its plot.
    elif data_type == 'rot':
        dancers[d_idx][sensor_key][f'{data_type}'].append(value[0])
        cutoff = len(dancers[d_idx][sensor_key][f'{data_type}']) - 500

        if cutoff > 0:
            del dancers[d_idx][sensor_key][f'{data_type}'][0]

        dpg.configure_item(
            f'{data_type}{d_idx}_{s_idx}',
            y = dancers[d_idx][sensor_key][f'{data_type}']
        )
    # Set total acceleration and binary value data to their plot.
    elif data_type == 'tot_a':
        dancers[d_idx][sensor_key][f'{data_type}'].append(value[0])
        dancers[d_idx][sensor_key][f'b_{data_type}'].append(value[1])
        cutoff = len(dancers[d_idx][sensor_key][f'{data_type}']) - 500

        if cutoff > 0:
            del dancers[d_idx][sensor_key][f'{data_type}'][0]

        dpg.configure_item(
            f'{data_type}{d_idx}_{s_idx}',
            y = dancers[d_idx][sensor_key][f'{data_type}']
        )
        cutoff = len(dancers[d_idx][sensor_key][f'b_{data_type}']) - 500

        if cutoff > 0:
            del dancers[d_idx][sensor_key][f'b_{data_type}'][0]

        if dancers[d_idx][sensor_key][f'b_{data_type}'] == 0:
            dpg.configure_item(
                f'b_{data_type}{d_idx}_{s_idx}',
                y = dancers[d_idx][sensor_key][f'b_{data_type}']
            )
        elif dancers[d_idx][sensor_key][f'b_{data_type}'] == 1:
            dpg.configure_item(
               f'b_{data_type}{d_idx}_{s_idx}',
               y = dancers[d_idx][sensor_key][f'b_{data_type}']
            )