"""
``python -m kinematics.cli`` - the same CLI as the ``kinematics`` console script.

Working/run_all.py launches the CLI this way, with the interpreter it is itself
running on. That skips a ``uv run`` start-up per sweep, and gives worker processes
(GIF frame rendering) an importable ``__main__`` on Windows, which a console-script
launcher does not reliably provide.
"""

from kinematics.cli.bootstrap import main

if __name__ == "__main__":
    main()
