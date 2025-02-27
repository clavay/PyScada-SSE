#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.sse.models import Historic
from pyscada.utils.scheduler import Process as BaseProcess
from pyscada.models import BackgroundProcess

from django.utils.timezone import now

import signal
import json
import logging

logger = logging.getLogger(__name__)


class HistoricProcess(BaseProcess):
    def __init__(self, dt=5, **kwargs):
        self.historic_id = 0
        super().__init__(dt=dt, **kwargs)

    def loop(self):
        historic = Historic.objects.get(pk=self.historic_id)

        bp = BackgroundProcess.objects.filter(
            enabled=True,
            done=False,
            pid=self.pid,
            parent_process__pk=self.parent_process_id,
        ).first()

        if bp is None:
            logger.debug(f"Historic {self.historic_id} no BP found")
            return -1, None

        bp.message = "reading..."
        bp.save(update_fields=["message"])

        logger.info("start reading ")

        historic.read_and_send_data()
        logger.info("stop reading ")

        historic.done = True
        historic.busy = False
        historic.save(update_fields=["busy", "done"])

        bp.done = True
        bp.last_update = now()
        bp.message = "read done"
        bp_update_fields = ["done", "last_update", "message"]

        #if not bp.failed:
        #    bp.message = "stopped"
        #    bp_update_fields.append("message")

        bp.save(update_fields=bp_update_fields)

        bp.stop(signal.SIGKILL)

        return 0, None

class SSEProcess(BaseProcess):
    def __init__(self, dt=30, **kwargs):
        super().__init__(dt=dt, **kwargs)

    def loop(self):
        """
        check for historic to manage
        """

        # delete old historic
        [h.delete() if h.is_expired() else None for h in Historic.objects.all()]

        # delete done and failed BPs
        [bp.delete() if bp.done or bp.failed else None for bp in BackgroundProcess.objects.filter(label__startswith="pyscada.sse.historic-")]

        return 1, None
