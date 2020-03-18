# Copyright (c) 2020 Anastasiia Birillo, Elena Lyulina

import ast
import logging
import pandas as pd
from typing import List

from src.main.util import consts
from src.main.preprocessing.code_tracker_handler import get_ct_language
from src.main.util.file_util import get_all_file_system_items, ct_file_condition, get_result_folder, \
    write_based_on_language, get_name_from_path, get_parent_folder_name, get_extension_from_file

log = logging.getLogger(consts.LOGGER_NAME)

TESTS_RESULTS = consts.CODE_TRACKER_COLUMN.TESTS_RESULTS.value
CHOSEN_TASK = consts.CODE_TRACKER_COLUMN.CHOSEN_TASK.value
TASK_STATUS = consts.CODE_TRACKER_COLUMN.TASK_STATUS.value


def unpack_tests_results(tests_results: str, tasks: list) -> list:
    tests_results = ast.literal_eval(tests_results)
    if len(tests_results) != len(tasks):
        log.error(f'Cannot identify tasks because of unexpected tests_results length: {len(tests_results)}')
        raise ValueError(f'Cannot identify tasks because of unexpected tests_results length: {len(tests_results)}')
    return tests_results


def get_solved_task(tests_results: str) -> str:
    tasks = consts.TASK.tasks_values()
    tests_results = unpack_tests_results(tests_results, tasks)
    solved_tasks = [t for i, t in enumerate(tasks) if tests_results[i] == 1]
    if len(solved_tasks) == 0:
        log.info(f'No solved tasks found, tests results: {tests_results}')
        return consts.DEFAULT_VALUES.TASK.value
    elif len(solved_tasks) == 1:
        log.info(f'Found solved task {solved_tasks[0]}, tests results: {tests_results}')
        return solved_tasks[0]
    else:
        log.error(f'Several tasks are solved: {solved_tasks}, tests results: {tests_results}')
        raise ValueError(f'Several tasks are solved: {solved_tasks}, tests results: {tests_results}')


def find_splits(ct_df: pd.DataFrame) -> pd.DataFrame:
    # fill chosen task according to solved task
    ct_df[CHOSEN_TASK] = ct_df.apply(lambda row: get_solved_task(row[TESTS_RESULTS]), axis=1)

    # change task status according to chosen task
    ct_df.loc[ct_df[CHOSEN_TASK].isnull(), TASK_STATUS] = consts.DEFAULT_VALUES.TASK_STATUS.value
    ct_df.loc[ct_df[CHOSEN_TASK].notnull(), TASK_STATUS] = consts.TASK_STATUS.SOLVED.value

    # backward fill chosen task
    ct_df[CHOSEN_TASK] = ct_df[CHOSEN_TASK].bfill()
    return ct_df


# to find start index for each group of rows with the same task
def find_task_start_indices(df: pd.DataFrame, task: consts.TASK) -> List[int]:
    # an index is the start index for some task, if CHOSEN_TASK at this index equals task, but at index-1 -- doesn't,
    # so we should compare it with shifted dataframe
    return df.index[(df[CHOSEN_TASK] == task.value) & (df[CHOSEN_TASK].shift(1) != task.value)].tolist()


def find_task_dfs(df: pd.DataFrame, task: consts.TASK) -> List[pd.DataFrame]:
    start_indices = find_task_start_indices(df, task)
    split_indices = zip(start_indices, start_indices[1:] + [df.shape[0]])
    # split df into several dfs with only one group of rows with the same task
    split_dfs = [df[start_index:end_index] for start_index, end_index in split_indices]
    # in each df find this group of rows with the same task
    return [split_df[split_df[CHOSEN_TASK] == task.value] for split_df in split_dfs]


# 2.0 version with a different task_df extraction
def split_tasks_into_separate_files(path: str, result_name_suffix='tasks_2') -> None:
    files = get_all_file_system_items(path, ct_file_condition, consts.FILE_SYSTEM_ITEM.FILE.value)
    result_folder = get_result_folder(path, result_name_suffix)
    for file in files:
        log.info(f'Start splitting file {file}')
        ct_df = pd.read_csv(file, encoding=consts.ISO_ENCODING)
        language = get_ct_language(ct_df)
        split_df = find_splits(ct_df)
        for task in consts.TASK.tasks():
            task_dfs = find_task_dfs(split_df, task)
            for i, task_df in enumerate(task_dfs):
                if not task_df.empty:
                    # change name to get something like pies/ati_207_test_5894859_i.csv
                    filename = task.value + '/' + get_parent_folder_name(file) + '_' + get_name_from_path(file, False) + f'_{i}' + get_extension_from_file(file)
                    write_based_on_language(result_folder, filename, task_df, language)
