import json
import logging
import urllib.request

_LOGGER = logging.getLogger(__name__)

URL_POWER_FLOW = "{}://{}/solar_api/v1/GetPowerFlowRealtimeData.fcgi"
URL_SYSTEM_METER = "{}://{}/solar_api/v1/GetMeterRealtimeData.cgi?Scope=System"
URL_SYSTEM_INVERTER = "{}://{}/solar_api/v1/GetInverterRealtimeData.cgi?Scope=System"
URL_DEVICE_METER = "{}://{}/solar_api/v1/GetMeterRealtimeData.cgi?Scope=Device&DeviceId={}"
URL_DEVICE_STORAGE = "{}://{}/solar_api/v1/GetStorageRealtimeData.cgi?Scope=Device&DeviceId={}"
URL_DEVICE_INVERTER_CUMULATIVE = "{}://{}/solar_api/v1/GetInverterRealtimeData.cgi?Scope=Device&DeviceId={}&DataCollection=CumulationInverterData"
URL_DEVICE_INVERTER_COMMON = "{}://{}/solar_api/v1/GetInverterRealtimeData.cgi?Scope=Device&DeviceId={}&DataCollection=CommonInverterData"

class Fronius:
    '''
    Interface to communicate with the Fronius Symo over http / JSON
    Attributes:
        host        The ip/domain of the Fronius device
        useHTTPS    Use HTTPS instead of HTTP
        timeout     HTTP timeout in seconds
    '''
    def __init__(self, host, useHTTPS = False, timeout = 10):
        '''
        Constructor
        '''
        self.host = host
        self.timeout = timeout
        if useHTTPS:
            self.protocol = "https"
        else:
            self.protocol = "http"


    def current_power_flow(self):
        '''
        Get the current power flow of a smart meter system.
        '''
        url = URL_POWER_FLOW.format(self.protocol, self.host)

        _LOGGER.debug("Get current system power flow data for {}".format(url))

        return self._current_data(url, self._system_power_flow)


    def current_system_meter_data(self):
        '''
        Get the current meter data.
        '''
        url = URL_SYSTEM_METER.format(self.protocol, self.host)

        _LOGGER.debug("Get current system meter data for {}".format(url))

        return self._current_data(url, self._system_meter_data)


    def current_system_inverter_data(self):
        '''
        Get the current inverter data.
        The values are provided as cumulated values and for each inverter
        '''
        url = URL_SYSTEM_INVERTER.format(self.protocol, self.host)

        _LOGGER.debug("Get current system inverter data for {}".format(url))

        return self._current_data(url, self._system_inverter_data)


    def current_meter_data(self, device = 0):
        '''
        Get the current meter data for a device.
        '''
        url = URL_DEVICE_METER.format(self.protocol, self.host, device)

        _LOGGER.debug("Get current meter data for {}".format(url))

        return self._current_data(url, self._device_meter_data)


    def current_storage_data(self, device = 0):
        '''
        Get the current storage data for a device.
        '''
        url = URL_DEVICE_STORAGE.format(self.protocol, self.host, device)

        _LOGGER.debug("Get current storage data for {}".format(url))

        return self._current_data(url, self._device_storage_data)


    def current_inverter_data(self, device = 1):
        '''
        Get the current inverter data of one device.
        '''
        url = URL_DEVICE_INVERTER_COMMON.format(self.protocol, self.host, device)

        _LOGGER.debug("Get current inverter data for {}".format(url))

        return self._current_data(url, self._device_inverter_data)


    def _fetch_json(self, url):
        request = urllib.request.urlopen(url)
        return json.loads(request.read().decode())


    def _status_data(self, json):

        sensor = {}

        sensor['timestamp'] = { 'value': json['Head']['Timestamp'] }
        sensor['status'] = json['Head']['Status']
        sensor['status_code'] = { 'value': json['Head']['Status']['Code'] }
        sensor['status_reason'] = { 'value': json['Head']['Status']['Reason'] }
        sensor['status_message'] = { 'value': json['Head']['Status']['UserMessage'] }

        return sensor


    def _current_data(self, url, fun):
        json = self._fetch_json(url)
        sensor = self._status_data(json)

        # break if Data is empty
        if not json['Body'] or not json['Body']['Data']:
            _LOGGER.info("No data returned from {}".format(url))
            return sensor
        else:
            return fun(sensor, json['Body']['Data'])


    def _system_power_flow(self, sensor, data):
        _LOGGER.debug("Converting system power flow data: '{}'".format(data))

        site = data['Site']
        inverter = data['Inverters']['1'] # TODO: implement more inverters
  
        if "Battery_Mode" in inverter:
            sensor['battery_mode'] = { 'value': inverter['Battery_Mode'] }
        if "SOC" in inverter:
            sensor['state_of_charge'] = { 'value': inverter['SOC'], 'unit' :"%" }

        if "BatteryStandby" in site:
            sensor['battery_standby'] = { 'value' : site['BatteryStandby'] }
        if "E_Day" in site:
            sensor['energy_day'] = { 'value': site['E_Day'], 'unit': "Wh" }
        if "E_Total" in site:
            sensor['energy_total'] = { 'value': site['E_Total'], 'unit': "Wh" }
        if "E_Year" in site:
            sensor['energy_year'] = { 'value': site['E_Year'], 'unit': "Wh" }
        if "Meter_Location" in site:
            sensor['meter_location'] = { 'value': site['Meter_Location'] }
        if "Mode" in site:
            sensor['meter_mode'] = { 'value': site['Mode'] }
        if "P_Akku" in site:
            sensor['power_battery'] = { 'value': site['P_Akku'], 'unit': "W" }
        if "P_Grid" in site:
            sensor['power_grid'] = { 'value': site['P_Grid'], 'unit': "W" }
        if "P_Load" in site:
            sensor['power_load'] = { 'value': site['P_Load'], 'unit': "W" }
        if "P_PV" in site:
            sensor['power_photovoltaics'] = { 'value': site['P_PV'], 'unit': "W" }
        if "rel_Autonomy" in site:
            sensor['relative_autonomy'] = { 'value': site['rel_Autonomy'], 'unit': "%" }
        if "rel_SelfConsumption" in site:
            sensor['relative_self_consumption'] = { 'value': site['rel_SelfConsumption'], 'unit': "%" }

        return sensor


    def _system_meter_data(self, sensor, data):
        _LOGGER.debug("Converting system meter data: '{}'".format(data))

        sensor['meters'] = { }

        for i in data:
            sensor['meters'][i] = self._meter_data(data[i])

        return sensor


    def _system_inverter_data(self, sensor, data):
        _LOGGER.debug("Converting system inverter data: '{}'".format(data))

        sensor['energy_day'] = { 'value': 0, 'unit': "Wh" }
        sensor['energy_total'] = { 'value': 0, 'unit': "Wh" }
        sensor['energy_year'] = { 'value': 0, 'unit': "Wh" }
        sensor['power_ac'] = { 'value': 0, 'unit': "W" }

        sensor['inverters'] = {}

        if "DAY_ENERGY" in data:
            for i in data['DAY_ENERGY']['Values']:
                sensor['inverters'][i] = { }
                sensor['inverters'][i]['energy_day'] = { 'value': data['DAY_ENERGY']['Values'][i], 'unit': data['DAY_ENERGY']['Unit'] }
                sensor['energy_day']['value'] += data['DAY_ENERGY']['Values'][i]
        if "TOTAL_ENERGY" in data:
            for i in data['TOTAL_ENERGY']['Values']:
                sensor['inverters'][i]['energy_total'] = { 'value': data['TOTAL_ENERGY']['Values'][i], 'unit': data['TOTAL_ENERGY']['Unit'] }
                sensor['energy_total']['value'] += data['TOTAL_ENERGY']['Values'][i]
        if "YEAR_ENERGY" in data:
            for i in data['YEAR_ENERGY']['Values']:
                sensor['inverters'][i]['energy_year'] = { 'value': data['YEAR_ENERGY']['Values'][i], 'unit': data['TOTAL_ENERGY']['Unit'] }
                sensor['energy_year']['value'] += data['YEAR_ENERGY']['Values'][i]
        if "PAC" in data:
            for i in data['PAC']['Values']:
                sensor['inverters'][i]['power_ac'] = { 'value': data['PAC']['Values'][i], 'unit': data['TOTAL_ENERGY']['Unit'] }
                sensor['power_ac']['value'] += data['PAC']['Values'][i]

        return sensor


    def _device_meter_data(self, sensor, data):
        _LOGGER.debug("Converting meter data: '{}'".format(data))

        sensor.update(self._meter_data(data))

        return sensor


    def _device_storage_data(self, sensor, data):
        _LOGGER.debug("Converting storage data from '{}'".format(data))

        if 'Controller' in data:
            controller = self._controller_data(data['Controller'])
            sensor.update(controller)

        if 'Modules' in data:
            sensor['modules'] = { }
            module_count = 0;

            for module in data['Modules']:
                sensor['modules'][module_count] = self._module_data(module)
                module_count += 1

        return sensor


    def _device_inverter_data(self, sensor, data):
        _LOGGER.debug("Converting inverter data from '{}'".format(data))

        if "DAY_ENERGY" in data:
            sensor['energy_day'] = { 'value': data['DAY_ENERGY']['Value'], 'unit': data['DAY_ENERGY']['Unit'] }
        if "TOTAL_ENERGY" in data:
            sensor['energy_total'] = { 'value': data['TOTAL_ENERGY']['Value'], 'unit': data['TOTAL_ENERGY']['Unit'] }
        if "YEAR_ENERGY" in data:
            sensor['energy_year'] = { 'value': data['YEAR_ENERGY']['Value'], 'unit': data['YEAR_ENERGY']['Unit'] }
        if "FAC" in data:
            sensor['frequency_ac'] = { 'value': data['FAC']['Value'], 'unit': data['FAC']['Unit'] }
        if "IAC" in data:
            sensor['current_ac'] = { 'value': data['IAC']['Value'], 'unit': data['IAC']['Unit'] }
        if "IDC" in data:
            sensor['current_dc'] = { 'value': data['IDC']['Value'], 'unit': data['IDC']['Unit'] }
        if "PAC" in data:
            sensor['power_ac'] = { 'value': data['PAC']['Value'], 'unit': data['PAC']['Unit'] }
        if "UAC" in data:
            sensor['voltage_ac'] = { 'value': data['UAC']['Value'], 'unit': data['UAC']['Unit'] }
        if "UDC" in data:
            sensor['voltage_dc'] = { 'value': data['UDC']['Value'], 'unit': data['UDC']['Unit'] }

        return sensor


    def _meter_data(self, data):

        meter = {}

        if "Current_AC_Phase_1" in data:
            meter['current_ac_phase_1'] = { 'value': data['Current_AC_Phase_1'], 'unit': "A" }
        if "Current_AC_Phase_2" in data:
            meter['current_ac_phase_2'] = { 'value': data['Current_AC_Phase_2'], 'unit': "A" }
        if "Current_AC_Phase_3" in data:
            meter['current_ac_phase_3'] = { 'value': data['Current_AC_Phase_3'], 'unit': "A" }
        if "EnergyReactive_VArAC_Sum_Consumed" in data:
            meter['energy_reactive_ac_consumed'] = { 'value': data['EnergyReactive_VArAC_Sum_Consumed'], 'unit': "Wh" }
        if "EnergyReactive_VArAC_Sum_Produced" in data:
            meter['energy_reactive_ac_produced'] = { 'value': data['EnergyReactive_VArAC_Sum_Produced'], 'unit': "Wh" }
        if "EnergyReal_WAC_Minus_Absolute" in data:
            meter['energy_real_ac_minus'] = { 'value': data['EnergyReal_WAC_Minus_Absolute'], 'unit': "Wh" }
        if "EnergyReal_WAC_Plus_Absolute" in data:
            meter['energy_real_ac_plus'] = { 'value': data['EnergyReal_WAC_Plus_Absolute'], 'unit': "Wh" }
        if "EnergyReal_WAC_Sum_Consumed" in data:
            meter['energy_real_consumed'] = { 'value': data['EnergyReal_WAC_Sum_Consumed'], 'unit': "Wh" }
        if "EnergyReal_WAC_Sum_Produced" in data:
            meter['energy_real_produced'] = { 'value': data['EnergyReal_WAC_Sum_Produced'], 'unit': "Wh" }
        if "Frequency_Phase_Average" in data:
            meter['frequency_phase_average'] = { 'value': data['Frequency_Phase_Average'], 'unit': "Hz" }
        if "PowerApparent_S_Phase_1" in data:
            meter['power_apparent_phase_1'] = { 'value': data['PowerApparent_S_Phase_1'], 'unit': "W" }
        if "PowerApparent_S_Phase_2" in data:
            meter['power_apparent_phase_2'] = { 'value': data['PowerApparent_S_Phase_2'], 'unit': "W" }
        if "PowerApparent_S_Phase_3" in data:
            meter['power_apparent_phase_3'] = { 'value': data['PowerApparent_S_Phase_3'], 'unit': "W" }
        if "PowerApparent_S_Sum" in data:
            meter['power_apparent'] = { 'value': data['PowerApparent_S_Sum'], 'unit': "W" }
        if "PowerFactor_Phase_1" in data:
            meter['power_factor_phase_1'] = { 'value': data['PowerFactor_Phase_1'], 'unit': "W" }
        if "PowerFactor_Phase_2" in data:
            meter['power_factor_phase_2'] = { 'value': data['PowerFactor_Phase_2'], 'unit': "W" }
        if "PowerFactor_Phase_3" in data:
            meter['power_factor_phase_3'] = { 'value': data['PowerFactor_Phase_3'], 'unit': "W" }
        if "PowerFactor_Sum" in data:
            meter['power_factor'] = { 'value': data['PowerFactor_Sum'], 'unit': "W" }
        if "PowerReactive_Q_Phase_1" in data:
            meter['power_reactive_phase_1'] = { 'value': data['PowerReactive_Q_Phase_1'], 'unit': "W" }
        if "PowerReactive_Q_Phase_2" in data:
            meter['power_reactive_phase_2'] = { 'value': data['PowerReactive_Q_Phase_2'], 'unit': "W" }
        if "PowerReactive_Q_Phase_3" in data:
            meter['power_reactive_phase_3'] = { 'value': data['PowerReactive_Q_Phase_3'], 'unit': "W" }
        if "PowerReactive_Q_Sum" in data:
            meter['power_reactive'] = { 'value': data['PowerReactive_Q_Sum'], 'unit': "W" }
        if "PowerReal_P_Phase_1" in data:
            meter['power_real_phase_1'] = { 'value': data['PowerReal_P_Phase_1'], 'unit': "W" }
        if "PowerReal_P_Phase_2" in data:
            meter['power_real_phase_2'] = { 'value': data['PowerReal_P_Phase_2'], 'unit': "W" }
        if "PowerReal_P_Phase_3" in data:
            meter['power_real_phase_3'] = { 'value': data['PowerReal_P_Phase_3'], 'unit': "W" }
        if "PowerReal_P_Sum" in data:
            meter['power_real'] = { 'value': data['PowerReal_P_Sum'], 'unit': "W" }
        if "Voltage_AC_Phase_1" in data:
            meter['voltage_ac_phase_1'] = { 'value': data['Voltage_AC_Phase_1'], 'unit': "V" }
        if "Voltage_AC_Phase_2" in data:
            meter['voltage_ac_phase_2'] = { 'value': data['Voltage_AC_Phase_2'], 'unit': "V" }
        if "Voltage_AC_Phase_3" in data:
            meter['voltage_ac_phase_3'] = { 'value': data['Voltage_AC_Phase_3'], 'unit': "V" }
        if "Voltage_AC_PhaseToPhase_12" in data:
            meter['voltage_ac_phase_to_phase_12'] = { 'value': data['Voltage_AC_PhaseToPhase_12'], 'unit': "V" }
        if "Voltage_AC_PhaseToPhase_23" in data:
            meter['voltage_ac_phase_to_phase_23'] = { 'value': data['Voltage_AC_PhaseToPhase_23'], 'unit': "V" }
        if "Voltage_AC_PhaseToPhase_31" in data:
            meter['voltage_ac_phase_to_phase_31'] = { 'value': data['Voltage_AC_PhaseToPhase_31'], 'unit': "V" }
        if "Meter_Location_Current" in data:
            meter['meter_location'] = { 'value': data['Meter_Location_Current'] }
        if "Enable" in data:
            meter['enable'] = { 'value': data['Enable'] }
        if "Visible" in data:
            meter['visible'] = { 'value': data['Visible'] }
        if "Details" in data:
            meter['manufacturer'] = { 'value': data['Details']['Manufacturer'] }
            meter['model'] = { 'value': data['Details']['Model'] }
            meter['serial'] = { 'value': data['Details']['Serial'] }

        return meter


    def _controller_data(self, data):

        controller = {}

        if "Capacity_Maximum" in data:
            controller['capacity_maximum'] = { 'value': data['Capacity_Maximum'], 'unit': "Ah" }
        if "DesignedCapacity" in data:
            controller['capacity_designed'] = { 'value': data['DesignedCapacity'], 'unit': "Ah" }
        if "Current_DC" in data:
            controller['current_dc'] = { 'value': data['Current_DC'], 'unit': "A" }
        if "Voltage_DC" in data:
            controller['voltage_dc'] = { 'value': data['Voltage_DC'], 'unit': "V" }
        if "Voltage_DC_Maximum_Cell" in data:
            controller['voltage_dc_maximum_cell'] = { 'value': data['Voltage_DC_Maximum_Cell'], 'unit': "V" }
        if "Voltage_DC_Minimum_Cell" in data:
            controller['voltage_dc_minimum_cell'] = { 'value': data['Voltage_DC_Minimum_Cell'], 'unit': "V" }
        if "StateOfCharge_Relative" in data:
            controller['state_of_charge'] = { 'value': data['StateOfCharge_Relative'], 'unit': "%" }
        if "Temperature_Cell" in data:
            controller['temperature_cell'] = { 'value': data['Temperature_Cell'], 'unit': "C" }
        if "Enable" in data:
            controller['enable'] = { 'value': data['Enable'] }
        if "Details" in data:
            controller['manufacturer'] = { 'value': data['Details']['Manufacturer'] }
            controller['model'] = { 'value': data['Details']['Model'] }
            controller['serial'] = { 'value': data['Details']['Serial'] }

        return controller


    def _module_data(self, data):

        module = { }

        if "Capacity_Maximum" in data:
            module['capacity_maximum'] = { 'value': data['Capacity_Maximum'], 'unit': "Ah" }
        if "DesignedCapacity" in data:
            module['capacity_designed'] = { 'value': data['DesignedCapacity'], 'unit': "Ah" }
        if "Current_DC" in data:
            module['current_dc'] = { 'value': data['Current_DC'], 'unit': "A" }
        if "Voltage_DC" in data:
            module['voltage_dc'] = { 'value': data['Voltage_DC'], 'unit': "V" }
        if "Voltage_DC_Maximum_Cell" in data:
            module['voltage_dc_maximum_cell'] = { 'value': data['Voltage_DC_Maximum_Cell'], 'unit': "V" }
        if "Voltage_DC_Minimum_Cell" in data:
            module['voltage_dc_minimum_cell'] = { 'value': data['Voltage_DC_Minimum_Cell'], 'unit': "V" }
        if "StateOfCharge_Relative" in data:
            module['state_of_charge'] = { 'value': data['StateOfCharge_Relative'], 'unit': "%" }
        if "Temperature_Cell" in data:
            module['temperature_cell'] = { 'value': data['Temperature_Cell'], 'unit': "C" }
        if "Temperature_Cell_Maximum" in data:
            module['temperature_cell_maximum'] = { 'value': data['Temperature_Cell_Maximum'], 'unit': "C" }
        if "Temperature_Cell_Minimum" in data:
            module['temperature_cell_minimum'] = { 'value': data['Temperature_Cell_Minimum'], 'unit': "C" }
        if "CycleCount_BatteryCell" in data:
            module['cycle_count_cell'] = { 'value': data['CycleCount_BatteryCell'] }
        if "Status_BatteryCell" in data:
            module['status_cell'] = { 'value': data['Status_BatteryCell'] }
        if "Enable" in data:
            module['enable'] = { 'value': data['Enable'] }
        if "Details" in data:
            module['manufacturer'] = { 'value': data['Details']['Manufacturer'] }
            module['model'] = { 'value': data['Details']['Model'] }
            module['serial'] = { 'value': data['Details']['Serial'] }

        return module
