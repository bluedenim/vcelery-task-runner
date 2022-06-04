import logging
from datetime import timedelta
from typing import Any, Dict, Optional, Callable, List

from celery.result import AsyncResult
from django import dispatch
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.dispatch import receiver

from vcelerytaskrunner.models import TaskRunRecord
from vcelerytaskrunner.services.task_registry import (
    TaskRegistry,
    TaskInfo,
    LimitOffsetPagination,
    TaskInfosWithCount,
    TaskFilter,
)

logger = logging.getLogger(__name__)

celery_app = settings.VCELERY_TASKRUN_CELERY_APP
runnable_tasks = getattr(settings, "VCELERY_TASKRUN_RUNNABLE_TASKS", None)

TaskRunCallable = Callable[[str, str, List[Any], Dict[str, Any]], None]


TaskRunSignal = dispatch.Signal()
"""
Signal to listen to for notifications of task run events. The kwargs provided to listeners:

    task_name - name of the task
    task_id - ID of the task run
    args - positional arguments passed to the task
    kwargs - keyword arguments passed to the task
    user - User who ran the task (can be None)
"""


class TaskRunner:
    """
    Run tasks with args and kwargs parameters.
    """

    def __init__(self, task_registry: TaskRegistry, post_task_run: Optional[TaskRunCallable]):
        self.task_registry = task_registry
        self.post_task_run = post_task_run

    def run_task(
        self,
        task_name: str,
        args: List[Any],
        kwargs: Dict[str, Any],
        user: Optional[AbstractUser] = None,
        delay: timedelta = None
    ) -> AsyncResult:
        """
        Run a Celery task given its name and the parameters to pass to the task.

        :param task: the task name
        :param args: optional position arguments to the task
        :param kwargs: optional keyword arguments (kwargs) to the task
        :param user: optional User running the task
        :param delay: optional timedelta indicating the time to delay before actually running the task

        :return: an AsyncResult for the task run
        """
        task = self.task_registry.get_task(task_name)
        if task:
            result = task.apply_async(args=args, kwargs=kwargs, countdown=delay.total_seconds() if delay else None)
            TaskRunSignal.send_robust(
                sender=self.__class__, task_name=task_name, task_id=result.id, args=args, kwargs=kwargs, user=user
            )
            if self.post_task_run:
                self.post_task_run(task_name, result.id, args, kwargs)
        else:
            raise ValueError(f"No task found for name {task_name}")
        return result


def run_and_record(
    task: str, args: List[Any], kwargs: Dict[str, Any], user: AbstractUser, delay: Optional[timedelta] = None
) -> AsyncResult:
    """
    Helper function to run a task and record its running context as a TaskRunRecord.

    :param task: the task name
    :param args: optional position arguments to the task
    :param kwargs: optional keyword arguments (kwargs) to the task
    :param user: the User running the task (can be None if anonymous task run support is enabled)
    :param delay: optional timedelta indicating the time to delay before actually running the task

    :return: an AsyncResult for the task run
    """
    if task:
        def on_task_post_run(task_name: str, task_id: str, args: List[Any], kwargs: Dict[str, Any]) -> None:
            TaskRunRecord.objects.record_run_task(task_name, task_id, args, kwargs, user=user)

        logger.info(f"runnable_tasks={runnable_tasks}, task={task}")
        if runnable_tasks is not None and task not in runnable_tasks:
            raise ValidationError(f"task {task} is not runnable. Check task name and setting TASKRUN_RUNNABLE_TASKS.")

        try:
            task_registry = TaskRegistry(celery_app, runnable_tasks)
            task_runner = TaskRunner(task_registry, post_task_run=on_task_post_run)

            result = task_runner.run_task(task, args, kwargs, user=user, delay=delay)
        except Exception as e:
            logger.exception(
                "Cannot run task %s with (args=%s, kwargs=%s): %s",
                task, args, kwargs, e
            )
            raise
    else:
        raise ValueError("task name required")
    return result


@receiver(TaskRunSignal, sender=TaskRunner)
def task_run_listener(sender, **kwargs):
    """
    Example of a signal handler for task run events.
    """
    task_name = kwargs['task_name']
    task_id = kwargs['task_id']
    task_run_args = kwargs['args']
    task_run_kwargs = kwargs['kwargs']
    user = kwargs.get('user')

    logger.info(
        f"task_run_listener: task {task_name} (ID {task_id}) run by {user}"
        f" with args={task_run_args}, kwargs={task_run_kwargs}"
    )


def get_task_infos(task_filter: TaskFilter, pagination: Optional[LimitOffsetPagination] = None
) -> TaskInfosWithCount:
    """
    Collects a list of runnable tasks' names and return them.

    :param mask: optional search mask to filter by
    :param runnable_only: optional flag to filter tasks for only ones runnable
    :param pagination" optional pagination options

    :return: tasks that can be run by run_and_record() function
    """
    task_registry = TaskRegistry(celery_app, runnable_tasks)

    return task_registry.get_task_infos(task_filter, pagination=pagination)


def get_task_info(task_name: str) -> Optional[TaskInfo]:
    """
    Find a task by the name using EXACT match.

    :param task_name: the name to find a task by (case-sensitive)

    :return: a TaskInfo if found
    """
    task_registry = TaskRegistry(celery_app, runnable_tasks)
    return task_registry.get_task_info(task_name)
