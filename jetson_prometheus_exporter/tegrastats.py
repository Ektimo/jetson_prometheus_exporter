"""Large part of this script is from jetson_stats(https://github.com/rbonghi/jetson_stats), thank you!"""
import subprocess
from pathlib import Path
import re
import os

from .logger import factory

SWAP_RE = re.compile(r'SWAP (\d+)\/(\d+)(\w)B( ?)\(cached (\d+)(\w)B\)')
IRAM_RE = re.compile(r'IRAM (\d+)\/(\d+)(\w)B( ?)\(lfb (\d+)(\w)B\)')
RAM_RE = re.compile(r'RAM (\d+)\/(\d+)(\w)B( ?)\(lfb (\d+)x(\d+)(\w)B\)')
MTS_RE = re.compile(r'MTS fg (\d+)% bg (\d+)%')
VALS_RE = re.compile(r'\b([A-Z0-9_]+) ([0-9%@]+)(?=[^/])\b')
VAL_FRE_RE = re.compile(r'\b(\d+)%@(\d+)')
CPU_RE = re.compile(r'CPU \[(.*?)\]')
VOLT_RE = re.compile(r'\b(\w+) ([0-9.]+)\/([0-9.]+)\b')
TEMP_RE = re.compile(r'\b(\w+)@(-?[0-9.]+)C\b')


def val_freq(val):
    if '@' in val:
        match = VAL_FRE_RE.search(val)
        return {'val': int(match.group(1)), 'frq': int(match.group(2))}
    else:
        return {'val': int(val)}


def SWAP(text):
    """
        SWAP X/Y (cached Z)
        X = Amount of SWAP in use in megabytes.
        Y = Total amount of SWAP available for applications.
        Z = Amount of SWAP cached in megabytes.
    """
    match = SWAP_RE.search(text)
    if match:
        return {'use': int(match.group(1)),
                'tot': int(match.group(2)),
                'unit': match.group(3),
                # group 4 is an optional space
                'cached': {'size': int(match.group(5)),
                           'unit': match.group(6)}}
    else:
        return {}


def IRAM(text):
    """
        IRAM X/Y (lfb Z)
        IRAM is memory local to the video hardware engine.
        X = Amount of IRAM memory in use, in kilobytes.
        Y = Total amount of IRAM memory available.
        Z = Size of the largest free block.
    """
    match = IRAM_RE.search(text)
    if match:
        return {'use': int(match.group(1)),
                'tot': int(match.group(2)),
                'unit': match.group(3),
                # group 4 is an optional space
                'lfb': {'size': int(match.group(5)),
                        'unit': match.group(6)}}
    else:
        return {}


def RAM(text):
    """
        RAM X/Y (lfb NxZ)
        Largest Free Block (lfb) is a statistic about the memory allocator.
        It refers to the largest contiguous block of physical memory
        that can currently be allocated: at most 4 MB.
        It can become smaller with memory fragmentation.
        The physical allocations in virtual memory can be bigger.
        X = Amount of RAM in use in MB.
        Y = Total amount of RAM available for applications.
        N = The number of free blocks of this size.
        Z = is the size of the largest free block.
    """
    match = RAM_RE.search(text)
    if match:
        return {'use': int(match.group(1)),
                'tot': int(match.group(2)),
                'unit': match.group(3),
                # group 4 is an optional space
                'lfb': {'nblock': int(match.group(5)),
                        'size': int(match.group(6)),
                        'unit': match.group(7)}
                }
    else:
        return {}


def MTS(text):
    """ Parse MTS

        MTS fg X% bg Y%
        X = Time spent in foreground tasks.
        Y = Time spent in background tasks.
    """
    match = MTS_RE.search(text)
    if match:
        return {'fg': int(match.group(1)), 'bg': int(match.group(1))}
    else:
        return {}


def VALS(text):
    """ Add all values

        Parse all type of vals:
        - EMC X%@Y
          EMC is the external memory controller,
          through which all sysmem/carve-out/GART memory accesses go.
          X = Percent of EMC memory bandwidth being used, relative to the current running frequency.
          Y = EMC frequency in megahertz.
        - APE Y
          APE is the audio processing engine.
          The APE subsystem consists of ADSP (Cortex®-A9 CPU), mailboxes, AHUB, ADMA, etc.
          Y = APE frequency in megahertz.
        - GR3D X%@Y
          GR3D is the GPU engine.
          X = Percent of the GR3D that is being used, relative to the current running frequency.
          Y = GR3D frequency in megahertz
        - MSENC Y
          Y = MSENC frequency in megahertz.
          MSENC is the video hardware encoding engine.
        - NVENC Y
          Y = NVENC frequency in megahertz.
          NVENC is the video hardware encoding engine.
        - NVDEC Y
          Y = NVDEC frequency in megahertz.
          NVDEC is the video hardware decoding engine.
          It is shown only when hardware decoder/encoder engine is used.
    """
    vals = {}
    for name, val in re.findall(VALS_RE, text):
        # Remove from name "FREQ" name
        name = name.split('_')[0] if "FREQ" in name else name
        # Export value
        vals[name] = val_freq(val)
    return vals


def CPUS(text):
    """ Parse CPU information and extract status

        CPU [X%,Y%, , ]@Z or CPU [X%@Z, Y%@Z,...]
        X and Y are rough approximations based on time spent
        in the system idle process as reported by the Linux kernel in /proc/stat.
        X = Load statistics for each of the CPU cores relative to the
            current running frequency Z, or 'off' in case a core is currently powered down.
        Y = Load statistics for each of the CPU cores relative to the
            current running frequency Z, or 'off' in case a core is currently powered down.
        Z = CPU frequency in megahertz. Goes up or down dynamically depending on the CPU workload.
    """
    match = CPU_RE.search(text)
    cpus = []
    if match:
        # Extract
        cpus_list = match.group(1).split(',')
        for idx, cpu_str in enumerate(cpus_list):
            # Set name CPU
            cpu = {'name': 'CPU' + str(idx + 1)}
            # status
            if 'off' == cpu_str:
                cpu['status'] = 0
            else:
                cpu['status'] = 1
                val = val_freq(cpu_str)
                cpu.update(val)
                # Update status governor
                governor_name = '/sys/devices/system/cpu/cpu' + str(idx) + '/cpufreq/scaling_governor'
                # Add governor CPU if only exist
                if os.path.isfile(governor_name):
                    with open(governor_name, 'r') as f:
                        cpu['governor'] = f.read()[:-1]
            # Add in list
            cpus += [cpu]
    return cpus


def TEMPS(text):
    """ Parse all temperatures in tegrastats output

        [temp name]@XC
        [temp name] is one of the names under the nodes
        X = Current temperature
        /sys/devices/virtual/thermal/thermal_zoneX/type.
    """
    return {name: float(val) for name, val in re.findall(TEMP_RE, text)}


def VOLTS(text):
    """ Parse all voltages in tegrastats output

        [VDD_name] X/Y
        X = Current power consumption in milliwatts.
        Y = Average power consumption in milliwatts.
    """
    return {name: {'cur': int(cur), 'avg': int(avg)} for name, cur, avg in re.findall(VOLT_RE, text)}


def decode(text):
    stats = VALS(text)

    mts = MTS(text)
    if mts:
        stats['MTS'] = mts
    swap = SWAP(text)
    if swap:
        stats['SWAP'] = swap
    iram = IRAM(text)
    if iram:
        stats['IRAM'] = iram

    stats['RAM'] = RAM(text)
    stats['CPU'] = CPUS(text)
    stats['TEMP'] = TEMPS(text)
    stats['VOLT'] = VOLTS(text)
    return stats


class TegrastatsException(Exception):
    pass


def get_tegrastats_file():
    TEGRASTATS = ['/usr/bin/tegrastats', '/home/nvidia/tegrastats']
    for file_tegra in TEGRASTATS:
        if Path(file_tegra).is_file():
            return file_tegra
    raise TegrastatsException("Tegrastats is not availabe on this device!")


class Tegrastats:
    def __init__(self, logfile, interval):
        self.logfile = logfile
        self.interval = interval#in miliseconds!
        self.tegrastats_file = get_tegrastats_file()
        self.logger = factory(__name__)
        self.__start()

    def __start(self):
        start = subprocess.run(f'{self.tegrastats_file} --logfile {self.logfile} --interval {self.interval} --start', shell=True)
        if start.returncode != 0:
            raise TegrastatsException('Failed to start tegrastats!')

    def stop(self):
        end = subprocess.run(f'{self.tegrastats_file} --stop', shell=True)
        if end.returncode != 0:
            raise TegrastatsException('Failed to stop tegrastats!')

    def read(self):
        raw_data = subprocess.check_output(f'tail -1 {self.logfile}', shell=True)
        try:
            return decode(raw_data.decode("utf-8"))
        except Exception as e:
            self.logger.error(f'failed to parse tegrasta:{raw_data}, with error: {str(e)}')

    def logfile_cleanup(self):
        cleanup = subprocess.run(f'> {self.logfile}', shell=True)
        if cleanup.returncode != 0:
            raise TegrastatsException(f'Failed to cleanup tegrastats logfile! Return code: "{cleanup.returncode}", message: stdout-"{cleanup.stdout}", stderr:"{cleanup.stderr}"')

