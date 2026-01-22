from consts import WIDTH, HEIGHT, Direction


def is_valid(center_x: int, center_y: int) -> bool:
    """Checks if given position is within bounds

    Args:
        center_x: x-coordinate
        center_y: y-coordinate

    Returns:
        True if valid, False otherwise
    """
    return 0 < center_x < WIDTH - 1 and 0 < center_y < HEIGHT - 1


def _get_snap_command(screenshot_id: int, obstacle: dict, robot_position) -> str:
    """Generate SNAP command with direction suffix based on obstacle and robot positions.
    
    Args:
        screenshot_id: ID of the obstacle to photograph
        obstacle: Dict with obstacle info {'x', 'y', 'd', 'id'}
        robot_position: Current robot state with x, y, direction
    
    Returns:
        SNAP command string like 'SNAP1_L', 'SNAP1_C', or 'SNAP1_R'
    """
    ob_d = obstacle['d']
    robot_d = robot_position.direction
    
    # Mapping: (obstacle_direction, robot_direction) -> (compare_attr, left_cond, right_cond)
    # left_cond/right_cond: True if obstacle coord > robot coord means L/R respectively
    direction_map = {
        (6, 2): ('y', True, False),   # Obstacle WEST, robot EAST
        (2, 6): ('y', False, True),   # Obstacle EAST, robot WEST
        (0, 4): ('x', True, False),   # Obstacle NORTH, robot SOUTH
        (4, 0): ('x', False, True),   # Obstacle SOUTH, robot NORTH
    }
    
    key = (ob_d, robot_d)
    if key not in direction_map:
        return f"SNAP{screenshot_id}"
    
    attr, left_when_greater, right_when_greater = direction_map[key]
    ob_val = obstacle[attr]
    robot_val = getattr(robot_position, attr)
    
    if ob_val == robot_val:
        return f"SNAP{screenshot_id}_C"
    elif ob_val > robot_val:
        suffix = '_L' if left_when_greater else '_R'
    else:
        suffix = '_R' if left_when_greater else '_L'
    
    return f"SNAP{screenshot_id}{suffix}"


def command_generator(states: list, obstacles: list) -> list:
    """Takes in a list of states and generates a list of commands for the robot to follow.
    
    Args:
        states: List of State objects representing robot path
        obstacles: List of obstacles, each a dict with keys 'x', 'y', 'd', 'id'

    Returns:
        List of command strings for the robot (FW, BW, FR, FL, BR, BL, SNAP, FIN)
    """

    # Convert the list of obstacles into a dictionary with key as the obstacle id and value as the obstacle
    obstacles_dict = {ob['id']: ob for ob in obstacles}
    
    # Initialize commands list
    commands = []

    # Iterate through each state in the list of states
    for i in range(1, len(states)):
        steps = "00"

        # If previous state and current state are the same direction,
        if states[i].direction == states[i - 1].direction:
            # Forward - Must be (east facing AND x value increased) OR (north facing AND y value increased)
            if (states[i].x > states[i - 1].x and states[i].direction == Direction.EAST) or (states[i].y > states[i - 1].y and states[i].direction == Direction.NORTH):
                commands.append("FW10")
            # Forward - Must be (west facing AND x value decreased) OR (south facing AND y value decreased)
            elif (states[i].x < states[i-1].x and states[i].direction == Direction.WEST) or (
                    states[i].y < states[i-1].y and states[i].direction == Direction.SOUTH):
                commands.append("FW10")
            # Backward - All other cases where the previous and current state is the same direction
            else:
                commands.append("BW10")

            # If any of these states has a valid screenshot ID, add a SNAP command
            if states[i].screenshot_id != -1:
                snap_cmd = _get_snap_command(
                    states[i].screenshot_id,
                    obstacles_dict[states[i].screenshot_id],
                    states[i]
                )
                commands.append(snap_cmd)
            continue

        # If previous state and current state are not the same direction, it means that there will be a turn command involved
        # Assume there are 4 turning command: FR, FL, BL, BR (the turn command will turn the robot 90 degrees)
        # FR00 | FR30: Forward Right;
        # FL00 | FL30: Forward Left;
        # BR00 | BR30: Backward Right;
        # BL00 | BL30: Backward Left;

        # Facing north previously
        if states[i - 1].direction == Direction.NORTH:
            # Facing east afterwards
            if states[i].direction == Direction.EAST:
                # y value increased -> Forward Right
                if states[i].y > states[i - 1].y:
                    commands.append("FR{}".format(steps))
                # y value decreased -> Backward Left
                else:
                    commands.append("BL{}".format(steps))
            # Facing west afterwards
            elif states[i].direction == Direction.WEST:
                # y value increased -> Forward Left
                if states[i].y > states[i - 1].y:
                    commands.append("FL{}".format(steps))
                # y value decreased -> Backward Right
                else:
                    commands.append("BR{}".format(steps))
            else:
                raise Exception("Invalid turing direction")

        elif states[i - 1].direction == Direction.EAST:
            if states[i].direction == Direction.NORTH:
                if states[i].y > states[i - 1].y:
                    commands.append("FL{}".format(steps))
                else:
                    commands.append("BR{}".format(steps))

            elif states[i].direction == Direction.SOUTH:
                if states[i].y > states[i - 1].y:
                    commands.append("BL{}".format(steps))
                else:
                    commands.append("FR{}".format(steps))
            else:
                raise Exception("Invalid turing direction")

        elif states[i - 1].direction == Direction.SOUTH:
            if states[i].direction == Direction.EAST:
                if states[i].y > states[i - 1].y:
                    commands.append("BR{}".format(steps))
                else:
                    commands.append("FL{}".format(steps))
            elif states[i].direction == Direction.WEST:
                if states[i].y > states[i - 1].y:
                    commands.append("BL{}".format(steps))
                else:
                    commands.append("FR{}".format(steps))
            else:
                raise Exception("Invalid turing direction")

        elif states[i - 1].direction == Direction.WEST:
            if states[i].direction == Direction.NORTH:
                if states[i].y > states[i - 1].y:
                    commands.append("FR{}".format(steps))
                else:
                    commands.append("BL{}".format(steps))
            elif states[i].direction == Direction.SOUTH:
                if states[i].y > states[i - 1].y:
                    commands.append("BR{}".format(steps))
                else:
                    commands.append("FL{}".format(steps))
            else:
                raise Exception("Invalid turing direction")
        else:
            raise Exception("Invalid position")

        # If any of these states has a valid screenshot ID, add a SNAP command
        if states[i].screenshot_id != -1:
            snap_cmd = _get_snap_command(
                states[i].screenshot_id,
                obstacles_dict[states[i].screenshot_id],
                states[i]
            )
            commands.append(snap_cmd)

    # Final command is the stop command (FIN)
    commands.append("FIN")

    # Compress commands if there are consecutive forward or backward commands
    compressed_commands = [commands[0]]

    for i in range(1, len(commands)):
        # If both commands are BW
        if commands[i].startswith("BW") and compressed_commands[-1].startswith("BW"):
            # Get the number of steps of previous command
            steps = int(compressed_commands[-1][2:])
            # If steps are not 90, add 10 to the steps
            if steps != 90:
                compressed_commands[-1] = "BW{}".format(steps + 10)
                continue

        # If both commands are FW
        elif commands[i].startswith("FW") and compressed_commands[-1].startswith("FW"):
            # Get the number of steps of previous command
            steps = int(compressed_commands[-1][2:])
            # If steps are not 90, add 10 to the steps
            if steps != 90:
                compressed_commands[-1] = "FW{}".format(steps + 10)
                continue
        
        # Otherwise, just add as usual
        compressed_commands.append(commands[i])

    return compressed_commands
