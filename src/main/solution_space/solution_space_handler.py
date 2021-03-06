# Copyright (c) 2020 Anastasiia Birillo, Elena Lyulina

import ast
import enum
import logging
from typing import Tuple, List, Union, Any

import pandas as pd

from src.main.util import consts
from src.main.util.data_util import Column
from src.main.canonicalization.consts import TREE_TYPE
from src.main.util.log_util import log_and_raise_error
from src.main.solution_space.serialized_code import Code
from src.main.splitting.splitting import unpack_tests_results
from src.main.solution_space.solution_graph import SolutionGraph
from src.main.canonicalization.canonicalization import are_asts_equal, get_trees
from src.main.solution_space.data_classes import AtiItem, Profile, User, CodeInfo
from src.main.util.file_util import get_all_file_system_items, extension_file_condition
from src.main.util.consts import DEFAULT_VALUE, TASK, LANGUAGE, EXTENSION, INT_EXPERIENCE, TEST_RESULT

log = logging.getLogger(consts.LOGGER_NAME)


def __get_column_value(solutions: pd.DataFrame, index: int, column: Column) -> Any:
    return solutions[column.value].iloc[index]


def __get_column_unique_value(solutions: pd.DataFrame, column: Column, default: Any) -> Any:
    column = column.value
    unique_values = solutions[column].unique()
    if len(unique_values) == 0:
        log.info(f'Unique values not found')
        return default
    if len(unique_values) > 1:
        log_and_raise_error(f'There is more than 1 unique value in column {column}: {unique_values}', log)
    return unique_values[0]


def get_enum_or_default(enum_meta: enum.EnumMeta, value: str, default: DEFAULT_VALUE) \
        -> Union[enum.EnumMeta, DEFAULT_VALUE]:
    return enum_meta._value2member_map_.get(value, default)


def __get_ati_data(solutions: pd.DataFrame, index: int) -> AtiItem:
    timestamp = __get_column_value(solutions, index, consts.ACTIVITY_TRACKER_COLUMN.TIMESTAMP_ATI)
    str_event_type = __get_column_value(solutions, index, consts.ACTIVITY_TRACKER_COLUMN.EVENT_TYPE)
    event_type = get_enum_or_default(consts.ACTIVITY_TRACKER_EVENTS, str_event_type, DEFAULT_VALUE.EVENT_TYPE)
    event_data = __get_column_value(solutions, index, consts.ACTIVITY_TRACKER_COLUMN.EVENT_DATA)
    return AtiItem(timestamp=timestamp, event_type=event_type, event_data=event_data)


def __are_same_fragments(current_anon_tree: ast.AST, solutions: pd.DataFrame, next_index: int) -> bool:
    fragment = __get_column_value(solutions, next_index, consts.CODE_TRACKER_COLUMN.FRAGMENT)
    next_anon_tree, = get_trees(fragment, {TREE_TYPE.ANON})
    return are_asts_equal(current_anon_tree, next_anon_tree)


# Get ati data and add it to the ati_elements list if it is not empty
def __handle_current_ati(ati_elements: List[AtiItem], solutions: pd.DataFrame, index: int) -> None:
    ati_element = __get_ati_data(solutions, index)
    if not ati_element.is_empty():
        log.info(f'Find not empty ati element: {ati_element}')
        ati_elements.append(ati_element)


# Find the same code fragments in data and construct list of ati items for this fragment
def __find_same_fragments(solutions: pd.DataFrame, start_index: int) -> Tuple[int, List[AtiItem], ast.AST, ast.AST]:
    i, ati_elements = start_index + 1, []
    __handle_current_ati(ati_elements, solutions, start_index)
    current_fragment = __get_column_value(solutions, start_index, consts.CODE_TRACKER_COLUMN.FRAGMENT)
    current_anon_tree, current_canon_tree = get_trees(current_fragment, {TREE_TYPE.ANON, TREE_TYPE.CANON})

    while i < solutions.shape[0] and __are_same_fragments(current_anon_tree, solutions, i):
        __handle_current_ati(ati_elements, solutions, i)
        i += 1
    return i, ati_elements, current_anon_tree, current_canon_tree


def __get_profile(solutions: pd.DataFrame) -> Profile:
    # Data should be preprocessed so in 'age' and 'experience' columns should be only 1 unique value for each column
    age = __get_column_unique_value(solutions, consts.CODE_TRACKER_COLUMN.AGE, consts.DEFAULT_VALUE.AGE.value)
    str_experience = __get_column_unique_value(solutions, consts.CODE_TRACKER_COLUMN.INT_EXPERIENCE,
                                               consts.DEFAULT_VALUE.INT_EXPERIENCE.value)
    experience = get_enum_or_default(INT_EXPERIENCE, str_experience, DEFAULT_VALUE.INT_EXPERIENCE)
    return Profile(age=age, experience=experience)


def __get_user(solutions: pd.DataFrame) -> User:
    return User(__get_profile(solutions))


def __get_code_info(solutions: pd.DataFrame, user: User, index: int,
                    ati_actions: List[AtiItem]) -> CodeInfo:
    date = __get_column_value(solutions, index, consts.CODE_TRACKER_COLUMN.DATE)
    timestamp = __get_column_value(solutions, index, consts.CODE_TRACKER_COLUMN.TIMESTAMP)
    return CodeInfo(user, timestamp, date, ati_actions)


def __is_compiled(test_result: float) -> bool:
    return test_result != consts.TEST_RESULT.INCORRECT_CODE.value


def __is_correct_fragment(tests_results: str) -> bool:
    tasks = consts.TASK.tasks()
    tests_results = unpack_tests_results(tests_results, tasks)
    compiled_task_count = len([t for i, t in enumerate(tasks) if __is_compiled(tests_results[i])])
    # It is an error, if a part of the tasks is incorrect, but another part is correct.
    # For example: [-1,1,0.5,0.5,-1,-1]
    if 0 < compiled_task_count < len(tasks):
        log_and_raise_error(f'A part of the tasks is incorrect, but another part is correct: {tests_results}', log)
    return compiled_task_count == len(tasks)


def __filter_incorrect_fragments(solutions: pd.DataFrame) -> pd.DataFrame:
    return solutions.loc[solutions[consts.CODE_TRACKER_COLUMN.TESTS_RESULTS.value].apply(__is_correct_fragment)]


def get_task_index(task: TASK) -> int:
    return consts.TASK.tasks().index(task)


def get_rate(tests_results: str, task_index: int) -> float:
    tasks = TASK.tasks()
    tests_results = unpack_tests_results(tests_results, tasks)
    if task_index >= len(tasks) or task_index >= len(tests_results):
        log_and_raise_error(f'Task index {task_index} is more than length of tasks list', log)
    return tests_results[task_index]


def __get_code(solutions: pd.DataFrame, index: int, task_index: int, canon_tree: ast.AST, anon_tree: ast.AST) -> Code:
    tests_results = __get_column_value(solutions, index, consts.CODE_TRACKER_COLUMN.TESTS_RESULTS)
    rate = get_rate(tests_results, task_index)
    log.info(f'Task index is :{task_index}, rate is: {rate}')
    return Code(anon_tree, canon_tree, rate)


def __convert_to_datetime(df: pd.DataFrame) -> None:
    for column in [consts.CODE_TRACKER_COLUMN.DATE, consts.ACTIVITY_TRACKER_COLUMN.TIMESTAMP_ATI]:
        df[column.value] = pd.to_datetime(df[column.value], errors='ignore')


def __create_code_info_chain(file: str, task: TASK) -> List[Tuple[Code, CodeInfo]]:
    log.info(f'Start solution space creating for file {file} for task {task}')
    data = pd.read_csv(file, encoding=consts.ISO_ENCODING)
    __convert_to_datetime(data)
    solutions = __filter_incorrect_fragments(data)
    log.info(f'Size of solutions after filtering incorrect fragments is {solutions.shape[0]}')
    task_index = get_task_index(task)
    i, code_info_chain = 0, []
    user = __get_user(solutions)
    while i < solutions.shape[0]:
        old_index = i
        i, ati_actions, anon_tree, canon_tree = __find_same_fragments(solutions, i)
        code = __get_code(solutions, old_index, task_index, canon_tree, anon_tree)
        code_info = __get_code_info(solutions, user, old_index, ati_actions)
        code_info_chain.append((code, code_info))
    log.info(f'Size of code info chain before removing loops is {len(code_info_chain)}')
    code_info_chain = __remove_loops(code_info_chain, user)
    log.info(f'Size of code info chain after removing loops is {len(code_info_chain)}')
    log.info(f'Finish solution space creating for file {file} for task {task}')
    return code_info_chain


# Todo: find a better way for it
# Todo: handle a case when there is no empty_code in the chain
# Detect loops in code_info_chain and remove all intermediate states which include in the loops
# Before changes: Tree_1 -> Tree_2 -> Tree_3 -> Tree_1 -> Tree_4
# After changes: Tree_1 -> Tree_4
def __remove_loops(code_info_chain: List[Tuple[Code, CodeInfo]], user: User) -> List[Tuple[Code, CodeInfo]]:
    # Add empty code
    # We want to remove loops, but we can have the situation: Tree1 -> Tree2 -> Tree3 -> Empty Tree -> Tree5
    # In the case we will get after loops removing: Tree1 -> Tree2 -> Tree3 -> Empty Tree -> Tree5,
    # but it is incorrect, because we expect Empty Tree -> Tree5
    # If we add empty code, we will have: Empty Tree -> Tree1 -> Tree2 -> Tree3 -> Empty Tree -> Tree5
    # and we will get after loops removing: Empty Tree -> Tree5
    code_info_chain = [(Code.from_source('', TEST_RESULT.CORRECT_CODE.value), CodeInfo(user))] + code_info_chain

    current_tree_index = 0
    while current_tree_index < len(code_info_chain):
        current_anon_tree = code_info_chain[current_tree_index][0].anon_tree
        same_tree_indexes = []
        for next_tree_index in range(current_tree_index + 1, len(code_info_chain)):
            next_anon_tree = code_info_chain[next_tree_index][0].anon_tree
            if are_asts_equal(current_anon_tree, next_anon_tree):
                same_tree_indexes.append(next_tree_index)
        if len(same_tree_indexes) > 0:
            del code_info_chain[current_tree_index:max(same_tree_indexes)]
        current_tree_index += 1
    return code_info_chain


def construct_solution_graph(path: str, task: TASK, language: LANGUAGE = LANGUAGE.PYTHON) -> SolutionGraph:
    files = get_all_file_system_items(path, extension_file_condition(EXTENSION.CSV))
    sg = SolutionGraph(task, language)
    log.info(f'Start creating solution space from path {path}')
    for file in files:
        log.info(f'Start handling file {file}')
        code_info_chain = __create_code_info_chain(file, task)
        sg.add_code_info_chain(code_info_chain)
    log.info(f'Finish creating solution space from path {path}')
    log.info('Start finding medians')
    sg.find_all_medians()
    log.info('Finish finding medians')
    return sg
