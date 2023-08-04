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
from examples.parse_rcpsp import parse_rcpsp_to_up
from examples.parse_jobshop import parse_jsplib
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def run_convert_ft06():
    model = parse(FT06, "no_name", add_operators=True)
    convertor = ConvertToDiscreteOptim(model)
    model_do = convertor.build_scheduling_problem_do()
    logger.info(f"Model : {model_do}")


def run_convert_jsplib():
    model = parse_jsplib()
    convertor = ConvertToDiscreteOptim(model)
    model_do = convertor.build_scheduling_problem_do()
    logger.info(f"Model Jobshop : {model_do}")


def run_convert_rcpsp():
    model = parse_rcpsp_to_up()
    convertor = ConvertToDiscreteOptim(model)
    model_do = convertor.build_scheduling_problem_do()
    logger.info(f"Model RCPSP: {model_do}")


if __name__ == "__main__":
    run_convert_ft06()
    run_convert_rcpsp()
    run_convert_jsplib()
