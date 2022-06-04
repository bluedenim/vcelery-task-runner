from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task
def ha_ha_ha(name:str = "Alan Smithee", an_int: int = 0) -> bool:
    logger.info(f"ha_ha_ha: {name}, {an_int}")
    return True


@shared_task
def ha_ha_ha2(name:str = "Alan Smithee", an_int: int = 0) -> bool:
    logger.info(f"ha_ha_ha: {name}, {an_int}")
    return True


@shared_task
def ha_ha_ha3(name:str = "Alan Smithee", an_int: int = 0) -> bool:
    logger.info(f"ha_ha_ha: {name}, {an_int}")
    return True


@shared_task
def ha_ha_ha4(name:str = "Alan Smithee", an_int: int = 0) -> bool:
    logger.info(f"ha_ha_ha: {name}, {an_int}")
    return True


@shared_task
def ha_ha_ha5(name:str = "Alan Smithee", an_int: int = 0) -> bool:
    logger.info(f"ha_ha_ha: {name}, {an_int}")
    return True


@shared_task
def ha_ha_ha6(name:str = "Alan Smithee", an_int: int = 0) -> bool:
    logger.info(f"ha_ha_ha: {name}, {an_int}")
    return True


@shared_task
def ha_ha_ha7(name:str = "Alan Smithee", an_int: int = 0) -> bool:
    logger.info(f"ha_ha_ha: {name}, {an_int}")
    return True


@shared_task
def ha_ha_ha8(name:str = "Alan Smithee", an_int: int = 0) -> bool:
    logger.info(f"ha_ha_ha: {name}, {an_int}")
    return True


@shared_task
def he_he(name:str = "Alan Smithee", an_int: int = 40) -> bool:
    logger.info(f"he_he: {name}, {an_int}")
    return True
