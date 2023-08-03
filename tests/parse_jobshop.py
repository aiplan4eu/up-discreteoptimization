# Basic parser of JSPLib instance, that you can find here.
# https://github.com/tamy0612/JSPLIB. We provide one example file in the repo : ta59

from typing import List, Dict, Optional
import os
from unified_planning.model.scheduling import SchedulingProblem, Activity
from unified_planning.shortcuts import LT
import logging
logger = logging.getLogger(__name__)
this_folder = os.path.dirname(os.path.abspath(__file__))
default_file = os.path.join(this_folder, "ta59")


def parse_jsplib(filename: Optional[str] = None):
    if filename is None:
        filename = default_file
    with open(filename, "r") as file:
        lines = file.readlines()
        processed_line = 0
        job_shop_problem = []
        nb_jobs = None
        n_machines = None
        for line in lines:
            if not (line.startswith("#")):
                split_line = line.split()
                if processed_line == 0:
                    nb_jobs = int(split_line[0])
                    n_machines = int(split_line[1])
                else:
                    job = [{"machine_id": int(split_line[i]),
                            "processing_time": int(split_line[i+1])} for i in range(0, len(split_line), 2)]
                    job_shop_problem.append(job)
                processed_line += 1
    assert len(job_shop_problem) == nb_jobs
    all_machines = set([x["machine_id"] for i in range(nb_jobs) for x in job_shop_problem[i]])
    assert len(all_machines) == n_machines
    problem = SchedulingProblem("Jobshop-example")
    machines_dict = {}
    for machine in all_machines:
        machines_dict[machine] = problem.add_resource(name=f"machine_{machine}",
                                                      capacity=1)
    activities: Dict[int, List[Activity]] = {}
    for index_job in range(nb_jobs):
        activities[index_job] = []
        for index_subjob in range(len(job_shop_problem[index_job])):
            activities[index_job].append(
                problem.add_activity(f"job_{index_job}_sub_{index_subjob}",
                                     duration=job_shop_problem[index_job][index_subjob]["processing_time"])
            )
            activities[index_job][-1].uses(resource=machines_dict[job_shop_problem[index_job]
                                                                  [index_subjob]["machine_id"]],
                                           amount=1)
            if index_subjob >= 1:
                problem.add_constraint(LT(activities[index_job][-2].end,
                                          activities[index_job][-1].start))  # Subjobs have precedence relations.
    logger.info(f"Scheduling problem (job shop) instanciated, {problem}")
    return problem


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parse_jsplib()
