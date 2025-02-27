# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pyscada

__version__ = "0.8.0"
__author__ = "Camille Lavayssiere"
__email__ = "team@pyscada.org"
__description__ = "Server-Sent-Event extension for PyScada a Python and Django based Open Source SCADA System"
__app_name__ = "SSE"

parent_process_list = [
    {
        "pk": 21,
        "label": "pyscada.sse",
        "process_class": "pyscada.sse.worker.SSEProcess",
        "process_class_kwargs": '{"dt_set":1}',
        "enabled": True,
    },
]
