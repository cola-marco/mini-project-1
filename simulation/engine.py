import heapq
import math
from pathlib import Path
import random
import sys
from dataclasses import dataclass
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.scheduling.job import Job
from models.scheduling.task import Task
from models.scheduling.taskset import TaskSet
from models.simulation.event import Event, EventType


@dataclass
class ProcessorState:
    """
    @Author: Alejandro Garcia Bejarano
    """

    clock: float = 0  # simulation time
    running_job: Optional[Job] = None
    running_since: float = 0  # accumulated busy time


class SimulationEngine:
    """
    @Author: Alejandro Garcia Bejarano
    """

    def __init__(
        self,
        taskset: TaskSet,
        algorithm: str = "DM",
        seed: Optional[int] = None,
        use_wcet: bool = False,
    ):
        self.taskset = taskset
        self.algorithm = algorithm.upper()
        self.use_wcet = use_wcet

        # == Run Reproducibility ==
        # TODO: make seeds for reproductible tests
        self.rng = random.Random(seed)

        # == Min-heap ordered (time, event_type, task_id) ==
        # On conflict priority: COMPLETION -> ARRIVAL -> DEADLINE
        self.state = ProcessorState()
        self.event_queue: list[Event] = []

        # == Job Tracking ==
        self.ready_queue: list[Job] = []
        self.completed_jobs: list[Job] = []
        self.all_jobs: list[Job] = []

        # == Ouput data ==
        # (start_processing, end_processing, task_id)
        # Note: the endprocessing could be task finished/ task preempted
        self.schedule_trace: list[tuple[float, float, int]] = []
        # (time, preempted_job, by_job)
        self.preemption_log: list[tuple[float, Job, Job]] = []

        # == Instence Counters Hashmap ==
        # task_i : has run 1 run
        # task_i+1 : has run 2 runs
        self._next_j: dict[int, int] = {t.id: 1 for t in taskset}

    def run(self, duration: Optional[float] = None) -> list[Job]:
        """
        @Details: Run simulation for duration
        @Returns: The list of the completed runs
        @Note: Because jobs are repeated without jitter then is one Hyperperiod
        """

        # TODO: Refactor this logic, if we were to use jitter analysis
        H = self.taskset.hyperperiod
        if duration is None:
            duration = H

        print(
            f"== Start of Simulation ==\n"
            f"Algorithm {self.algorithm} | Hyperperiod={H}"
            f"| duration={duration} | U={self.taskset.utilization:.4f}"
        )

        # Step 1: Schedule ARRIVAL for tasks
        for task in self.taskset:
            heapq.heappush(
                self.event_queue,
                Event(
                    time=float(task.phase),
                    event_type=EventType.ARRIVAL,
                    task_id=task.id,
                ),
            )

        # Step 2: Main event loop
        while self.event_queue:
            event = heapq.heappop(self.event_queue)

            if event.time > duration:
                break

            self.state.clock = event.time

            # In-order processing of critial sections
            if event.event_type == EventType.ARRIVAL:
                self._handle_arrival(event, duration)
            if event.event_type == EventType.COMPLETION:
                self._handle_completion(event)
            # TODO: Event.DEADLINE can be extended to mark misses in graph
            # We can add it to the job_trace, but is not necessary
            # if event.event_type == EventType.DEADLINE:
            #     pass

        # Flush the last running segment
        self._pause_running_job()
        n_done = len(self.completed_jobs)
        n_total = len(self.all_jobs)
        n_missed = sum(1 for j in self.all_jobs if j.missed_deadline)

        print(
            "== End of Simulation ==\n",
            f"{n_done} out of {n_total} completed\n",
            f"{n_missed} jobs where missed",
        )

        return self.completed_jobs

    # TODO: Add visual representations (e.g matplotlib)
    def get_statistics(self) -> dict:
        """
        @Details: Per-task breakdown of the statistics of each simulation
        @Returns dict[task_id]:
            R_i : Worst Case response time (max R_{i,j})
            avg_R_i : Average Reponse Time
            missed : Number of deadline misses (f_{i,j} > d_{i,j}
        """
        stats = {}

        for task in self.taskset:
            task_jobs = [j for j in self.all_jobs if j.task_id == task.id]

            completed_jobs = [j for j in self.completed_jobs if j.task_id == task.id]
            missed_jobs = [j for j in task_jobs if j.missed_deadline]

            response_times = [
                j.response_time for j in completed_jobs if j.response_time is not None
            ]

            stats[task.id] = {
                "R_i": max(response_times) if response_times else 0.0,
                "avg_R_i": (
                    sum(response_times) / len(response_times) if response_times else 0.0
                ),
                "min_R_i": min(response_times) if response_times else 0.0,
                "missed": len(missed_jobs),
                "total_jobs": len(task_jobs),
                "completed": len(completed_jobs),
                "preemptions": sum(j.preemtion_count for j in task_jobs)
            }

        return stats

    # =========================================================================
    #  EVENT HANDLERS
    # =========================================================================

    def _handle_arrival(self, event: Event, duration: float):
        """
        Process τ_{i,j} and schedule next τ_{i,j+1}

        1. Calculate U(BCET,WCET)
        2. Apply jitter on release time
        3. Create job, add to ready queue
        4. Schedule DEADLINE event at d_{i,j}
        5. Schedule next ARRIVAL at r_{i,j+1}
        6. Make scheduling dicision (preemption?)
        """

        task = self.taskset.get_task(event.task_id)

        # Update instance counter
        j = self._next_j[task.id]
        self._next_j[task.id] = j + 1

        # Note: this project just requires the WCET
        exec_time = (
            task.wcet if self.use_wcet else self.rng.randint(task.bcet, task.wcet)
        )

        # TODO: Double check with the TA if this step is necessary
        # Note: this step is no necessary for the mini-project-01
        jitter_offset = 0.0
        if task.jitter > 0:
            jitter_offset = self.rng.uniform(0, task.jitter)
        # actual_release = event.time + jitter_offset => disabled jitter because the scheduler started the job before its actual release, causing finish_time <= release_time error.
        actual_release = event.time

        # Create τ_{i,j}
        job = Job(
            task_id=task.id,
            job_id=j,
            release_time=actual_release,
            absolute_deadline=actual_release + task.deadline,
            execution_time=exec_time,
            remaining_time=exec_time,
        )
        self.all_jobs.append(job)  # logs
        self.ready_queue.append(job)

        # Schedule new DEADLINE event for τ_{i,j}
        heapq.heappush(
            self.event_queue,
            Event(
                time=float(job.absolute_deadline),
                event_type=EventType.DEADLINE,
                task_id=task.id,
                job_id=job.job_id,
            ),
        )

        # Schedule next ARRIVAL: r_{i,j+1} -> event.time + T_i
        # Note: ARRIVAL events does not have Job_ID yet
        next_nominal_release = event.time + task.period
        if next_nominal_release < duration:
            heapq.heappush(
                self.event_queue,
                Event(
                    time=next_nominal_release,
                    event_type=EventType.ARRIVAL,
                    task_id=task.id,
                ),
            )

        self._schedule(actual_release)

    def _handle_completion(self, event: Event):
        """
        Process: τ_{i,j} finishes at time f_{i,j}.
        Clean up the completion deadlines of job_id which was preempted.
        """
        job = self.state.running_job

        # Stale event check
        if (
            job is None
            or job.task_id != event.task_id
            or job.job_id != event.job_id  # τ_{i,j} is the same completion jth event
        ):
            return

        expected_completion = self.state.running_since + job.remaining_time
        if abs(expected_completion - event.time) > 1e-9:
            return  # stale completion, not the new one

        # Record f_{i,j}
        job.finish_time = event.time
        job.remaining_time = 0.0
        self.completed_jobs.append(job)

        # Log scehdule segment
        self.schedule_trace.append((self.state.running_since, event.time, job.task_id))

        if job in self.ready_queue:
            self.ready_queue.remove(job)

        # Liberate the Processor Resource
        self.state.running_job = None
        self._schedule(event.time)

    def _handle_deadline(self, event: Event):
        """
        Check feasibility of τ_{i,j} at its absolute deadline d_{i,j}
        """
        job = self._find_job(event.task_id, event.job_id)
        if job is not None and not job.is_completed:
            pass  # Deadline missed, detected on job.py ~line 63

    # =========================================================================
    # SCHEDULING DESICIONS
    # =========================================================================

    def _schedule(self, current_time: float):
        """
        Core scheduling decision - select highest-priority ready job.

        For DM/RM: fixed priority (compare task parameters)
        For EDF: dynamic priority (compare absolute deadline d_{i,j})
        """

        # empty queue?
        if not self.ready_queue:
            return

        best_job = self._pick_highest_priority()
        if best_job is None:
            return

        current_job = self.state.running_job

        if current_job is best_job:
            return

        # Preemption handling
        if current_job is not None:
            elapsed = current_time - self.state.running_since
            current_job.remaining_time -= elapsed
            current_job.preemtion_count += 1

            self.schedule_trace.append(
                (self.state.running_since, current_time, current_job.task_id)
            )
            self.preemption_log.append((current_time, current_job, best_job))

        # Start/resume the new best job
        if best_job.start_time is None:
            best_job.start_time = current_time  # s_{i,j}

        self.state.running_job = best_job
        self.state.running_since = current_time

        # Schedule COMPLETION event
        # This will queue compleetion times with old for the old jobs
        # Note: look at handle_completion on how the queue of old
        # completion events is handle
        completion_time = current_time + best_job.remaining_time
        heapq.heappush(
            self.event_queue,
            Event(
                time=completion_time,
                event_type=EventType.COMPLETION,
                task_id=best_job.task_id,
                job_id=best_job.job_id,
            ),
        )

    # TODO: Discuss with the TA if you gotta do RM if DM is an enhanced version of RM
    def _pick_highest_priority(self) -> Optional[Job]:
        """
        Select the highest priority job based on the algorihtm

        DM: 1/D_i - shorter relative deadline [Section 4.5]
        EDF: 1/d_{i,j} - Earlier Absolute Deadline [Section 4.4]
        RM: 1/T_i - Shorter Period [Section 4.3]
        """

        # No events yet?
        if not self.ready_queue:
            return None

        if self.algorithm == "DM":
            return min(
                self.ready_queue,
                key=lambda j: (self.taskset.get_task(j.task_id).deadline, j.task_id),
            )

        if self.algorithm == "EDF":
            return min(self.ready_queue, key=lambda j: (j.absolute_deadline, j.task_id))

        if self.algorithm == "RM":
            return min(
                self.ready_queue,
                key=lambda j: (self.taskset.get_task(j.task_id).period, j.task_id),
            )

        raise ValueError(f"Unknown algorithm: {self.algorithm}")

    # =========================================================================
    #  HELPERS
    # =========================================================================

    def _pause_running_job(self):
        if self.state.running_job is not None:
            elapsed = self.state.clock - self.state.running_since
            self.state.running_job.remaining_time -= elapsed
            self.schedule_trace.append(
                (
                    self.state.running_since,
                    self.state.clock,
                    self.state.running_job.task_id,
                )
            )

    def _find_job(self, task_id: int, job_id: Optional[int]) -> Optional[Job]:
        if job_id is None:
            return None
        for job in self.all_jobs:
            if task_id == job.task_id and job_id == job_id:
                return job
        return None
