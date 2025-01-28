#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.sse.models import Historic
from pyscada.utils.scheduler import Process as BaseProcess
import logging

logger = logging.getLogger(__name__)


class Process(BaseProcess):
    def __init__(self, dt=1, **kwargs):
        super(Process, self).__init__(dt=dt, **kwargs)

    def loop(self):
        """
        check for events and trigger actions
        """
        for item in Historic.objects.filter(done=False):
            try:
                logger.info(
                    f"loop Historic.{getattr(item, 'id', 'new')}-session-{getattr(item, 'session_key')}-view-{getattr(getattr(item, 'view'),'id')}"
                )
                item.read_and_send_data()
            except Exception as e:
                logger.error(e, exc_info=True)

        [h.delete() if h.is_expired() else None for h in Historic.objects.all()]

        return 1, None
