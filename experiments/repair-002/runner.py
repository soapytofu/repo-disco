"""Run one research repair attempt; never serialize credentials.

Run from the repository root with a trusted local agenda checkpoint.
"""

import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import logging
import os
from pathlib import Path
import pickle
import shutil
import stat
import subprocess
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from hydra.utils import instantiate
from langchain_core.callbacks import BaseCallbackHandler
from omegaconf import OmegaConf


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


class EvidenceCallback(BaseCallbackHandler):
    raise_error = True

    def __init__(self, run):
        self.run = run
        self.calls = 0
        self.completions = 0
        self.usage = None

    def on_chat_model_start(self, serialized, messages, **kwargs):
        self.calls += 1
        if self.calls > 1:
            raise RuntimeError("This pilot permits only one model invocation")
        write_json(self.run / "prompt.json", [
            [{"role": msg.type, "content": msg.content} for msg in batch]
            for batch in messages
        ])

    def on_llm_end(self, response, **kwargs):
        self.completions += 1
        message = response.generations[0][0].message
        self.usage = getattr(message, "usage_metadata", None)
        write_json(self.run / "response.json", {
            "content": message.content,
            "usage_metadata": self.usage,
            "stop_reason": message.response_metadata.get("stopReason"),
            "model_id": message.response_metadata.get("model_id"),
        })
        write_json(self.run / "token-usage.json", {
            "model_invocations": self.calls,
            "model_completions": self.completions,
            "usage": self.usage,
            "measured_cost": None,
        })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--key-file", type=Path,
                        default=Path.home() / ".repodisco-bedrock-handoff")
    args = parser.parse_args()

    with args.checkpoint.open("rb") as handle:
        data = pickle.load(handle)
    pending = [
        task_id for task_id, task in data["tasks"].items()
        if task.type == "repair"
        and str(data["status"][task_id].work_status) in {"NEW", "ATTEMPTED"}
    ]
    if len(pending) != 1:
        raise RuntimeError("Expected exactly one pending repair task")
    program_path = data["tasks"][pending[0]].properties["program"]
    before = data["objects"][program_path].content.decode("utf-8")
    original = (ROOT / "experiments/extension-001/extended-program.dfy").read_text()
    if before.rstrip() != original.rstrip():
        raise RuntimeError("Checkpoint is not the original failed extension")

    run = ROOT / "outputs" / datetime.now(timezone.utc).strftime(
        "bedrock-repair-%Y%m%dT%H%M%S-%fZ")
    run.mkdir(parents=True, exist_ok=False)
    shutil.copy2(args.checkpoint, run / "agenda.pkl")
    (run / "input-program.dfy").write_text(before)
    shutil.copy2(__file__, run / "runner.py")
    cfg = OmegaConf.create({
        "agenda": {
            "_target_": "agenda.LocalAgenda", "language": "dafny",
            "max_attempts": int(data["total_attempts"]) + 1,
            "checkpoint_path": str(run / "agenda.pkl"),
            "checkpoint_interval": 1, "benchmark_codebase_time": None,
            "sort_every": 100,
            "logger": {"_target_": "logger.noop.NoOpLogger"},
        },
        "scheduler": {
            "_target_": "scheduler.RoundRobinScheduler",
            "language": "dafny", "turn_fuel": 1,
            "workers": [{
                "_target_": "worker.llm_fixer.LLMFixer",
                "language": "dafny", "distill": "all",
                "llm": {
                    "_target_": "langchain_aws.ChatBedrockConverse",
                    "_convert_": "all",
                    "model": "us.anthropic.claude-sonnet-4-6",
                    "region_name": "us-east-1", "max_tokens": 4096,
                    "config": {
                        "_target_": "botocore.config.Config",
                        "connect_timeout": 15, "read_timeout": 90,
                        "retries": {"total_max_attempts": 1},
                    },
                },
            }],
        },
    })
    OmegaConf.save(cfg, run / "run-config.yaml")
    write_json(run / "environment.json", {
        "source_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True).strip(),
        "python": sys.version,
        "packages": {p: version(p) for p in [
            "boto3", "botocore", "langchain-aws", "langchain-core",
            "hydra-core", "omegaconf", "z3-solver",
        ]},
        "input_sha256": hashlib.sha256(before.encode()).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(run / "scheduler.log"),
                  logging.StreamHandler()],
    )
    print(f"RUN_DIRECTORY={run}", flush=True)
    consume_key(args.key_file)
    recorder = EvidenceCallback(run)
    try:
        agenda = instantiate(cfg.agenda)
        scheduler = instantiate(cfg.scheduler)
        scheduler.workers[0]._llm.callbacks = [recorder]
        asyncio.run(scheduler.run(agenda))
    finally:
        os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)

    with (run / "agenda.pkl").open("rb") as handle:
        final = pickle.load(handle)
    obj = final["objects"][program_path]
    after = obj.content.decode("utf-8")
    (run / "output-program.dfy").write_text(after)
    (run / "verifier-stdout.txt").write_text(obj.properties.get("verification_stdout", ""))
    (run / "verifier-stderr.txt").write_text(obj.properties.get("verification_stderr", ""))
    task_status = final["status"][pending[0]]
    write_json(run / "result.json", {
        "model_invocations": recorder.calls,
        "model_completions": recorder.completions,
        "token_usage": recorder.usage,
        "measured_cost": None,
        "attempts_before": data["total_attempts"],
        "attempts_after": final["total_attempts"],
        "task_status": str(task_status.work_status),
        "worker_notes": task_status.worker_notes,
        "program_changed": before != after,
        "stored_verification_outcome": obj.properties.get("verification_outcome"),
        "verification_note": "If program_changed is false, stored verifier output may be inherited from the input.",
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    print((run / "result.json").read_text(), flush=True)


if __name__ == "__main__":
    main()
