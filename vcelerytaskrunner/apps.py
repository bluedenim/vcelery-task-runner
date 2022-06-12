import logging
from datetime import timedelta, datetime

from django.apps import AppConfig
from django.conf import settings
from django.utils.timezone import get_current_timezone

logger = logging.getLogger(__name__)


TASK_RUN_RECORD_LONGEVITY_PERMANENT = "PERMANENT"


class AppConfig(AppConfig):
    name = 'vcelerytaskrunner'

    def _prune_task_run_records(self, prune_records_created_before: datetime):
        try:
            TaskRunRecord = self.get_model(f"{self.name}.TaskRunRecord")

            records_to_prune = TaskRunRecord.objects.filter(created_at__lt=prune_records_created_before)

            if records_to_prune.exists():
                logger.warning(
                    f"Pruning {records_to_prune.count()} TaskRunRecords created before {prune_records_created_before}"
                )
                records_to_prune.delete()
        except LookupError:
            pass

    def ready(self):
        task_run_record_longevity = getattr(settings, "VCELERY_TASK_RUN_RECORD_LONGEVITY", None)
        perform_prune = True

        if task_run_record_longevity is None:
            logger.warning("VCELERY_TASK_RUN_RECORD_LONGEVITY is not set or not a timedelta. Assuming 4 weeks")
            task_run_record_longevity = timedelta(weeks=4)
        elif task_run_record_longevity == TASK_RUN_RECORD_LONGEVITY_PERMANENT:
            perform_prune = False
        elif not isinstance(task_run_record_longevity, timedelta):
            raise ValueError("VCELERY_TASK_RUN_RECORD_LONGEVITY must be a timedelta.")

        if perform_prune:
            logger.info(f"Pruning TaskRunRecords older than {task_run_record_longevity}")

            now = datetime.utcnow()
            if settings.USE_TZ:
                now = datetime.now(get_current_timezone())
            if task_run_record_longevity.total_seconds() > 0:
                prune_before = now - task_run_record_longevity
            else:
                prune_before = now + task_run_record_longevity

            self._prune_task_run_records(prune_before)
        else:
            logger.info("VCELERY_TASK_RUN_RECORD_LONGEVITY set to PERMANENT. Skipping pruning.")
