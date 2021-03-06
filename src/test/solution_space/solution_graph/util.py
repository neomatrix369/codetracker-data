# Copyright (c) 2020 Anastasiia Birillo, Elena Lyulina

from typing import Tuple, List

from src.main.util.consts import TEST_RESULT
from src.main.canonicalization.consts import TREE_TYPE
from src.main.solution_space.serialized_code import Code
from src.main.util.helper_classes.id_counter import IdCounter
from src.main.canonicalization.canonicalization import get_trees
from src.main.solution_space.solution_graph import SolutionGraph, Vertex


def create_code_from_source(source: str, rate: float = TEST_RESULT.CORRECT_CODE.value) -> Code:
    anon_tree, canon_tree = get_trees(source, {TREE_TYPE.ANON, TREE_TYPE.CANON})
    return Code(anon_tree, canon_tree, rate)


def get_two_vertices(sg: SolutionGraph) -> List[Vertex]:
    source_0 = 'print(\'Hi\')'
    source_1 = 'x = 6\nif x > 5:\n    x = 5\nprint(x)'
    sources = [source_0, source_1]
    rates = [TEST_RESULT.CORRECT_CODE.value] * len(sources)
    return [Vertex(sg, code=Code.from_source(s, rates[i])) for i, s in enumerate(sources)]


# Reset graph, vertex and code last ids to avoid different ids in one-by-one test running and running them all at once
def init_default_ids() -> None:
    IdCounter.reset_all()
