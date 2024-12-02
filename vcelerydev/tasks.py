from datetime import datetime
from typing import List, Dict, Literal

from backports.zoneinfo import ZoneInfo
from celery import shared_task
from celery.utils.log import get_task_logger
from typing_extensions import Annotated

from vcelerydev.models.payment import Payment

logger = get_task_logger(__name__)


PACIFIC_TZ_NAME = "America/Los_Angeles"


@shared_task
def say_hello(to_name: str = "My little friend") -> str:
    message = f"say_hello: Hello, {to_name}."
    logger.info(message)
    return message


@shared_task
def count_for_me(my_name: str, count_to: int, step: int = 1) -> None:
    logger.info(f"count_for_me: Counting to {count_to} with step {step} for {my_name}:")
    for i in range(0, count_to+1, step):
        logger.info(f"count_for_me: {i}")


@shared_task
def to_timezone(dt: datetime, to_tz: str = PACIFIC_TZ_NAME) -> datetime:
    tz = ZoneInfo(to_tz)
    new_dt = dt.astimezone(tz)
    logger.info(f"to_timezone: {dt.isoformat()} in {tz} is {new_dt.isoformat()}")
    return new_dt


@shared_task
def process_incoming_payment(payer: str, payment: Payment) -> None:
    logger.info(f"process_incoming_payment: Processing incoming payment from {payer}: {payment}")


@shared_task
def legacy_task(a_name, an_integer):
    message = f"legacy_task: This is a_name: {a_name}, and this is an_integer: {an_integer}."
    logger.info(message)
    return message


@shared_task
def task_with_annotated_param(annotated_var: Annotated[int, "the annotated variable"])  -> None:
    logger.info(f"task_with_annotated_param: task with annotated param called with {0 + annotated_var}.")


@shared_task
def process_lists(integers: List[int], strings: List[str]) -> None:
    logger.info(f"process_lists: list of int: {[0 + i  for i in integers]}")
    logger.info(f"process_lists: list of str: {[f'{s}' for s in strings]}")


@shared_task
def process_dicts(items: Dict[Literal["items"], Dict[str, List[int]]]) -> None:
    # {"items": {"one": [1, 2, 3], "two": [4, 5]}}
    for key, ints in items["items"].items():
        logger.info(f"process_dicts: {key}: {ints}")
