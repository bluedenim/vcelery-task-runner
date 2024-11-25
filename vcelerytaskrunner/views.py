import json
import logging
from datetime import datetime, timedelta
from inspect import Parameter
from typing import Any, Dict, List, Optional, _GenericAlias

from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin, AccessMixin
from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponseRedirect, HttpRequest, HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from pydantic import BaseModel

from rest_framework.exceptions import ParseError

from vcelerytaskrunner.services.task_registry import (
    TaskInfo,
    DEFAULT_PAGE_SIZE,
    LimitOffsetPagination,
    TaskFilter,
    TaskRegistry,
    TaskParameter,
)
from vcelerytaskrunner.services.task_runner import run_and_record, get_task_infos, get_task_info, TASK_REGISTRY
from rest_framework.views import APIView


logger = logging.getLogger(__name__)


PERMISSIONS_CAN_SEE_TASKS = ["vcelerytaskrunner.view_taskrunrecord"]
PERMISSIONS_CAN_SEE_AND_RUN_TASKS = ["vcelerytaskrunner.view_taskrunrecord", "vcelerytaskrunner.add_taskrunrecord"]

VCELERY_SHOW_ONLY_RUNNABLE_TASKS = getattr(settings, "VCELERY_SHOW_ONLY_RUNNABLE_TASKS", False)



class TasksAPIView(AccessMixin, APIView):
    """
    Returns a list of Celery tasks
    """

    @staticmethod
    def _create_task_run_url(task_info: TaskInfo) -> str:
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
    """
    Undocumented and not fully supported (yet).
    """
    # curl -d "{\"kwargs\": {\"to_name\":\"John\"}}" -H "Content-Type: application/json" -u root:nothing1234 -XPOST http://localhost:8000/api/task_run/?task=vcelerydev.tasks.say_hello
    # curl -d "{\"kwargs\": {\"to_name\":\"John\"}}" -H "Content-Type: application/json" -u van:nothing1234 -XPOST http://localhost:8000/api/task_run/?task=vcelerydev.tasks.say_hello

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
    """
    Main view that shows all the tasks.
    """
    permission_required = PERMISSIONS_CAN_SEE_TASKS
    template_name = "vcelerytaskrunner/tasks.html"

    def get_context_data(self, **kwargs):
        context_data = {
            "show_runnable_only": "true" if VCELERY_SHOW_ONLY_RUNNABLE_TASKS else "false",
        }
        return context_data


@method_decorator(login_required, name='dispatch')
class TaskRunFormView(PermissionRequiredMixin, TemplateView):
    """
    View where the user can enter parameters to invoke a task.
    """
    permission_required = PERMISSIONS_CAN_SEE_AND_RUN_TASKS
    template_name = "vcelerytaskrunner/task_run.html"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        task_name: Optional[str] = request.GET.get("task")
        task_info: Optional[TaskInfo] = None
        if task_name:
            task_info = get_task_info(task_name)
        if not task_name or not task_info or not task_info['runnable']:
            logger.error(
                "Non-existent or not runnable task %s requested by %s", task_name, request.user
            )
            return HttpResponseRedirect(reverse("vcelery-tasks"))

        return super().get(request, args, kwargs)

    @staticmethod
    def _format_parameter_display_value(task_parameters: List[TaskParameter]) -> List[str]:
        param_displays: List[str] = []

        for task_param in task_parameters:
            display_value = task_param.name
            if task_param.type_info:
                display_value += f": {task_param.type_info}"
            if task_param.default:
                value = task_param.default.value
                if isinstance(value, str):
                    value = f"'{value}'"
                display_value += f" = {value}"
                param_displays.append(display_value)
            else:
                param_displays.append(display_value)

        return param_displays

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        task_name = self.request.GET.get("task")
        context_data = super().get_context_data(**kwargs)

        # if a task name was provided, then prefill
        if task_name:
            task_registry: TaskRegistry = TASK_REGISTRY
            task_params = task_registry.get_task_parameters(task_name)
            
            context_data["task_params"] = task_params
            param_displays = self._format_parameter_display_value(task_params)
            
            context_data["task_param_displays"] = param_displays
            context_data["task"] = task_name

        # Copy the task_id from the cookie (set from a post that redirected here) to the context to be rendered.
        task_id = self.request.COOKIES.pop("task_id", None)
        if task_id:
            context_data["task_id"] = task_id

        # Same for error message
        error_message = self.request.COOKIES.pop("error_message", None)
        if error_message:
            context_data["error_message"] = error_message

        return context_data

    def render_to_response(self, context, **response_kwargs) -> HttpResponse:
        response = super().render_to_response(context, **response_kwargs)

        # We're moved the task_id to the context and rendered the contents by now, so there is no more need for
        # the cookie.
        response.delete_cookie("task_id")
        response.delete_cookie("error_message")

        return response

    def _deserialize_task_param_value(self, task_param: TaskParameter, value: Any) -> Any:
        has_default = task_param.default is not None
        deserialized_value = value
        if value:
            if isinstance(task_param.annotation, _GenericAlias):
                # This only works for values that can be deserialized from JSON e.g. List[int] and List[str]
                deserialized_value = json.loads(value)
            elif issubclass(task_param.annotation, datetime):
                # fromisoformat() doesn't know how to parse "Z"
                if value.endswith("Z"):
                    value = value[:len(value)-1] + "-00:00"
                deserialized_value = datetime.fromisoformat(value)
            elif issubclass(task_param.annotation, BaseModel):
                deserialized_value = task_param.annotation.model_validate_json(value)
            elif task_param.annotation == Parameter.empty:
                logger.warning(f"No type hint available for {task_param.name}. Using str.")
                deserialized_value = str(value)
            else:
                deserialized_value = task_param.annotation(value)
        else:
            if not has_default:
                # Missing parameter
                raise ValueError(f"Missing value for {task_param.name}")
            else:
                deserialized_value = task_param.default.value
        return deserialized_value

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        task_name = request.POST.get("task")
        
        try:
            if task_name:
                task_registry: TaskRegistry = TASK_REGISTRY
                task_params = task_registry.get_task_parameters(task_name)
                
                call_args = []
                call_kwargs= {}
                for task_param in task_params:
                    posted_value = request.POST.get(task_param.name)
                    param_value = self._deserialize_task_param_value(task_param, posted_value)
                
                    if task_param.default is not None:
                        call_kwargs[task_param.name] = param_value
                    else:
                        call_args.append(param_value)
                    
                logger.info(f"Calling task {task_name} with args={call_args}, kwargs={call_kwargs}")
                
                result = task_registry.get_task(task_name).apply_async(args=call_args, kwargs=call_kwargs)
                
                # Redirect back to myself but with a cookie value for the Celery task ID
                url = f"{reverse('vcelery-task-run')}?task={task_name}"
                response = HttpResponseRedirect(url)
                response.set_cookie("task_id", result.id)
                return response
            else:
                raise ValueError(f"Missing task property from {request.POST}")
        except Exception as e:
            msg = f"Error calling {task_name}: {e}"
            logger.exception(msg)


            # Redirect back to myself but with a cookie value for the error message
            url = f"{reverse('vcelery-task-run')}?task={task_name}"
            response = HttpResponseRedirect(url)
            response.set_cookie("error_message", str(e))
            return response
