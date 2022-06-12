import json
import logging
from datetime import timedelta
from typing import Any, Dict, List
from urllib.parse import quote

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin, AccessMixin
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.forms.utils import ErrorList
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, FormView

from rest_framework.exceptions import ParseError

from vcelerytaskrunner.models import TASKNAME_MAXLEN
from vcelerytaskrunner.services.task_registry import TaskInfo, DEFAULT_PAGE_SIZE, LimitOffsetPagination, TaskFilter
from vcelerytaskrunner.services.task_runner import run_and_record, get_task_infos, get_task_info
from rest_framework.views import APIView


logger = logging.getLogger(__name__)


PERMISSIONS_CAN_SEE_TASKS = ["vcelerytaskrunner.view_taskrunrecord"]
PERMISSIONS_CAN_SEE_AND_RUN_TASKS = ["vcelerytaskrunner.view_taskrunrecord", "vcelerytaskrunner.add_taskrunrecord"]

VCELERY_SHOW_ONLY_RUNNABLE_TASKS = getattr(settings, "VCELERY_SHOW_ONLY_RUNNABLE_TASKS", False)



class TasksAPIView(AccessMixin, APIView):
    def _create_task_run_url(self, task_info: TaskInfo) -> str:
        return f"{reverse('vcelery-task-run')}?task={quote(task_info['name'])}"

    def get(self, request):
        if not request.user.has_perms(PERMISSIONS_CAN_SEE_TASKS):
            return self.handle_no_permission()

        mask = request.GET.get("mask")
        runnable_only = True

        if VCELERY_SHOW_ONLY_RUNNABLE_TASKS:
            logger.debug(f"VCELERY_SHOW_ONLY_RUNNABLE_TASKS is True, so ignoring runnableOnly param")
        else:
            runnable_only_param = request.GET.get("runnableOnly")
            if not runnable_only_param or runnable_only_param.lower() == "false":
                runnable_only = False

        entries = []
        offset = int(request.GET.get("offset") or 0)
        limit = int(request.GET.get("limit") or DEFAULT_PAGE_SIZE)
        task_infos_w_count = get_task_infos(
            TaskFilter(mask=mask, runnable_only=runnable_only),
            pagination=LimitOffsetPagination(offset=offset, limit=limit)
        )
        for task_info in task_infos_w_count["task_infos"]:
            entry = task_info.copy()
            entry['task_run_url'] = self._create_task_run_url(task_info)
            entries.append(entry)

        return JsonResponse(data={"tasks": entries, "total_count": task_infos_w_count["count"]})


class TaskRunAPIView(AccessMixin, APIView):
    # curl -d "{\"kwargs\": {\"name\":\"John\",\"an_int\":56}}" -H "Content-Type: application/json" -u root:nothing1234 -XPOST http://localhost:8000/api/task_run/?task=vcelerydev.tasks.ha_ha_ha
    # curl -d "{\"kwargs\": {\"name\":\"John\",\"an_int\":56}}" -H "Content-Type: application/json" -u van:nothing1234 -XPOST http://localhost:8000/api/task_run/?task=vcelerydev.tasks.he_he

    def post(self, request):
        if not request.user.has_perms(PERMISSIONS_CAN_SEE_AND_RUN_TASKS):
            return self.handle_no_permission()

        task_name_param = request.GET.get("task")
        if task_name_param:
            try:
                args = request.data.get("args") or []
                kwargs = request.data.get("kwargs") or {}
                logger.debug(f"task={task_name_param}, args={args}, kwargs={kwargs}")
                delay_param = request.data.get("delay") if request.data else None
                delay = None
                if delay_param:
                    delay = timedelta(seconds=int(delay_param))

                result = run_and_record(task_name_param, args=args, kwargs=kwargs, user=request.user, delay=delay)
                result_data = {"error": False, "task_id": result.id}
            except (ValidationError, ParseError) as e:
                result_data = {"error": True, "error_msg": str(e)}
            except Exception as e:
                logger.exception("Cannot run task %s with %s: %s", task_name_param, request.data or {}, e)
                result_data = {"error": True, "error_msg": str(e)}
        else:
            result_data = {"error": True, "error_msg": "'task' parameter required"}

        return JsonResponse(data=result_data)


@method_decorator(login_required, name='dispatch')
class TasksView(PermissionRequiredMixin, TemplateView):
    permission_required = PERMISSIONS_CAN_SEE_TASKS
    template_name = "vcelerytaskrunner/tasks.html"

    def get_context_data(self, **kwargs):
        context_data = {
            "show_runnable_only": "true" if VCELERY_SHOW_ONLY_RUNNABLE_TASKS else "false",
        }
        return context_data


class TaskRunForm(forms.Form):
    task = forms.CharField(label="Task", max_length=TASKNAME_MAXLEN)
    args = forms.CharField(label="Args", max_length=3000, widget=forms.Textarea, required=False)
    kwargs = forms.CharField(label="KWArgs", max_length=5000, widget=forms.Textarea, required=False)

    def clean_task(self) -> str:
        task_name = self.cleaned_data.get("task")
        if task_name:
            task_info = get_task_info(task_name)
            if not task_info or not task_info['runnable']:
                raise ValidationError(f"Task is not found or runnable.")
        else:
            raise ValidationError("Need a task name.")
        return task_name

    def clean_args(self) -> List[Any]:
        args = self.cleaned_data.get("args") or "[]"
        try:
            args = json.loads(args)
        except Exception as e:
            raise ValidationError("Invalid JSON")

        if not isinstance(args, list):
            raise ValidationError("Should be a list of parameters. Read the instructions again.")
        return args

    def clean_kwargs(self) -> Dict[str, Any]:
        kwargs = self.cleaned_data.get("kwargs") or "{}"
        try:
            kwargs = json.loads(kwargs)
        except Exception as e:
            raise ValidationError("Invalid JSON")

        if not isinstance(kwargs, dict):
            raise ValidationError("Should be a dict of named parameters. Read the instructions again.")
        return kwargs


@method_decorator(login_required, name='dispatch')
class TaskRunFormView(PermissionRequiredMixin, FormView):
    permission_required = PERMISSIONS_CAN_SEE_AND_RUN_TASKS
    template_name = "vcelerytaskrunner/task_run.html"
    form_class = TaskRunForm

    def get(self, request, *args, **kwargs):
        task = request.GET.get("task")

        if task:
            task_info = get_task_info(task)
        if not task or not task_info or not task_info['runnable']:
            logger.error(
                "Non-existent or not runnable task %s requested by %s", task, request.user
            )
            return HttpResponseRedirect(reverse("vcelery-tasks"))

        self.task = task
        return super().get(request, args, kwargs)

    def get_context_data(self, **kwargs):
        """Insert the form into the context dict."""
        context_data = super().get_context_data(**kwargs)

        # if a task name was provided, then prefill
        if hasattr(self, "task"):
            context_data["form"]["task"].initial = self.task

        return context_data

    def post(self, request, *args, **kwargs):
        # Just so we can record the request.user to be used by form_valid later
        self.user = request.user

        return super().post(request, args, kwargs)

    def form_valid(self, form):
        task_from_form = form.cleaned_data['task']
        args_from_form = form.cleaned_data['args']
        kwargs_from_form = form.cleaned_data['kwargs']

        try:
            result = run_and_record(task_from_form, args=args_from_form, kwargs=kwargs_from_form, user=self.user)
            url = reverse("vcelery-task-run-result", kwargs={'task_id': result.id})
            return HttpResponseRedirect(url)
        except Exception as e:
            errors = form._errors.setdefault(NON_FIELD_ERRORS, ErrorList())
            errors.append(f"Error: {e}")
            return self.form_invalid(form)


class TaskRunResultView(TemplateView):
    template_name = "vcelerytaskrunner/task_run_result.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
            "task_id": kwargs.get("task_id"),
        })

        return context
