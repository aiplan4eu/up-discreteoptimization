import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import unified_planning as up
from discrete_optimization.rcpsp.rcpsp_model import RCPSPModel, RCPSPSolution
from unified_planning.model import (
    Effect,
    EffectKind,
    Fluent,
    FNode,
    OperatorKind,
    Timepoint,
    Timing,
)
from unified_planning.model.scheduling.scheduling_problem import (
    Activity,
    SchedulingProblem,
)

logger = logging.getLogger(__name__)


class ConvertToDiscreteOptim:
    def __init__(self, problem: SchedulingProblem):
        self.problem: SchedulingProblem = problem
        self.activity_list: List[Activity] = problem.activities
        self.activity_map = {a.name: a for a in self.activity_list}
        self.resource_list = problem.fluents
        self.metric_list = problem.quality_metrics
        self.constraint_list = problem.all_constraints()
        self.initial_values_map = problem.explicit_initial_values
        self.original_resource_set_of_resource_set = {}

    def build_scheduling_problem_do(self):
        # COMPUTE RESOURCE AND CALENDARS
        fluents: List["up.model.fluent.Fluent"] = self.problem.fluents

        capacity_resource = {}
        resource_set = set()
        for r in fluents:
            if r.type.is_int_type():
                resource_set.add(r.name)
                capacity_resource[r.name] = r.type.upper_bound
        calendar_resource = {
            r: capacity_resource[r] * np.ones(100000) for r in capacity_resource
        }
        base_effects: List[Tuple[Timing, Effect]] = self.problem.base_effects
        for time, effect in base_effects:
            fnode: FNode = effect.fluent
            actual_fluent: Fluent = fnode.fluent()
            name_fluent = actual_fluent.name
            if name_fluent in calendar_resource:
                if effect.kind == EffectKind.DECREASE:
                    # assert effect.value.is_constant()
                    # assert effect.value.constant_value()
                    calendar_resource[name_fluent][
                        time.delay :
                    ] -= effect.value.constant_value()
                if effect.kind == EffectKind.INCREASE:
                    calendar_resource[name_fluent][
                        time.delay :
                    ] += effect.value.constant_value()

        # DEFINE Tasks data
        from unified_planning.model import Parameter

        set_name_activities = set()
        activities: List[Activity] = self.problem.activities
        start_var_to_activity: Dict[Timepoint, Activity] = {}
        end_var_to_activity: Dict[Timepoint, Activity] = {}
        mode_details: Dict[
            str, Dict[int, Dict[str, int]]
        ] = {}  # {Task name: {mode: {"duration": , "resource"...}}
        for activity in activities:
            name_activity = activity.name
            mode_details[name_activity] = {1: {}}
            duration_upper = activity.duration.upper.constant_value()
            duration_lower = activity.duration.lower.constant_value()
            assert duration_lower == duration_upper
            mode_details[name_activity][1]["duration"] = int(duration_lower)
            effects_var: Dict[
                "up.model.timing.Timing", List["up.model.effect.Effect"]
            ] = activity.effects
            for timing in effects_var:
                if timing.timepoint == activity.start and timing.delay == 0:
                    # Starting effect
                    effects_starts: List[Effect] = effects_var[timing]
                    for eff in effects_starts:
                        resource_consume = eff.fluent.fluent().name
                        if eff.kind == EffectKind.DECREASE:
                            mode_details[name_activity][1][resource_consume] = int(
                                eff.value.type.upper_bound
                            )
            set_name_activities.add(name_activity)
            start_var_to_activity[activity.start] = activity
            end_var_to_activity[activity.end] = activity

        all_constraints: List[
            Tuple[FNode, Optional[Activity]]
        ] = self.problem.all_constraints()
        # Defines precedence constraints.
        successors = {task: [] for task in set_name_activities}
        for constraint in all_constraints:
            fnode = constraint[0]
            if len(fnode.args) == 2 and fnode.node_type == OperatorKind.LE:
                # Is probably a classical precedence constraint.
                if (
                    fnode.args[1].timing().delay == 0
                    and fnode.args[0].timing().delay == 0
                ):
                    arg0 = fnode.args[0].timing().timepoint
                    arg1 = fnode.args[1].timing().timepoint
                    if arg0 in end_var_to_activity and arg1 in start_var_to_activity:
                        act0_name = end_var_to_activity[arg0].name
                        act1_name = start_var_to_activity[arg1].name
                        successors[act0_name].append(act1_name)
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

    def build_up_plan(self, solution: RCPSPSolution) -> Dict[Any, int]:
        # TODO : recode this.
        assignment_dict = {}
        activities_list = []
        for activity_name in solution.rcpsp_schedule:
            if activity_name in self.activity_map:
                act = self.activity_map[activity_name]
                assignment_dict[act.start] = solution.get_start_time(activity_name)
                assignment_dict[act.end] = solution.get_end_time(activity_name)
                activities_list.append(act)
        # up_plan = Schedule(assignment=assignment_dict, activities=activities_list)
        return assignment_dict
