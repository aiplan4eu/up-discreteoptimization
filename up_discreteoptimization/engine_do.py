import logging
from typing import IO, Callable, Optional, Type

import unified_planning as up
import unified_planning.engines
import unified_planning.engines.mixins
from discrete_optimization.generic_tools.do_solver import SolverDO
from discrete_optimization.rcpsp.rcpsp_model import RCPSPModel, RCPSPSolution
from discrete_optimization.rcpsp.rcpsp_solvers import (
    look_for_solver_class,
    solve,
    solvers_map,
)
from unified_planning.engines import PlanGenerationResultStatus
from unified_planning.model import ProblemKind

from up_discreteoptimization.convert_problem import ConvertToDiscreteOptim

logger = logging.getLogger(__name__)


class EngineDiscreteOptimization(
    up.engines.Engine, up.engines.mixins.OneshotPlannerMixin
):
    def __init__(self, solver_class: Optional[Type[SolverDO]] = None, **kwargs):
        up.engines.Engine.__init__(self)
        up.engines.mixins.OneshotPlannerMixin.__init__(self)
        self.converter: Optional[ConvertToDiscreteOptim] = None
        self.solver_class = solver_class
        self.params_solver = kwargs
        self.do_problem: Optional[RCPSPModel] = None
        self.do_solution: Optional[RCPSPSolution] = None

    @property
    def name(self) -> str:
        return "Discrete-optimization"

    @staticmethod
    def supported_kind() -> ProblemKind:
        supported_kind = ProblemKind()
        supported_kind.set_problem_class("SCHEDULING")  # type: ignore
        return supported_kind

    @staticmethod
    def supports(problem_kind: "up.model.ProblemKind") -> bool:
        return problem_kind <= EngineDiscreteOptimization.supported_kind()

    def _solve(
        self,
        problem: "up.model.AbstractProblem",
        heuristic: Optional[
            Callable[["up.model.state.ROState"], Optional[float]]
        ] = None,
        timeout: Optional[float] = None,
        output_stream: Optional[IO[str]] = None,
    ) -> "up.engines.results.PlanGenerationResult":
        assert isinstance(problem, up.model.scheduling.SchedulingProblem)
        problem: RCPSPModel = self._convert_input_problem(problem)
        self.do_problem = problem
        if self.solver_class is None:
            solution: RCPSPSolution = problem.get_dummy_solution()
        else:
            results = solve(
                method=self.solver_class, rcpsp_model=problem, **self.params_solver
            )
            solution = results.get_best_solution()
        self.do_solution = solution
        up_plan = self._convert_output_problem(solution)
        return up.engines.PlanGenerationResult(
            PlanGenerationResultStatus.UNSOLVABLE_PROVEN
            if up_plan is None
            else PlanGenerationResultStatus.SOLVED_SATISFICING,
            up_plan,
            self.name,
        )

    def _convert_input_problem(self, problem: "up.model.Problem") -> RCPSPModel:
        self.converter = ConvertToDiscreteOptim(problem)
        scheduling_problem = self.converter.build_scheduling_problem_do()
        return scheduling_problem

    def _convert_output_problem(self, solution: RCPSPSolution):
        return self.converter.build_up_plan(solution)
