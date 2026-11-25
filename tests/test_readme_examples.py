"""Re-runs every `$ python -m src.main ...` example in README.md and compares the output."""

import contextlib
import io
import re
import shlex

from src.main import main

BLOCK = re.compile(r"```text\n\$ python -m src\.main(.*?)\n(.*?)```", re.S)


def test_readme_sample_runs_match_real_output():
    with open("README.md", encoding="utf-8") as f:
        blocks = BLOCK.findall(f.read())
    assert len(blocks) >= 3, "README should contain at least three sample runs"
    for args, expected in blocks:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            main(shlex.split(args))
        assert buffer.getvalue().rstrip() == expected.rstrip(), f"README example out of date: {args}"
