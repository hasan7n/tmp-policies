# Recipe — the inference tutorial, end to end, in a browser

Run [`docs/docs/tutorial_inference.md`](../../docs/docs/tutorial_inference.md)
from first click to last through the web UI, on a machine with no screen, and
come out with a video of it happening. Both of the tutorial's policies, FL-DS
and FL-IS, in one run.

**Done means:** the run prints `PASSED: 44 steps`, and there is one `run.mp4` of
the browser doing it.

## Parameters

`fix_problems` — given to you by whoever asked for the run.

- `False` — at the first thing that does not work, **stop**. Report the step, the
  command, the output, and which file and line you think is responsible. Change
  nothing.
- `True` — fix it, say plainly what you changed and why, then start the run again
  from the top. Never edit a test to make it pass, never delete a check to get
  past it, and never widen a timeout without saying you did.

Either way: report what actually happened. A step you skipped is a step you
report as skipped.

## What it needs

| Thing | Why |
| --- | --- |
| Docker | everything but the FL server and the public guardian runs in a container |
| ~20GB free under `/var/lib/docker` | the PDO images |
| Google Chrome | selenium fetches its own driver |
| `Xvfb` | the display the browser draws on (`sudo apt-get install -y xvfb`) |
| `ffmpeg` | records that display (`pip install imageio-ffmpeg` also works) |
| `selenium` in the Python you point `$PYTHON` at | the clicking |

Without Xvfb or ffmpeg the run still passes, headless, with **no video at all**
— and says so on its first line. That is a failure of this recipe's goal; report
it rather than reporting a pass.

## 1. Check the codebase still matches this recipe

Do this first, every time. This recipe names files, form fields and policy names;
any of them can have moved.

```bash
cd <repo> && git log --oneline -5 && git status --short
```

These must exist:

| file | what this recipe uses it for |
| --- | --- |
| `tools/tests/run_webui_inference_test.sh` | brings the stack up and runs the test |
| `tools/tests/webui_inference_test.py` | the clicking |
| `tools/tests/recorder.py` | the display and the video |
| `tools/make_tutorial_files.sh` | writes the cohort and the script the tutorial uses |
| `tools/start_fl_server.sh` | the job board the inference flow goes through |
| `policy_cards/FL/inference-disease-specific-research/` | the first policy tested |
| `policy_cards/FL/inference-institution-specific-restriction/` | the second one |

And the images the stack runs must be present locally or pullable — the tags the
`tools/docker_*.sh` scripts name (`mlcommons/pdo_base_client`,
`mlcommons/toy_guardian`, `mlcommons/toy_inference_guardian`, plus the ledger,
services and registry images). Build the first three with
`bash tools/docker_build_all.sh` if they are missing; that script also pushes, so
comment the pushes out if you only want them locally.

## 2. Run it

```bash
PYTHON=/path/to/venv/bin/python bash tools/tests/run_webui_inference_test.sh
```

Takes about fifteen minutes, much of it the ledger and enclave services coming
up. It tears the stack down afterwards; pass `-k` to leave it running.

| flag | effect |
| --- | --- |
| `-k` | keep the stack up after the test |
| `-n` | skip setup entirely and drive whatever is already running |
| `-H` | run headed on your own screen; records nothing |
| `-a DIR` | artifacts directory (default `/tmp/pdo_webui_artifacts`) |

It does all of this by itself: generates the user keys, starts the ledger and
enclave services, starts both registries, writes the tutorial files, starts the
FL server, starts the webapp with its guardian deploy watcher, and then drives
the browser through the tutorial:

script owner publishes the script behind a public guardian and reads its DID →
trusted issuer creates an issuer object and signs a `ScriptHashCredential` and an
`IntendedDataUseCredential` about that script → dataset owner registers the
cohort behind an inference guardian, attaches the disease-scope policy and trusts
the issuer → script owner requests the run and gets metrics back.

Then the part the tutorial can only describe: the owner narrows `allowedDiseases`
to a code the script is not declared for, the **same** request is refused at the
capability step, the owner puts it back, and the request succeeds again. Without
that, a passing run only proves the machinery runs — not that the policy decides.
Then a second script, hashing to something else but carrying the first one's
digest: the policy approves it and the guardian refuses it.

The second half is the tutorial's Part 5, the FL-IS policy. The trusted issuer
adds a session-key issuer (which brings a wallet key authority with it), the
script owner creates a wallet and has that wallet sign a `ScriptOwnershipCredential`
over the script with its own contract key, the issuer vouches for the requester's
institution, and a second cohort goes up behind FL-IS trusting all three issuers.
The run is requested with both roles filled and metrics come back.

Its denial is the one specific to this policy: a *second* wallet signs the same
ownership claim about the same script — correctly, with its own key — and the same
request is refused, because the wallet claiming the script is not the wallet the
affiliation is about. Re-signing from the right wallet makes it pass again.

## 3. What you should have at the end

```
/tmp/pdo_webui_artifacts/run.mp4     the browser, start to end, real time
/tmp/pdo_webui_artifacts/run_4x.mp4  the same thing, watchable
/tmp/pdo_webapp.log                  the webapp's own log
/tmp/pdo_fl_server.log               every job the FL server handed out
/tmp/pdo_engine.log                  ledger + enclave services
tools/pdo_scratch/guardian_requests/guardian_deploy.log
                                     what each guardian printed as it came up
```

Check the video is real before reporting success — it should be about as long as
the run took:

```bash
ffmpeg -hide_banner -i /tmp/pdo_webui_artifacts/run.mp4 2>&1 | grep -E 'Duration|Stream'
```

The 4x copy is made for you by the same script; `run.mp4` is the authoritative
one.

Failure screenshots (`<step>.png`, `<step>.html`) only appear when a step fails.
If they are there, the run did not pass, whatever else it printed — the setup
clears the previous run's, so what you find is always this run's.

## 4. When something fails

The script prints the failing step, the browser's URL, a screenshot and the
page's HTML. Read those first. The video ends on the failure with the step name
in the caption bar, which is usually the quickest way to see what the browser was
looking at.

Things that have actually gone wrong here:

| symptom | cause |
| --- | --- |
| `Timed out ... waiting for the enclave services` | a previous run's ledger container is still up on the old workspace; tear down and retry |
| every step fails at the identity dropdown | the webapp is up but its PDO client cannot reach the ledger — check `/tmp/pdo_webapp.log` |
| registering the cohort fails at "Waiting for the guardian to be healthy" | the inference guardian container did not come up; see `guardian_deploy.log` |
| the run step fails at "Waiting for the FL client to report" | no FL client is polling — the guardian is up but its bundled client crashed, or the FL server was not running when it started |
| the run step fails at "Submitting the job to the FL server" | the webapp container cannot reach the FL server; it needs `FL_SERVER_URL` pointing at the host gateway (see `pdo_client/docker/run_webapp.sh`) |
| `Not recording: Xvfb is not installed` | see the requirements table above |

## 5. Clean up

The script tears down after itself unless you passed `-k`. To do it by hand:

```bash
bash tools/stop_all.sh
bash tools/docker_stop_all.sh
```
