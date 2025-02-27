# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import datetime
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from . import __app_name__
import logging

logger = logging.getLogger(__name__)


class PyScadaSSEConfig(AppConfig):
    name = "pyscada." + __app_name__.lower()
    verbose_name = _("PyScada " + __app_name__)
    path = os.path.dirname(os.path.realpath(__file__))
    default_auto_field = "django.db.models.AutoField"

    def pyscada_app_init(self):
        logger.debug(f"{__app_name__} init app")

        try:
            from pyscada.sse.models import SSE

            SSE.objects.get_or_create(id=1)
        except ProgrammingError:
            pass
        except OperationalError:
            pass

    def pyscada_send_cov_notification(self, variable=None, variable_property=None):
        logger.debug(f"{variable} {variable_property}")
        from .models import Historic

        for hst in (
            Historic.objects.filter(
                updated__gte=datetime.datetime.now(tz=datetime.timezone.utc)
                - datetime.timedelta(days=1)
            )
            .filter(
                Q(variables__in=[variable])
                | Q(status_variables__in=[variable])
                | Q(variable_properties__in=[variable_property])
            )
            .distinct()
        ):
            vdo = hst.view.data_objects(hst.user)
            logger.debug(vdo)
            if (
                variable is not None
                and "variable" in vdo
                and variable.pk in vdo["variable"]
            ):
                pass
            elif (
                variable_property is not None
                and "variable_property" in vdo
                and variable_property.pk in vdo["variable_property"]
            ):
                pass
            else:
                logger.info(
                    f"variable {variable} or variable_property {variable_property} not allowed in view {hst.view} for user {hst.user}"
                )
                return False

            data = {}
            timestamp = 0
            if variable is not None:
                data[variable.id] = variable.cached_values_to_write
                for t, v in variable.cached_values_to_write:
                    timestamp = max(timestamp, t)
            if variable_property is not None:
                t = variable_property.last_modified.timestamp() * 1000
                data["variable_properties"] = {
                    variable_property.id: float(variable_property.value())
                }
                data["variable_properties_last_modified"] = {variable_property.id: t}
                timestamp = max(timestamp, t)
            data["timestamp"] = timestamp
            logger.info({f"data_sse {hst}: {data}"})
            hst.send_message({"data": data})
