# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from . import views
from pyscada.hmi.models import View

from django.urls import path, include

import django_eventstream

urlpatterns = [
    path("form/awrite_task_sse/", views.aform_write_task),
    path("need_historical_data/", views.need_historical_data),
    path("events/session//", views.no_session_key),
    # django_eventstream path should start with "events/"
    path(
        "events/broadcast/",
        include(django_eventstream.urls),
        {"channels": ["broadcast"], "send_filter": views.send_filter},
    ),
    path(
        "events/session/<session_id>/view/<view_id>",
        include(django_eventstream.urls),
        {
            "format-channels": ["session-{session_id}-view-{view_id}"],
            "send_filter": views.send_filter,
        },
    ),
]
