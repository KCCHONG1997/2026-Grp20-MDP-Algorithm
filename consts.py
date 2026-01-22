from enum import Enum


class Direction(int, Enum):
    NORTH = 0
    EAST = 2
    SOUTH = 4
    WEST = 6
    SKIP = 8

    def __int__(self):
        return self.value

    @staticmethod
    def rotation_cost(d1, d2):
        diff = abs(d1 - d2)
        return min(diff, 8 - diff)

MOVE_DIRECTION = [
    (1, 0, Direction.EAST),
    (-1, 0, Direction.WEST),
    (0, 1, Direction.NORTH),
    (0, -1, Direction.SOUTH),
]

TURN_FACTOR = 1

EXPANDED_CELL = 1 # for both agent and obstacles

WIDTH = 20
HEIGHT = 20

ITERATIONS = 2000
TURN_RADIUS = 1

SAFE_COST = 1000 # the cost for the turn in case there is a chance that the robot is touch some obstacle
SCREENSHOT_COST = 50 # the cost for the place where the picture is taken

# Mapping from symbol name to ID for image recognition
NAME_TO_ID = {
    "NA": 'NA',
    "Bullseye": 10,
    "One": 11,
    "Two": 12,
    "Three": 13,
    "Four": 14,
    "Five": 15,
    "Six": 16,
    "Seven": 17,
    "Eight": 18,
    "Nine": 19,
    "A": 20,
    "B": 21,
    "C": 22,
    "D": 23,
    "E": 24,
    "F": 25,
    "G": 26,
    "H": 27,
    "S": 28,
    "T": 29,
    "U": 30,
    "V": 31,
    "W": 32,
    "X": 33,
    "Y": 34,
    "Z": 35,
    "Up": 36,
    "Down": 37,
    "Right": 38,
    "Left": 39,
    "Up Arrow": 36,
    "Down Arrow": 37,
    "Right Arrow": 38,
    "Left Arrow": 39,
    "Stop": 40
}
