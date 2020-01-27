from time import sleep
import sys
import argparse

from prometheus_client import start_http_server
from prometheus_client.core import REGISTRY
import schedule

from .exporter import JetsonExporter
from .logger import factory

def start_exporter(port, update_period, tegrastats_logfile, logfile_clenup_interval_hours):
    logger = factory(__name__)
    logger.info(f'Starting exporter on port: {port}, update_period: {update_period}, tegrastats_logfile: {tegrastats_logfile}, logfile_clenup_interval_hours: {logfile_clenup_interval_hours}')
    start_http_server(port)
    data_collector = JetsonExporter(update_period, tegrastats_logfile)
    try:
        sleep(update_period*2)
        REGISTRY.register(data_collector)

        schedule.every(logfile_clenup_interval_hours).minutes.do(data_collector.jetson.tegrastats.logfile_cleanup)
        while True:
            schedule.run_pending()
            sleep(100)
    except KeyboardInterrupt:
        data_collector.jetson.tegrastats.stop()
    except Exception as e:
        logger.error(f'Exporter exited because of exception: {str(e)}')
        data_collector.jetson.tegrastats.stop()
        sys.exit(1)


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, nargs='?', default=8000, help='Port on which metrics will be available.')
    parser.add_argument('--update_period', type=int, nargs='?', default=1, help='Period(in seconds) in which we will get new metrics from tegrastats.')
    parser.add_argument('--tegrastats_logfile', type=str, nargs='?', default='./stats.log', help='Where to write tegrastats output to.')
    parser.add_argument('--logfile_clenup_interval_hours', type=int, nargs='?', default=1, help='After how many hours we want to clean up tegrastats_logfile(argument above).')
    return vars(parser.parse_args())


if __name__ == '__main__':
    start_exporter(**cli())