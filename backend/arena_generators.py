
import random


# ============================================================
# CONFIGURATION
# ============================================================

SUDOKU_SIZE = 6
SUDOKU_BOX_ROWS = 2
SUDOKU_BOX_COLS = 3

# Clue counts out of 36 cells.
# Fewer clues generally means a harder puzzle.
SUDOKU_CLUES = {
    "easy": 24,
    "medium": 20,
    "hard": 16,
}

KENKEN_SIZES = {
    "easy": 4,
    "medium": 5,
    "hard": 6,
}

KENKEN_MAX_CAGE_SIZE = {
    "easy": 2,
    "medium": 3,
    "hard": 4,
}


# ============================================================
# SUDOKU: 6 x 6 WITH 2 x 3 REGIONS
# ============================================================

def _sudoku_solution(rng):
    """
    Generate a randomized valid 6x6 Sudoku solution.

    Rules:
      - 6 rows
      - 6 columns
      - 2-row x 3-column regions
      - Numbers 1 through 6
    """

    size = SUDOKU_SIZE
    box_rows = SUDOKU_BOX_ROWS
    box_cols = SUDOKU_BOX_COLS

    digits = list(range(1, size + 1))
    rng.shuffle(digits)

    digit_map = {
        index + 1: digits[index]
        for index in range(size)
    }

    bands = list(range(size // box_rows))
    stacks = list(range(size // box_cols))

    rng.shuffle(bands)
    rng.shuffle(stacks)

    rows = [
        band * box_rows + row
        for band in bands
        for row in rng.sample(range(box_rows), box_rows)
    ]

    cols = [
        stack * box_cols + col
        for stack in stacks
        for col in rng.sample(range(box_cols), box_cols)
    ]

    return [
        [
            digit_map[
                (row * box_cols + row // box_rows + col) % size + 1
            ]
            for col in cols
        ]
        for row in rows
    ]


def _sudoku_solution_count(board, limit=2):
    """
    Count valid solutions for a 6x6 Sudoku board.

    Stops as soon as 'limit' solutions have been found.

    Uses bitmasks and minimum-remaining-values search.
    """

    size = SUDOKU_SIZE
    box_rows = SUDOKU_BOX_ROWS
    box_cols = SUDOKU_BOX_COLS

    if not isinstance(board, list) or len(board) != size:
        return 0

    if any(not isinstance(row, list) or len(row) != size for row in board):
        return 0

    grid = [row[:] for row in board]

    rows = [0] * size
    cols = [0] * size
    boxes = [0] * (size // box_rows * (size // box_cols))

    full_mask = (1 << (size + 1)) - 2

    # Load the existing clues and reject conflicts.
    for row in range(size):
        for col in range(size):
            value = grid[row][col]

            if value == 0:
                continue

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 1
                or value > size
            ):
                return 0

            bit = 1 << value

            box = (
                (row // box_rows) * (size // box_cols)
                + col // box_cols
            )

            if (
                rows[row] & bit
                or cols[col] & bit
                or boxes[box] & bit
            ):
                return 0

            rows[row] |= bit
            cols[col] |= bit
            boxes[box] |= bit

    solution_count = 0

    def solve():
        nonlocal solution_count

        if solution_count >= limit:
            return

        best_cell = None
        best_mask = 0
        best_size = size + 1

        # Find the empty cell with the fewest candidates.
        for row in range(size):
            for col in range(size):
                if grid[row][col] != 0:
                    continue

                box = (
                    (row // box_rows) * (size // box_cols)
                    + col // box_cols
                )

                mask = full_mask & ~(
                    rows[row] | cols[col] | boxes[box]
                )

                candidate_count = mask.bit_count()

                if candidate_count == 0:
                    return

                if candidate_count < best_size:
                    best_cell = (row, col, box)
                    best_mask = mask
                    best_size = candidate_count

                    if best_size == 1:
                        break

            if best_size == 1:
                break

        # All cells filled: one complete solution found.
        if best_cell is None:
            solution_count += 1
            return

        row, col, box = best_cell
        mask = best_mask

        while mask and solution_count < limit:
            bit = mask & -mask
            mask ^= bit

            value = bit.bit_length() - 1

            grid[row][col] = value

            rows[row] |= bit
            cols[col] |= bit
            boxes[box] |= bit

            solve()

            rows[row] ^= bit
            cols[col] ^= bit
            boxes[box] ^= bit

            grid[row][col] = 0

    solve()

    return solution_count


def generate_sudoku(difficulty="medium", rng=None):
    """
    Generate a fresh 6x6 Sudoku puzzle with a unique solution.

    Return format remains compatible with arena.py.
    """

    if difficulty not in SUDOKU_CLUES:
        raise ValueError(
            "Difficulty must be easy, medium, or hard"
        )

    rng = rng or random.Random()

    target_clues = SUDOKU_CLUES[difficulty]

    best_result = None

    # Multiple attempts help achieve the requested clue count.
    for _ in range(5):
        solution = _sudoku_solution(rng)
        puzzle = [row[:] for row in solution]

        cells = [
            (row, col)
            for row in range(SUDOKU_SIZE)
            for col in range(SUDOKU_SIZE)
        ]

        rng.shuffle(cells)

        clues = SUDOKU_SIZE * SUDOKU_SIZE

        for row, col in cells:
            if clues <= target_clues:
                break

            previous = puzzle[row][col]
            puzzle[row][col] = 0

            # Remove a clue only if exactly one solution remains.
            if _sudoku_solution_count(puzzle, limit=2) == 1:
                clues -= 1
            else:
                puzzle[row][col] = previous

        result = {
            "type": "sudoku",
            "difficulty": difficulty,
            "size": SUDOKU_SIZE,
            "grid": puzzle,
            "solution": solution,
            "clues": clues,
        }

        if best_result is None or clues < best_result["clues"]:
            best_result = result

        if clues <= target_clues:
            return result

    # Even if the target clue count cannot be reached,
    # return the best uniquely solvable puzzle found.
    return best_result


# ============================================================
# KENKEN: LATIN SQUARE AND CAGE GENERATION
# ============================================================

def _latin_solution(size, rng):
    """
    Generate a randomized Latin-square solution.

    Every row and column contains each number exactly once.
    """

    symbols = list(range(1, size + 1))
    rng.shuffle(symbols)

    rows = list(range(size))
    cols = list(range(size))

    rng.shuffle(rows)
    rng.shuffle(cols)

    return [
        [
            symbols[(rows[row] + cols[col]) % size]
            for col in range(size)
        ]
        for row in range(size)
    ]


def _product(values):
    result = 1

    for value in values:
        result *= value

    return result


def _make_cages(solution, max_cage_size, rng):
    """
    Partition the solution into connected arithmetic cages.

    Every grid cell belongs to exactly one cage.

    Cage format:
      {
          "cells": [[row, col], ...],
          "operation": "+",
          "target": 10
      }

    This coordinate format is used by the frontend.
    """

    size = len(solution)

    remaining = {
        (row, col)
        for row in range(size)
        for col in range(size)
    }

    cages = []

    while remaining:
        start = rng.choice(tuple(remaining))

        cells = [start]
        remaining.remove(start)

        wanted = rng.randint(
            1,
            min(max_cage_size, size)
        )

        while len(cells) < wanted:
            frontier = set()

            for row, col in cells:
                neighbors = (
                    (row - 1, col),
                    (row + 1, col),
                    (row, col - 1),
                    (row, col + 1),
                )

                for nr, nc in neighbors:
                    if (nr, nc) in remaining:
                        frontier.add((nr, nc))

            if not frontier:
                break

            chosen = rng.choice(tuple(frontier))

            cells.append(chosen)
            remaining.remove(chosen)

        values = [
            solution[row][col]
            for row, col in cells
        ]

        if len(values) == 1:
            operation = "="
            target = values[0]

        else:
            choices = [
                ("+", sum(values)),
                ("×", _product(values)),
            ]

            if len(values) == 2:
                a, b = values

                choices.append(
                    ("−", abs(a - b))
                )

                if max(a, b) % min(a, b) == 0:
                    choices.append(
                        ("÷", max(a, b) // min(a, b))
                    )

            operation, target = rng.choice(choices)

        cages.append({
            "cells": [
                [row, col]
                for row, col in cells
            ],
            "operation": operation,
            "target": target,
        })

    return cages


# ============================================================
# KENKEN: CAGE VALIDATION
# ============================================================

def _kenken_cage_valid(cage, grid):
    """
    Check whether the currently entered values in a cage
    can still satisfy its arithmetic target.
    """

    cells = cage["cells"]

    values = [
        grid[row][col]
        for row, col in cells
        if grid[row][col] != 0
    ]

    if not values:
        return True

    target = cage["target"]
    operation = cage["operation"]

    complete = len(values) == len(cells)

    if operation == "=":
        return (
            len(values) == 1
            and values[0] == target
        )

    if operation == "+":
        total = sum(values)

        return (
            total == target
            if complete
            else total <= target
        )

    if operation == "×":
        current_product = _product(values)

        return (
            current_product == target
            if complete
            else target % current_product == 0
        )

    if operation == "−":
        if not complete:
            return True

        if len(values) != 2:
            return False

        return abs(values[0] - values[1]) == target

    if operation == "÷":
        if not complete:
            return True

        if len(values) != 2:
            return False

        a, b = max(values), min(values)

        return (
            b != 0
            and a % b == 0
            and a // b == target
        )

    return False


# ============================================================
# KENKEN: SOLUTION COUNTING
# ============================================================

def _kenken_solution_count(
    size,
    cages,
    limit=2,
    max_nodes=150000,
):
    """
    Count valid KenKen solutions.

    Enforces:
      - Each row uses numbers 1..size once.
      - Each column uses numbers 1..size once.
      - Every arithmetic cage satisfies its target.

    Returns:
      (solution_count, exceeded_node_budget)
    """

    grid = [
        [0] * size
        for _ in range(size)
    ]

    rows = [0] * size
    cols = [0] * size

    full_mask = (1 << (size + 1)) - 2

    cage_for = {}

    # Verify that cages cover every cell exactly once.
    for cage_index, cage in enumerate(cages):
        if not cage.get("cells"):
            return 0, False

        for cell in cage["cells"]:
            if (
                not isinstance(cell, (list, tuple))
                or len(cell) != 2
            ):
                return 0, False

            row, col = cell

            if (
                not isinstance(row, int)
                or not isinstance(col, int)
                or not 0 <= row < size
                or not 0 <= col < size
            ):
                return 0, False

            if (row, col) in cage_for:
                return 0, False

            cage_for[(row, col)] = cage_index

    if len(cage_for) != size * size:
        return 0, False

    solution_count = 0
    nodes = 0
    exceeded = False

    def solve():
        nonlocal solution_count, nodes, exceeded

        if solution_count >= limit or exceeded:
            return

        nodes += 1

        if nodes > max_nodes:
            exceeded = True
            return

        best_cell = None
        best_candidates = None

        # Find the empty cell with the fewest valid candidates.
        for row in range(size):
            for col in range(size):
                if grid[row][col] != 0:
                    continue

                mask = full_mask & ~(
                    rows[row] | cols[col]
                )

                candidates = []

                while mask:
                    bit = mask & -mask
                    mask ^= bit

                    value = bit.bit_length() - 1

                    grid[row][col] = value

                    cage_index = cage_for[(row, col)]
                    cage = cages[cage_index]

                    if _kenken_cage_valid(cage, grid):
                        candidates.append((value, bit))

                    grid[row][col] = 0

                if not candidates:
                    return

                if (
                    best_candidates is None
                    or len(candidates) < len(best_candidates)
                ):
                    best_cell = (row, col)
                    best_candidates = candidates

                if len(best_candidates) == 1:
                    break

            if best_candidates and len(best_candidates) == 1:
                break

        if best_cell is None:
            solution_count += 1
            return

        row, col = best_cell

        for value, bit in best_candidates:
            grid[row][col] = value

            rows[row] |= bit
            cols[col] |= bit

            solve()

            rows[row] ^= bit
            cols[col] ^= bit

            grid[row][col] = 0

            if solution_count >= limit or exceeded:
                return

    solve()

    return solution_count, exceeded


# ============================================================
# KENKEN: PUZZLE GENERATION
# ============================================================

def generate_kenken(difficulty="medium", rng=None):
    """
    Generate a fresh KenKen puzzle with a unique solution.

    Return format remains compatible with arena.py and
    the PuzzlePlayer frontend.
    """

    if difficulty not in KENKEN_SIZES:
        raise ValueError(
            "Difficulty must be easy, medium, or hard"
        )

    rng = rng or random.Random()

    size = KENKEN_SIZES[difficulty]
    max_cage_size = KENKEN_MAX_CAGE_SIZE[difficulty]

    for _ in range(120):
        solution = _latin_solution(size, rng)

        cages = _make_cages(
            solution,
            max_cage_size,
            rng
        )

        count, exceeded = _kenken_solution_count(
            size,
            cages,
            limit=2,
            max_nodes=150000,
        )

        if count == 1 and not exceeded:
            return {
                "type": "kenken",
                "difficulty": difficulty,
                "size": size,
                "grid": [
                    [0] * size
                    for _ in range(size)
                ],
                "cages": cages,
                "solution": solution,
            }

    raise RuntimeError(
        "Could not generate a unique KenKen puzzle. Please retry."
    )


# ============================================================
# SUBMISSION VALIDATION
# ============================================================

def validate_grid(submitted, solution, size):
    """
    Validate the submitted puzzle grid against the private
    generated solution.

    Rejects:
      - Incorrect dimensions
      - Non-integer values
      - Boolean values
      - Values outside 1..size
      - Incorrect solutions
    """

    if not isinstance(submitted, list):
        return False

    if not isinstance(solution, list):
        return False

    if len(submitted) != size or len(solution) != size:
        return False

    for row in submitted:
        if not isinstance(row, list) or len(row) != size:
            return False

        for value in row:
            if isinstance(value, bool) or not isinstance(value, int):
                return False

            if value < 1 or value > size:
                return False

    for row in solution:
        if not isinstance(row, list) or len(row) != size:
            return False

    return submitted == solution
