from datetime import datetime
import inspect
import json
import logging
from collections import OrderedDict
from dataclasses import dataclass
from inspect import Parameter, Signature
from typing import Dict, Optional, Set, _GenericAlias, List, Any, Type
try:
    from typing_extensions import TypedDict
except:
    from typing import TypedDict

try:
    from typing_extensions import _AnnotatedAlias
except:
    from typing import _AnnotatedAlias

from pydantic import BaseModel


from celery.local import Proxy

logger = logging.getLogger(__name__)


@dataclass
class DefaultValue:
    value: Any


class TaskInfo(TypedDict):
    """
    Task name and whether it is runnable
    """
    name: str
    runnable: bool


DEFAULT_PAGE_SIZE = 40


class TaskFilter(TypedDict):
    mask: str
    runnable_only: bool


class LimitOffsetPagination(TypedDict):
    offset: int
    limit: int


class TaskInfosWithCount(TypedDict):
    task_infos: List[TaskInfo]
    count: int


@dataclass
class TaskParameter:
    name: str
    annotation : Type
    type_info: Optional[str] = None
    is_base_model: bool = False
    json_schema: Optional[Dict] = None
    default: Optional[DefaultValue] = None

    class Encoder(json.JSONEncoder):
        def default(self, o):
            if hasattr(o, "to_dict"):
                return o.to_dict()
            if isinstance(o, datetime):
                return o.isoformat()            
            if isinstance(o, TaskParameter):
                return o.to_dict()
            if isinstance(o, DefaultValue):
                return o.value
            return super().default(o)

    @classmethod
    def from_parameter(cls, parameter: Parameter) -> "TaskParameter":
        annotation = parameter.annotation
        is_base_model = False
        json_schema = None
        type_info = None

        if isinstance(annotation, _AnnotatedAlias):
            # If the parameter is annotated, just use the underlying type and ignore the metadata
            annotation = annotation.__origin__

        if isinstance(annotation, _GenericAlias):
            type_info = str(annotation).replace("typing.", "").replace("typing_extensions.", "")
        elif annotation == Signature.empty:
            pass
        elif isinstance(annotation, type):
            type_info = annotation.__name__
            if issubclass(annotation, BaseModel):
                is_base_model = True
                json_schema = annotation.model_json_schema()
        else:
            type_info = str(annotation)

        inst = cls(name=parameter.name, annotation=annotation, type_info=type_info, is_base_model=is_base_model, json_schema=json_schema)
        if parameter.default != Parameter.empty:
            val = parameter.default
            inst.default = DefaultValue(value=val)

        return inst

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type_info": self.type_info,
            "is_base_model": self.is_base_model,
            "json_schema": self.json_schema,
            "default": self.default.value if self.default is not None else None
        }

    @staticmethod
    def json_encoder() -> Type[json.JSONEncoder]:
        return TaskParameter.Encoder
        

class TaskRegistry:
    """
    Registry of Celery tasks with methods to query for task names and to look up tasks for a name.
    """
    tasks = OrderedDict()  # type: Dict[str, Proxy]
    task_names = []

    def __init__(self, celery_app, runnable_tasks: Optional[Set[str]] = None):
        self.celery_app = celery_app

        self.runnable_tasks = None
        self.runnable_tasks_set = set()
        if runnable_tasks is not None:
            self.runnable_tasks = runnable_tasks.copy()
            self.runnable_tasks_set = set(self.runnable_tasks)

        if not self.tasks:
            self._refresh_registry()

    def _refresh_registry(self):
        logger.info("Refreshing tasks registry")
        self.celery_app.autodiscover_tasks(force=True)

        self.tasks.clear()
        self.tasks.update(self.celery_app.tasks)
        self.task_names.clear()

        # Assumption: self.task_names is of a "manageable" number to store in memory. Are there systems where the
        # number of celery tasks exceed comfortable memory footprint?
        self.task_names.extend(sorted(name for name in self.tasks.keys() if not name.startswith("celery")))

        logger.info(f"{len(self.task_names)} task(s) found: {self.task_names}")
        if self.runnable_tasks is None:
            logger.warning("No VCELERY_TASKRUN_RUNNABLE_TASKS configured, so all tasks are runnable.")
        elif not self.runnable_tasks:
            logger.warning("VCELERY_TASKRUN_RUNNABLE_TASKS is empty, so NO tasks are runnable.")
        else:
            logger.info(f"Runnable task(s): {self.runnable_tasks}")

    def get_task_infos(
        self,
        task_filter: Optional[TaskFilter],
        pagination: Optional[LimitOffsetPagination] = None
    ) -> TaskInfosWithCount:
        """
        Filters list of recognized task names against a white list of tasks names that are runnable.

        :param task_filter: optional filter parameters to use to filter results
        :param pagination: optional pagination for the results (defaults to the first DEFAULT_PAGE_SIZE entries)

        :return: TaskInfo on recognized tasks
        """
        pagination = pagination or LimitOffsetPagination(offset=0, limit=DEFAULT_PAGE_SIZE)
        mask = task_filter['mask']
        runnable_only = task_filter['runnable_only']

        mask = mask.lower() if mask else None
        offset = max(0, pagination['offset'])
        limit = max(0, pagination['limit'])

        if mask:
            matched_task_names = [task_name for task_name in self.task_names if mask in task_name.lower()]
        else:
            matched_task_names = self.task_names

        if runnable_only and self.runnable_tasks is not None:
            matched_task_names = [
                task_name for task_name in matched_task_names
                if task_name in self.runnable_tasks_set
            ]

        return TaskInfosWithCount(
            task_infos=[
                TaskInfo(
                    name=task_name,
                    runnable=(self.runnable_tasks is None) or (task_name in self.runnable_tasks_set)
                )
                for task_name in matched_task_names[offset:offset+limit]
            ],
            count=len(matched_task_names)
        )

    def get_task_info(self, task_name: str) -> Optional[TaskInfo]:
        """
        Filters list of recognized task names against an exact task name.

        :param task_name: the task name to filter by

        :return: TaskInfo on the task (if found)
        """
        task_info = None

        task = self.get_task(task_name)
        if task:
            task_info = TaskInfo(
                name=task_name,
                runnable=(self.runnable_tasks is None) or (task_name in self.runnable_tasks)
            )
        return task_info

    def get_task(self, task_name: str) -> Optional[Proxy]:
        """
        Looks up a task by a task name

        :param task_name: the name of the task to look up

        :return: task matching the name (or None)
        """
        return self.tasks.get(task_name)

    def get_task_parameters(self, task_name: str) -> List[TaskParameter]:
        """
        Looks up the parameters from a Celery task based on its name. If found, iterate through its parameters and
        return information about them.

        :param task_name: the name of the Celery task

        :return: the parameters extracted (can be empty)
        """
        parameters = []

        task = self.get_task(task_name)
        if task:
            signature = inspect.signature(task)
            for _, parameter in signature.parameters.items():
                parameters.append(TaskParameter.from_parameter(parameter))
        return parameters
