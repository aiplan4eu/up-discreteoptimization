import logging
from typing import Dict, List, Tuple

import numpy as np
import unified_planning as up
from discrete_optimization.rcpsp.rcpsp_model import RCPSPModel, RCPSPSolution
from unified_planning.model import Effect, EffectKind, FNode, Timepoint
from unified_planning.model.scheduling.schedule import Schedule
from unified_planning.model.scheduling.scheduling_problem import Activity as upActivity
from unified_planning.model.scheduling.scheduling_problem import SchedulingProblem

logger = logging.getLogger(__name__)


class ConvertToDiscreteOptim:
    def __init__(self, problem: SchedulingProblem):
        self.problem: SchedulingProblem = problem
        self.activity_list: List[upActivity] = problem._activities
        self.activity_map = {a.name: a for a in self.activity_list}
        self.resource_list = problem.fluents
        self.object_list = problem._objects
        self.object_map = {o.name: o for o in self.object_list}
        self.availability_map: Dict[
            "up.model.timing.Timing", List["up.model.effect.Effect"]
        ] = problem._base.effects
        self.metric_list = problem.quality_metrics
        self.constraint_list = problem.constraints
        self.initial_values_map = problem.explicit_initial_values
        self.original_resource_set_of_resource_set = {}

    def build_scheduling_problem_do(self):
        # COMPUTE RESOURCE AND CALENDARS
        fluents = self.problem.fluents
        capacity_resource = {}
        resource_set = set()
        for r in fluents:
            if r.type.is_int_type():
                resource_set.add(r.name)
                capacity_resource[r.name] = r.type.upper_bound
        calendar_resource = {
            r: capacity_resource[r] * np.ones(100000) for r in capacity_resource
        }
        availability_map: Dict[
            "up.model.timing.Timing", List["up.model.effect.Effect"]
        ] = self.problem._base.effects
        for time in availability_map:
            for effect in availability_map[time]:
                str_fluent = str(effect.fluent)
                if str_fluent in calendar_resource:
                    if effect.kind.name == EffectKind.DECREASE:
                        calendar_resource[str_fluent][time.delay :] -= effect.value
                    if effect.kind.name == EffectKind.INCREASE:
                        calendar_resource[str_fluent][time.delay :] += effect.value

        # DEFINE Tasks data
        variables: List[Tuple[Timepoint, upActivity]] = self.problem.variables
        set_name_activities = set()
        activities_without_double: List[upActivity] = []
        start_var_to_activity: Dict[Timepoint, upActivity] = {}
        end_var_to_activity: Dict[Timepoint, upActivity] = {}
        start_var_str_to_activity_name: Dict[str, str] = {}
        end_var_str_to_activity_name: Dict[str, str] = {}
        activity_name_to_act: Dict[str, upActivity] = {}
        mode_details: Dict[str, Dict[int, Dict[str, int]]] = {}
        for x in variables:
            name_activity = x[1].name
            if name_activity not in set_name_activities:
                activities_without_double += [x[1]]
                set_name_activities.add(name_activity)
                start_var_to_activity[x[1].start] = x[1]
                end_var_to_activity[x[1].end] = x[1]
                start_var_str_to_activity_name[str(x[1].start)] = name_activity
                end_var_str_to_activity_name[str(x[1].end)] = name_activity
                activity_name_to_act[name_activity] = x[1]
                mode_details[name_activity] = {1: {}}
                if (
                    x[1].duration.upper.type.is_int_type()
                    and x[1].duration.lower.type.is_int_type()
                ):
                    assert (
                        x[1].duration.upper.type.upper_bound
                        == x[1].duration.upper.type.lower_bound
                        == x[1].duration.lower.type.upper_bound
                        == x[1].duration.lower.type.lower_bound
                    )
                    mode_details[name_activity][1]["duration"] = int(
                        x[1].duration.upper.type.upper_bound
                    )
                for var in x[1].effects.keys():
                    if str(var) == str(x[1].start):  # Consume some things, normally
                        effects_starts: List[Effect] = x[1].effects[var]
                        for eff in effects_starts:
                            resource_consume = str(eff.fluent)
                            if eff.kind == EffectKind.DECREASE:
                                mode_details[name_activity][1][resource_consume] = int(
                                    eff.value.type.upper_bound
                                )
        # Details of the task, as defined in discropt library

        # Defines precedence constraints.
        successors = {task: [] for task in set_name_activities}
        for act in activities_without_double:
            constraints = act.constraints
            for constr in constraints:
                if len(constr.args) == 2:
                    arg_0 = str(constr.args[0])
                    arg_1 = str(constr.args[1])
                    # utilise is_timing_exp() et timing()
                    # Precedence constraint !
                    if (
                        arg_0 in end_var_str_to_activity_name
                        and arg_1 in start_var_str_to_activity_name
                    ):
                        # assert que le delai est à 0
                        assert constr.args[1].timing().delay == 0
                        if constr.is_le():
                            successors[end_var_str_to_activity_name[arg_0]].append(
                                start_var_str_to_activity_name[arg_1]
                            )
        source_task = "source_"
        sink_task = "sink_"
        mode_details[source_task] = {1: {"duration": 0}}
        mode_details[sink_task] = {1: {"duration": 0}}
        successors[source_task] = list(set_name_activities)
        successors[sink_task] = []
        for k in set_name_activities:
            successors[k].append(sink_task)
        tasks_list = [source_task] + list(set_name_activities) + [sink_task]

        # Deadline and release are put in activity.constraints : ((start_0, GlobalTiming(10)), <=) -> TODO
        return RCPSPModel(
            resources=calendar_resource,
            non_renewable_resources=[],
            mode_details=mode_details,
            successors=successors,
            horizon=100000,
            tasks_list=tasks_list,
            source_task=source_task,
            sink_task=sink_task,
        )

    def build_up_plan(self, solution: RCPSPSolution) -> "up.model.scheduling.schedule":
        assignment_dict = {}
        activities_list = []
        for activity_name in solution.rcpsp_schedule:
            if activity_name in self.activity_map:
                act = self.activity_map[activity_name]
                assignment_dict[act.start] = solution.get_start_time(activity_name)
                assignment_dict[act.end] = solution.get_end_time(activity_name)
                activities_list.append(act)
        up_plan = Schedule(assignment=assignment_dict, activities=activities_list)
        return up_plan
