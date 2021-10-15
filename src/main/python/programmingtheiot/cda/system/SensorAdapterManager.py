#####
# 
# This class is part of the Programming the Internet of Things project.
# 
# It is provided as a simple shell to guide the student and assist with
# implementation for the Programming the Internet of Things exercises,
# and designed to be modified by the student as needed.
#

import logging

from importlib import import_module

from apscheduler.schedulers.background import BackgroundScheduler

import programmingtheiot.common.ConfigConst as ConfigConst

from programmingtheiot.common.ConfigUtil import ConfigUtil
from programmingtheiot.common.IDataMessageListener import IDataMessageListener

from programmingtheiot.cda.sim.SensorDataGenerator import SensorDataGenerator
from programmingtheiot.cda.sim.HumiditySensorSimTask import HumiditySensorSimTask
from programmingtheiot.cda.sim.TemperatureSensorSimTask import TemperatureSensorSimTask
from programmingtheiot.cda.sim.PressureSensorSimTask import PressureSensorSimTask


class SensorAdapterManager(object):
    """
	Shell representation of class for student implementation.

	"""

    # SensorAdapterManager Constructor
    def __init__(self, useEmulator=False):
        configUtil = ConfigUtil()

        # set default pollRate
        self.pollRate = configUtil.getInteger( section=ConfigConst.CONSTRAINED_DEVICE, key=ConfigConst.POLL_CYCLES_KEY,defaultVal=ConfigConst.DEFAULT_POLL_CYCLES)

        # set default useEmulator
        if not useEmulator:
            self.useEmulator = configUtil.getBoolean(section=ConfigConst.CONSTRAINED_DEVICE,
                    key=ConfigConst.ENABLE_EMULATOR_KEY)
        else:
            self.useEmulator = useEmulator

        # set default locationID
        self.locationID = configUtil.getProperty(  section=ConfigConst.CONSTRAINED_DEVICE, key=ConfigConst.DEVICE_LOCATION_ID_KEY, defaultVal=ConfigConst.NOT_SET)

        # check if pollRate is valid
        if self.pollRate <= 0:
            self.pollRate = ConfigConst.DEFAULT_POLL_CYCLES

        # set scheduler job
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job( self.handleTelemetry, 'interval', seconds=self.pollRate)

        self.dataMsgListener = None

        if self.useEmulator:
            logging.info("Emulators will be used!")

            # load the temperature sensor emulator (you can use either `import_module()` as shown, or `__import__()`)
            tempModule = import_module('programmingtheiot.cda.emulated.TemperatureSensorEmulatorTask',
                                       'TemperatureSensorEmulatorTask')
            teClazz = getattr(tempModule, 'TemperatureSensorEmulatorTask')
            self.tempAdapter = teClazz()

            # load the pressure sensor emulator (you can use either `import_module()` as shown, or `__import__()`)
            pressureModule = import_module('programmingtheiot.cda.emulated.PressureSensorEmulatorTask',
                                           'PressureSensorEmulatorTask')
            prClazz = getattr(pressureModule, 'PressureSensorEmulatorTask')
            self.pressureAdapter = prClazz()

            # load the humidity sensor emulator (you can use either `import_module()` as shown, or `__import__()`)
            humidityModule = import_module('programmingtheiot.cda.emulated.HumiditySensorEmulatorTask',
                                           'HumiditySensorEmulatorTask')
            hmClazz = getattr(humidityModule, 'HumiditySensorEmulatorTask')
            self.humidityAdapter = hmClazz()
        else:
            self.dataGenerator = SensorDataGenerator()

            # set temperature data
            tempFloor = configUtil.getFloat( section=ConfigConst.CONSTRAINED_DEVICE, key=ConfigConst.TEMP_SIM_FLOOR_KEY, defaultVal= SensorDataGenerator.LOW_NORMAL_INDOOR_TEMP)

            tempCeiling = configUtil.getFloat(
                    section=ConfigConst.CONSTRAINED_DEVICE,
                    key=ConfigConst.TEMP_SIM_CEILING_KEY,
                    defaultVal= SensorDataGenerator.HI_NORMAL_INDOOR_TEMP)

            tempData = self.dataGenerator.generateDailyIndoorTemperatureDataSet(
                    minValue=tempFloor,
                    maxValue=tempCeiling,
                    useSeconds=False)

            self.tempAdapter = TemperatureSensorSimTask(dataSet=tempData)

            # set pressure data
            pressureFloor =configUtil.getFloat(
                    section=ConfigConst.CONSTRAINED_DEVICE,
                    key=ConfigConst.PRESSURE_SIM_FLOOR_KEY,
                    defaultVal=SensorDataGenerator.LOW_NORMAL_ENV_PRESSURE)

            pressureCeiling = configUtil.getFloat(
                    section=ConfigConst.CONSTRAINED_DEVICE,
                    key=ConfigConst.PRESSURE_SIM_CEILING_KEY,
                    defaultVal= SensorDataGenerator.HI_NORMAL_ENV_PRESSURE)

            pressureData = self.dataGenerator.generateDailyEnvironmentPressureDataSet(
                    minValue=pressureFloor,
                    maxValue=pressureCeiling,
                    useSeconds=False)

            self.pressureAdapter = PressureSensorSimTask(dataSet=pressureData)

            # set humidity data
            humidityFloor = configUtil.getFloat(
                    section=ConfigConst.CONSTRAINED_DEVICE,
                    key=ConfigConst.HUMIDITY_SIM_FLOOR_KEY,
                    defaultVal= SensorDataGenerator.LOW_NORMAL_ENV_HUMIDITY)

            humidityCeiling = configUtil.getFloat(
                    section=ConfigConst.CONSTRAINED_DEVICE,
                    key=ConfigConst.HUMIDITY_SIM_CEILING_KEY,
                    defaultVal=SensorDataGenerator.HI_NORMAL_ENV_HUMIDITY)

            humidityData = self.dataGenerator.generateDailyEnvironmentHumidityDataSet(minValue=humidityFloor,maxValue=humidityCeiling,useSeconds=False)

            self.humidityAdapter = HumiditySensorSimTask(dataSet=humidityData)

    # handle telemetry data
    def handleTelemetry(self):
        humidityData = self.humidityAdapter.generateTelemetry()
        pressureData = self.pressureAdapter.generateTelemetry()
        tempData = self.tempAdapter.generateTelemetry()

        humidityData.setLocationID(self.locationID)
        pressureData.setLocationID(self.locationID)
        tempData.setLocationID(self.locationID)

        logging.info('Generated humidity data: ' + str(humidityData))
        logging.info('Generated pressure data: ' + str(pressureData))
        logging.info('Generated temp data: ' + str(tempData))

        if self.dataMsgListener:
            self.dataMsgListener.handleSensorMessage(humidityData)
            self.dataMsgListener.handleSensorMessage(pressureData)
            self.dataMsgListener.handleSensorMessage(tempData)

    # set listener
    def setDataMessageListener(self, listener: IDataMessageListener) -> bool:
        if listener:
            self.dataMsgListener = listener

    # start manager
    def startManager(self):
        logging.info('Started SensorAdapterManager.')

        if not self.scheduler.running:
            self.scheduler.start()
        else:
            logging.warning( 'SensorAdapterManager scheduler already started.')

    # stop manager
    def stopManager(self):
        logging.info('Stopped SensorAdapterManager.')

        try:
            self.scheduler.shutdown()
        except:
            logging.warning( 'SensorAdapterManager scheduler already stopped.')
