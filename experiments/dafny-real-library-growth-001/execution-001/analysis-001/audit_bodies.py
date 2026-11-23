"""Read-only audit of saved implementation semantics and parent/prompt links.

Uses the frozen guard lexer; no native/provider/transport calls or acceptance.
Root's separate collection reviewer owns the full raw/accounting replay.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

EXPERIMENT = Path(__file__).resolve().parents[2]
ARCHIVE = EXPERIMENT / "execution-001/retrieved-001"
PACKAGE, MODEL = ARCHIVE / "package", ARCHIVE / "model-001"
RUNTIME_SHA = "69d07a07241982e21bf06cf16ed038187c8fd2d2a7fff1e71443515745f49548"
INPUTS = {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())


def read(path):
    raw = path.read_bytes()
    INPUTS[path.relative_to(EXPERIMENT).as_posix()] = sha(raw)
    return raw


def load(path):
    return json.loads(read(path))


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def call_sites(tokens):
    """Count syntax, not runtime frequency; exclude comments/literal interiors.

    Assertion/specification expressions also contain ordinary call forms.
    Reveal is separate, even though its surface spelling contains parentheses.
    """
    counts = {"ordinary_call_form": Counter(), "reveal_directive": Counter()}
    for index, token in enumerate(tokens):
        if token[0] != "identifier" or (index and tokens[index - 1][1] == "."):
            continue
        name, end = token[1], index + 1
        while end + 1 < len(tokens) and tokens[end] == ("punctuation", ".") and tokens[end + 1][0] == "identifier":
            name += "." + tokens[end + 1][1]
            end += 2
        if end < len(tokens) and tokens[end] == ("punctuation", "("):
            kind = "reveal_directive" if index and tokens[index - 1] == ("identifier", "reveal") else "ordinary_call_form"
            counts[kind][name] += 1
    return {kind: dict(sorted(values.items())) for kind, values in counts.items()}


def main():
    freeze_raw = read(PACKAGE / "execution-001/runtime-freeze.json")
    require(sha(freeze_raw) == RUNTIME_SHA, "Unexpected frozen runtime")
    freeze = json.loads(freeze_raw)
    for name in ("common/guard.py", "common/review_native.py", "pilot/draft-002/scope.json"):
        require(sha(read(PACKAGE / name)) == freeze["files"][name], "Audit dependency changed: " + name)
    sys.path.insert(0, str(PACKAGE / "common"))
    import guard
    require(Path(guard.__file__).resolve() == PACKAGE / "common/guard.py", "Mixed guard import")
    scope, summary = load(PACKAGE / "pilot/draft-002/scope.json"), load(MODEL / "summary.json")
    require(summary["synthetic"] is False and summary["status"] == "COMPLETE", "Not a completed real collection")
    specification = load(EXPERIMENT / "pilot/preparation-input-002.json")
    rows, bodies, request_ids = [], {}, []
    token_groups, byte_groups = defaultdict(lambda: defaultdict(list)), defaultdict(lambda: defaultdict(list))
    for slot in scope["slots"]:
        sid, project, stage = slot["id"], slot["project"], slot["stage"]
        directory = MODEL / "slots" / sid
        config = scope["projects"][project]["stages"][str(stage)]
        profile = load(PACKAGE / config["edit_profile"])
        require(sha(read(PACKAGE / config["edit_profile"])) == freeze["files"][config["edit_profile"]], sid + ": profile changed")
        body_raw = read(directory / "body.txt")
        body, tokens = body_raw.decode(), guard.body_tokens(body_raw.decode())
        bodies[sid] = body
        calls = call_sites(tokens)
        group = project + "/stage" + str(stage)
        token_groups[group][digest(tokens)].append(sid)
        byte_groups[group][sha(body_raw)].append(sid)
        binding, envelope = load(directory / "response-binding.json"), load(directory / "envelope.json")
        response = load(MODEL / "requests" / ("response-%03d.json" % binding["request_sequence"]))
        payload = response["text"][envelope["start_char"]:envelope["end_char"]]
        require(sha(response["text"].encode()) == envelope["raw_sha256"] and sha(payload.encode()) == envelope["payload_sha256"], sid + ": envelope differs")
        require(json.loads(payload) == {"body": body}, sid + ": provider body differs")
        require(digest(response) == binding["response_sha256"] and response["request_id"] == binding["request_id"], sid + ": provider binding differs")
        request_ids.append(response["request_id"])
        target = profile["addition"]["path"]
        source = read(directory / "candidate" / target)
        rendered, body_review = guard.render_body(profile, body)
        require(source == rendered, sid + ": body/protected source changed")
        edit, native = load(directory / "edit-review.json"), load(directory / "native-review.json")
        require(edit["body"] == body_review and native["synthetic"] is False and native["qualified_success"] and not native["warnings"], sid + ": qualification differs")
        prompt = load(directory / "prompt.json")
        require(prompt["guard_profile_sha256"] == digest(profile), sid + ": prompt profile differs")
        reference_entry = specification["projects"][project]["reference_sources"][str(stage)]
        reference_raw = read(EXPERIMENT / reference_entry["path"])
        require(sha(reference_raw) == reference_entry["sha256"], sid + ": analyst reference changed")
        begin, end = profile["addition"]["begin_marker"], profile["addition"]["end_marker"]
        reference_body = reference_raw.decode().split(begin, 1)[1].split(end, 1)[0]
        row = dict(slot_id=sid, project=project, stage=stage, stage_id=profile["stage_id"], chain_id=slot["chain_id"],
                   body_sha256=sha(body_raw), body_token_sha256=digest(tokens), token_count=len(tokens),
                   source_path=(directory / "candidate" / target).relative_to(EXPERIMENT).as_posix(),
                   body_first_source_line=source.decode().split(begin, 1)[0].count("\n") + begin.count("\n") + 1,
                   request_id=response["request_id"], provider_body_exact=True, protected_source_exact=True,
                   named_units=len(native["units"]), strict_zero_warning_native_pass=True, calls=calls,
                   analyst_reference_token_identical=tokens == guard.body_tokens(reference_body), parent=None)
        if stage == 1 and project == "stdlib":
            require(calls["ordinary_call_form"].get("a.Push") == 1 and calls["ordinary_call_form"].get("AppendAll") == 1, sid + ": unexpected recursive body")
            row["semantic_read"] = "Return on empty input; otherwise push the first value through upstream DynamicArray and recurse on the tail. Host-fixed decreases |values| proves termination."
        elif stage == 1:
            require(calls["ordinary_call_form"].get("U.SeqToUInt16", 0) >= 1 and calls["ordinary_call_form"].get("U.UInt16SeqDeserializeSerialize") == 1, sid + ": upstream calls absent")
            row["semantic_read"] = "Reject a missing two-byte prefix or truncated payload; decode using upstream SeqToUInt16; return exact payload and suffix, with a round-trip lemma used in proof statements."
        else:
            parent_sid = slot["parent_slot_id"]
            parent_dir = MODEL / "slots" / parent_sid
            receipt, parent_binding = load(parent_dir / "parent-receipt.json"), load(parent_dir / "response-binding.json")
            parent_name = profile["parent_requirement"]["addition_path"]
            parent_raw = read(parent_dir / "candidate" / parent_name)
            require(read(directory / "candidate" / parent_name) == parent_raw, sid + ": parent substituted or changed")
            require(receipt["origin"] == "model_candidate" and receipt["synthetic"] is False and receipt["accepted"], sid + ": not a real accepted parent")
            require(receipt["chain_id"] == slot["chain_id"] and receipt["project"] == project, sid + ": cross-lineage parent")
            require(receipt["request_id"] == parent_binding["request_id"] and receipt["response_sha256"] == parent_binding["response_sha256"], sid + ": parent request mismatch")
            require(prompt["parent_audit"]["receipt_sha256"] == digest(receipt) and prompt["parent_source_sha256"] == sha(parent_raw), sid + ": parent/prompt binding differs")
            prefix = config["parent_display_fixed_prefix_utf8"].encode()
            require(parent_raw.startswith(prefix), sid + ": invalid metadata removal")
            text = prompt["payload"]["messages"][0]["content"][0]["text"]
            require(parent_raw[len(prefix):].decode() in text and "{{ACCEPTED_PARENT_SOURCE}}" not in text, sid + ": exact parent absent from prompt")
            api = "Append.AppendAll" if project == "stdlib" else "F.ReadU16Frame"
            require(calls["ordinary_call_form"].get(api) == 2, sid + ": parent calls absent")
            reveals = calls["reveal_directive"].get(api, 0)
            require(reveals == (1 if project == "aws" else 0), sid + ": reveal count differs")
            row["parent"] = dict(slot_id=parent_sid, source_path=parent_name, source_sha256=sha(parent_raw),
                                 receipt_canonical_sha256=digest(receipt), request_id=receipt["request_id"],
                                 exact_child_source=True, exact_prompt_view=True, api=api, ordinary_call_sites=2,
                                 reveal_directives=reveals, necessary_dependency_claim=False)
            row["semantic_read"] = ("Record old size; append suffix then prefix through accepted AppendAll; return final size." if project == "stdlib" else
                                    "Reveal accepted ReadU16Frame; parse input, propagate failure, parse the first result's exact suffix, propagate failure, then return both payloads and final suffix.")
        rows.append(row)
    require(len(request_ids) == len(set(request_ids)) == 12, "Not twelve distinct request IDs")
    diversity = {group: dict(samples=sum(len(ids) for ids in groups.values()), byte_distinct_bodies=len(byte_groups[group]),
                             token_distinct_bodies=len(groups), token_groups=list(groups.values())) for group, groups in sorted(token_groups.items())}
    report = dict(schema="dafny-library-independent-body-lineage-audit-v1", runtime_sha256=RUNTIME_SHA,
                  source_run_id=summary["run_id"], observations=rows, exact_parent_lineages=6,
                  distinct_request_ids=12, observed_child_parent_ordinary_call_sites=12,
                  additional_parent_reveal_directives=3, body_diversity=diversity,
                  blocking_integrity_or_mathematical_findings=[], new_model_calls=0, new_native_calls=0,
                  analysis_scope="Body semantics, protected-source reconstruction and exact parent/prompt/request links. Root review_collection.py owns the full raw/accounting/source/native replay.",
                  defensible_result="Twelve fresh verified implementation additions form six two-stage lineages across two selected real-library scopes. Every child visibly reuses its own accepted stage-one API under host-supplied fixed contracts.",
                  limitations=[
                      "Four fixed stage tasks repeated three times are not twelve independent tasks. All three standard-library bodies are identical within each stage.",
                      "AWS children reveal the opaque parent definition. This is accepted-source reuse with unfolding available, not exclusively opaque-contract reasoning.",
                      "Call-site counts exclude comments/literal interiors and separate reveal. They do not measure dynamic invocation frequency, minimal proofs, necessary dependence or causal structural effects.",
                      "Host supplies addition names/interfaces/contracts, task selection and full selected upstream context. This is constrained executable extension, not unconstrained API discovery or whole-upstream synthesis.",
                      "Native verification checks saved contracts under pinned tools/source/trust. No compile/run, runtime benchmark or stack-stress test was performed; recursive AppendAll is not a demonstrated performance improvement.",
                      "Two selected three-file development scopes do not establish held-out generalization, Verus performance, full AWS MPL coverage or a feedback advantage. The earlier broad AWS qualification failure remains separate.",
                      "The 12/12 ceiling establishes feasibility on these tasks; harder/diverse tasks and comparative baselines are needed to discriminate capability."],
                  meeting_example=dict(title="A new array operation becomes the next operation's dependency",
                                       parent_slot="slot-01", child_slot="slot-03", upstream_api="Std.DynamicArray.DynamicArray.Push",
                                       parent_body_verbatim=bodies["slot-01"], child_body_verbatim=bodies["slot-03"],
                                       contract_summary="AppendAll preserves validity and appends values. AppendRotated appends values[pivot..] + values[..pivot], returns old/new size, and preserves validity, capacity monotonicity and allocation freshness.",
                                       illustrative_not_executed="For prior items [9], values [10,20,30] and pivot 1, the specified final items are [9,20,30,10], start=1, end=4.",
                                       reference_comparison="The analyst AppendAll reference used a loop. The model parent uses recursion; the child is linked to that actual parent, not an analyst substitution."),
                  input_sha256=INPUTS)
    output = Path(__file__).with_name("body-lineage-audit.json")
    require(not output.exists(), "Preserve existing analysis output")
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    for row in rows:
        print(json.dumps({key: row[key] for key in ("slot_id", "project", "stage", "named_units", "calls", "analyst_reference_token_identical")}, sort_keys=True))
    print(json.dumps(dict(report_sha256=sha(output.read_bytes()), input_pins=len(INPUTS), exact_parent_lineages=6,
                          body_diversity=diversity, ordinary_parent_call_sites=12, parent_reveal_directives=3,
                          blocking_findings=0, new_model_calls=0, new_native_calls=0), sort_keys=True))


if __name__ == "__main__":
    main()
