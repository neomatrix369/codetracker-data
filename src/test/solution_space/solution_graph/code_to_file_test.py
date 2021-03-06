# Copyright (c) 2020 Anastasiia Birillo, Elena Lyulina

import os
import logging
import unittest
from typing import List, Tuple

import pytest

from src.test.test_config import to_skip, TEST_LEVEL
from src.main.canonicalization.consts import TREE_TYPE
from src.main.util.language_util import get_extension_by_language
from src.main.solution_space.solution_graph import SolutionGraph, Vertex
from src.main.util.consts import LOGGER_NAME, TASK, FILE_SYSTEM_ITEM, LANGUAGE
from src.main.util.file_util import get_all_file_system_items, remove_directory
from src.test.solution_space.solution_graph.util import get_two_vertices, init_default_ids
from src.main.solution_space.consts import GRAPH_FOLDER_PREFIX, SOLUTION_SPACE_TEST_FOLDER, FILE_PREFIX

log = logging.getLogger(LOGGER_NAME)

CURRENT_TASK = TASK.PIES
NOT_DEFAULT_GRAPH_PREFIX = 'test_graph'
NOT_DEFAULT_FILE_PREFIX = 'test_code'
SolutionGraph.solution_space_folder = SOLUTION_SPACE_TEST_FOLDER
GRAPHS_PARENT_FOLDER = os.path.join(SOLUTION_SPACE_TEST_FOLDER, str(CURRENT_TASK.value))


def get_full_paths(short_paths: List[str]) -> List[str]:
    return [os.path.join(GRAPHS_PARENT_FOLDER, s_p) for s_p in short_paths]


def create_three_graphs() -> Tuple[int, SolutionGraph, SolutionGraph, SolutionGraph]:
    sg_0 = SolutionGraph(CURRENT_TASK)
    sg_1 = SolutionGraph(CURRENT_TASK, file_prefix=NOT_DEFAULT_FILE_PREFIX)
    sg_2 = SolutionGraph(CURRENT_TASK, graph_folder_prefix=NOT_DEFAULT_GRAPH_PREFIX,
                         file_prefix=NOT_DEFAULT_FILE_PREFIX)
    return 3, sg_0, sg_1, sg_2


# Since {graph_n} graphs were created, several empty_vertices were created also,
# so first {graph_n} code ids are already taken.
# All next vertices will have code ids started from {graph_n}
def get_range(graph_n: int, vertices: List[Vertex]) -> range:
    return range(graph_n, len(vertices) + graph_n)


def get_actual_graph_folders() -> List[str]:
    return get_all_file_system_items(GRAPHS_PARENT_FOLDER, item_type=FILE_SYSTEM_ITEM.SUBDIR)


def get_actual_code_files(graph_folder_name: str) -> List[str]:
    return get_all_file_system_items(os.path.join(GRAPHS_PARENT_FOLDER, graph_folder_name))


def get_expected_files(graph_id: int, code_id: int, anon_tree_id: int, graph_prefix: str = GRAPH_FOLDER_PREFIX,
                       file_prefix: str = FILE_PREFIX,
                       language: LANGUAGE = LANGUAGE.PYTHON) -> List[str]:
    ext = get_extension_by_language(language).value
    graph_folder_name = f'{graph_prefix}_{graph_id}'
    code_file_prefix = f'{file_prefix}_{code_id}'
    return [os.path.join(GRAPHS_PARENT_FOLDER, graph_folder_name,
                         f'{code_file_prefix}_{TREE_TYPE.ANON.value}_{anon_tree_id}{ext}')]


def get_expected_empty_file(graph_id: int, graph_prefix: str = GRAPH_FOLDER_PREFIX, file_prefix: str = FILE_PREFIX,
                            language: LANGUAGE = LANGUAGE.PYTHON) -> str:
    # Empty vertex is created together with graph, so its code_id and anon_tree_id are equal to graph_id.
    # Example:
    # 1. First graph (graph_id is 0) is created -> SerializedCode (code_id is 0) for empty vertex is created ->
    #    -> AnonTree (anon_tree_id is 0) for empty vertex is created
    # 2. Second graph (graph_id is 1) is created -> SerializedCode (code_id is 1) for empty vertex is created ->
    #    -> AnonTree (anon_tree_id is 1) for empty vertex is created
    # 3. ... and so on
    return get_expected_files(graph_id, graph_id, graph_id, graph_prefix, file_prefix, language)[0]


def delete_graphs_parent_folder() -> None:
    remove_directory(GRAPHS_PARENT_FOLDER)


@pytest.mark.skipif(to_skip(current_module_level=TEST_LEVEL.SOLUTION_SPACE), reason=TEST_LEVEL.SOLUTION_SPACE.value)
class TestCodeToFile:

    # Create three graphs and check all folders names which were created for each graph
    def test_folders_names(self) -> None:
        delete_graphs_parent_folder()
        init_default_ids()
        create_three_graphs()

        expected_folders_names = get_full_paths([f'{GRAPH_FOLDER_PREFIX}_0',
                                                 f'{GRAPH_FOLDER_PREFIX}_1',
                                                 f'{NOT_DEFAULT_GRAPH_PREFIX}_2'])
        case = unittest.TestCase()
        case.assertCountEqual(expected_folders_names, get_actual_graph_folders())

    def test_folder_structure_with_default_files_names(self) -> None:
        init_default_ids()
        graph_n, sg_0, _, _ = create_three_graphs()
        vertices = get_two_vertices(sg_0)
        expected_files = sum([get_expected_files(sg_0.id, i, i) for i in get_range(graph_n, vertices)], [])
        expected_files.append(get_expected_empty_file(sg_0.id))
        actual_files = get_actual_code_files(f'{GRAPH_FOLDER_PREFIX}_{sg_0.id}')
        case = unittest.TestCase()
        case.assertCountEqual(expected_files, actual_files)

    def test_folder_structure_with_not_default_files_names(self) -> None:
        init_default_ids()
        graph_n, _, sg_1, _ = create_three_graphs()
        vertices = get_two_vertices(sg_1)
        expected_files = sum([get_expected_files(sg_1.id, i, i, file_prefix=NOT_DEFAULT_FILE_PREFIX)
                              for i in get_range(graph_n, vertices)], [])
        expected_files.append(get_expected_empty_file(sg_1.id, file_prefix=NOT_DEFAULT_FILE_PREFIX))
        actual_files = get_actual_code_files(f'{GRAPH_FOLDER_PREFIX}_{sg_1.id}')
        case = unittest.TestCase()
        case.assertCountEqual(expected_files, actual_files)

    def test_folder_structure_with_all_not_default_names(self) -> None:
        init_default_ids()
        graph_n, _, _, sg_2 = create_three_graphs()
        vertices = get_two_vertices(sg_2)
        expected_files = sum([get_expected_files(sg_2.id, i, i, NOT_DEFAULT_GRAPH_PREFIX, NOT_DEFAULT_FILE_PREFIX)
                              for i in get_range(graph_n, vertices)], [])
        expected_files.append(get_expected_empty_file(sg_2.id, NOT_DEFAULT_GRAPH_PREFIX, NOT_DEFAULT_FILE_PREFIX))
        actual_files_names = get_actual_code_files(f'{NOT_DEFAULT_GRAPH_PREFIX}_{sg_2.id}')
        case = unittest.TestCase()
        case.assertCountEqual(expected_files, actual_files_names)
