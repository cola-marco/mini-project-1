# file to run a batch of task sets
from pathlib import Path
from models.scheduling.taskset import TaskSet
from simulation.engine import SimulationEngine


def run_batch(output_folder: str, use_wcet=False, seed=42):
    results = []

    csv_files = list(Path(output_folder).rglob("*.csv"))[:10] #first 10 .csv files containing tasksets

    print(f"Found {len(csv_files)} tasksets")

    for file in csv_files:
        taskset = TaskSet.from_csv(file)

        duration = 10 * taskset.D_max

        # --- DM ---
        engine_dm = SimulationEngine(
            taskset, algorithm="DM", seed=seed, use_wcet=use_wcet
        )
        engine_dm.run(duration=duration)
        dm_stats = engine_dm.get_statistics()

        # --- EDF ---
        engine_edf = SimulationEngine(
            taskset, algorithm="EDF", seed=seed, use_wcet=use_wcet
        )
        engine_edf.run(duration=duration)
        edf_stats = engine_edf.get_statistics()

        # --- Aggregate per taskset ---
        total_dm_missed = sum(s["missed"] for s in dm_stats.values())
        total_edf_missed = sum(s["missed"] for s in edf_stats.values())

        max_dm_R = max(s["R_i"] for s in dm_stats.values())
        max_edf_R = max(s["R_i"] for s in edf_stats.values())

        results.append({
            "file": file.name,
            "U": taskset.utilization,
            "DM_missed": total_dm_missed,
            "EDF_missed": total_edf_missed,
            "DM_R": max_dm_R,
            "EDF_R": max_edf_R,
        })

    return results