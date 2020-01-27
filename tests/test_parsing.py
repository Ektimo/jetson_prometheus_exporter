from jetson_prometheus_exporter import tegrastats

def test_tegrastats_parsing():
    tegrastats_sample = 'RAM 2015/3964MB (lfb 98x4MB) SWAP 29/1982MB (cached 3MB) CPU [6%@102,5%@102,4%@102,3%@102] EMC_FREQ 0% GR3D_FREQ 0% PLL@28C CPU@31.5C PMIC@100C GPU@30.5C AO@36C thermal@31.25C POM_5V_IN 1388/1388 POM_5V_GPU 122/122 POM_5V_CPU 163/163'
    parsed_tegrastat_sample = {
        'EMC': {'val': 0}, 'GR3D': {'val': 0}, 'SWAP': {'use': 29, 'tot': 1982, 'unit': 'M', 'cached': {'size': 3, 'unit': 'M'}},
        'RAM': {'use': 2015, 'tot': 3964, 'unit': 'M', 'lfb': {'nblock': 98, 'size': 4, 'unit': 'M'}},
        'CPU': [
            {'name': 'CPU1', 'status': 1, 'val': 6, 'frq': 102, 'governor': 'powersave'},
            {'name': 'CPU2', 'status': 1, 'val': 5, 'frq': 102, 'governor': 'powersave'},
            {'name': 'CPU3', 'status': 1, 'val': 4, 'frq': 102, 'governor': 'powersave'},
            {'name': 'CPU4', 'status': 1, 'val': 3, 'frq': 102, 'governor': 'powersave'}
        ],
        'TEMP': {'PLL': 28.0, 'CPU': 31.5, 'PMIC': 100.0, 'GPU': 30.5, 'AO': 36.0, 'thermal': 31.25},
        'VOLT': {'POM_5V_IN': {'cur': 1388, 'avg': 1388}, 'POM_5V_GPU': {'cur': 122, 'avg': 122}, 'POM_5V_CPU': {'cur': 163, 'avg': 163}}
    }
    assert tegrastats.decode(tegrastats_sample) == parsed_tegrastat_sample