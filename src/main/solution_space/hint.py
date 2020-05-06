# Copyright (c) 2020 Anastasiia Birillo, Elena Lyulina

import logging

from src.main.util import consts
from src.main.solution_space.serialized_code import Code
from src.main.solution_space.data_classes import CodeInfo
from src.main.solution_space.path_finder.path_finder import IPathFinder
from src.main.solution_space.solution_graph import SolutionGraph, Vertex
from src.main.canonicalization.canonicalization import get_code_from_tree, Type
from src.main.canonicalization.diffs.rivers_diff_handler import RiversDiffHandler
from src.main.solution_space.measured_vertex.measured_vertex import IMeasuredVertex

log = logging.getLogger(consts.LOGGER_NAME)


class Hint:
    def __init__(self, recommended_code: str):
        self._recommended_code = recommended_code

    @property
    def recommended_code(self) -> str:
        return self._recommended_code


class HintHandler:
    def __init__(self, graph: SolutionGraph, path_finder: Type[IPathFinder], measured_vertex: Type[IMeasuredVertex]):
        self._graph = graph
        self._path_finder = path_finder(graph, measured_vertex)

    @property
    def graph(self) -> str:
        return self._graph

    @property
    def path_finder(self) -> IPathFinder:
        return self._path_finder

    def get_hint(self, source_code: str, code_info: CodeInfo) -> Hint:
        diff_handler = RiversDiffHandler(source_code=source_code)
        user_vertex = Vertex(self._graph, Code.from_source(source_code, rate=None, task=self._graph.task), code_info)

        next_vertex = self.path_finder.find_next_vertex(user_vertex)
        log.info(f'Next vertex id is {next_vertex.id}')

        diffs_and_types_list = [diff_handler.get_diffs(a_t.tree, next_vertex.serialized_code.canon_tree)
                                for a_t in next_vertex.serialized_code.anon_trees]
        diffs_len_list = list(map(lambda diff_and_type: len(diff_and_type[0]), diffs_and_types_list))
        diffs, type = diffs_and_types_list[diffs_len_list.index(min(diffs_len_list))]
        log.info(f'The best type of trees is {type.value}')

        # Apply the first diff
        # Todo: new version of apply diffs
        recommended_tree = diff_handler.apply_diffs(diffs, type)
        return Hint(get_code_from_tree(recommended_tree))
