from typing import List, Dict, Optional
from discrete_optimization.rcpsp.rcpsp_parser import parse_file, RCPSPModel
from discrete_optimization.rcpsp.rcpsp_utils import create_fake_tasks
import os

from unified_planning.model.scheduling import SchedulingProblem
from unified_planning.shortcuts import Equals, LE
import logging
logger = logging.getLogger(__name__)
this_folder = os.path.dirname(os.path.abspath(__file__))
default_file = os.path.join(this_folder, "j301_1.sm")


def parse_rcpsp_to_up(filename: Optional[str] = None):
    if filename is None:
        filename = default_file
    rcpsp_problem: RCPSPModel = parse_file(file_path=filename)
    return from_do_to_up(rcpsp_problem)


def from_do_to_up(rcpsp_problem: RCPSPModel) -> SchedulingProblem:
    problem = SchedulingProblem("rcpsp")
    # Initialize resource pools
    resources = {}
    for resource in rcpsp_problem.resources_list:
        resources[resource] = problem.add_resource(resource, rcpsp_problem.get_max_resource_capacity(resource))
    # Initialize tasks and resource consumptions.
    activities = {}
    for activity in rcpsp_problem.tasks_list:
        activities[activity] = problem.add_activity(name=str(activity),
                                                    duration=rcpsp_problem.mode_details[activity][1]["duration"])
        for resource in rcpsp_problem.mode_details[activity][1]:
            if rcpsp_problem.mode_details[activity][1][resource] == 0:
                continue
            if resource in resources:
                activities[activity].uses(resources[resource], rcpsp_problem.mode_details[activity][1][resource])
    # Precedence constraints (classical)
    for activity in rcpsp_problem.successors:
        for next_activity in rcpsp_problem.successors[activity]:
            problem.add_constraint(LE(activities[activity].end, activities[next_activity].start))
    # "Special constraints"
    # - Deadline/Release constraints.
    # - some generalized precedence constraints.
    if rcpsp_problem.do_special_constraints:
        for activity in rcpsp_problem.special_constraints.end_times_window:
            up_value_end = rcpsp_problem.special_constraints.end_times_window[activity][1]
            if up_value_end is not None:
                activities[activity].add_deadline(up_value_end)
        for activity in rcpsp_problem.special_constraints.start_times_window:
            low_value_start = rcpsp_problem.special_constraints.start_times_window[activity][0]
            if low_value_start is not None:
                activities[activity].add_release_date(low_value_start)
        for ac1, ac2 in rcpsp_problem.special_constraints.start_together:
            problem.add_constraint(Equals(activities[ac1].start, activities[ac2].start))
        for ac1, ac2 in rcpsp_problem.special_constraints.start_at_end:
            problem.add_constraint(Equals(activities[ac1].end, activities[ac2].start))
        for ac1, ac2, lag in rcpsp_problem.special_constraints.start_at_end_plus_offset:
            problem.add_constraint(LE(activities[ac1].end+lag, activities[ac2].start))
        for ac1, ac2, lag in rcpsp_problem.special_constraints.start_after_nunit:
            problem.add_constraint(LE(activities[ac1].start+lag, activities[ac2].start))

    # Calendar on resource. We use one function coded in do library that was creating fake "tasks"
    # consuming resource during some time window. It is equivalent to increase/decrease effects
    resource_consumption_data: List[Dict[str, int]] = create_fake_tasks(rcpsp_problem=rcpsp_problem)
    for record in resource_consumption_data:
        resource = next((k for k in record if k in resources), None)
        if resource is not None:
            consumption = record[resource]
            start = record["start"]
            end = record["start"]+record["duration"]
            problem.add_decrease_effect(start, resources[resource], int(consumption))
            problem.add_increase_effect(end, resources[resource], int(consumption))
    logger.info(f"Scheduling problem instanciated, {problem}")
    return problem


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parse_rcpsp_to_up()

