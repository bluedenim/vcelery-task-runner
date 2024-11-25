from datetime import datetime
from backports.zoneinfo import ZoneInfo
from celery import shared_task
from celery.utils.log import get_task_logger
from typing_extensions import Annotated

from vcelerydev.models.payment import Payment

logger = get_task_logger(__name__)


PACIFIC_TZ_NAME = "America/Los_Angeles"


@shared_task
def say_hello(to_name: str = "My little friend") -> str:
    message = f"Hello, {to_name}."
    logger.info(message)
    return message


@shared_task
def count_for_me(my_name: str, count_to: int, step: int = 1) -> None:
    logger.info(f"Counting to {count_to} with step {step} for {my_name}:")
    for i in range(0, count_to+1, step):
        logger.info(f" {i}")


@shared_task
def to_timezone(dt: datetime, to_tz: str = PACIFIC_TZ_NAME) -> datetime:
    tz = ZoneInfo(to_tz)
    new_dt = dt.astimezone(tz)
    logger.info(f"{dt.isoformat()} in {tz} is {new_dt.isoformat()}")


@shared_task
def process_incoming_payment(payer: str, payment: Payment) -> None:
    logger.info(f"Processing incoming payment from {payer}: {payment}")


@shared_task
def legacy_task(a_name, an_integer):
    message = f"This is a name: {a_name}, and this is a number: {0 + an_integer}."
    logger.info(message)
    return message


@shared_task
def task_with_annotated_param(annotated_var: Annotated[int, "the annotated variable"])  -> None:
    logger.info(f"task with annotated param called with {0 + annotated_var}.")
