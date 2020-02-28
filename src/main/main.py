import datetime
import logging
import os
import sys

import pandas as pd

sys.path.append('.')
from src.main.splitting.splitting import run_tests
from src.main.util import consts
from src.main.util.consts import PATH_CMD_ARG, LOGGER_FORMAT
from src.main.util.file_util import add_slash

from src.main.statistics_gathering.get_statistics import get_statistics

pd.set_option('display.max_rows', 250)
pd.set_option('display.max_columns', 100)

log = logging.getLogger(consts.LOGGER_NAME)


def __get_data_path():
    args = sys.argv
    path = args[args.index(PATH_CMD_ARG) + 1]
    if not os.path.isdir(path):
        log.error(f'It is not a folder, passed path is {path}')
        sys.exit(1)
    return add_slash(path)


def main():
    logging.basicConfig(filename=consts.LOGGER_FILE, format=LOGGER_FORMAT, level=logging.INFO)
    path = __get_data_path()

    # preprocess data before splitting
    # preprocess_data(path)

    # run tests for all tasks and write their results in ct data
    # pass the path from previous action?
    # log.info(f'Current time: {str(datetime.datetime.now())}')
    # run_tests(path)
    # log.info(f'Current time: {str(datetime.datetime.now())}')

    log.info(f'Current time: {str(datetime.datetime.now())}')
    get_statistics(path)
    log.info(f'Current time: {str(datetime.datetime.now())}')


    # there should be splitting then


if __name__ == '__main__':
    main()
