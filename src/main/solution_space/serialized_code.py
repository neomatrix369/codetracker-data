# Copyright (c) 2020 Anastasiia Birillo, Elena Lyulina

from __future__ import annotations

import os
import ast
import logging
from typing import List, Callable, Optional, Set

from src.main.util import consts
from src.main.util.consts import TASK, DEFAULT_VALUE
from src.main.util.math_util import get_safety_median
from src.main.util.log_util import log_and_raise_error
from src.main.canonicalization.consts import TREE_TYPE
from src.main.solution_space.consts import EMPTY_MEDIAN
from src.main.util.helper_classes.id_counter import IdCounter
from src.main.solution_space.data_classes import CodeInfo, User
from src.main.util.language_util import get_extension_by_language
from src.main.util.helper_classes.pretty_string import PrettyString
from src.main.splitting.tasks_tests_handler import check_tasks, create_in_and_out_dict
from src.main.util.file_util import create_file, is_file, add_suffix_to_file, remove_directory, create_directory
from src.main.canonicalization.canonicalization import are_asts_equal, get_code_from_tree, get_trees, AstStructure

log = logging.getLogger(consts.LOGGER_NAME)


class ISerializedObject:
    def __init__(self, folder_with_files: str, file_prefix: str,
                 language: consts.LANGUAGE = consts.LANGUAGE.PYTHON, to_delete_prev_folder: bool = True):
        self._folder_with_files = folder_with_files
        self._file_prefix = file_prefix
        self._language = language
        if to_delete_prev_folder:
            remove_directory(self._folder_with_files)
        create_directory(self._folder_with_files)

    @property
    def folder_with_files(self) -> str:
        return self._folder_with_files

    @property
    def file_prefix(self) -> str:
        return self._file_prefix

    @property
    def language(self) -> consts.LANGUAGE:
        return self._language

    def get_file_path(self, suffix: Optional[str] = None, object_id: Optional[int] = None) -> str:
        extension = get_extension_by_language(self._language)
        file_name = f'{self._file_prefix}'
        if object_id is not None:
            file_name += f'_{str(object_id)}'
        if suffix is not None:
            file_name += f'_{suffix}'
        return os.path.join(self._folder_with_files, f'{file_name}{str(extension.value)}')


class SerializedTree:
    def __init__(self, file_path: str, tree: ast.AST, tree_id: int, to_create_file: bool = True):
        self._tree = tree
        self._tree_file = add_suffix_to_file(file_path, str(tree_id))
        if to_create_file:
            self.create_file_for_tree(to_overwrite=True)

    @property
    def tree_file(self) -> str:
        return self._tree_file

    @tree_file.setter
    def tree_file(self, tree_file) -> None:
        self._tree_file = tree_file

    @property
    def tree(self) -> ast.AST:
        return self._tree

    def create_file_for_tree(self, to_overwrite: bool = False) -> str:
        if self._tree_file is not None and not to_overwrite:
            log_and_raise_error(f'File for tree {get_code_from_tree(self.tree)} already exists in files dict', log)

        if not is_file(self.tree_file):
            code = get_code_from_tree(self.tree)
            create_file(code, self.tree_file)

        self._tree_file = self.tree_file
        return self.tree_file


class AnonTree(IdCounter, PrettyString, SerializedTree):
    def __init__(self, anon_tree: ast.AST, rate: float, file_path: str, code_info: Optional[CodeInfo] = None,
                 to_create_file: bool = True):
        self._code_info_list = [] if code_info is None else [code_info]
        self._age_median = None
        self._experience_median = None
        self._rate = rate
        IdCounter.__init__(self, to_store_items=True)
        PrettyString.__init__(self)
        SerializedTree.__init__(self, file_path, anon_tree, self.id, to_create_file)
        self._ast_structure = AstStructure.get_ast_structure(anon_tree)
        self._next_anon_trees_ids = []

    @property
    def nodes_number(self) -> int:
        return self._ast_structure.nodes_number

    @property
    def ast_structure(self) -> AstStructure:
        return self._ast_structure

    @property
    def next_anon_trees_ids(self) -> List[int]:
        return self._next_anon_trees_ids

    @property
    def tree(self) -> ast.AST:
        return self._tree

    @property
    def code_info_list(self) -> List[CodeInfo]:
        return self._code_info_list

    @property
    def rate(self) -> float:
        return self._rate

    @property
    def age_median(self) -> Optional[int]:
        return self._age_median

    @property
    def experience_median(self) -> Optional[int]:
        return self._experience_median

    @age_median.getter
    def age_median(self) -> int:
        if self._age_median is None:
            log_and_raise_error('Median is not found yet, you should call find_medians first', log)
        return self._age_median

    @experience_median.getter
    def experience_median(self) -> int:
        if self._experience_median is None:
            log_and_raise_error('Median is not found yet, you should call find_medians first', log)
        return self._experience_median

    # Returns True if all anon_trees have non-empty attribute
    @staticmethod
    def have_non_empty_attr(attr: str, anon_trees: List[AnonTree]) -> bool:
        for anon_tree in anon_trees:
            if getattr(anon_tree, attr) == EMPTY_MEDIAN:
                return False
        return True

    def add_next_anon_tree(self, next_anon_tree: AnonTree) -> bool:
        if next_anon_tree.id in self._next_anon_trees_ids \
                or next_anon_tree.id == self.id:
            return False
        self._next_anon_trees_ids.append(next_anon_tree.id)
        return True

    def add_code_info(self, code_info: CodeInfo) -> None:
        self._code_info_list.append(code_info)

    def get_unique_users(self) -> Set[User]:
        return set([code_info.user for code_info in self._code_info_list])

    @staticmethod
    def __find_median(default_value: int, all_values: List[int]) -> int:
        non_default_values = list(filter(lambda v: v != default_value, all_values))
        return get_safety_median(non_default_values, EMPTY_MEDIAN)

    def find_medians(self) -> None:
        unique_users = self.get_unique_users()

        ages: List[int] = [u.profile.age for u in unique_users]
        self._age_median = self.__find_median(DEFAULT_VALUE.AGE.value, ages)

        experiences: List[int] = [u.profile.experience.value for u in unique_users]
        self._experience_median = self.__find_median(DEFAULT_VALUE.INT_EXPERIENCE.value, experiences)

        log.info(f'Found medians for AnonTree {self.id}, unique users number is {len(unique_users)}, '
                 f'age median is {self._age_median}, experience median is {self._experience_median}')

    def __str__(self):
        return f'Anon_tree: {get_code_from_tree(self._tree)}\n' \
               f'Code info:\n{list(map(str, self._code_info_list))}\n' \
               f'Structure: {self._ast_structure}' \



class Code(PrettyString):

    def __init__(self, anon_tree: ast.AST, canon_tree: ast.AST, rate: float,
                 language: consts.LANGUAGE = consts.LANGUAGE.PYTHON):
        self._canon_tree = canon_tree
        self._rate = rate
        self._anon_tree = anon_tree
        self._language = language

    @classmethod
    def from_source(cls, source: str, rate: Optional[float], task: Optional[TASK] = None,
                    language: consts.LANGUAGE = consts.LANGUAGE.PYTHON) -> Code:
        anon_tree, canon_tree = get_trees(source, {TREE_TYPE.ANON, TREE_TYPE.CANON})
        if rate is None:
            if task is None:
                log_and_raise_error('Cannot find rate without task: both are None', log)
            rate = check_tasks([task], source, create_in_and_out_dict([task]), language)[0]
        return Code(anon_tree, canon_tree, rate, language)

    @property
    def canon_tree(self) -> ast.AST:
        return self._canon_tree

    @property
    def anon_tree(self) -> ast.AST:
        return self._anon_tree

    @property
    def rate(self) -> float:
        return self._rate

    @property
    def language(self) -> consts.LANGUAGE:
        return self._language

    def __str__(self) -> str:
        return f'Rate: {self._rate}\nLanguage: {self._language.value}\n' \
               f'Canon tree:\n{get_code_from_tree(self._canon_tree)}\n' \
               f'Anon tree:\n{get_code_from_tree(self.anon_tree)}\n'


class SerializedCode(IdCounter, PrettyString, ISerializedObject):

    def __init__(self, code: Code, code_info: CodeInfo, folder_with_files: str, file_prefix: str):
        PrettyString.__init__(self)
        IdCounter.__init__(self)
        ISerializedObject.__init__(self, folder_with_files=folder_with_files, file_prefix=file_prefix,
                                   language=code.language, to_delete_prev_folder=False)
        anon_tree = AnonTree(code.anon_tree, code.rate,
                             self.get_file_path(f'{TREE_TYPE.ANON.value}', self.id), code_info)
        self._anon_trees = [anon_tree]
        self._canon_tree = code.canon_tree
        self._rate = code.rate

    @property
    def canon_tree(self) -> ast.AST:
        return self._canon_tree

    @property
    def anon_trees(self) -> List[AnonTree]:
        return self._anon_trees

    @property
    def language(self) -> consts.LANGUAGE:
        return self._language

    def is_full(self) -> bool:
        return self._rate == consts.TEST_RESULT.FULL_SOLUTION.value

    def add_anon_tree(self, anon_tree: ast.AST, rate: float, code_info: CodeInfo) -> Optional[str]:
        if rate != self._rate:
            log_and_raise_error(f'Different rates in SerializedCode: {self._rate} and in new AnonTree: {rate}\n'
                                f'canon_tree:\n{get_code_from_tree(self._canon_tree)}\n'
                                f'first anon_tree:\n{get_code_from_tree(self.anon_trees[0].tree)}\n'
                                f'new anon_tree:\n{get_code_from_tree(anon_tree)}\n', log)
        found_anon_tree = self.find_anon_tree(anon_tree)
        if found_anon_tree:
            found_anon_tree.add_code_info(code_info)
            return None

        new_anon_tree = AnonTree(anon_tree, rate, self.get_file_path(f'{TREE_TYPE.ANON.value}', self.id), code_info)
        self._anon_trees.append(new_anon_tree)
        return new_anon_tree.tree_file

    def get_anon_files(self, filter_anon_trees: Callable[[AnonTree], bool] = (lambda tree: True)) -> List[str]:
        anon_tree_files = []
        for anon_tree in list(filter(filter_anon_trees, self._anon_trees)):
            anon_tree_files.append(anon_tree.tree_file)
        return anon_tree_files

    # Todo: We don't use it anymore, but while we have Distance class, we have not to delete it
    def get_canon_file(self) -> str:
        return ''

    def recreate_files_for_trees(self, new_folder_with_files: str) -> None:
        self._folder_with_files = new_folder_with_files
        self.__create_files_for_trees(to_overwrite=True)

    def __create_files_for_trees(self, to_overwrite: bool = False) -> None:
        for i, anon_tree in enumerate(self._anon_trees):
            anon_tree.tree_file = self.get_file_path(f'{TREE_TYPE.ANON.value}_{i}', anon_tree.id)
            anon_tree._tree_file = anon_tree.create_file_for_tree(to_overwrite=to_overwrite)

    def find_anon_tree(self, anon_tree: ast.AST) -> Optional[AnonTree]:
        current_nodes_number = AstStructure.get_nodes_number_in_ast(anon_tree)
        for a_t in self._anon_trees:
            # It will work faster
            if current_nodes_number != a_t.nodes_number:
                continue
            elif are_asts_equal(a_t.tree, anon_tree):
                return a_t
        return None

    def __str__(self) -> str:
        return f'Id: {self._id}\n' \
               f'Rate: {self._rate}\n' \
               f'Language: {self._language.value}\n' \
               f'Canon tree:\n{get_code_from_tree(self._canon_tree)}\n' \
               f'Anon trees: \n{list(map(str, self._anon_trees))}\n'
