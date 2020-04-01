# Copyright (c) 2020 Anastasiia Birillo, Elena Lyulina

import logging
from typing import Type
from logging import Logger

from src.main.util.consts import LOGGER_FORMAT, LOGGER_FILE, LOGGER_TEST_FILE


def log_and_raise_error(msg: str, log: Logger, error: Type[Exception] = ValueError) -> None:
    log.error(msg)
    raise error(msg)


def configure_logger(in_test_mode: bool = False) -> None:
    filename = LOGGER_TEST_FILE if in_test_mode else LOGGER_FILE
    logging.basicConfig(filename=filename, format=LOGGER_FORMAT, level=logging.INFO)