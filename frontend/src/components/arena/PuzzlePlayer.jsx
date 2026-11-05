
import { useMemo, useState } from "react";
import {
  X, Play, Send, RotateCcw, RotateCw, Eraser,
  Trash2, Trophy, Loader2, Sparkles, CircleHelp,
} from "lucide-react";
import { api } from "@/lib/api";

const DIFFICULTIES = [
  { key: "easy", xp: 10 },
  { key: "medium", xp: 20 },
  { key: "hard", xp: 35 },
];

const BRAND = ["#00DFFF", "#526BFF", "#F52BBE"];

function cloneGrid(grid) {
  return grid.map((row) => [...row]);
}

function getCellCoordinates(cell, size) {
  if (Array.isArray(cell) && cell.length >= 2) {
    return [Number(cell[0]), Number(cell[1])];
  }

  if (typeof cell === "number") {
    return [Math.floor(cell / size), cell % size];
  }

  if (typeof cell === "string") {
    const parts = cell.split(",").map(Number);
    if (parts.length === 2 && parts.every(Number.isFinite)) return parts;
  }

  if (cell && typeof cell === "object") {
    const row = Number(cell.row ?? cell.r);
    const col = Number(cell.col ?? cell.c);
    if (Number.isFinite(row) && Number.isFinite(col)) return [row, col];
  }

  return null;
}

function normalizeCages(cages = [], size = 0) {
  const cellMap = {};
  const anchors = {};

  cages.forEach((cage, index) => {
    const coordinates = (cage.cells || [])
      .map((cell) => getCellCoordinates(cell, size))
      .filter(
        (point) =>
          point &&
          point[0] >= 0 &&
          point[0] < size &&
          point[1] >= 0 &&
          point[1] < size
      );

    coordinates.forEach(([row, col]) => {
      cellMap[`${row}-${col}`] = index;
    });

    if (coordinates.length) {
      coordinates.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
      const [row, col] = coordinates[0];
      anchors[`${row}-${col}`] = cage;
    }
  });

  return { cellMap, anchors };
}

function formatOperation(operation) {
  const symbols = {
    "*": "×",
    x: "×",
    "/": "÷",
    "-": "−",
    "+": "+",
    "=": "",
  };

  return symbols[operation] ?? operation ?? "";
}

export default function PuzzlePlayer({ game, onClose, onScored }) {
  const isSudoku = game === "sudoku";

  const [difficulty, setDifficulty] = useState("easy");
  const [puzzle, setPuzzle] = useState(null);
  const [grid, setGrid] = useState([]);
  const [selected, setSelected] = useState(null);

  const [history, setHistory] = useState([]);
  const [redoStack, setRedoStack] = useState([]);

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("info");
  const [completed, setCompleted] = useState(false);
  const [xp, setXp] = useState(0);
  const [helpOpen, setHelpOpen] = useState(false);

  const size = grid.length || puzzle?.grid?.length || 0;

  const numbers = useMemo(
    () => Array.from({ length: size }, (_, index) => index + 1),
    [size]
  );

  const { cellMap, anchors } = useMemo(
    () => normalizeCages(puzzle?.cages || [], size),
    [puzzle?.cages, size]
  );

  const canEdit = (row, col) =>
    Boolean(puzzle && puzzle.grid[row]?.[col] === 0 && !completed);

  const isSelected = (row, col) =>
    selected?.[0] === row && selected?.[1] === col;

  // ------------------------------------------------------
  // GENERATE PUZZLE
  // ------------------------------------------------------

  async function startPuzzle() {
    setLoading(true);
    setMessage("");
    setMessageType("info");
    setCompleted(false);
    setXp(0);
    setHistory([]);
    setRedoStack([]);
    setSelected(null);

    try {
      const response = await api.post("/arena/puzzles/start", {
        game,
        difficulty,
      });

      const data = response.data;

      if (!Array.isArray(data?.grid) || !data.grid.length) {
        throw new Error("The server returned an invalid puzzle grid.");
      }

      const initialGrid = cloneGrid(data.grid);

      setPuzzle(data);
      setGrid(initialGrid);

      let firstEmpty = null;

      for (let row = 0; row < initialGrid.length; row++) {
        for (let col = 0; col < initialGrid[row].length; col++) {
          if (initialGrid[row][col] === 0 && !firstEmpty) {
            firstEmpty = [row, col];
          }
        }
      }

      setSelected(firstEmpty);
    } catch (error) {
      setMessage(
        error.response?.data?.detail ||
        error.message ||
        "Unable to generate puzzle. Please try again."
      );
      setMessageType("error");
    } finally {
      setLoading(false);
    }
  }

  // ------------------------------------------------------
  // MOVES AND HISTORY
  // ------------------------------------------------------

  function saveMove(nextGrid) {
    setHistory((previous) => [...previous, cloneGrid(grid)]);
    setRedoStack([]);
    setGrid(nextGrid);
    setMessage("");
    setMessageType("info");
  }

  function enterNumber(number) {
    if (!selected || !puzzle || completed) return;

    const [row, col] = selected;
    if (!canEdit(row, col)) return;

    const next = cloneGrid(grid);
    next[row][col] = number;
    saveMove(next);
  }

  function clearCell() {
    if (!selected || !puzzle || completed) return;

    const [row, col] = selected;
    if (!canEdit(row, col) || grid[row][col] === 0) return;

    const next = cloneGrid(grid);
    next[row][col] = 0;
    saveMove(next);
  }

  function undo() {
    if (!history.length || completed) return;

    const previous = history[history.length - 1];

    setRedoStack((stack) => [...stack, cloneGrid(grid)]);
    setGrid(previous);
    setHistory((stack) => stack.slice(0, -1));
    setMessage("");
    setMessageType("info");
  }

  function redo() {
    if (!redoStack.length || completed) return;

    const next = redoStack[redoStack.length - 1];

    setHistory((stack) => [...stack, cloneGrid(grid)]);
    setGrid(next);
    setRedoStack((stack) => stack.slice(0, -1));
    setMessage("");
    setMessageType("info");
  }

  function clearAll() {
    if (!puzzle || completed) return;

    const next = grid.map((row, rowIndex) =>
      row.map((value, colIndex) =>
        puzzle.grid[rowIndex][colIndex] !== 0 ? value : 0
      )
    );

    saveMove(next);
  }

  // ------------------------------------------------------
  // SUBMISSION AND FEEDBACK
  // ------------------------------------------------------

  async function submitPuzzle() {
    if (!puzzle || completed || submitting) return;

    const hasEmptyCells = grid.some((row) =>
      row.some((value) => value === 0)
    );

    if (hasEmptyCells) {
      setMessage("Complete all empty cells before submitting your solution.");
      setMessageType("error");
      return;
    }

    setSubmitting(true);
    setMessage("");
    setMessageType("info");

    try {
      const response = await api.post(
        `/arena/puzzles/${puzzle.puzzle_id}/submit`,
        { grid }
      );

      const data = response.data;

      if (data.correct) {
        const awarded = data.xp_awarded || 0;

        setCompleted(true);
        setXp(awarded);

        setMessage(
          awarded > 0
            ? `Correct solution! You earned ${awarded} XP.`
            : "Correct solution! Practice completed."
        );

        setMessageType("success");
        onScored?.();
      } else {
        setMessage(
          data.message || "Incorrect solution. Check your entries and try again."
        );
        setMessageType("error");
      }
    } catch (error) {
      setMessage(
        error.response?.data?.detail ||
        "Submission failed. Please try again."
      );
      setMessageType("error");
    } finally {
      setSubmitting(false);
    }
  }

  // ------------------------------------------------------
  // SUDOKU GLASS CELLS
  // ------------------------------------------------------

  function sudokuCellStyle(row, col) {
    const active = isSelected(row, col);
    const given = puzzle?.grid[row]?.[col] !== 0;

    const region = (Math.floor(row / 2) + Math.floor(col / 3)) % 2;

    const background = active
      ? "linear-gradient(135deg,rgba(0,223,255,.30),rgba(82,107,255,.20),rgba(245,43,190,.16))"
      : given
        ? region === 0
          ? "linear-gradient(135deg,rgba(22,47,72,.88),rgba(14,30,51,.84))"
          : "linear-gradient(135deg,rgba(26,43,70,.88),rgba(13,27,47,.84))"
        : region === 0
          ? "linear-gradient(135deg,rgba(9,25,43,.92),rgba(6,16,30,.90))"
          : "linear-gradient(135deg,rgba(12,29,50,.92),rgba(7,19,34,.90))";

    const major = "rgba(0,223,255,.9)";
    const minor = "rgba(82,107,255,.32)";

    return {
      backgroundImage: background,
      color: active ? "#ffffff" : given ? "#f4faff" : "#7deeff",
      backdropFilter: "blur(8px)",
      borderTop:
        row === 0 || row % 2 === 0
          ? `2px solid ${major}`
          : `1px solid ${minor}`,
      borderBottom: row === size - 1 ? `2px solid ${major}` : "none",
      borderLeft:
        col === 0 || col % 3 === 0
          ? `2px solid ${major}`
          : `1px solid ${minor}`,
      borderRight: col === size - 1 ? `2px solid ${major}` : "none",
      boxShadow: active
        ? "inset 0 0 0 1px #00dfff,0 0 18px rgba(0,223,255,.22)"
        : "inset 0 0 12px rgba(255,255,255,.015)",
    };
  }

  // ------------------------------------------------------
  // KENKEN: MONOCHROME DARK CELLS + NEON CYAN CAGES
  // ------------------------------------------------------

  function kenkenCellStyle(row, col) {
    const key = `${row}-${col}`;
    const cageIndex = cellMap[key];

    const sameCage = (r, c) =>
      cageIndex !== undefined &&
      cellMap[`${r}-${c}`] === cageIndex;

    const active = isSelected(row, col);
    const given = puzzle?.grid[row]?.[col] !== 0;

    const cageBorder = "2px solid #00DFFF";
    const innerBorder = "1px solid rgba(170,190,210,.18)";

    const borderFor = (r, c) =>
      sameCage(r, c) ? innerBorder : cageBorder;

    return {
      backgroundImage: active
        ? "linear-gradient(135deg,rgba(0,223,255,.19),rgba(0,223,255,.08))"
        : given
          ? "linear-gradient(145deg,rgba(31,36,44,.96),rgba(15,19,26,.98))"
          : "linear-gradient(145deg,rgba(22,26,34,.96),rgba(8,12,19,.98))",

      color: active ? "#ffffff" : "#f6f8ff",
      backdropFilter: "blur(8px)",

      borderTop:
        row === 0
          ? cageBorder
          : borderFor(row - 1, col),

      borderLeft:
        col === 0
          ? cageBorder
          : borderFor(row, col - 1),

      borderRight: "none",
      borderBottom: "none",

      boxShadow: active
        ? "inset 0 0 0 1px #00DFFF,0 0 14px rgba(0,223,255,.18)"
        : "inset 0 0 12px rgba(255,255,255,.018)",
    };
  }

  const keypadColumns = size === 6 ? 6 : size === 4 ? 4 : 3;

  const helpPoints = isSudoku
    ? [
        "Fill every empty cell using numbers 1 to 6.",
        "Each row must contain 1 to 6 without repetition.",
        "Each column must contain 1 to 6 without repetition.",
        "Each highlighted 2 × 3 box must contain 1 to 6.",
        "Tap a cell, then tap a number to enter it.",
        "Use Undo, Redo and Clear to correct your entries.",
        "Submit your completed grid to check your answer.",
      ]
    : [
        `Fill every row and column using numbers 1 to ${size || "N"}, without repetition.`,
        "Each outlined cage has a target number and an operation.",
        "Combine the numbers inside a cage to reach its target.",
        "Addition (+): add the cage numbers.",
        "Multiplication (×): multiply the cage numbers.",
        "Subtraction (−) and division (÷): use the two cage numbers.",
        "Tap a cell, enter a number, then submit when complete.",
      ];

  // ------------------------------------------------------
  // RENDER
  // ------------------------------------------------------

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center overflow-y-auto bg-[#02040a]/90 p-2 backdrop-blur-2xl sm:items-center sm:p-4"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose?.();
      }}
    >
      <div
        className="relative my-2 flex w-full max-w-5xl flex-col overflow-hidden rounded-3xl border border-white/10 sm:my-auto sm:max-h-[96dvh]"
        style={{
          background: "rgba(8,12,22,.82)",
          backdropFilter: "blur(26px)",
          boxShadow:
            "0 0 65px rgba(0,223,255,.09),0 0 85px rgba(245,43,190,.055),inset 0 1px rgba(255,255,255,.055)",
        }}
      >
        {/* Three-color brand accents */}
        <div className="h-[3px] shrink-0 bg-gradient-to-r from-cyan-400 via-blue-500 to-fuchsia-500" />

        {/* HEADER */}
        <header className="flex shrink-0 items-center justify-between gap-4 border-b border-white/10 px-4 py-4 sm:px-7">
          <div className="min-w-0">
            <p className="font-mono text-[9px] uppercase tracking-[0.38em] text-cyan-300 sm:text-[10px]">
              SANKALP’26 // ARENA
            </p>

            <h2 className="mt-1 font-display text-xl font-black uppercase tracking-wider text-white sm:text-2xl">
              {isSudoku ? "Sudoku" : "KenKen"}
            </h2>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <button
              onClick={() => setHelpOpen(true)}
              aria-label="How to play"
              title="How to play"
              className="flex h-10 w-10 items-center justify-center rounded-full border border-white/15 bg-white/[0.025] text-cyan-200 backdrop-blur-xl transition hover:border-fuchsia-400 hover:text-fuchsia-200"
            >
              <CircleHelp size={19} />
            </button>

            <button
              onClick={onClose}
              aria-label="Close puzzle"
              className="flex h-10 w-10 items-center justify-center rounded-full border border-cyan-400/40 bg-white/[0.025] text-white backdrop-blur-xl transition hover:border-fuchsia-400 hover:text-fuchsia-200"
            >
              <X size={20} />
            </button>
          </div>
        </header>

        <main className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6 lg:p-7">

          {/* DIFFICULTY SELECTION */}
          {!puzzle && (
            <section className="mx-auto flex min-h-[45vh] max-w-xl flex-col items-center justify-center text-center">
              <div
                className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-cyan-300/30 text-cyan-200"
                style={{
                  background:
                    "linear-gradient(135deg,rgba(0,223,255,.14),rgba(82,107,255,.12),rgba(245,43,190,.12))",
                  backdropFilter: "blur(15px)",
                  boxShadow: "0 0 25px rgba(0,223,255,.08)",
                }}
              >
                <Sparkles size={26} />
              </div>

              <h3 className="font-display text-xl font-bold uppercase text-white sm:text-2xl">
                Initialize {isSudoku ? "Sudoku" : "KenKen"}
              </h3>

              <p className="mt-2 max-w-sm text-sm leading-relaxed text-white/50">
                Select your difficulty and prepare for the challenge.
              </p>

              <div className="mt-8 grid w-full grid-cols-3 gap-2 sm:gap-3">
                {DIFFICULTIES.map(({ key, xp: reward }, index) => {
                  const active = difficulty === key;
                  const accent = BRAND[index];

                  return (
                    <button
                      key={key}
                      onClick={() => setDifficulty(key)}
                      className={`group flex min-h-[82px] flex-col items-center justify-center gap-1 rounded-xl border backdrop-blur-xl transition-all duration-300 ${
                        active
                          ? "border-white/35 text-white"
                          : "border-white/10 bg-white/[0.025] text-white/65 hover:border-white/25"
                      }`}
                      style={{
                        background: active
                          ? `linear-gradient(125deg,${accent}28,${BRAND[(index + 1) % 3]}20,${BRAND[(index + 2) % 3]}18)`
                          : "rgba(255,255,255,.025)",
                        boxShadow: active
                          ? `0 0 22px ${accent}20,inset 0 0 15px ${accent}0b`
                          : "inset 0 0 12px rgba(255,255,255,.015)",
                      }}
                    >
                      <span className="font-display text-xl font-black sm:text-2xl">
                        {reward} XP
                      </span>

                      <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-white/55 sm:text-[10px]">
                        {key}
                      </span>
                    </button>
                  );
                })}
              </div>

              <button
                onClick={startPuzzle}
                disabled={loading}
                className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl border border-white/20 px-5 py-4 font-mono text-xs font-bold uppercase tracking-[0.2em] text-white backdrop-blur-xl transition hover:border-cyan-300/60 disabled:opacity-50"
                style={{
                  background:
                    "linear-gradient(105deg,rgba(0,223,255,.15),rgba(82,107,255,.15),rgba(245,43,190,.13))",
                  boxShadow:
                    "0 0 24px rgba(0,223,255,.07),inset 0 0 18px rgba(255,255,255,.025)",
                }}
              >
                {loading ? (
                  <Loader2 size={17} className="animate-spin" />
                ) : (
                  <Play size={17} />
                )}

                {loading ? "Preparing..." : "Let's Begin"}
              </button>

              {message && (
                <div
                  role="alert"
                  className="mt-5 w-full rounded-xl border border-fuchsia-400/30 bg-fuchsia-400/5 p-4 text-sm text-white/80 backdrop-blur-xl"
                >
                  {message}
                </div>
              )}
            </section>
          )}

          {/* ACTIVE PUZZLE */}
          {puzzle && (
            <>
              <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/50">
                    {difficulty} difficulty
                    <span className="mx-2 text-cyan-400">·</span>
                    {size} × {size}
                  </p>

                  <p className="mt-1 text-xs text-white/35">
                    {isSudoku
                      ? "Complete every row, column and 2 × 3 region."
                      : "Complete every row, column and arithmetic cage."}
                  </p>
                </div>

                <span
                  className="rounded-full border border-white/15 px-3 py-2 font-mono text-[10px] uppercase tracking-wider text-white/80 backdrop-blur-xl"
                  style={{
                    background:
                      "linear-gradient(105deg,rgba(0,223,255,.08),rgba(82,107,255,.08),rgba(245,43,190,.07))",
                  }}
                >
                  {puzzle.scored ? `${puzzle.xp || 0} XP` : "Practice mode"}
                </span>
              </div>

              <div className="grid grid-cols-1 items-stretch gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(250px,.8fr)] lg:gap-8">

                {/* GAME BOARD */}
                <section className="min-w-0">
                  <div
                    className="mx-auto w-full"
                    style={{ maxWidth: "min(100%, 33rem)" }}
                  >
                    <div
                      className="overflow-hidden rounded-xl p-[2px]"
                      style={{
                        background: isSudoku
                          ? "linear-gradient(135deg,#00DFFF,#526BFF,#F52BBE)"
                          : "#00DFFF",
                        boxShadow: isSudoku
                          ? "0 0 30px rgba(0,190,255,.13)"
                          : "0 0 25px rgba(0,223,255,.12)",
                      }}
                    >
                      <div
                        className="grid aspect-square w-full overflow-hidden rounded-[10px]"
                        style={{
                          gridTemplateColumns: `repeat(${size},minmax(0,1fr))`,
                          background: "rgba(4,8,16,.96)",
                        }}
                      >
                        {grid.map((row, rowIndex) =>
                          row.map((value, colIndex) => {
                            const cage = anchors[`${rowIndex}-${colIndex}`];

                            const style = isSudoku
                              ? sudokuCellStyle(rowIndex, colIndex)
                              : kenkenCellStyle(rowIndex, colIndex);

                            return (
                              <button
                                key={`${rowIndex}-${colIndex}`}
                                type="button"
                                disabled={completed}
                                onClick={() => setSelected([rowIndex, colIndex])}
                                aria-label={`Row ${rowIndex + 1}, column ${colIndex + 1}, ${value || "empty"}`}
                                aria-pressed={isSelected(rowIndex, colIndex)}
                                style={style}
                                className="relative flex aspect-square min-w-0 select-none items-center justify-center font-mono text-base font-semibold transition-colors duration-100 sm:text-xl"
                              >
                                {!isSudoku && cage && (
                                  <span className="pointer-events-none absolute left-[3px] top-[2px] z-10 text-[8px] font-bold leading-none text-white/90 sm:left-1 sm:top-1 sm:text-[11px]">
                                    {cage.target}{formatOperation(cage.operation)}
                                  </span>
                                )}

                                <span className={!isSudoku && cage ? "mt-2" : ""}>
                                  {value || ""}
                                </span>
                              </button>
                            );
                          })
                        )}
                      </div>
                    </div>
                  </div>

                  <p className="mt-3 text-center font-mono text-[9px] uppercase tracking-[0.2em] text-white/35">
                    {isSudoku
                      ? "Regions: 2 rows × 3 columns"
                      : "Cage targets appear in the top-left cell"}
                  </p>
                </section>

                {/* CONTROL PANEL */}
                <aside className="flex min-w-0 flex-col gap-4 lg:min-h-[33rem]">

                  {/* UNDO / CLEAR / REDO */}
                  <div className="grid grid-cols-[1fr_1.5fr_1fr] gap-2">
                    <button
                      onClick={undo}
                      disabled={!history.length || completed}
                      aria-label="Undo"
                      className="flex items-center justify-center rounded-xl border border-white/10 bg-white/[0.035] py-3 text-white/70 backdrop-blur-xl transition hover:border-cyan-400/50 hover:text-cyan-200 disabled:opacity-25"
                    >
                      <RotateCcw size={17} />
                    </button>

                    <button
                      onClick={clearAll}
                      disabled={completed}
                      className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.035] py-3 font-mono text-[10px] font-bold uppercase tracking-widest text-white/70 backdrop-blur-xl transition hover:border-fuchsia-400/50 hover:text-fuchsia-200 disabled:opacity-25"
                    >
                      <Eraser size={15} />
                      Clear all
                    </button>

                    <button
                      onClick={redo}
                      disabled={!redoStack.length || completed}
                      aria-label="Redo"
                      className="flex items-center justify-center rounded-xl border border-white/10 bg-white/[0.035] py-3 text-white/70 backdrop-blur-xl transition hover:border-cyan-400/50 hover:text-cyan-200 disabled:opacity-25"
                    >
                      <RotateCw size={17} />
                    </button>
                  </div>

                  <button
                    onClick={clearCell}
                    disabled={
                      !selected ||
                      !canEdit(...(selected || [0, 0])) ||
                      grid[selected?.[0] ?? 0]?.[selected?.[1] ?? 0] === 0
                    }
                    className="flex w-full items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.025] py-3 font-mono text-[10px] font-bold uppercase tracking-widest text-white/55 backdrop-blur-xl transition hover:border-fuchsia-400/40 hover:text-fuchsia-200 disabled:opacity-25"
                  >
                    <Trash2 size={15} />
                    Clear selected cell
                  </button>

                  {/* NUMBER KEYPAD */}
                  <div>
                    <p className="mb-3 font-mono text-[9px] uppercase tracking-[0.25em] text-white/40">
                      Number keypad
                    </p>

                    <div
                      className="grid gap-2"
                      style={{
                        gridTemplateColumns: `repeat(${keypadColumns},minmax(0,1fr))`,
                      }}
                    >
                      {numbers.map((number) => (
                        <button
                          key={number}
                          onClick={() => enterNumber(number)}
                          disabled={
                            !selected ||
                            !canEdit(...(selected || [0, 0])) ||
                            completed
                          }
                          className="flex aspect-square max-h-16 items-center justify-center rounded-xl border border-white/10 font-display text-xl font-bold text-white backdrop-blur-xl transition hover:border-cyan-300/60 hover:text-cyan-100 active:translate-y-[2px] disabled:cursor-not-allowed disabled:opacity-30 sm:text-2xl"
                          style={{
                            background:
                              "linear-gradient(135deg,rgba(0,223,255,.10),rgba(82,107,255,.10),rgba(245,43,190,.07))",
                            boxShadow:
                              "0 3px 0 rgba(82,107,255,.15),inset 0 0 12px rgba(255,255,255,.025)",
                          }}
                        >
                          {number}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* SUBMIT */}
                  <button
                    onClick={submitPuzzle}
                    disabled={submitting || completed}
                    className="flex w-full items-center justify-center gap-2 rounded-xl border border-white/20 px-4 py-4 font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-white backdrop-blur-xl transition hover:border-cyan-300/60 disabled:opacity-40"
                    style={{
                      background:
                        "linear-gradient(105deg,rgba(0,223,255,.17),rgba(82,107,255,.16),rgba(245,43,190,.14))",
                    }}
                  >
                    {submitting ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Send size={16} />
                    )}

                    {submitting
                      ? "Checking solution..."
                      : completed
                        ? "Solved"
                        : "Submit solution"}
                  </button>

                  {/* NEW PUZZLE */}
                  <button
                    onClick={startPuzzle}
                    disabled={loading}
                    className="flex w-full items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.025] px-4 py-3 font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-white/65 backdrop-blur-xl transition hover:border-fuchsia-400/40 hover:text-white disabled:opacity-30"
                  >
                    {loading ? (
                      <Loader2 size={15} className="animate-spin" />
                    ) : (
                      <RotateCcw size={15} />
                    )}
                    New puzzle
                  </button>

                  {/* RESULT AREA — MOVED UP SLIGHTLY */}
                  <div
                    role="status"
                    aria-live="polite"
                    className="mt-auto mb-5 flex min-h-[135px] flex-col items-center justify-center rounded-2xl border p-4 text-center backdrop-blur-2xl"
                    style={{
                      borderColor:
                        messageType === "success"
                          ? "rgba(0,223,255,.40)"
                          : messageType === "error"
                            ? "rgba(245,43,190,.38)"
                            : "rgba(255,255,255,.08)",
                      background:
                        messageType === "success"
                          ? "linear-gradient(130deg,rgba(0,223,255,.10),rgba(82,107,255,.10),rgba(245,43,190,.08))"
                          : messageType === "error"
                            ? "linear-gradient(130deg,rgba(245,43,190,.10),rgba(82,107,255,.07),rgba(0,223,255,.06))"
                            : "linear-gradient(130deg,rgba(255,255,255,.035),rgba(82,107,255,.025),rgba(245,43,190,.025))",
                      boxShadow: "inset 0 0 18px rgba(255,255,255,.018)",
                    }}
                  >
                    {message ? (
                      <>
                        {completed && (
                          <Trophy size={24} className="mb-2 text-cyan-200" />
                        )}

                        <p
                          className={`text-sm font-semibold leading-relaxed ${
                            completed ? "text-cyan-100" : "text-white/85"
                          }`}
                        >
                          {message}
                        </p>

                        {completed && xp > 0 && (
                          <p className="mt-2 bg-gradient-to-r from-cyan-300 via-blue-400 to-fuchsia-400 bg-clip-text font-display text-2xl font-black text-transparent">
                            +{xp} XP
                          </p>
                        )}
                      </>
                    ) : (
                      <p className="font-mono text-[9px] uppercase leading-relaxed tracking-[0.2em] text-white/25">
                        Your result will appear here after submission.
                      </p>
                    )}
                  </div>
                </aside>
              </div>
            </>
          )}
        </main>

        {/* Three-color bottom accent */}
        <div className="h-[3px] shrink-0 bg-gradient-to-r from-cyan-400 via-blue-500 to-fuchsia-500" />
      </div>

      {/* HOW TO PLAY DIALOG */}
      {helpOpen && (
        <div
          className="fixed inset-0 z-[120] flex items-center justify-center bg-black/80 p-4 backdrop-blur-xl"
          onClick={(event) => {
            if (event.target === event.currentTarget) setHelpOpen(false);
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="puzzle-help-title"
            className="w-full max-w-md overflow-hidden rounded-2xl border border-white/15 shadow-2xl backdrop-blur-2xl"
            style={{
              background: "rgba(9,13,25,.88)",
              boxShadow:
                "0 0 45px rgba(0,223,255,.09),0 0 45px rgba(245,43,190,.07)",
            }}
          >
            <div className="h-[2px] bg-gradient-to-r from-cyan-400 via-blue-500 to-fuchsia-500" />

            <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
              <div>
                <p className="font-mono text-[9px] uppercase tracking-[0.3em] text-cyan-300">
                  SANKALP’26 // ARENA
                </p>

                <h3
                  id="puzzle-help-title"
                  className="mt-1 font-display text-lg font-bold uppercase text-white"
                >
                  How to play {isSudoku ? "Sudoku" : "KenKen"}
                </h3>
              </div>

              <button
                onClick={() => setHelpOpen(false)}
                aria-label="Close instructions"
                className="flex h-9 w-9 items-center justify-center rounded-full border border-white/15 text-white/70 transition hover:border-fuchsia-400 hover:text-white"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-3 px-5 py-5">
              {(isSudoku
                ? [
                    "Fill every empty cell using numbers 1 to 6.",
                    "Each row must contain 1 to 6 without repetition.",
                    "Each column must contain 1 to 6 without repetition.",
                    "Each highlighted 2 × 3 box must contain 1 to 6.",
                    "Tap a cell, then tap a number to enter it.",
                    "Use Undo, Redo and Clear to correct your entries.",
                    "Submit your completed grid to check your answer.",
                  ]
                : [
                    `Fill every row and column using numbers 1 to ${size || "N"}, without repetition.`,
                    "Each outlined cage has a target number and an operation.",
                    "Combine the numbers inside a cage to reach its target.",
                    "Addition (+): add the cage numbers.",
                    "Multiplication (×): multiply the cage numbers.",
                    "Subtraction (−) and division (÷): use the two cage numbers.",
                    "Tap a cell, enter a number, then submit when complete.",
                  ]
              ).map((point, index) => (
                <div
                  key={index}
                  className="flex items-start gap-3 text-sm leading-relaxed text-white/75"
                >
                  <span
                    className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border font-mono text-[10px] text-white"
                    style={{
                      borderColor: BRAND[index % 3],
                      background: `${BRAND[index % 3]}18`,
                    }}
                  >
                    {index + 1}
                  </span>

                  <span>{point}</span>
                </div>
              ))}
            </div>

            <div className="border-t border-white/10 p-4">
              <button
                onClick={() => setHelpOpen(false)}
                className="w-full rounded-xl border border-white/15 py-3 font-mono text-[10px] font-bold uppercase tracking-[0.2em] text-white backdrop-blur-xl transition hover:border-fuchsia-400/50"
                style={{
                  background:
                    "linear-gradient(100deg,rgba(0,223,255,.12),rgba(82,107,255,.12),rgba(245,43,190,.12))",
                }}
              >
                Got it — Let's play
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
