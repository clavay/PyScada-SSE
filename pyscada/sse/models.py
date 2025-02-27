# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.hmi.models import View, WidgetContentModel
from pyscada.models import Variable, VariableProperty, BackgroundProcess

from django.db import models
from django.contrib.auth.models import User
from django.forms.models import BaseInlineFormSet
from django import forms
from django.template.loader import get_template
from django.conf import settings

from django_eventstream import send_event
from time import time
from datetime import datetime, timezone, timedelta
import signal
import logging

logger = logging.getLogger(__name__)


class Historic(models.Model):
    view = models.ForeignKey(View, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=100)
    start = models.DateTimeField()
    end = models.DateTimeField()
    variables = models.ManyToManyField(Variable)
    status_variables = models.ManyToManyField(Variable, related_name="status_variables")
    variable_properties = models.ManyToManyField(VariableProperty)

    done = models.BooleanField(default=False)
    busy = models.BooleanField(default=False)
    updated = models.DateTimeField(auto_now=True)

    def to_data(self):
        out = {}
        out["id"] = self.id
        out["view"] = self.view.link_title
        out["user"] = self.user.id
        out["session_key"] = self.session_key
        out["start"] = self.start
        out["end"] = self.end
        out["variable_ids"] = list(self.variables.values_list("id", flat=True))
        out["status_variable_ids"] = list(
            self.status_variables.values_list("id", flat=True)
        )
        out["variable_property_ids"] = list(
            self.variable_properties.values_list("id", flat=True)
        )
        out["done"] = self.done
        out["busy"] = self.busy
        return out

    def send_message(self, message={}, async_publish=False):
        message["historic_state"] = self.to_data()
        if "data" not in message:
            message["data"] = {}
        if "server_time" not in message["data"]:
            message["data"]["server_time"] = time() * 1000
        # logger.debug(f"send state to session-{self.session_key}-view-{self.view.id} : {message}")
        self.send_event("message", message, async_publish=async_publish)

    def send_event(self, event_type="message", message=None, async_publish=False):
        send_event(
            f"session-{self.session_key}-view-{self.view.id}",
            event_type,
            message,
            async_publish=async_publish,
        )

    def is_expired(self, td=timedelta(days=1)):
        return datetime.now(tz=timezone.utc) - self.updated >= td

    def read_and_send_data(self):
        self.send_message({"historic": "read_start"}, async_publish=True)
        start = self.start.timestamp() * 1000
        end = self.end.timestamp() * 1000
        start_temp = end_temp = end

        # status variables
        status_variable_list = list(self.status_variables.values_list("id", flat=True))
        read_multiple_kwargs = {
            "variable_ids": status_variable_list,
            "time_min": end_temp / 1000,
            "time_max": end_temp / 1000,
            "time_in_ms": True,
            "query_first_value": True,
        }
        if len(status_variable_list):
            result = Variable.objects.read_multiple(**read_multiple_kwargs)
            # logger.info(result)
            self.send_message({"data": result, "percent": 0}, async_publish=True)

        # variable_properties
        result = {}
        result["variable_properties"] = {}
        result["variable_properties_last_modified"] = {}
        for item in VariableProperty.objects.filter(
            pk__in=self.variable_properties.all()
        ):
            result["variable_properties"][item.pk] = item.value()
            result["variable_properties_last_modified"][item.pk] = (
                item.last_modified.timestamp() * 1000
            )
        # logger.info(result)
        self.send_message({"data": result, "percent": 0}, async_publish=True)

        # chart variables
        dt_ms = 1 * 24 * 3600 * 1000  # 1 day in millisecond
        vars_ids = list(self.variables.values_list("id", flat=True))

        if len(vars_ids):
            while start_temp > start:
                self.start = start_temp
                t_start = time()
                start_temp = max(start_temp - dt_ms, start)
                read_multiple_kwargs = {
                    "variable_ids": vars_ids,
                    "time_min": start_temp / 1000,
                    "time_max": end_temp / 1000,
                    "time_in_ms": True,
                }
                result = Variable.objects.read_multiple(**read_multiple_kwargs)
                # logger.debug(result)
                result["timestamp"] = end
                percent = (end - start_temp) / (end - start)
                logger.debug(
                    f"{percent}% - querying {datetime.fromtimestamp(start_temp/1000)} to {datetime.fromtimestamp(end_temp/1000)} for {list(self.variables.values_list('id', flat=True))} {list(self.status_variables.values_list('id', flat=True))} {list(self.variable_properties.values_list('id', flat=True))}"
                )
                self.send_message(
                    {"data": result, "percent": percent}, async_publish=True
                )
                end_temp = start_temp

        self.send_message({"historic": "read_end", "percent": 1}, async_publish=True)
        self.done = True
        self.save(update_fields=["done"])

    def update_objects(
        self, variables=list(), status_variables=list(), variable_properties=list()
    ):
        vdo = self.view.data_objects(self.user)
        logger.debug(vdo)
        variables_filtered = []
        for var in variables:
            if "variable" in vdo and var.pk in vdo["variable"]:
                variables_filtered.append(var)
            else:
                logger.info(
                    f"variable {var} not allowed in view {self.view} for user {self.user}"
                )
        status_variables_filtered = []
        for var in status_variables:
            if "variable" in vdo and var.pk in vdo["variable"]:
                status_variables_filtered.append(var)
            else:
                logger.info(
                    f"status_variable {var} not allowed in view {self.view} for user {self.user}"
                )

        variable_properties_filtered = []
        for var in variable_properties:
            if "variable_property" in vdo and var.pk in vdo["variable_property"]:
                variable_properties_filtered.append(var)
            else:
                logger.info(
                    f"variable_property {var} not allowed in view {self.view} for user {self.user}"
                )
        logger.debug(variables_filtered)
        logger.debug(status_variables_filtered)
        logger.debug(variable_properties_filtered)
        self.variables.clear()
        self.status_variables.clear()
        self.variable_properties.clear()
        self.variables.add(*variables_filtered)
        self.status_variables.add(*status_variables_filtered)
        self.variable_properties.add(*variable_properties_filtered)

        self.done = False
        self.save(update_fields=["done"])


class SSE(WidgetContentModel):
    id = models.AutoField(primary_key=True)

    def __str__(self):
        return str(self.id)

    def visible(self):
        return True

    def data_objects(self, user):
        # used to get all objects which need to retrive data
        return {}

    def gen_html(self, **kwargs):
        """
        :return: main panel html and sidebar html as
        """
        widget_pk = kwargs["widget_pk"] if "widget_pk" in kwargs else 0

        main_template = get_template("load_sse.html")
        main_content = main_template.render(
            dict(widget_pk=widget_pk, view=kwargs["view"], request=kwargs["request"])
        )
        sidebar_content = None

        opts = dict()
        STATIC_URL = (
            str(settings.STATIC_URL) if hasattr(settings, "STATIC_URL") else "/static/"
        )
        opts["javascript_files_list"] = [
            f"{STATIC_URL}django_eventstream/eventsource.min.js",
            f"{STATIC_URL}django_eventstream/reconnecting-eventsource.js",
        ]

        return main_content, sidebar_content, opts
