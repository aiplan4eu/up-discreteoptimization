import os


os.environ["DO_SKIP_MZN_CHECK"] = "1"
import logging
import unified_planning.engines
from discrete_optimization.generic_tools.ea.ga_tools import ParametersGa
from discrete_optimization.rcpsp.rcpsp_solvers import (
    CP_RCPSP_MZN,
    LP_RCPSP,
    LS_RCPSP_Solver,
    CPSolverName, CPM, LargeNeighborhoodSearchScheduling,
    LargeNeighborhoodSearchRCPSP, LNS_LP_RCPSP_SOLVER, LNS_CP_RCPSP_SOLVER, ParametersCP,
    PileSolverRCPSP, PileSolverRCPSP_Calendar, GA_RCPSP_Solver, CP_MRCPSP_MZN
)
from discrete_optimization.rcpsp.rcpsp_utils import (
    plot_ressource_view,
    plot_task_gantt,
    plt,
)
from discrete_optimization.generic_rcpsp_tools.gphh_solver import GPHH, ParametersGPHH
from example_jobshop import FT06, parse
from up_discreteoptimization.convert_problem import ConvertToDiscreteOptim, RCPSPModel
from up_discreteoptimization.engine_do import EngineDiscreteOptimization

logging.basicConfig(level=logging.INFO)


def run_convert():
    model = parse(FT06, "no_name", add_operators=True)
    vars = model.variables
    effects = model.effects()
    constraints = model.constraints
    convertor = ConvertToDiscreteOptim(model)
    model_do = convertor.build_scheduling_problem_do()
    params_gphh = ParametersGPHH.default()
    params_gphh.pop_size = 20
    params_gphh.n_gen = 1000
    params_ga = ParametersGa.default_rcpsp()
    params_ga.max_evals = 1000000
    params_cp = ParametersCP.default()
    params_cp.free_search = True
    params_cp.time_limit = 3
    with EngineDiscreteOptimization(
            solver_class=LargeNeighborhoodSearchScheduling,
            nb_iteration_lns=200,
            parameters_cp=params_cp,
            cp_solver_name=CPSolverName.ORTOOLS # cp_solver_name=CPSolverName.ORTOOLS, output_type=True
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
