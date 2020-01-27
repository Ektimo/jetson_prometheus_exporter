## Deployment
Run `python3 setup.py install` and then `python3 -m jetson_prometheus_exporter`. See `python3 -m jetson_prometheus_exporter --help` for command line arguments.

## Docker
As of december 2019, tegrastats isn't available in official base image for jetson `nvcr.io/nvidia/l4t-base:r32.3.1`.

## TODO
 * Deploy it as systemd service.   
 * Improve tests.   