from consts import WIDTH, HEIGHT, Direction

# Default speed for motor commands (0-100, multiplied by 71 for PWM 0-7199)
DEFAULT_SPEED = 50
# Global command ID counter for motor protocol
_cmd_id = 1


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


def command_generator(states: list, obstacles: list, speed: int = None) -> list:
    """Takes in a list of states and generates a list of motor protocol commands for the robot to follow.
    
    Args:
        states: List of State objects representing robot path
        obstacles: List of obstacles, each a dict with keys 'x', 'y', 'd', 'id'
        speed: Motor speed (0-100). If None, uses DEFAULT_SPEED

    Returns:
        List of motor protocol command strings in format :[cmdId]/[component]/[command]/[param1]/[param2];
    """

    # Convert the list of obstacles into a dictionary with key as the obstacle id and value as the obstacle
    obstacles_dict = {ob['id']: ob for ob in obstacles}
    
    # Use provided speed or default
    motor_speed = speed if speed is not None else DEFAULT_SPEED
    
    # Initialize commands list and command ID counter
    commands = []
    global _cmd_id
    cmd_id = 1

    # Iterate through each state in the list of states
    for i in range(1, len(states)):
        steps = "00"

        # If previous state and current state are the same direction,
        if states[i].direction == states[i - 1].direction:
            # Forward - Must be (east facing AND x value increased) OR (north facing AND y value increased)
            if (states[i].x > states[i - 1].x and states[i].direction == Direction.EAST) or (states[i].y > states[i - 1].y and states[i].direction == Direction.NORTH):
                commands.append(f":{cmd_id}/MOTOR/FWD/{motor_speed}/10;")
                cmd_id += 1
            # Forward - Must be (west facing AND x value decreased) OR (south facing AND y value decreased)
            elif (states[i].x < states[i-1].x and states[i].direction == Direction.WEST) or (
                    states[i].y < states[i-1].y and states[i].direction == Direction.SOUTH):
                commands.append(f":{cmd_id}/MOTOR/FWD/{motor_speed}/10;")
                cmd_id += 1
            # Backward - All other cases where the previous and current state is the same direction
            else:
                commands.append(f":{cmd_id}/MOTOR/REV/{motor_speed}/10;")
                cmd_id += 1

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
                    commands.append(f":{cmd_id}/MOTOR/TURN90R/{motor_speed}/0;")
                    cmd_id += 1
                # y value decreased -> Backward Left
                else:
                    commands.append(f":{cmd_id}/MOTOR/TURN90L/{motor_speed}/0;")
                    cmd_id += 1
            # Facing west afterwards
            elif states[i].direction == Direction.WEST:
                # y value increased -> Forward Left
                if states[i].y > states[i - 1].y:
                    commands.append(f":{cmd_id}/MOTOR/TURN90L/{motor_speed}/0;")
                    cmd_id += 1
                # y value decreased -> Backward Right
                else:
                    commands.append(f":{cmd_id}/MOTOR/TURN90R/{motor_speed}/0;")
                    cmd_id += 1
            else:
                raise Exception("Invalid turing direction")

        elif states[i - 1].direction == Direction.EAST:
            if states[i].direction == Direction.NORTH:
                if states[i].y > states[i - 1].y:
                    commands.append(f":{cmd_id}/MOTOR/TURN90L/{motor_speed}/0;")
                    cmd_id += 1
                else:
                    commands.append(f":{cmd_id}/MOTOR/TURN90R/{motor_speed}/0;")
                    cmd_id += 1

            elif states[i].direction == Direction.SOUTH:
                if states[i].y > states[i - 1].y:
                    commands.append(f":{cmd_id}/MOTOR/TURN90L/{motor_speed}/0;")
                    cmd_id += 1
                else:
                    commands.append(f":{cmd_id}/MOTOR/TURN90R/{motor_speed}/0;")
                    cmd_id += 1
            else:
                raise Exception("Invalid turing direction")

        elif states[i - 1].direction == Direction.SOUTH:
            if states[i].direction == Direction.EAST:
                if states[i].y > states[i - 1].y:
                    commands.append(f":{cmd_id}/MOTOR/TURN90R/{motor_speed}/0;")
                    cmd_id += 1
                else:
                    commands.append(f":{cmd_id}/MOTOR/TURN90L/{motor_speed}/0;")
                    cmd_id += 1
            elif states[i].direction == Direction.WEST:
                if states[i].y > states[i - 1].y:
                    commands.append(f":{cmd_id}/MOTOR/TURN90L/{motor_speed}/0;")
                    cmd_id += 1
                else:
                    commands.append(f":{cmd_id}/MOTOR/TURN90R/{motor_speed}/0;")
                    cmd_id += 1
            else:
                raise Exception("Invalid turing direction")

        elif states[i - 1].direction == Direction.WEST:
            if states[i].direction == Direction.NORTH:
                if states[i].y > states[i - 1].y:
                    commands.append(f":{cmd_id}/MOTOR/TURN90R/{motor_speed}/0;")
                    cmd_id += 1
                else:
                    commands.append(f":{cmd_id}/MOTOR/TURN90L/{motor_speed}/0;")
                    cmd_id += 1
            elif states[i].direction == Direction.SOUTH:
                if states[i].y > states[i - 1].y:
                    commands.append(f":{cmd_id}/MOTOR/TURN90R/{motor_speed}/0;")
                    cmd_id += 1
                else:
                    commands.append(f":{cmd_id}/MOTOR/TURN90L/{motor_speed}/0;")
                    cmd_id += 1
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

    # Final command is the stop command
    commands.append(f":{cmd_id}/MOTOR/STOP/0/0;")
    cmd_id += 1
    commands.append("FIN")  # Keep FIN marker for higher-level processing

    # Compress commands if there are consecutive forward or backward commands
    compressed_commands = [commands[0]]

    for i in range(1, len(commands)):
        # If both commands are REV (backward)
        if "/MOTOR/REV/" in commands[i] and "/MOTOR/REV/" in compressed_commands[-1]:
            # Extract distance from previous command
            parts = compressed_commands[-1].split("/")
            distance = int(parts[-1].rstrip(";"))
            # If distance is not 90, add 10 to the distance
            if distance != 90:
                cmd_parts = compressed_commands[-1].split("/")
                cmd_parts[-1] = f"{distance + 10};"
                compressed_commands[-1] = "/".join(cmd_parts)
                continue

        # If both commands are FWD (forward)
        elif "/MOTOR/FWD/" in commands[i] and "/MOTOR/FWD/" in compressed_commands[-1]:
            # Extract distance from previous command
            parts = compressed_commands[-1].split("/")
            distance = int(parts[-1].rstrip(";"))
            # If distance is not 90, add 10 to the distance
            if distance != 90:
                cmd_parts = compressed_commands[-1].split("/")
                cmd_parts[-1] = f"{distance + 10};"
                compressed_commands[-1] = "/".join(cmd_parts)
                continue
        
        # Otherwise, just add as usual
        compressed_commands.append(commands[i])

    return compressed_commands
