# Copyright (c) 2020 Anastasiia Birillo, Elena Lyulina

import ast
import logging
from typing import List, Optional

from src.main.util.consts import LOGGER_NAME
from src.main.solution_space.solution_graph import Vertex
from src.main.solution_space.path_finder.path_finder import IPathFinder
from src.main.canonicalization.canonicalization import get_code_from_tree
from src.main.solution_space.consts import DIFFS_PERCENT_TO_GO_DIRECTLY, DISTANCE_TO_GRAPH_THRESHOLD, \
    ROLLBACK_PROBABILITY

log = logging.getLogger(LOGGER_NAME)


class PathFinderV2(IPathFinder):

    def find_next_vertex(self, user_vertex: Vertex) -> Vertex:
        """
        1. Find the closest goal (__find_closest_goal)
        2. Find the closest graph_vertex (__find_closest_vertex_with_path)
        3. Choose between them using __go_through_graph
        """
        log.info(f'Start finding the next code state for '
                 f'the user code: {get_code_from_tree(user_vertex.serialized_code.anon_trees[0])} and '
                 f'the user: {user_vertex.code_info_list[0].user}')
        goal = self.__find_closest_goal(user_vertex)
        graph_vertex = self.__find_closest_vertex_with_path(user_vertex, goal)
        # We can have graph_vertex = None
        if graph_vertex and self.__go_through_graph(user_vertex, graph_vertex, goal):
            log.info(f'We are going through graph')
            return graph_vertex
        else:
            log.info(f'We are going directly to the goal')
            return goal

    def __choose_best_vertex(self, user_vertex: Vertex, vertices: List[Vertex]) -> Optional[Vertex]:
        """
        1. Sort candidates using MeasuredVertex
        2. Return the first candidate
        """

        if len(vertices) == 0:
            return None
        candidates = list(map(lambda vertex: self.get_measured_vertex(user_vertex, vertex), vertices))
        candidates.sort()
        log.info(f'Candidates ids are {([c.vertex.id for c in candidates])}')
        log.info(f'The best vertex id is {candidates[0].vertex.id}')
        return candidates[0].vertex

    # Note: A goal is a vertex, which has the rate equals 1 and it connects to the end vertex
    def __find_closest_goal(self, user_vertex: Vertex) -> Vertex:
        """
        1. Get list of all goals
        2. Find the closest using __choose_best_vertex()
        """
        log.info(f'Goals ids are {[p.id for p in self._graph.end_vertex.parents]}')
        return self.__choose_best_vertex(user_vertex, self._graph.end_vertex.parents)

    # Note: we have to remove the 'user_code' from the set
    def __find_closest_vertex_with_path(self, user_vertex: Vertex, goal: Vertex) -> Optional[Vertex]:
        """
        1. If there is a vertex in the graph with same canon_tree:
            1.1 Return __choose_best_vertex on vertex children
        2. Consider each vertex with small __get_rollback_probability as candidate
        3. Choose the best vertex from candidates using __choose_best_vertex()
        """
        user_diffs_to_goal = user_vertex.get_dist(goal)
        # Todo: 14/04 test vertex from graph
        vertex_in_graph = self._graph.find_vertex(user_vertex.canon_tree)
        if vertex_in_graph:
            return self.__choose_best_vertex(user_vertex, vertex_in_graph.children)

        candidates = []
        vertices = self._graph.get_traversal()
        vertices.remove(self._graph.start_vertex)

        for vertex in vertices:
            if self.__get_rollback_probability(user_vertex.canon_tree, vertex.canon_tree) <= ROLLBACK_PROBABILITY:
                candidates.append(vertex)
            #
            # diffs = self._graph.get_diffs_number_between_vertexes(vertex, goal)
            #
            # if diffs <= user_diffs_to_goal:
            #     candidates.append(vertex)
        return self.__choose_best_vertex(user_vertex, candidates)

    @staticmethod
    def __get_rollback_probability(user_canon_tree: ast.AST, vertex_canon_tree: ast.AST) -> float:
        """
        1. Get rollback probability by counting percentage of the same lines
        """
        # Todo: use AST comparing or other measure
        included_lines_count = 0
        vertex_code_lines = get_code_from_tree(vertex_canon_tree).strip('\n').split('\n')
        user_code = get_code_from_tree(user_canon_tree)
        for line in vertex_code_lines:
            if line in user_code:
                included_lines_count += 1
        return included_lines_count / len(vertex_code_lines)

    @staticmethod
    def __is_far_from_graph(diffs_from_user_to_goal: int, diffs_from_user_to_graph_vertex: int) -> bool:
        return diffs_from_user_to_graph_vertex / diffs_from_user_to_goal > DISTANCE_TO_GRAPH_THRESHOLD

    @staticmethod
    def __is_most_of_path_is_done(diffs_from_empty_to_goal: int, diffs_from_user_to_goal: int) -> bool:
        return diffs_from_user_to_goal <= diffs_from_empty_to_goal * DIFFS_PERCENT_TO_GO_DIRECTLY

    @staticmethod
    def __is_rate_worse(user_rate: float, graph_vertex_rate: float):
        # TODO: 14/04 or If number of passed tests > 0 then True???
        return user_rate > 0 and graph_vertex_rate == 0

    # Returns should we go through graph or directly to the goal
    def __go_through_graph(self, user_vertex: Vertex, graph_vertex: Vertex, goal: Vertex) -> bool:
        """
        1. If __is_most_of_path_is_done, return False
        2. If __is_rate_worse, return False
        3. Return not __is_far_from_graph
        """
        diffs_from_user_to_goal = user_vertex.get_dist(goal)
        diffs_from_empty_to_user = self._empty_vertex.get_dist(user_vertex)
        if self.__is_most_of_path_is_done(diffs_from_empty_to_user + diffs_from_user_to_goal,
                                          diffs_from_user_to_goal):
            return False

        if self.__is_rate_worse(user_vertex.serialized_code.rate, graph_vertex.serialized_code.rate):
            return False

        diffs_from_user_to_graph_vertex = user_vertex.get_dist(graph_vertex)
        return not self.__is_far_from_graph(diffs_from_user_to_goal, diffs_from_user_to_graph_vertex)
