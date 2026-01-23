# Command Sequence Explanation

This document explains the robot command stream your server returned.

## Legend

- Movement (10 = one grid cell = 10 cm)
  - `FWxx`: Move forward by xx cm (e.g., `FW10` = 1 cell, `FW50` = 5 cells)
  - `BWxx`: Move backward by xx cm
- Turns (90° pivots with an arc; "00" is a placeholder)
  - `FR00`: Forward–Right 90° turn
  - `FL00`: Forward–Left 90° turn
  - `BR00`: Backward–Right 90° turn
  - `BL00`: Backward–Left 90° turn
- Image capture
  - `SNAPk_[L|C|R]`: Take a photo of obstacle `k`
    - Suffix indicates left/center/right framing relative to the obstacle’s face direction
- End
  - `FIN`: Route complete

Notes
- The arena is 20×20 cells. The robot center moves on cell centers and respects a 3×3 footprint clearance.
- Direction values the planner uses internally: 0=NORTH, 2=EAST, 4=SOUTH, 6=WEST.

## Sequence Breakdown

1. `FW50` – forward 5 cells
2. `FR00` – 90° turn forward-right
3. `FW10` – forward 1 cell
4. `BL00` – 90° turn backward-left
5. `BW30` – back 3 cells
6. `BR00` – 90° turn backward-right (reorient)
7. `SNAP3_C` – capture obstacle 3 (center-framed)
8. `FR00` – 90° turn forward-right
9. `FW30` – forward 3 cells
10. `FL00` – 90° turn forward-left
11. `FW40` – forward 4 cells
12. `FL00` – 90° turn forward-left
13. `FW10` – forward 1 cell
14. `SNAP4_C` – capture obstacle 4 (center-framed)
15. `BL00` – 90° turn backward-left
16. `FW10` – forward 1 cell
17. `FL00` – 90° turn forward-left
18. `BW20` – back 2 cells
19. `FL00` – 90° turn forward-left
20. `BW10` – back 1 cell
21. `SNAP1_C` – capture obstacle 1 (center-framed)
22. `BW30` – back 3 cells
23. `BR00` – 90° turn backward-right
24. `BW10` – back 1 cell
25. `SNAP2_C` – capture obstacle 2 (center-framed)
26. `FL00` – 90° turn forward-left
27. `BW10` – back 1 cell
28. `FR00` – 90° turn forward-right
29. `FW20` – forward 2 cells
30. `FR00` – 90° turn forward-right
31. `BW10` – back 1 cell
32. `SNAP5_C` – capture obstacle 5 (center-framed)
33. `FIN` – route complete

## Quick Reference

- Distance units map 10 → 1 grid cell (10 cm).
- SNAP target IDs correspond to the obstacle `id` provided in the `/path` request.
- The planner may mix forward/backward moves with turning arcs to honor clearance and view angles.