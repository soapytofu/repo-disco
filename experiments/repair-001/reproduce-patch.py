"""Reproduce the recorded patch failure without a model call or Dafny run."""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from patch import apply_text_diff


before = (HERE / "input-program.dfy").read_text()
response = (HERE / "model-response.txt").read_text()
observed = (HERE / "failed-repair.dfy").read_text()
actual = apply_text_diff(before, response)
assert actual.rstrip("\n") == observed.rstrip("\n")

malformed_anchors = [
    line
    for line in response.splitlines()
    if line.startswith("@@") and not line.endswith("@@")
]
assert len(malformed_anchors) == 2

normalized = "\n".join(
    line + " @@" if line in malformed_anchors else line
    for line in response.splitlines()
) + "\n"
candidate = apply_text_diff(before, normalized)
saved_candidate = (HERE / "anchor-normalization-candidate.dfy").read_text()
assert candidate == saved_candidate

print("Reproduced the recorded failed repair.")
print("Adding the two closing anchor delimiters reproduces the saved candidate.")
print("No model request or Dafny verification was performed.")
