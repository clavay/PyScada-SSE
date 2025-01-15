# test send message

from time import time
import datetime
import pyscada

dt = datetime.timedelta(days=1).total_seconds() * 1000
start_init = start = datetime.datetime.now()
while start > start_init - datetime.timedelta(days=6*30):
    t_start = time()
    read_multiple_kwargs = {
             "variable_ids": [1944],
                    "time_min": start.timestamp(),
                    "time_max": start.timestamp()+dt/1000,
                    "time_in_ms": True,
                }
    result = pyscada.models.Variable.objects.read_multiple(**read_multiple_kwargs)
    result_length = []
    for k, v in result.items():
                result_length.append([k, len(v) if type(v) == list else None])
    percent = (start_init-start)/datetime.timedelta(days=6*30)
    pyscada.sse.models.Historic.objects.last().send_message({"data": result, "percent": percent})
    print(f"{percent} - {start} - {time()-t_start} - {result_length}")
    start -= datetime.timedelta(days=1)
pyscada.sse.models.Historic.objects.last().send_message({"percent": 1})


# single message
from time import time
mt = time() * 1000
result = {
 'timestamp': mt,
 'date_saved_max': mt,
 1944: [[mt * 1000, 5],[mt * 1000, 5]]
 }
pyscada.sse.models.Historic.objects.last().send_message({"data": result})

pyscada.sse.models.Historic.objects.last().send_event("stream-reset", "test reset")
pyscada.sse.models.Historic.objects.last().send_event("stream-error", "test error")


# send broadcast
from django_eventstream import send_event

send_event("broadcast", "message", "test")