from prometheus_client.core import GaugeMetricFamily

from .jetson_stats import get_uptime, status_disk
from .tegrastats import Tegrastats
from .logger import factory


class Jetson(object):
    def __init__(self, interval, tegrastats_logfile):
        #interval is in seconds, Tegrastats needs it in miliseconds
        self.tegrastats = Tegrastats(tegrastats_logfile, interval*1000)
        self.interval = interval

    def update(self):
        self.stats = self.tegrastats.read()
        self.disk = dict(status_disk())
        self.uptime = get_uptime()


class JetsonExporter(object):
    def __init__(self, interval, tegrastats_logfile):
        self.jetson = Jetson(interval, tegrastats_logfile)
        self.logger = factory(__name__)

    def __cpu(self):
        cpu_gauge = GaugeMetricFamily(
            'cpu', 'cpu statistics from tegrastats', labels=['core', 'statistic'],
        )
        for core_data in self.jetson.stats['CPU']:
            core_number = core_data['name'].replace('CPU', '')
            core_status = 1 if core_data['status'] == 'ON' else 0
            cpu_gauge.add_metric([core_number, 'status'], value=core_status)
            if core_data['status'] == 0:
                 continue
            cpu_gauge.add_metric([core_number, 'freq'], value=core_data['frq'])
            cpu_gauge.add_metric([core_number, 'val'], value=core_data['val'])
        return cpu_gauge


    def __gpu(self):
        gpu_gauge = GaugeMetricFamily('gpu_utilization_percentage', 'gpu statistics from tegrastats',)
        gpu_gauge.add_metric([], value=str(self.jetson.stats['GR3D']['val']))
        return gpu_gauge

    def __ram(self):
        ram_gauge = GaugeMetricFamily(
            'ram',
            f'ram statistics from tegrastats, with units in {self.jetson.stats["RAM"]["unit"]}',
            labels=['statistic'],
        )
        ram_gauge.add_metric(['total'], value=self.jetson.stats['RAM']['tot'])
        ram_gauge.add_metric(['used'], value=self.jetson.stats['RAM']['use'])
        return ram_gauge

    def __swap(self):
        swap_gauge = GaugeMetricFamily(
            'swap',
            f'swap statistics from tegrastats, with units in {self.jetson.stats["SWAP"]["unit"]}',
            labels=['statistic'],
        )
        swap_gauge.add_metric(['total'], value=self.jetson.stats['SWAP']['tot'])
        swap_gauge.add_metric(['used'], value=self.jetson.stats['SWAP']['use'])
        return swap_gauge

    def __temperature(self):
        temperature_gauge = GaugeMetricFamily(
            'temperature', 'temperature statistics from tegrastats',labels=['machine_part'],
        )
        for machine_part, temperature in self.jetson.stats['TEMP'].items():
            temperature_gauge.add_metric([machine_part], value=str(temperature))
        return temperature_gauge

    def __voltage(self):
        voltage_gauge = GaugeMetricFamily(
            'voltage', 'voltage statistics from tegrastats', labels=['source'],
        )
        for source, data in self.jetson.stats['VOLT'].items():
            voltage_gauge.add_metric([source], value=str(data['cur']))
        return voltage_gauge

    def __disk(self):
        disk_gauge = GaugeMetricFamily(
            'disk', 'disk statistics in bytes', labels=['mountpoint', 'statistic'],
        )
        for mountpoint, data in self.jetson.disk.items():
            for statistic, value in data.items():
                disk_gauge.add_metric([mountpoint, statistic], value=value)
        return disk_gauge

    def __uptime(self):
        uptime_gauge = GaugeMetricFamily('uptime', 'machine uptime')
        uptime_gauge.add_metric([], value=str(self.jetson.uptime))
        return uptime_gauge

    def collect(self):
        self.jetson.update()
        try:
            yield self.__cpu()
            yield self.__gpu()
            yield self.__ram()
            yield self.__swap()
            yield self.__temperature()
            yield self.__voltage()
        except Exception as e:
            self.logger.error(f'Issue with tegrastats data, probably empty({str(e)}).')
        yield self.__disk()
        yield self.__uptime()
