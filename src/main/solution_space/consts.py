# Copyright (c) 2020 Anastasiia Birillo, Elena Lyulina

import os
from enum import Enum

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class VERTEX_TYPE(Enum):
    START = 'start'
    END = 'end'
    INTERMEDIATE = 'intermediate'


# Todo: rewrite it
# Make sure 'INT_EXPERIENCE' is the last one, otherwise columns in result table in test_system will be in wrong order
class TEST_INPUT(Enum):
    SOURCE_CODE = 'source'
    RATE = 'rate'
    AGE = 'age'
    INT_EXPERIENCE = 'int_experience'


class EVALUATION_TYPE(Enum):
    HINTS = 'hints'
    PROFILE = 'profile'


SOLUTION_SPACE_FOLDER = ROOT_DIR + '/../../resources/solution_space'
TEST_SYSTEM_FRAGMENTS = ROOT_DIR + '/../../resources/test_system/fragments'
TEST_SYSTEM_GRAPH = ROOT_DIR + '/../../resources/test_system/test_system_graph.pickle'
SOLUTION_SPACE_TEST_FOLDER = ROOT_DIR + '/../../resources/test_data/solution_space'
EMPTY_CODE_FILE = ROOT_DIR + '/../../resources/solution_space/empty_code.py'
HINT_FOLDER = ROOT_DIR + '/../../resources/hint'
EVALUATION_FRAGMENTS_PATH = ROOT_DIR + '/../../resources/evaluation'

GRAPH_FOLDER_PREFIX = 'graph'
FILE_PREFIX = 'code'
USER_FILE_PREFIX = 'user_code'

DIFFS_PERCENT_TO_GO_DIRECTLY = 0.2
DISTANCE_TO_GRAPH_THRESHOLD = 2
ROLLBACK_PROBABILITY = 0.7

EMPTY_MEDIAN = -1
