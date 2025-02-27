# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.models import Variable, VariableProperty, DeviceWriteTask
from pyscada.models import BackgroundProcess
from pyscada.hmi.models import View, GroupDisplayPermission, ControlItem
from pyscada.utils import get_group_display_permission_list
from pyscada.sse.models import Historic

from django.db import IntegrityError, transaction
from django.core.serializers.json import DjangoJSONEncoder
from django.template.response import TemplateResponse
from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseBadRequest
from django.views.decorators.csrf import requires_csrf_token
from django.contrib.auth.decorators import login_required

from os import kill
import signal
import json
from time import time
import datetime
import logging

logger = logging.getLogger(__name__)


@login_required
@requires_csrf_token
def test_sse(request):
    return TemplateResponse(request, "test_sse.html")


@login_required
async def no_session_key(request):
    logger.warning(f"no session key for {request}")
    return HttpResponseBadRequest("Missing session_key")


@login_required
@requires_csrf_token
def need_historical_data(request):
    if request.method == "POST":
        data = json.loads(request.body)
        logger.info(data)
        user = request.user
        session_key = request.session.session_key
        start = data["start"]
        end = data["end"]

        try:
            view = get_group_display_permission_list(
                View.objects, request.user.groups.all()
            ).get(id=data["view_id"])
        except View.DoesNotExist as e:
            logger.warning(e)
            body = (
                json.dumps(
                    {"error": "view with id {request.POST['view_id']} not found."},
                    cls=DjangoJSONEncoder,
                )
                + "\n"
            )
            return HttpResponse(body, content_type="application/json")

        with transaction.atomic():  # create the historic
            try:
                hst, created = Historic.objects.update_or_create(
                    session_key=session_key,
                    view=view,
                    defaults={
                        "user": user,
                        "start": datetime.datetime.fromtimestamp(
                            start / 1000, tz=datetime.timezone.utc
                        ),
                        "end": datetime.datetime.fromtimestamp(
                            end / 1000, tz=datetime.timezone.utc
                        ),
                        "done": True,
                        "busy": True,
                    },
                )
            except Historic.MultipleObjectsReturned:
                logger.info(
                    f"Deleting duplicate {Historic.objects.filter(session_key=session_key, view=view)[1:].count()} historic of session {session_key} and view {view}"
                )
                Historic.objects.filter(
                    id__in=list(
                        Historic.objects.filter(
                            session_key=session_key, view=view
                        ).values_list("pk", flat=True)[1:]
                    )
                ).delete()
                hst, created = Historic.objects.update_or_create(
                    session_key=session_key,
                    view=view,
                    defaults={
                        "user": user,
                        "start": datetime.datetime.fromtimestamp(
                            start / 1000, tz=datetime.timezone.utc
                        ),
                        "end": datetime.datetime.fromtimestamp(
                            end / 1000, tz=datetime.timezone.utc
                        ),
                        "done": True,
                        "busy": True,
                    },
                )

            if start == end == 0:
                # send server time
                hst.send_message()
            else:
                if end == 0:
                    end = time() * 1000
                if start == 0:
                    start = (time() - 2 * 3600) * 1000

                variables = list(Variable.objects.filter(id__in=data["variable_ids"]))
                status_variables = list(
                    Variable.objects.filter(id__in=data["status_variable_ids"])
                )
                variable_properties = list(
                    VariableProperty.objects.filter(id__in=data["variable_property_ids"])
                )
                hst.update_objects(variables, status_variables, variable_properties)

                bp = None

                try:
                    sseBp = BackgroundProcess.objects.get(label="pyscada.sse")
                    logger.info(f"creating BP")
                    bp, created = BackgroundProcess.objects.get_or_create(
                        label="pyscada.sse.historic-%d" % hst.pk,
                        defaults={
                            "message":"waiting..",
                            "enabled":True,
                            "parent_process_id":sseBp.parent_process_id,
                            "process_class":"pyscada.sse.worker.HistoricProcess",
                            "process_class_kwargs":json.dumps({"historic_id": hst.pk}),
                            }
                    )
                except BackgroundProcess.MultipleObjectsReturned:
                    for bp in BackgroundProcess.objects.filter(label="pyscada.sse.historic-%d" % hst.pk,):
                        bp.stop(signal.SIGKILL)
                        bp.delete()
                    bp, created = BackgroundProcess.objects.get_or_create(
                        label="pyscada.sse.historic-%d" % hst.pk,
                        defaults={
                            "message":"waiting..",
                            "enabled":True,
                            "parent_process_id":sseBp.parent_process_id,
                            "process_class":"pyscada.sse.worker.HistoricProcess",
                            "process_class_kwargs":json.dumps({"historic_id": hst.pk}),
                            }
                        )
                except BackgroundProcess.DoesNotExist:
                    logger.warning(f"SSE BackgroundProcess does not exist.")
                finally:
                    if bp is not None:
                        logger.info("bp found")
                        if not created:
                            logger.info(f"not created {bp.pid}")
                            bp.stop(signal.SIGKILL)
                            bp.delete()
                            bp, created = BackgroundProcess.objects.get_or_create(
                                label="pyscada.sse.historic-%d" % hst.pk,
                                defaults={
                                    "message":"waiting..",
                                    "enabled":True,
                                    "parent_process_id":sseBp.parent_process_id,
                                    "process_class":"pyscada.sse.worker.HistoricProcess",
                                    "process_class_kwargs":json.dumps({"historic_id": hst.pk}),
                                    }
                            )
        logger.info("end need hist")
        body = json.dumps(hst.to_data(), cls=DjangoJSONEncoder) + "\n"
        return HttpResponse(body, content_type="application/json")
    else:
        return HttpResponseNotAllowed(["POST"])


def send_filter(user, channel, item):
    logger.info(user)
    logger.info(channel)
    logger.info(item)
    return False


@login_required
async def aform_write_task(request):
    if "key" in request.POST and "value" in request.POST:
        key = int(request.POST["key"])
        item_type = request.POST["item_type"]
        value = request.POST["value"]
        # check if float as DeviceWriteTask doesn't support string values
        try:
            float(value)
        except ValueError:
            try:
                vp = VariableProperty.objects.get(id=key)
                if item_type == "variable_property" and vp.value_class.upper() in [
                    "STRING"
                ]:
                    VariableProperty.objects.update_property(
                        variable_property=vp,
                        value=value,
                    )
                    # TODO: write string
                    # cwt = DeviceWriteTask(
                    #    variable_property_id=key,
                    #    value=value,
                    #    start=time.time(),
                    #    user=request.user,
                    # )
                    # cwt.create_and_notificate(cwt)
                    return HttpResponse(status=200)
            except VariableProperty.DoesNotExist:
                pass
            logger.info(f"Cannot write STRING '{value}' to {item_type} {key}")
            return HttpResponse(status=403)
        if await GroupDisplayPermission.objects.acount() == 0:
            if item_type == "variable":
                cwt = DeviceWriteTask(
                    variable_id=key, value=value, start=time(), user=request.user
                )
                await cwt.acreate_and_notificate(cwt)
                return HttpResponse(status=200)
            elif item_type == "variable_property":
                cwt = DeviceWriteTask(
                    variable_property_id=key,
                    value=value,
                    start=time(),
                    user=request.user,
                )
                await cwt.acreate_and_notificate(cwt)
                return HttpResponse(status=200)
        else:
            if "view_id" in request.POST:
                # for a view, get the list of variables and variable properties for which the user can retrieve and write data
                view_id = int(request.POST["view_id"])
                view = await View.objects.aget(id=view_id)
                vdo = await view.adata_objects(request.user)
                logger.info(vdo)
            else:
                vdo = None  # should it get data objets for all views ?

            if item_type == "variable":
                can_write = False
                if vdo is not None:
                    # filter active_variables using variables from which the user can write data
                    if "variable_write" in vdo and int(key) in vdo["variable_write"]:
                        can_write = True
                    else:
                        logger.info(
                            f"variable {key} not allowed to write in view {view_id} for user {request.user}"
                        )
                else:
                    # keeping old check, remove it later
                    if (
                        await get_group_display_permission_list(
                            ControlItem.objects, request.user.groups.all()
                        )
                        .filter(type=0, variable_id=key)
                        .aexists()
                    ):
                        can_write = True
                    else:
                        logger.info(
                            "Missing group display permission for write task (variable %s)"
                            % key
                        )
                if can_write:
                    cwt = DeviceWriteTask(
                        variable_id=key,
                        value=value,
                        start=time(),
                        user=request.user,
                    )
                    await cwt.acreate_and_notificate(cwt)
                    return HttpResponse(status=200)
            elif item_type == "variable_property":
                can_write = False
                if vdo is not None:
                    # filter active_variables using variables from which the user can write data
                    if (
                        "variable_property_write" in vdo
                        and int(key) in vdo["variable_property_write"]
                    ):
                        can_write = True
                    else:
                        logger.info(
                            f"variable property {key} not allowed to write in view {view_id} for user {request.user}"
                        )
                else:
                    # keeping old check, remove it later
                    if (
                        await get_group_display_permission_list(
                            ControlItem.objects, request.user.groups.all()
                        )
                        .filter(type=0, variable_property_id=key)
                        .aexists()
                    ):
                        can_write = True
                    else:
                        logger.debug(
                            "Missing group display permission for write task (VP %s)"
                            % key
                        )
                if can_write:
                    cwt = DeviceWriteTask(
                        variable_property_id=key,
                        value=value,
                        start=time(),
                        user=request.user,
                    )
                    await cwt.acreate_and_notificate(cwt)
                    return HttpResponse(status=200)
    else:
        logger.debug("key or value missing in request : %s" % request.POST)
    return HttpResponse(status=404)
