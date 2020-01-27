import psutil

def get_uptime():
    """ Read uptime system
        http://planzero.org/blog/2012/01/26/system_uptime_in_python,_a_better_way
    """
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
    return uptime_seconds


def status_disk():
    partitions = psutil.disk_partitions()
    for p in partitions:
        yield (p.mountpoint, psutil.disk_usage(p.mountpoint)._asdict())
