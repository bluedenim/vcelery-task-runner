from typing import Any, Dict, Optional, List

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import CharField, TextField, DateTimeField, ForeignKey


TASKNAME_MAXLEN = 200


class TaskRunRecordManager(models.Manager):

    def record_run_task(
        self, task_name: str, task_id: str, args: List[Any], kwargs: Dict[str, Any], user: Optional[AbstractUser] = None
    ) -> "TaskRunRecord":
        """
        Create and save a record for a task run.

        :param task_name: the name of the task that was run
        :param task_id: the task ID
        :param args: optional positional arguments passed to the task
        :param kwargs: optional keyword arguments passed to the task
        :param user: optional User who ran the task

        :return: an instance of TaskRunRecord created
        """
        run_with = f"args={args}, kwargs={kwargs}"
        if user and user.is_anonymous:
            if getattr(settings, "TASKRUN_ALLOW_ANONYMOUS_USER", False):
                user = None
            else:
                raise PermissionDenied("Set TASKRUN_ALLOW_ANONYMOUS_USER to allow anonymous users.")
        return super().create(task_name=task_name, task_id=task_id, run_by=user, run_with=run_with)


class TaskRunRecord(models.Model):
    task_name = CharField(max_length=TASKNAME_MAXLEN, db_index=True)
    task_id = CharField(max_length=100, db_index=True)
    run_by = ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, null=True, blank=True)
    run_with = TextField(help_text="The params the task was run with")

    created_at = DateTimeField(auto_now_add=True, db_index=True)

    objects = TaskRunRecordManager()

    def __str__(self) -> str:
        return f"Task {self.task_name} (ID {self.task_id}) run by {self.run_by} at {self.created_at.isoformat()}"
