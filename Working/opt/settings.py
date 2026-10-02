"""
Which optimizer script this run is configured by.

Every setting the search reads - the template model, the sweep set, the free
parameters, the objectives - lives in ONE optimizer script (Working/optimizer.py,
Working/underlegoptimizer.py, or any copy you make). Nothing in opt/ names a script:
the script you launch hands itself over, and every module here asks this one for
it.

    # at the bottom of an optimizer script
    if __name__ == "__main__":
        run_optimization(__file__)

Worker processes start from nothing (Windows always spawns), so the script's path
is also put in the environment, which every worker inherits; the first time a
worker asks for its settings, it loads the same file.
"""

import importlib.util
import os
import sys
from pathlib import Path

#: Environment variable carrying the active script's path into worker processes.
ENV_VAR = "BSSR_OPTIMIZER_SCRIPT"

#: Module name the active script is registered under. Deliberately not
#: "optimizer", so `import optimizer` can never quietly pick up the wrong file.
MODULE_NAME = "bssr_active_optimizer"

#: Working/, which relative paths in a script are resolved against.
WORKING = Path(__file__).resolve().parent.parent

#: Settings every optimizer script must define, beyond the search itself.
REQUIRED = ("TEMPLATE", "AXLE", "SWEEP_SET", "CASES",
            "TRACK_WIDTH", "CASTER_DEG", "MIN_ARM_SEPARATION")

_active = None


def activate(script):
    """Load an optimizer script and make it the settings for this process."""
    global _active
    path = Path(script).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"optimizer script not found: {path}")
    if str(WORKING) not in sys.path:
        sys.path.insert(0, str(WORKING))  # so the script can `import opt...`
    spec = importlib.util.spec_from_file_location(MODULE_NAME, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    missing = [name for name in REQUIRED if not hasattr(module, name)]
    if missing:
        raise AttributeError(
            f"{path.name} does not define {', '.join(missing)}. Every optimizer "
            "script states its own references; see Working/optimizer.py."
        )
    os.environ[ENV_VAR] = str(path)
    _active = module
    return module


def current():
    """The active optimizer script, loading it in a worker on first use."""
    if _active is not None:
        return _active
    script = os.environ.get(ENV_VAR)
    if not script:
        raise RuntimeError(
            "no optimizer script is active. Launch one (uv run python "
            "Working/optimizer.py), or call opt.settings.activate(path) first."
        )
    return activate(script)


def script_path():
    """Path of the active optimizer script."""
    return Path(os.environ.get(ENV_VAR) or current().__file__)


def resolve(value):
    """A path setting: absolute, or relative to Working/."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else (WORKING / path).resolve()


def template_dir():
    """The template model folder (TEMPLATE)."""
    folder = resolve(current().TEMPLATE)
    if not folder.is_dir():
        raise FileNotFoundError(f"TEMPLATE model folder not found: {folder}")
    return folder


def relative_to_working(path):
    """`path` relative to Working/ when it is inside it, for CSVs and messages."""
    path = Path(path).resolve()
    try:
        return path.relative_to(WORKING).as_posix()
    except ValueError:
        return path.as_posix()
