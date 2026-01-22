import heapq
import math
from itertools import product
from typing import List
import numpy as np
from entities.Robot import Robot
from entities.Entity import Obstacle, CellState, Grid
from consts import Direction, MOVE_DIRECTION, TURN_FACTOR, ITERATIONS, TURN_RADIUS, SAFE_COST
from python_tsp.exact import solve_tsp_dynamic_programming

turn_wrt_big_turns = [[3 * TURN_RADIUS, TURN_RADIUS],
                  [4 * TURN_RADIUS, 2 * TURN_RADIUS]]


class MazeSolver:
    def __init__(
            self,
            size_x: int,
            size_y: int,
            robot_x: int,
            robot_y: int,
            robot_direction: Direction,
            big_turn=None # the big_turn here is to allow 3-1 turn(0 - by default) | 4-2 turn(1)
    ):
        # Initialize a Grid object for the arena representation
        self.grid = Grid(size_x, size_y)
        # Initialize a Robot object for robot representation
        self.robot = Robot(robot_x, robot_y, robot_direction)
        # Create tables for paths and costs
        self.path_table = dict()
        self.cost_table = dict()
        if big_turn is None:
            self.big_turn = 0
        else:
            self.big_turn = int(big_turn)

    def add_obstacle(self, x: int, y: int, direction: Direction, obstacle_id: int):
        """Add obstacle to MazeSolver object

        Args:
            x (int): x coordinate of obstacle
            y (int): y coordinate of obstacle
            direction (Direction): Direction of obstacle
            obstacle_id (int): ID of obstacle
        """
        # Create an obstacle object
        obstacle = Obstacle(x, y, direction, obstacle_id)
        # Add created obstacle to grid object
        self.grid.add_obstacle(obstacle)

    def reset_obstacles(self):
        self.grid.reset_obstacles()

    @staticmethod
    def compute_coord_distance(x1: int, y1: int, x2: int, y2: int, level: int = 1) -> float:
        """Compute the L-n distance between two coordinates

        Args:
            x1 (int)
            y1 (int)
            x2 (int)
            y2 (int)
            level (int, optional): L-n distance to compute. Defaults to 1.

        Returns:
            float: L-n distance between the two given points
        """
        horizontal_distance = x1 - x2
        vertical_distance = y1 - y2

        # Euclidean distance
        if level == 2:
            return math.sqrt(horizontal_distance ** 2 + vertical_distance ** 2)

        return abs(horizontal_distance) + abs(vertical_distance)

    @staticmethod
    def compute_state_distance(start_state: CellState, end_state: CellState, level: int = 1) -> float:
        """Compute the L-n distance between two cell states

        Args:
            start_state (CellState): Start cell state
            end_state (CellState): End cell state
            level (int, optional): L-n distance to compute. Defaults to 1.

        Returns:
            float: L-n distance between the two given cell states
        """
        return MazeSolver.compute_coord_distance(start_state.x, start_state.y, end_state.x, end_state.y, level)

    @staticmethod
    def get_visit_options(n):
        """Generate all possible n-digit binary strings

        Args:
            n (int): number of digits in binary string to generate

        Returns:
            List: list of all possible n-digit binary strings
        """
        s = []
        l = bin(2 ** n - 1).count('1')

        for i in range(2 ** n):
            s.append(bin(i)[2:].zfill(l))

        s.sort(key=lambda x: x.count('1'), reverse=True)
        return s

    def get_optimal_order_dp(self, retrying) -> List[CellState]:
        distance = 1e9
        optimal_path = []

        #print(f"Inside get_optimal_order_dp: retrying = {retrying}")
        # Get all possible positions that can view the obstacles
        all_view_positions = self.grid.get_view_obstacle_positions(retrying)
        #print(f"all_view_positions: {all_view_positions}")
        #print(f"All view position: {all_view_positions}")

        for op in self.get_visit_options(len(all_view_positions)):
            # op is binary string of length len(all_view_positions) == len(obstacles)
            # If index == 1 means the view_positions[index] is selected to visit, otherwise drop

            # Calculate optimal_cost table

            # Initialize `items` to be a list containing the robot's start state as the first item
            items = [self.robot.get_start_state()]
            # Initialize `cur_view_positions` to be an empty list
            cur_view_positions = []
            
            # print(f"===================\nop = {op}")
            # print("List of obstacle visited: \n")

            # For each obstacle
            for idx in range(len(all_view_positions)):
                # If robot is visiting
                if op[idx] == '1':
                    # Add possible cells to `items`
                    items = items + all_view_positions[idx]
                    # Add possible cells to `cur_view_positions`
                    cur_view_positions.append(all_view_positions[idx])
                    #print("obstacle: {}\n".format(self.grid.obstacles[idx]))

            # Generate the path cost for the items
            self.path_cost_generator(items)
            
            # Generate all combinations using itertools.product (more efficient)
            ranges = [range(len(vp)) for vp in cur_view_positions]
            combination = list(product(*ranges))[:ITERATIONS] if ranges else [[]]

            for c in combination:
                visited_candidates = [0] # add the start state of the robot

                cur_index = 1
                fixed_cost = 0 # the cost applying for the position taking obstacle pictures
                for index, view_position in enumerate(cur_view_positions):
                    visited_candidates.append(cur_index + c[index])
                    fixed_cost += view_position[c[index]].penalty
                    cur_index += len(view_position)
                
                cost_np = np.zeros((len(visited_candidates), len(visited_candidates)))

                for s in range(len(visited_candidates) - 1):
                    for e in range(s + 1, len(visited_candidates)):
                        u = items[visited_candidates[s]]
                        v = items[visited_candidates[e]]
                        if (u, v) in self.cost_table.keys():
                            cost_np[s][e] = self.cost_table[(u, v)]
                        else:
                            cost_np[s][e] = 1e9
                        cost_np[e][s] = cost_np[s][e]
                cost_np[:, 0] = 0
                _permutation, _distance = solve_tsp_dynamic_programming(cost_np)
                # print(f"fixed_cost = {fixed_cost}")
                # print(f"distance = {_distance}")
                if _distance + fixed_cost >= distance:
                    continue

                optimal_path = [items[0]]
                distance = _distance + fixed_cost

                for i in range(len(_permutation) - 1):
                    from_item = items[visited_candidates[_permutation[i]]]
                    to_item = items[visited_candidates[_permutation[i + 1]]]

                    cur_path = self.path_table[(from_item, to_item)]
                    for j in range(1, len(cur_path)):
                        optimal_path.append(CellState(cur_path[j][0], cur_path[j][1], cur_path[j][2]))

                    optimal_path[-1].set_screenshot(to_item.screenshot_id)

            if optimal_path:
                # if found optimal path, return
                break

        return optimal_path, distance

    def get_safe_cost(self, x: int, y: int) -> int:
        """Get the safe cost of a particular x,y coordinate wrt obstacles that are exactly 2 units away.

        Args:
            x: x-coordinate
            y: y-coordinate

        Returns:
            SAFE_COST if too close to obstacle diagonally, 0 otherwise
        """
        for ob in self.grid.obstacles:
            dx, dy = abs(ob.x - x), abs(ob.y - y)
            # Check if obstacle is diagonally close (within 2 units in both directions)
            if (dx == 2 and dy == 2) or (dx == 1 and dy == 2) or (dx == 2 and dy == 1):
                return SAFE_COST
        return 0

    def get_neighbors(self, x: int, y: int, direction: Direction) -> List[tuple]:
        """
        Return a list of tuples with format: (newX, newY, new_direction, safe_cost)
        Neighbors are coordinates that are reachable via forward/backward movement or turns.
        """
        neighbors = []
        bigger = turn_wrt_big_turns[self.big_turn][0]
        smaller = turn_wrt_big_turns[self.big_turn][1]
        
        # Turn displacement mapping: (current_dir, new_dir) -> [(dx1, dy1), (dx2, dy2)] for two turn options
        # Each turn has a forward turn and a backward turn option
        turn_map = {
            (Direction.NORTH, Direction.EAST): [(bigger, smaller), (-smaller, -bigger)],
            (Direction.EAST, Direction.NORTH): [(smaller, bigger), (-bigger, -smaller)],
            (Direction.EAST, Direction.SOUTH): [(smaller, -bigger), (-bigger, smaller)],
            (Direction.SOUTH, Direction.EAST): [(bigger, -smaller), (-smaller, bigger)],
            (Direction.SOUTH, Direction.WEST): [(-bigger, -smaller), (smaller, bigger)],
            (Direction.WEST, Direction.SOUTH): [(-smaller, -bigger), (bigger, smaller)],
            (Direction.WEST, Direction.NORTH): [(-smaller, bigger), (bigger, -smaller)],
            (Direction.NORTH, Direction.WEST): [(smaller, -bigger), (-bigger, smaller)],
        }
        
        for dx, dy, md in MOVE_DIRECTION:
            if md == direction:
                # Forward/backward movement in same direction
                for sign in [1, -1]:
                    nx, ny = x + sign * dx, y + sign * dy
                    if self.grid.reachable(nx, ny):
                        neighbors.append((nx, ny, md, self.get_safe_cost(nx, ny)))
            else:
                # Turning movement
                key = (direction, md)
                if key in turn_map:
                    for turn_dx, turn_dy in turn_map[key]:
                        nx, ny = x + turn_dx, y + turn_dy
                        if self.grid.reachable(nx, ny, turn=True) and self.grid.reachable(x, y, preTurn=True):
                            neighbors.append((nx, ny, md, self.get_safe_cost(nx, ny) + 10))
        
        return neighbors

    def path_cost_generator(self, states: List[CellState]):
        """Generate the path cost between the input states and update the tables accordingly

        Args:
            states (List[CellState]): cell states to visit
        """
        def record_path(start, end, parent: dict, cost: int):

            # Update cost table for the (start,end) and (end,start) edges
            self.cost_table[(start, end)] = cost
            self.cost_table[(end, start)] = cost

            path = []
            cursor = (end.x, end.y, end.direction)

            while cursor in parent:
                path.append(cursor)
                cursor = parent[cursor]

            path.append(cursor)

            # Update path table for the (start,end) and (end,start) edges, with the (start,end) edge being the reversed path
            self.path_table[(start, end)] = path[::-1]
            self.path_table[(end, start)] = path

        def astar_search(start: CellState, end: CellState):
            # astar search algo with three states: x, y, direction

            # If it is already done before, return
            if (start, end) in self.path_table:
                return

            # Heuristic to guide the search: 'distance' is calculated by f = g + h
            # g is the actual distance moved so far from the start node to current node
            # h is the heuristic distance from current node to end node
            g_distance = {(start.x, start.y, start.direction): 0}

            # format of each item in heap: (f_distance of node, x coord of node, y coord of node)
            # heap in Python is a min-heap
            heap = [(self.compute_state_distance(start, end), start.x, start.y, start.direction)]
            parent = dict()
            visited = set()

            while heap:
                # Pop the node with the smallest distance
                _, cur_x, cur_y, cur_direction = heapq.heappop(heap)
                
                if (cur_x, cur_y, cur_direction) in visited:
                    continue

                if end.is_eq(cur_x, cur_y, cur_direction):
                    record_path(start, end, parent, g_distance[(cur_x, cur_y, cur_direction)])
                    return

                visited.add((cur_x, cur_y, cur_direction))
                cur_distance = g_distance[(cur_x, cur_y, cur_direction)]

                for next_x, next_y, new_direction, safe_cost in self.get_neighbors(cur_x, cur_y, cur_direction):
                    if (next_x, next_y, new_direction) in visited:
                        continue

                    move_cost = Direction.rotation_cost(new_direction, cur_direction) * TURN_FACTOR + 1 + safe_cost

                    # the cost to check if any obstacles that considered too near the robot; if it
                    # safe_cost =

                    # new cost is calculated by the cost to reach current state + cost to move from
                    # current state to new state + heuristic cost from new state to end state
                    next_cost = cur_distance + move_cost + \
                                self.compute_coord_distance(next_x, next_y, end.x, end.y)

                    if (next_x, next_y, new_direction) not in g_distance or \
                            g_distance[(next_x, next_y, new_direction)] > cur_distance + move_cost:
                        g_distance[(next_x, next_y, new_direction)] = cur_distance + move_cost
                        parent[(next_x, next_y, new_direction)] = (cur_x, cur_y, cur_direction)

                        heapq.heappush(heap, (next_cost, next_x, next_y, new_direction))

        # Nested loop through all the state pairings
        for i in range(len(states) - 1):
            for j in range(i + 1, len(states)):
                astar_search(states[i], states[j])

if __name__ == "__main__":
    pass
