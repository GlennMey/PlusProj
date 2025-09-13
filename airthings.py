#!/usr/bin/env python3
import os
import sys
import json
import logging
import argparse
from time import sleep
from datetime import datetime
from airthings.waveplusplus import WavePlusPlus

def setup_logging(config):
    """Setup logging configuration"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-5.5s] %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler if configured
    if config.get('logging', {}).get('enabled', False):
        logfile_config = config.get('logging', {}).get('logfile', {})
        if logfile_config.get('enabled', False):
            log_path = logfile_config.get('path', 'logs')
            os.makedirs(log_path, exist_ok=True)
            
            dt = datetime.now().strftime("%Y-%m-%d")
            log_file = f"WavePlusPlus-{dt}.log"
            log_file_path = os.path.join(log_path, log_file)
            
            file_handler = logging.FileHandler(log_file_path)
            file_formatter = logging.Formatter(
                "%(asctime)s [%(levelname)-5.5s] %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
    
    return logger

def load_config(config_path):
    """Load configuration from file"""
    if not os.path.exists(config_path):
        return {}
    
    try:
        with open(config_path, 'r') as fh:
            return json.load(fh)
    except Exception as e:
        logging.error(f"Failed to load config file {config_path}: {e}")
        return {}

def parse_device_serials(serial_string):
    """Parse comma-separated serial numbers"""
    try:
        return [
            {"name": None, "serial": int(x.strip())}
            for x in serial_string.split(',')
        ]
    except ValueError:
        raise ValueError(
            "Invalid serial number passed. Must be integers "
            f"separated by commas. Received: {serial_string}"
        )

def main():
    parser = argparse.ArgumentParser(description='Airthings WavePlusPlus')
    parser.add_argument(
        '--config', '-c', default='config.json',
        help='The path to the configuration file.')
    parser.add_argument(
        '--device-serial', '-d',
        help='The serial number for the device. Can be a comma separated list.')

    args = parser.parse_args()
    
    # Handle device serials
    if args.device_serial:
        devices = parse_device_serials(args.device_serial)
        config = {
            "logging": {
                "enabled": True
            }
        }
        data_path = "data"
    else:
        config = load_config(args.config)
        if not config:
            raise FileNotFoundError(
                "No devices passed and no config.json found."
            )
        devices = config.get('devices', [])
        data_path = config.get('output', {}).get('path', 'data')
    
    # Setup logging
    logger = setup_logging(config)
    logger.info("Script Initialized")
    
    # Create data directory
    os.makedirs(data_path, exist_ok=True)
    logger.info(f"Output path: {data_path}")
    
    # Process each device
    for device in devices:
        serial = int(device['serial'])
        device_name = device.get('name', f"Device-{serial}")
        
        logger.info(f"Querying Device {device_name} (Serial: {serial})")
        
        sensors = None
        for attempt in range(5):
            try:
                waveplus = WavePlusPlus(serial)
                waveplus.connect()
                sensors = waveplus.read()
                waveplus.disconnect()
                
                if sensors:
                    logger.info("Successfully queried device.")
                    break
                else:
                    logger.warning(f"Failed to query device on attempt {attempt + 1}. Trying again in 5 seconds.")
                    
            except Exception as e:
                logger.error(f"Error querying device {serial}: {e}")
                if attempt < 4:  # Don't sleep on last attempt
                    sleep(5)
            finally:
                # Ensure cleanup even if error occurs
                try:
                    if 'waveplus' in locals():
                        waveplus.disconnect()
                except:
                    pass
        
        else:
            logger.warning(f"Failed to query device {serial} after five tries. Giving up!")
            continue
        
        # Save data
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        data_file = f"WavePlusPlus-{serial}-{timestamp}.json"
        data_file_path = os.path.join(data_path, data_file)
        
        try:
            with open(data_file_path, 'w') as fh:
                json.dump(sensors, fh, indent=4, sort_keys=False)
            logger.info(f"Data saved to {data_file_path}")
        except Exception as e:
            logger.error(f"Failed to save data to {data_file_path}: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Script interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Script failed with error: {e}")
        sys.exit(1)
