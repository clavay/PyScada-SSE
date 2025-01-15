# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.sse.models import Historic

from django.dispatch import receiver, Signal

import signal
import logging

logger = logging.getLogger(__name__)

consume_historic = Signal()

@receiver(consume_historic, sender=Historic)
def _consume_historic(sender, instance, **kwargs):
    """
    Send signal to send historical data
    """
    if type(instance) is Historic:
        logger.info(f"consume_historic {type(instance).__name__}.{getattr(instance, 'id', 'new')}-session-{getattr(instance, 'session_key')}-view-{getattr(getattr(instance, 'view'), 'id')}")
        try:
            instance.send_message({"historic": "saved"}, async_publish=True)
            if not instance.done and (instance.variables.count() or instance.status_variables.count() or instance.variable_properties.count()):
                instance.read_and_send_data()
            else:
                instance.send_message({"percent": 1})
        except Exception as e:
            logger.error(e, exc_info=True)
