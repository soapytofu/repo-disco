"""Additive warning policy; never changes frozen observations or their scores."""
from collections import Counter
from pathlib import PurePosixPath
import re

VERSION='real-repository-warning-policy-v2'
CLEANUP=re.compile(r"warning: failed to garbage collect incremental compilation session directory `([^`\n]+)`: Directory not empty \(os error 39\)")
SESSION=re.compile(r"debug/incremental/vest_dev-[a-z0-9]+/s-[a-z0-9]+-[a-z0-9]+-working")

def operational_cleanup(warning,command):
    """Recognize only the observed Cargo class inside this invocation's target."""
    match=CLEANUP.fullmatch(warning)
    if not match or command.count('--target-dir')!=1:return False
    index=command.index('--target-dir')+1
    if index>=len(command):return False
    target=PurePosixPath(command[index]);path=PurePosixPath(match[1])
    if not target.is_absolute() or not path.is_absolute():return False
    if '..' in target.parts or '..' in path.parts:return False
    if str(target)!=command[index] or str(path)!=match[1]:return False
    try:relative=path.relative_to(target).as_posix()
    except ValueError:return False
    return SESSION.fullmatch(relative) is not None

def report(project,observation,native,base):
    """Input is a source-bound native observation, recomputed from raw logs."""
    if project not in ('vest','dafny-vmc'):raise ValueError('Unknown project')
    observed=observation['warnings'];upstream=base['upstream_warnings']
    if not all(isinstance(x,str) for x in observed+upstream):raise ValueError('Invalid warnings')
    additional=list((Counter(observed)-Counter(upstream)).elements())
    missing=list((Counter(upstream)-Counter(observed)).elements())
    known=[];unknown=[]
    for warning in additional:
        (known if project=='vest' and operational_cleanup(warning,native['command']) else unknown).append(warning)
    proof=observation['proof_pass'] is True and observation['coverage_complete'] is True
    old=observation['qualified_scope_pass']
    if old!=(observation['proof_pass'] and not additional and not missing):
        raise ValueError('Frozen acceptance disagrees with exact warnings')
    return dict(policy=VERSION,proof_complete=proof,legacy_qualified_scope_pass=old,
                no_additional_warnings=not additional,upstream_warning_profile_complete=not missing,
                operational_warnings=known,unclassified_warnings=unknown,missing_upstream_warnings=missing,
                requires_warning_review=bool(unknown or missing),
                eligible_under_policy_v2=proof and not unknown and not missing,
                all_observed_warnings=list(observed),original_score_unchanged=True,
                live_repository_promoted=False)
