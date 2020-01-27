from distutils.core import setup

setup(name='jetson_prometheus_exporter',
      version='1.0',
      description='Collect prometheus metrics on jetson platforms.',
      author='Ektimo',
      author_email='info@ektimo.si',
      url='https://ektimo.ai/',
      packages=['jetson_prometheus_exporter'],
      install_requires=open('requirements.txt', 'r').read().splitlines(),
     )