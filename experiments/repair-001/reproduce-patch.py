"""Check recorded patch handling without a model call or Dafny run."""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from patch import apply_text_diff


before = (HERE / "input-program.dfy").read_text()
response = (HERE / "model-response.txt").read_text()
try:
    actual = apply_text_diff(before, response)
except ValueError as error:
    assert "Malformed anchor" in str(error)
    print("The patch reader now rejects the recorded malformed response.")
else:
    observed = (HERE / "failed-repair.dfy").read_text()
    assert actual.rstrip("\n") == observed.rstrip("\n")
    print("Reproduced the historical failure with the older patch reader.")

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
assert candidate.rstrip("\n") == saved_candidate.rstrip("\n")

print("Adding the two closing anchor delimiters reproduces the saved candidate.")
print("No model request or Dafny verification was performed.")

