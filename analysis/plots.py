import matplotlib.pyplot as plt
from pathlib import Path

# NOTE:
# The plotting functions expect statistics returned by
# SimulationEngine.get_statistics(), not by the older run_simulation() aggregation helper.
#
# Expected keys per task:
#   R_i        -> worst-case response time
#   avg_R_i    -> average response time
#   min_R_i    -> minimum response time
#   missed     -> number of missed deadlines
#   total_jobs -> number of released jobs
#   completed  -> number of completed jobs
#   preemptions-> number of preemptions

def plot_response_times(taskset, dm_stats, edf_stats):
    # Plot WCRT for DM and EDF:

    tasks = sorted(dm_stats.keys())

    dm = [dm_stats[t]["R_i"] for t in tasks]
    edf = [edf_stats[t]["R_i"] for t in tasks]
    deadlines = [taskset.get_task(t).deadline for t in tasks]

    x = range(len(tasks))

    plt.figure()

    plt.bar(x, dm, width=0.4, label="DM")
    plt.bar([i + 0.4 for i in x], edf, width=0.4, label="EDF")

    plt.plot(x, deadlines, linestyle="--", label="Deadline")

    plt.xticks([i + 0.2 for i in x], [f"T{t}" for t in tasks])
    plt.ylabel("Response Time")
    plt.title("Worst-Case Response Time Comparison")
    plt.legend()

    Path("figures").mkdir(exist_ok=True)
    plt.savefig("figures/response_times.png")

    plt.show()


def plot_deadline_misses(dm_stats, edf_stats):
    # Plot number of missed deadlines per task

    tasks = sorted(dm_stats.keys())

    dm = [dm_stats[t]["missed"] for t in tasks]
    edf = [edf_stats[t]["missed"] for t in tasks]

    x = range(len(tasks))

    plt.figure()

    plt.bar(x, dm, width=0.4, label="DM")
    plt.bar([i + 0.4 for i in x], edf, width=0.4, label="EDF")

    plt.xticks([i + 0.2 for i in x], [f"T{t}" for t in tasks])
    plt.ylabel("Missed Deadlines")
    plt.title("Deadline Misses per Task")
    plt.legend()

    Path("figures").mkdir(exist_ok=True)
    plt.savefig("figures/deadline_misses.png")

    plt.show()


def plot_gantt_chart(schedule_trace, title):
    """
    Plot schedule timeline (Gantt chart)

    schedule_trace format from schedule_trace:
        [(start, end, task_id)]
    """

    plt.figure()

    for start, end, task_id in schedule_trace:
        plt.barh(
            y=task_id,
            width=end - start,
            left=start,
        )

    plt.xlabel("Time")
    plt.ylabel("Task")
    plt.title(title)

    Path("figures").mkdir(exist_ok=True)
    filename = title.lower().replace(" ", "_") + ".png"
    plt.savefig(f"figures/{filename}")

    plt.show()