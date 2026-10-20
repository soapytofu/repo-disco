"""One full-program repair request, followed by Dafny verification.

Run from the research repository root. The key handoff is consumed once.
"""

from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from botocore.config import Config
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, SystemMessage
from code_output_parser import CodeOutputParser
from language import Language, Program


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def consume_key(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise RuntimeError("Key handoff must be a regular file owned by this account")
        if info.st_mode & 0o077 or info.st_size > 65536:
            raise RuntimeError("Key handoff has unsafe permissions or unexpected size")
        token = handle.read().strip()
    if not token:
        raise RuntimeError("Empty key handoff")
    path.unlink()
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = token


def main():
    before = (ROOT / "experiments/extension-001/extended-program.dfy").read_text()
    feedback = (ROOT / "experiments/extension-001/verifier-output.txt").read_text()
    system = (
        "You are an expert Dafny developer. Repair the supplied program using the verifier "
        "feedback. Return the COMPLETE corrected Dafny source, not a diff. "
        "Preserve Max and its existing ensures clauses, TestMax and its assertions, "
        "MaxCommutative and its contract, and TestMaxAlgebra with all its algebraic checks. "
        "Do not weaken specifications, remove checks, introduce assumptions, or disable "
        "verification. Make only the changes needed to repair the program. "
        "Output only Dafny source, optionally inside one dafny code fence."
    )
    user = f"Program:\n{before}\n\nVerifier feedback:\n{feedback}"
    prompt = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    run = ROOT / "outputs" / datetime.now(timezone.utc).strftime(
        "full-program-repair-%Y%m%dT%H%M%S-%fZ")
    run.mkdir(parents=True, exist_ok=False)
    (run / "input-program.dfy").write_text(before)
    (run / "input-verifier-output.txt").write_text(feedback)
    shutil.copy2(__file__, run / "runner.py")
    write_json(run / "prompt.json", prompt)
    write_json(run / "run-config.json", {
        "model": "us.anthropic.claude-sonnet-4-6", "region_name": "us-east-1",
        "max_tokens": 4096, "model_calls_limit": 1,
        "connect_timeout_seconds": 15, "read_timeout_seconds": 90,
        "sdk_total_max_attempts": 1, "verifier_timeout_seconds": 10,
        "output_format": "complete_program", "temperature": "provider_default",
        "parser": "CodeOutputParser", "checkpoint_modified": False,
    })
    write_json(run / "environment.json", {
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "python": sys.version,
        "packages": {p: version(p) for p in ["boto3", "botocore", "langchain-aws", "langchain-core", "z3-solver"]},
        "input_sha256": hashlib.sha256(before.encode()).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    print(f"RUN_DIRECTORY={run}", flush=True)
    consume_key(Path.home() / ".repodisco-bedrock-handoff")
    try:
        model = ChatBedrockConverse(
            model="us.anthropic.claude-sonnet-4-6", region_name="us-east-1",
            max_tokens=4096,
            config=Config(connect_timeout=15, read_timeout=90,
                          retries={"total_max_attempts": 1}),
        )
        response = model.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        write_json(run / "response.json", {
            "content": response.content, "usage_metadata": response.usage_metadata,
            "stop_reason": response.response_metadata.get("stopReason"),
        })
        write_json(run / "token-usage.json", {
            "model_invocations": 1, "model_completions": 1,
            "usage": response.usage_metadata, "measured_cost": None,
        })
    finally:
        os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)
    candidate = CodeOutputParser().invoke(response)
    if not candidate.strip():
        raise RuntimeError("Empty model output; no candidate to verify")
    (run / "output-program.dfy").write_text(candidate)
    ver = Language.DAFNY.get_backend().verify(
        Program(candidate, Language.DAFNY, name="full-program-repair.dfy"), timeout=10)
    (run / "verifier-stdout.txt").write_text(ver.stdout)
    (run / "verifier-stderr.txt").write_text(ver.stderr)
    result = {
        "model_invocations": 1, "token_usage": response.usage_metadata,
        "verification_outcome": ver.outcome.name, "verifier_exit_status": ver.status,
        "program_changed": before != candidate,
        "preservation_review": "pending manual inspection",
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(run / "result.json", result)
    print(json.dumps(result, indent=2), flush=True)
    print(ver.stdout, flush=True)


if __name__ == "__main__":
    main()
