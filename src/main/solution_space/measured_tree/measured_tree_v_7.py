# Copyright (c) 2020 Anastasiia Birillo, Elena Lyulina

from __future__ import annotations

import math
from typing import Tuple

from src.main.util.log_util import log_and_raise_error
from src.main.solution_space.consts import USERS_NUMBER
from src.main.solution_space.serialized_code import AnonTree
from src.main.canonicalization.diffs.gumtree import GumTreeDiff
from src.main.solution_space.path_finder.path_finder import log
from src.main.solution_space.path_finder_test_system import doc_param
from src.main.canonicalization.canonicalization import are_asts_equal
from src.main.solution_space.measured_tree.measured_tree import IMeasuredTree


class MeasuredTreeV7(IMeasuredTree):
    _age_w = 0.15
    _exp_w = 0.15
    _diffs_w = 0.5
    _users_w = -0.5
    _rollback_w = 4.0
    _rate_w = 0.3
    _structure_w = 6.5

    # def _IMeasuredTree__init_diffs_number_and_rollback_probability(self) -> None:
    #     self._diffs_number, delete_edits = GumTreeDiff \
    #         .get_diffs_and_delete_edits_numbers(self.user_tree.tree_file, self.candidate_tree.tree_file)
    #     self._rollback_probability = delete_edits

    def _IMeasuredTree__init_diffs_number_and_rollback_probability(self) -> None:
        if are_asts_equal(self._user_tree.tree, self._candidate_tree.tree):
            self._diffs_number = math.inf
            self._rollback_probability = 0
        else:
            diffs_number, delete_edits = GumTreeDiff \
                .get_diffs_and_delete_edits_numbers(self.user_tree.tree_file, self.candidate_tree.tree_file)
            self._diffs_number = diffs_number if diffs_number != 0 else math.inf
            self._rollback_probability = 0 if diffs_number == 0 else delete_edits / diffs_number

    @doc_param(_diffs_w, _users_w, _rate_w, _rollback_w, _age_w, _exp_w, _structure_w)
    def _IMeasuredTree__calculate_distance_to_user(self) -> Tuple[float, str]:
        """
        Finds distance as weighted sum of:
        1. diffs_number, weight: {0}
        2. users_count, weight: {1}
        3. rate reducing, weight: {2}
        4. rollback probability, weight: {3}
        5. same structure, weight: {6}
        6. (if possible) abs difference between age, weight: {4}
        7. (if possible) abs difference between exp, weight: {5}
        """
        distance = self._diffs_w * self._diffs_number \
                   + self._users_w * self.users_number / USERS_NUMBER[self._task] \
                   + self._rate_w * (self.user_tree.rate - self.candidate_tree.rate) \
                   + self._rollback_w * self.rollback_probability \
                   + self._structure_w * (self.user_tree.ast_structure - self.candidate_tree.ast_structure)
        distance_info = f'(diffs: {self._diffs_w} * {self._diffs_number}) + ' \
                        f'(users: {self._users_w} * {self.users_number} / {USERS_NUMBER[self._task]}) + ' \
                        f'(rate: {self._rate_w} * ({self.user_tree.rate} - {self.candidate_tree.rate})) + ' \
                        f'(rollback: {self._rollback_w} * {self.rollback_probability}) + ' \
                        f'(structure: {self._structure_w} * {self.user_tree.ast_structure - self.candidate_tree.ast_structure})'

        trees = [self.user_tree, self.candidate_tree]
        if AnonTree.have_non_empty_attr('_age_median', trees):
            distance += self._age_w * abs(self.user_tree.age_median - self.candidate_tree.age_median)
            distance_info += f' + (age: {self._age_w} * |{self.user_tree.age_median} - {self.candidate_tree.age_median}|)'
        if AnonTree.have_non_empty_attr('_experience_median', trees):
            distance += self._exp_w * abs(self.user_tree.experience_median - self.candidate_tree.experience_median)
            distance_info += f' + (exp: {self._exp_w} * |{self.user_tree.experience_median} - {self.candidate_tree.experience_median}|)'

        return distance, distance_info

    def __lt__(self, o: object):
        """
        1. If o is not an instance of class, raise an error
        2. Compare distance
        """
        if not isinstance(o, MeasuredTreeV7):
            log_and_raise_error(f'The object {o} is not {self.__class__} class', log)
        return self._distance_to_user < o._distance_to_user
