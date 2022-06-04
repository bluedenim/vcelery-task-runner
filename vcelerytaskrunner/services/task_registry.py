import logging
from collections import OrderedDict
from typing import Dict, Iterator, Optional, Set
from typing_extensions import TypedDict

from celery.local import Proxy

logger = logging.getLogger(__name__)


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
    task_infos: Iterator[TaskInfo]
    count: int


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
            logger.warning("No TASKRUN_RUNNABLE_TASKS configured, so all tasks are runnable.")
        elif not self.runnable_tasks:
            logger.warning("TASKRUN_RUNNABLE_TASKS is empty, so NO tasks are runnable.")
        else:
            logger.info(f"Runnable task(s): {self.runnable_tasks}")

    def get_task_infos(
        self,
        task_filter: Optional[TaskFilter],
        pagination: Optional[LimitOffsetPagination] = None
    ) -> TaskInfosWithCount:
        """
        Filters list of recognized task names against a white list of tasks names that are runnable.

        :param mask: optional mask to filter by
        :param runnable_only: optional flag to filter tasks for only ones runnable (default is True)
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
        Filters list of recognized task names against a exact task name.

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
