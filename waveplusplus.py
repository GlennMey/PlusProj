import struct
import logging
from bluepy3.btle import UUID, Peripheral, Scanner, DefaultDelegate


class WavePlusPlus():
    def __init__(self, SerialNumber):
        self.logger = logging.getLogger()
        self.logger.info("Initialized")
        self.periph = None
        self.curr_val_char = None
        self.MacAddr = None
        self.SN = SerialNumber
        self.uuid = UUID("b42e2a68-ade7-11e4-89d3-123b93f75cba")

    def connect(self):
        self.logger.debug(
            f"Attempting connection to device {self.SN}")
        if self.MacAddr is None:
            scanner = Scanner().withDelegate(DefaultDelegate())
            searchCount = 0
            # Loop for 50 scans or until we find it.
            while self.MacAddr is None:
                devices = scanner.scan(0.1)
                searchCount += 1
                for dev in devices:
                    ManuData = dev.getValueText(255)
                    self.logger.debug(
                        f"Checking if {dev.addr} is WavePlusPlus {ManuData}"
                    )
                    if ManuData:
                        SN = self.parseSerialNumber(ManuData)
                        if SN == self.SN:
                            self.logger.debug(
                                f"Found {dev.addr} with SN {SN}"
                            )
                            self.MacAddr = dev.addr
                if searchCount >= 50:
                    # Set to false if we hit 50.
                    # No breaks.
                    self.MacAddr = False
            if self.MacAddr is None or not self.MacAddr:
                self.logger.debug("Could not find device.")

        # Initialize Device
        if self.periph is None:
            self.logger.info(f"Connecting to Device {self.MacAddr}")
            self.periph = Peripheral(self.MacAddr)
        if self.curr_val_char is None:
            self.curr_val_char = self.periph.getCharacteristics(
                uuid=self.uuid
            )[0]

    def disconnect(self):
        if self.periph:
            self.logger.info("Disconnecting from Device")
            self.periph.disconnect()
            self.periph = None
            self.curr_val_char = None
        else:
            self.logger.info("No device to disconnect from.")

    def read(self):
        if (self.curr_val_char is None):
            self.logger.debug("ERROR: Devices are not connected.")
        raw_data = self.curr_val_char.read()
        sensor_data = self.parseSensors(raw_data)
        return sensor_data

    @staticmethod
    def parseSerialNumber(ManuDataHexStr):
        ManuData = bytearray.fromhex(ManuDataHexStr)
        if (((ManuData[1] << 8) | ManuData[0]) == 0x0334):
            SN = ManuData[2]
            SN |= (ManuData[3] << 8)
            SN |= (ManuData[4] << 16)
            SN |= (ManuData[5] << 24)
        else:
            SN = "Unknown"
        return SN

    def parseSensors(self, raw_data):
        raw_data = struct.unpack('BBBBHHHHHHHH', raw_data)
        sensor_version = raw_data[0]
        if sensor_version == 1:
            # build sensors
            sensor_data = {
                "config": {
                    "version": sensor_version,
                    "tbd1": raw_data[2],
                    "tbd2": raw_data[3]
                },
                "atmospheric": {
                    "humidity": {
                        "value": raw_data[1] / 2.0,
                        "unit": "%rH"
                    },
                    "temperature": {
                        "value": raw_data[6] / 100.0,
                        "unit": "C"
                    },
                    "pressure": {
                        "value": raw_data[7] / 50.0,
                        "unit": "hPa"
                    }
                },
                "particle": {
                    "radon_lt": {
                        "value": self.conv2radon(raw_data[4]),
                        "unit": "Bq/m3"
                    },
                    "radon_st": {
                        "value": self.conv2radon(raw_data[5]),
                        "unit": "Bq/m3"
                    },
                    "co2": {
                        "value": raw_data[8] * 1.0,
                        "unit": "ppm"
                    },
                    "voc": {
                        "value": raw_data[9] * 1.0,
                        "unit": "ppb"
                    }
                }
            }
        else:
            self.logger.info(
                f"Unknown Sensor Version {sensor_version}")
            self.logger.info(f"Raw Output: {raw_data}")
        return sensor_data

    @staticmethod
    def conv2radon(radon_raw):
        if 0 <= radon_raw <= 16383:
            radon = radon_raw
        else:
            radon = "N/A"  # bad read
        return radon
