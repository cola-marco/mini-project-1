"""
main.py
-------
02225 DRTS — Mini-Project 1
Entry point: loads task set, runs DM/EDF simulations, prints results.

Run:
    python main.py --taskset path/to/taskset.csv
    python main.py --taskset path/to/taskset.csv --use-wcet
    python main.py --taskset path/to/taskset.csv --replications 5 --seed 42

@Author: Alejandro Garcia Bejarano + AI Generated Assistance
"""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.scheduling.taskset import TaskSet
from simulation.engine import SimulationEngine

from analysis.plots import (
    plot_response_times,
    plot_deadline_misses,
    plot_gantt_chart,
)

# TODO: Code the analysis
# from analysis.dm_analysis import (
#     perform_dm_analysis,
#     check_ll_bound,
#     check_hyperbolic_bound
# )

# =========================================================================
#  ANSI Colors
# =========================================================================

BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
WHITE = "\033[37m"
BG_BLUE = "\033[40m"


def header(text):
    print(f"\n{BOLD}{BG_BLUE}{WHITE} {text} {RESET}")


def label(name, value, color=GREEN):
    print(f"  {DIM}{name}{RESET} = {color}{value}{RESET}")


# =========================================================================
#  EVALUATE THE DATASET ANALYTICALLY
# =========================================================================

# TODO: Evaluate the dataset analytically


# =========================================================================
#  SIMULATION PHASE
# =========================================================================


def run_simulation(
    taskset: TaskSet,
    algorithm: str,
    num_replication: int = 1,
    seed: int = 14,
    use_wcet: bool = False,
) -> dict:
    """
    Run simulation for a given algorithm with optional replications.

    @Returns: aggregated statistics per task
    @Author: Alejandro Garcia Bejarano + AI Generated Assistance
    """
    all_R_i: dict[int, list[float]] = {t.id: [] for t in taskset}
    all_missed: dict[int, int] = {t.id: 0 for t in taskset}

    # This replication loop is if we wanted
    # to experiment with jitter
    for rep in range(num_replication):
        engine = SimulationEngine(
            taskset=taskset,
            algorithm=algorithm,
            seed=seed + rep,
            use_wcet=use_wcet,
        )
        engine.run()
        stats = engine.get_statistics()

        for tid, s in stats.items():
            all_R_i[tid].append(s["R_i"])
            all_missed[tid] += s["missed"]

    aggregated = {}
    for task in taskset:
        wcrts = all_R_i[task.id]
        aggregated[task.id] = {
            "max_R_i": max(wcrts) if wcrts else 0.0,
            "avg_R_i": sum(wcrts) / len(wcrts) if wcrts else 0.0,
            "min_R_i": min(wcrts) if wcrts else 0.0,
            "total_missed": all_missed[task.id],
        }

    # ── Per-task results table ──
    print(
        f"\n  {BOLD}{WHITE}{'τ_i':<6}  {'max R_i':<10}  {'avg R_i':<10}  "
        f"{'D_i':<10}  {'missed':<8}{RESET}"
    )
    print(f"  {DIM}{'─' * 52}{RESET}")

    for tid in sorted(aggregated):
        a = aggregated[tid]
        t = taskset.get_task(tid)
        missed_color = RED if a["total_missed"] > 0 else GREEN

        print(
            f"  {YELLOW}τ_{tid:<4}{RESET}  "
            f"{CYAN}{a['max_R_i']:<10.1f}{RESET}  "
            f"{DIM}{a['avg_R_i']:<10.1f}{RESET}  "
            f"{MAGENTA}{t.deadline:<10}{RESET}  "
            f"{missed_color}{a['total_missed']:<8}{RESET}"
        )

    # ── Summary line ──
    total_missed = sum(a["total_missed"] for a in aggregated.values())
    if total_missed == 0:
        print(f"\n  {GREEN}✓ All deadlines met{RESET}")
    else:
        print(f"\n  {RED}✗ {total_missed} total deadline misses{RESET}")

    return aggregated


# =========================================================================
#  START PROGRAM
# =========================================================================


def main():
    parser = argparse.ArgumentParser(description="02225 DRTS — Mini-Project 1")
    parser.add_argument("--taskset", required=True, help="Path to task set CSV")
    parser.add_argument(
        "--replications",
        type=int,
        default=1,
        help="Number of simulation replications",
    )
    parser.add_argument("--seed", type=int, default=42, help="Base random seed")
    parser.add_argument(
        "--use-wcet",
        action="store_true",
        help="Always use WCET (no randomness, for validation)",
    )
    args = parser.parse_args()

    # ── 1. Load Γ ──
    header(f"LOADING TASK SET — {Path(args.taskset).name}")

    taskset = TaskSet.from_csv(args.taskset)

    print(f"  {BOLD}{YELLOW}{taskset}{RESET}")
    print()
    label("n                    ", f"{taskset.n}", CYAN)
    label("U                    ", f"{taskset.utilization:.4f}")
    label("H                    ", f"{taskset.hyperperiod}", CYAN)
    label("D_max                ", f"{taskset.D_max}", MAGENTA)
    label(
        "Constrained?         ",
        f"{taskset.has_constrained_deadlines}",
        RED if taskset.has_constrained_deadlines else GREEN,
    )

    # ── LL Bound quick check ──
    n = taskset.n
    ll_bound = n * (2 ** (1 / n) - 1)
    label("U_lub (LL bound)     ", f"{ll_bound:.4f}", CYAN)

    if taskset.utilization <= ll_bound:
        print(f"\n  {GREEN}✓ U ≤ U_lub → guaranteed schedulable by RM/DM{RESET}")
    elif taskset.utilization <= 1.0:
        print(f"\n  {YELLOW}? U_lub < U ≤ 1.0 → inconclusive, need RTA/dbf{RESET}")
    else:
        print(f"\n  {RED}✗ U > 1.0 → overloaded, no algorithm can schedule{RESET}")

    # TODO: 2. Analytical
    # dm_analytical, edf_analytical = run_analytical(taskset)

    # ── 3. Simulation ──
    mode = "WCET" if args.use_wcet else f"random (seed={args.seed})"
    
    # ---
    # NOTE:
    # We previously used run_simulation(), which internally created the engine and returned only aggregated statistics.
    #
    # However, for plotting we need access to internal simulation data such as: "engine.schedule_trace"
    #
    # Therefore we instantiate the SimulationEngine directly here so we can access both:
    # - aggregated statistics (get_statistics())
    # - detailed execution trace (schedule_trace)
    # ---

    # The hyperperiod of this task set is astronomically large due to the least common multiple of many relatively prime periods.
    # Simulating the full hyperperiod is infeasible, therefore we simulate a bounded time horizon proportional to the largest deadline.
    duration = 10 * taskset.D_max
    
    # We run two simulations:
    # 1. Deadline Monotonic
    # 2. Earliest Deadline First
    # Each engine produces:
    # - aggregated per-task statistics
    # - a schedule trace used for visualization
    
    header(f"SIMULATION — DM ({mode})")
    engine_dm = SimulationEngine(
        taskset=taskset,
        algorithm="DM",
        seed=args.seed,
        use_wcet=args.use_wcet,
    )

    engine_dm.run(duration=duration)
    dm_sim = engine_dm.get_statistics()


    header(f"SIMULATION — EDF ({mode})")

    engine_edf = SimulationEngine(
        taskset=taskset,
        algorithm="EDF",
        seed=args.seed,
        use_wcet=args.use_wcet,
    )

    engine_edf.run(duration=duration)
    edf_sim = engine_edf.get_statistics()
    
    # ── 4. Quick Comparison ──
    header("COMPARISON — DM vs EDF (max R_i)")

    print(
        f"\n  {BOLD}{WHITE}{'τ_i':<6}  {'DM R_i':<10}  {'EDF R_i':<10}  "
        f"{'D_i':<10}  {'winner':<8}{RESET}"
    )
    print(f"  {DIM}{'─' * 52}{RESET}")

    for tid in sorted(dm_sim):
        t = taskset.get_task(tid)
        dm_r = dm_sim[tid]["R_i"]   # R_i in engine.get_statistics() is already defined as WCRT, before, with run_simulation() we had max_R_i
        edf_r = edf_sim[tid]["R_i"]

        if dm_r < edf_r:
            winner = f"{CYAN}DM{RESET}"
        elif edf_r < dm_r:
            winner = f"{MAGENTA}EDF{RESET}"
        else:
            winner = f"{DIM}tie{RESET}"

        print(
            f"  {YELLOW}τ_{tid:<4}{RESET}  "
            f"{CYAN}{dm_r:<10.1f}{RESET}  "
            f"{MAGENTA}{edf_r:<10.1f}{RESET}  "
            f"{DIM}{t.deadline:<10}{RESET}  "
            f"{winner}"
        )

    # TODO: 4. Full Comparison with analytical
    # run_comparison(taskset, dm_analytical, dm_sim, edf_sim)

    # --- 5. Plots ---
    header("GENERATED PLOTS")
    
    plot_response_times(taskset, dm_sim, edf_sim)
    plot_deadline_misses(dm_sim, edf_sim)
    
    plot_gantt_chart(engine_dm.schedule_trace, "DM Schedule")
    plot_gantt_chart(engine_edf.schedule_trace, "EDF Schedule")
    
    print()


if __name__ == "__main__":
    main()
