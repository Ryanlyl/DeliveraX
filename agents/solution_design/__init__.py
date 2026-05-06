"""SolDesign stage package."""


def run_stage(request):
    from .stage import run_stage as _run_stage

    return _run_stage(request)

