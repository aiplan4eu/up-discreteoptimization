import os

os.environ["DO_SKIP_MZN_CHECK"] = "1"
import logging

import unified_planning.engines
from discrete_optimization.rcpsp.rcpsp_solvers import (
    CP_RCPSP_MZN,
    LP_RCPSP,
    LS_RCPSP_Solver,
)
from discrete_optimization.rcpsp.rcpsp_utils import (
    plot_ressource_view,
    plot_task_gantt,
    plt,
)
from discrete_optimization.rcpsp.solver.gphh_solver import GPHH
from example_jobshop import FT06, parse

from up_discreteoptimization.convert_problem import ConvertToDiscreteOptim, RCPSPModel
from up_discreteoptimization.engine_do import EngineDiscreteOptimization

logging.basicConfig(level=logging.DEBUG)


def run_convert():
    model = parse(FT06, "no_name")
    vars = model.variables
    effects = model.effects()
    constraints = model.constraints
    convertor = ConvertToDiscreteOptim(model)
    model_do = convertor.build_scheduling_problem_do()
    with EngineDiscreteOptimization(
        solver_class=CP_RCPSP_MZN, output_type=True
    ) as planner:
        result = planner.solve(model)
        if (
            result.status
            == unified_planning.engines.PlanGenerationResultStatus.SOLVED_SATISFICING
        ):
            print("DO returned: %s" % result.plan)
        else:
            print("No plan found.")
        sol = planner.do_solution
        print(planner.do_problem.evaluate(sol))
        plot_task_gantt(rcpsp_model=planner.do_problem, rcpsp_sol=sol)
        plot_ressource_view(rcpsp_model=planner.do_problem, rcpsp_sol=sol)
    plt.show()


if __name__ == "__main__":
    run_convert()
