# RepoDisco setup: Cannon, Dafny, and model access

This guide records the setup used for the first RepoDisco pilots. Last updated October 20, 2026. Commands below assume **Bash on Harvard Cannon** unless a step explicitly says to use your laptop or browser.

## What has worked

| Check | Recorded result |
| --- | --- |
| Python environment | `repodisco`, Python 3.11.17 |
| Diff and prompt formatter tests | 17 passed |
| Dafny verification tests | 8 passed |
| Dafny example with the replacement Z3 solver | 1 verified, 0 errors |
| OpenAI generation pilot | 2 verified, 0 errors |
| OpenAI extension pilot | Failed with a Dafny parse error; retained for diagnosis |
| AWS Bedrock / Claude Sonnet connection | Successful; 13 input and 5 output tokens |
| Claude complete-program repair (repair-003) | 4 verified, 0 errors after verifier-only timeout recheck; 541 input and 372 output tokens |

The AWS check confirms model access. A [Claude repair experiment](../../experiments/repair-001/README.md) subsequently ran but failed parsing; a separate assisted formatting correction passed with 4 verified, 0 errors. A later [complete-program repair](../../experiments/repair-003/README.md) passed with one model request and no manual code correction, after a verifier-only timeout recheck. Multi-module repository experiments have not yet been completed. The installation commands consolidate the working setup; they are not a fully pinned environment lockfile.

## 1. Resume an existing Cannon setup

From a terminal on your laptop:

```bash
ssh sophiezeng@login.rc.fas.harvard.edu
```

Use your FASRC credentials and its configured two-factor method. Harvard AWS sign-in is a separate login.

Once on a Cannon login node, request a compute session:

```bash
salloc -p test -c 2 --mem=8G -t 01:00:00
```

Wait for allocation to finish and the compute-node prompt to appear. Then:

```bash
module load python
mamba activate repodisco
cd "$HOME/formal-disco"
export PATH="$CONDA_PREFIX/bin:$PATH"
hash -r
hostname
python --version
```

For another researcher, replace the SSH username and use your own home directory. Do package installation and experiments inside the compute allocation.

Check remaining time:

```bash
squeue -j "$SLURM_JOB_ID" -o "%.18i %.2t %.10M %.10L"
```

Files in your home directory persist after the allocation ends. Environment activation and API keys entered into a shell must be restored in a new session. A one-hour interactive allocation can interrupt a longer experiment; use an appropriately configured batch job for longer runs.

## 2. First-time repository and Python setup

Skip this section if the existing environment and checkout work.

Inside an allocated compute session:

```bash
module load python
mamba create -n repodisco -c conda-forge python=3.11 pip -y
mamba activate repodisco
```

Clone only if `$HOME/formal-disco` does not already exist:

```bash
git clone https://github.com/soapytofu/repo-disco.git "$HOME/formal-disco"
cd "$HOME/formal-disco"
```

The checkout directory is named `formal-disco`, but the personal GitHub repository is `soapytofu/repo-disco`. For an existing checkout, inspect `git remote -v` before pushing.

Install the focused dependencies for these pilots:

```bash
python -m pip install hydra-core==1.3.2 omegaconf==2.3.0 numpy nltk langchain-openai tiktoken pytest openai
python -m pip install --upgrade "boto3>=1.39.0" langchain-aws
python -m nltk.downloader stopwords wordnet averaged_perceptron_tagger_eng
```

The upstream requirements include additional training and GPU dependencies. The small API-backed pilots do not require installing that entire stack.

## 3. Dafny 4.11.0 and Z3

The Ubuntu Dafny distribution's bundled Z3 did not run on the Cannon environment used here because of a system-library compatibility error. Using the Z3 4.12.1 Python wheel's executable worked.

For a fresh installation:

```bash
mkdir -p "$HOME/tools/dafny-4.11.0" "$HOME/tools/downloads"
curl -fL \
  https://github.com/dafny-lang/dafny/releases/download/v4.11.0/dafny-4.11.0-x64-ubuntu-22.04.zip \
  -o "$HOME/tools/downloads/dafny-4.11.0.zip"
unzip -n "$HOME/tools/downloads/dafny-4.11.0.zip" -d "$HOME/tools/dafny-4.11.0"
python -m pip install --only-binary=:all: z3-solver==4.12.1.0
```

Check the direct invocation:

```bash
"$CONDA_PREFIX/bin/z3" -version
"$HOME/tools/dafny-4.11.0/dafny/dafny" verify \
  --solver-path="$CONDA_PREFIX/bin/z3" \
  "$HOME/formal-disco/language/dafny/examples/max.dfy"
```

The recorded result was `1 verified, 0 errors`.

The framework calls `dafny` by name. Create this launcher in the activated `repodisco` environment, only if you have not already configured it:

```bash
cat > "$CONDA_PREFIX/bin/dafny" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
dafny_executable="$HOME/tools/dafny-4.11.0/dafny/dafny"
if [[ "${1:-}" == "verify" ]]; then
  shift
  exec "$dafny_executable" verify \
    --solver-path="${CONDA_PREFIX:?Activate repodisco first}/bin/z3" "$@"
fi
exec "$dafny_executable" "$@"
SH
chmod +x "$CONDA_PREFIX/bin/dafny"
export PATH="$CONDA_PREFIX/bin:$PATH"
hash -r
dafny --version
dafny verify language/dafny/examples/max.dfy
```

This launcher changes solver selection for `verify`; other Dafny subcommands pass through unchanged. It does not require changing Cannon system libraries.

Run the focused tests from the repository directory:

```bash
python -m pytest tests/test_diff.py tests/test_prompt_formatters.py -q
python -m pytest tests/test_dafny_backend.py::TestVerify -q
```

The recorded results were 17 and 8 passing tests, respectively.

## 4. AWS Bedrock access through Harvard

### Browser setup

1. Obtain access to the lab AWS account from the lab administrator.
2. Open the Harvard AWS login widget linked in the lab's [private AWS instructions](https://github.com/metareflection/aws-users), and sign in through Harvard.
3. Select the lab account and assigned role. In the AWS console, select **US East (N. Virginia), `us-east-1`**.
4. Open **Amazon Bedrock → API keys**. The successful exploratory setup used a long-term Bedrock API key with a 30-day expiry. Save the key privately when it is displayed.

If the lab repository is inaccessible, ask for GitHub access or the approved Harvard widget link. Access to GitHub and access to AWS are separate permissions. This public guide intentionally contains no private account identifiers or sign-in URLs.

A Bedrock API key is different from an AWS access-key-ID / secret-access-key pair. The verified workflow below uses the Bedrock bearer token directly; it does not require creating an IAM user or running `aws configure`. For general AWS services, follow Harvard's approved federated CLI instructions separately.

AWS recommends short-term credentials for stronger security; the long-term key here was for exploratory use. Renew or revoke it through the console as needed.

### Load the key into the current Cannon shell

Run this command **by itself**:

```bash
read -r -s -p "Paste your Bedrock API key, then press Enter: " AWS_BEARER_TOKEN_BEDROCK
```

At the prompt, paste only the key and press Enter. Nothing will appear while you paste. Do not replace the variable name in the command with the key, and do not paste the key into chat.

After the normal shell prompt returns, run:

```bash
printf '\n'
export AWS_BEARER_TOKEN_BEDROCK
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1
python -c 'import os; print("Bedrock key loaded" if os.environ.get("AWS_BEARER_TOKEN_BEDROCK") else "Bedrock key missing")'
```

Never print the token to check it, put it in YAML, or commit it to Git. These steps keep it in the current shell environment rather than saving it in the repository.

### Small connection test

This makes **one billable model request**. It already succeeded in the recorded setup; rerun only when you need to validate a new session or key.

```bash
python - <<'PY'
import boto3
from botocore.config import Config

client = boto3.client(
    "bedrock-runtime",
    region_name="us-east-1",
    config=Config(
        connect_timeout=15,
        read_timeout=60,
        retries={"total_max_attempts": 1},
    ),
)
response = client.converse(
    modelId="us.anthropic.claude-sonnet-4-6",
    messages=[{
        "role": "user",
        "content": [{"text": "Reply with only: connection successful"}],
    }],
    inferenceConfig={"maxTokens": 16},
)
for part in response["output"]["message"]["content"]:
    if "text" in part:
        print(part["text"])
print("Token usage:", response.get("usage", {}))
PY
```

Recorded output:

```text
connection successful
Token usage: {'inputTokens': 13, 'outputTokens': 5, 'totalTokens': 18, 'cacheReadInputTokens': 0, 'cacheWriteInputTokens': 0}
```

The model ID is the one tested on October 20, 2026. Availability and permitted models can change. An authorization failure may require the lab administrator to check permissions; re-entering the same key will not fix missing model access.

**Framework integration was exercised in [repair-001](../../experiments/repair-001/README.md).** Loading a Bedrock key does not convert existing OpenAI experiments to Claude. The worker's own `llm` configuration must select `langchain_aws.ChatBedrockConverse` and the intended model/region. Existing OpenAI pilot configs have been preserved.

## 5. OpenAI access, optional fallback

OpenAI API billing is separate from a personal ChatGPT subscription. Use a funded research project in the intended organization, then create a project API key. A lab organization invitation must be accepted before its projects become available.

Run this command by itself:

```bash
read -r -s -p "Paste your OpenAI API key, then press Enter: " OPENAI_API_KEY
```

Paste only the key at the prompt, press Enter, then run:

```bash
printf '\n'
export OPENAI_API_KEY
python -c 'import os; print("Key loaded" if os.environ.get("OPENAI_API_KEY") else "Key missing")'
python -c 'from openai import OpenAI; OpenAI(timeout=20, max_retries=0).models.list(); print("API connection successful")'
```

The final command checks API access without generating text. It does not prove access to every model or that a particular generation request will succeed.

OpenAI credentials are unnecessary for the Bedrock connection test. Remove keys from the current shell when finished if desired:

```bash
unset OPENAI_API_KEY AWS_BEARER_TOKEN_BEDROCK
```

## 6. Pilot evidence and reproduction

The committed records are:

- [Generation pilot](../../experiments/pilot-001/README.md): integer `Max` utility; verified successfully.
- [Extension pilot](../../experiments/extension-001/README.md): attempted additional properties; failed parsing because new declarations were inserted between a method signature and its body.

To reproduce the initial OpenAI pilot with a new paid generation request, first complete the environment, verifier, and OpenAI setup above. From the repository directory:

```bash
mkdir -p data
cp -n experiments/pilot-001/seed.jsonl data/repodisco-pilot-seed.jsonl
python scheduler.py --config-name repodisco_pilot
```

Review [the pilot configuration](../../config/repodisco_pilot.yaml) before running. It records model `gpt-5.6-luna`, one agenda attempt, and the original limits. This is a historical experiment setting, not a claim that this model is always the best or remains available. A rerun may produce different code.

The run writes a timestamped directory under `outputs/repodisco-pilot/`. Use its actual path to export the result:

```text
python materialize.py materialize outputs/repodisco-pilot/<RUN_TIMESTAMP>/agenda.pkl discoveries/<NEW_RUN_NAME>/
```

Replace both angle-bracket placeholders before executing. Keep each run in its own output/export directory.

The extension configuration contains paths from the original cluster run and should not be run unchanged as a fresh experiment. Its `max_attempts` limit is cumulative when resuming a checkpoint. Copy a checkpoint to a new run before testing a repair, and account for attempts already recorded.

Checkpoints under `outputs/` and exported `discoveries/` are ignored by Git. The readable experiment evidence is committed under `experiments/`. Cloning GitHub therefore does not restore the original checkpoint. Only load pickle checkpoints you trust.

For each repair experiment, preserve the failed program and verifier message, make a bounded repair attempt, then save the prompt/config, generated change, verifier output, token usage, and outcome. Check that the original specifications and intended declarations remain intact: verifier success alone does not establish that a repair preserved the task.

## 7. Save results and reconnect

Review changes before staging:

```bash
git status --short
git diff
```

Add only the intended config and readable experiment files by explicit path. Review the staged diff for keys or private information before committing and pushing to the personal repository. Raw checkpoints and credentials do not belong in Git.

When changes were committed directly on GitHub, update a clean Cannon checkout:

```bash
git pull --ff-only
```

If Git reports local changes or divergent history, inspect them before continuing; do not reset or force-push to discard work.

To finish an interactive compute session, run `exit`. If it returns to the login node, a second `exit` disconnects SSH.

If a terminal stops responding, reconnect in another terminal and inspect:

```bash
squeue -u sophiezeng
```

Check whether the previous allocation is still running or has reached its time limit. Do not assume a stalled progress bar means installation failed: after reactivating the environment, `python -c 'import openai; print(openai.__version__)'` can check the earlier package installation.

Common checks:

- **`read: ... not a valid identifier`:** run the exact Bash prompt command, then paste the key only when asked. The variable name must stay in the command.
- **Key missing after reconnect:** activate the environment and load the relevant key again.
- **Expired Bedrock token:** obtain a fresh key through the approved console flow and replace the shell value.
- **Dafny/Z3 system-library error:** check that `command -v dafny` points into the active environment and that its launcher uses `$CONDA_PREFIX/bin/z3`.
- **Missing Python module:** confirm `python --version` and `mamba activate repodisco` before installing anything.
- **Allocation almost over:** save readable results and request a new session before starting another experiment.

## 8. Let the research assistant run Cannon commands directly

The assistant can use a separate SSH session through a connection you authenticate on your Mac. It cannot control the existing macOS Terminal window through this app. This workflow was tested on October 20, 2026.

In a **new local Mac terminal tab**, run:

```bash
ssh -M -S "$HOME/.ssh/repodisco-codex.sock" -o ControlPersist=30m sophiezeng@login.rc.fas.harvard.edu
```

Complete the normal FASRC password and two-factor prompts yourself, then leave the tab open. The assistant can use the local control socket to run SSH commands without receiving your password or verification code. `ControlPersist=30m` allows the connection to remain for up to 30 minutes while idle after its initial session ends.

Example read-only check from the Mac:

```bash
ssh -S "$HOME/.ssh/repodisco-codex.sock" -o BatchMode=yes sophiezeng@login.rc.fas.harvard.edu hostname
```

Research commands must still run in an allocated compute job. The assistant should inspect `squeue` and use the actual active allocation, rather than assuming a job ID or compute node remains valid. The tested route used `srun --jobid=<ACTIVE_JOB_ID> --overlap -N1 -n1 -c2` and `mamba run -n repodisco` within that allocation.

**Shell environments are separate:** this shares authentication, not the Bedrock key loaded in an earlier terminal. A new model-running session needs its own approved credential setup. Do not print a key or send it through chat. The patch tests and Dafny checks require no model key.

For a bounded model run, the tested one-use handoff is created in the **original Cannon terminal** where the key is loaded:

```bash
python - <<'PY'
import getpass
import os
from pathlib import Path

key = os.environ.get('AWS_BEARER_TOKEN_BEDROCK') or getpass.getpass('Bedrock API key (hidden): ')
if not key.strip():
    raise SystemExit('No key entered; nothing saved.')
path = Path.home() / '.repodisco-bedrock-handoff'
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
with os.fdopen(fd, 'w') as f:
    f.write(key.strip())
print('Private key handoff ready.')
PY
```

The [recorded one-attempt runner](../../experiments/repair-002/runner.py) checks the handoff's owner/type/permissions, loads it into its own process, and deletes the file before making the model call. It never prints the key. A successful [direct run](../../experiments/repair-002/README.md) confirmed this credential flow and captured token usage, though the model's edit itself failed format validation.

The handoff is single-use, not persistent model access: another model-running process needs another handoff. Do not recreate it while a run is using it. If the run is cancelled before the file is consumed, remove the unused handoff from Cannon.

After all assistant-run commands have finished, you can close the shared connection from your Mac:

```bash
ssh -S "$HOME/.ssh/repodisco-codex.sock" -O exit sophiezeng@login.rc.fas.harvard.edu
```

This ends the shared SSH connection and may disconnect sessions using it. Reauthenticate when a later work session needs access.

## References

- [Harvard Cannon quickstart](https://docs.rc.fas.harvard.edu/kb/quickstart-guide/)
- [Harvard job submission guidance](https://docs.rc.fas.harvard.edu/kb/running-jobs/)
- [Harvard Python package installation](https://docs.rc.fas.harvard.edu/kb/python-package-installation/)
- [Dafny 4.11.0 release](https://github.com/dafny-lang/dafny/releases/tag/v4.11.0)
- [Lab AWS instructions — authorized members only](https://github.com/metareflection/aws-users)
- [AWS: generate Bedrock API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-generate.html)
- [AWS: use Bedrock API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-use.html)
- [AWS Bedrock getting started](https://docs.aws.amazon.com/bedrock/latest/userguide/getting-started.html)
- [OpenAI project management](https://help.openai.com/en/articles/9186755-managing-projects-in-the-api-platform)
- [OpenAI API and ChatGPT billing](https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform)
