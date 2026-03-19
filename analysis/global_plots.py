# plots for the full output/tasks
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict
from pathlib import Path


def plot_global_response_times(results):
    dm = [r["DM_R"] for r in results]
    edf = [r["EDF_R"] for r in results]

    x = range(len(results))

    plt.figure()

    plt.plot(x, dm, marker="o", label="DM")
    plt.plot(x, edf, marker="o", label="EDF")

    plt.xlabel("Taskset index")
    plt.ylabel("Worst-Case Response Time")
    plt.title("Global WCRT Comparison (DM vs EDF)")
    plt.legend()

    plt.savefig("figures/global_response_times.png")
    plt.show()


def plot_miss_distribution(results):
    dm = [r["DM_missed"] for r in results]
    edf = [r["EDF_missed"] for r in results]

    plt.figure()

    plt.boxplot([dm, edf], labels=["DM", "EDF"])

    plt.ylabel("Missed Deadlines")
    plt.title("Deadline Miss Distribution")

    plt.savefig("figures/miss_distribution.png")
    plt.show()


def plot_wcrt_distribution(results):
    dm = [r["DM_R"] for r in results]
    edf = [r["EDF_R"] for r in results]

    plt.figure()

    plt.hist(dm, bins=10, alpha=0.5, label="DM")
    plt.hist(edf, bins=10, alpha=0.5, label="EDF")

    plt.xlabel("Worst-Case Response Time")
    plt.ylabel("Frequency")
    plt.title("WCRT Distribution")
    plt.legend()

    plt.savefig("figures/wcrt_distribution.png")
    plt.show()
    
    
def plot_response_vs_deadline(results):
    dm = [r["DM_R"] for r in results]
    edf = [r["EDF_R"] for r in results]

    plt.figure()

    plt.scatter(dm, edf)

    plt.xlabel("DM WCRT")
    plt.ylabel("EDF WCRT")
    plt.title("DM vs EDF Response Times")

    plt.savefig("figures/response_scatter.png")
    plt.show()