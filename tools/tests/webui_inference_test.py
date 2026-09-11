"""The inference tutorial, driven through the web UI.

Every click `docs/docs/tutorial_inference.md` asks a reader to make, made by a
browser instead: the script owner publishes their code, the trusted issuer
vouches for it, the dataset owner puts a cohort behind an inference guardian and
attaches a disease-scope policy to it, and the script owner asks for the run.

It then does the one thing the tutorial can only describe -- it takes the policy
out of scope and watches the same request be refused, so a passing run is
evidence the policy is deciding rather than waving everything through.

The second half runs the tutorial's other policy, FL-IS, which asks who is
running the code rather than what the code is for. That one turns on a credential
the requester's own wallet signs, so it also checks the thing that makes such a
credential worth anything: swap in an ownership claim from a different wallet and
the same request stops being allowed.

Deliberately not pytest. This is a script: it runs top to bottom, prints each
step as it happens, and exits non-zero on the first failure with the browser's
last known state reported. Run it through ``run_webui_inference_test.sh``, which
brings the stack up around it.

It also records itself. The browser draws on a virtual display and ffmpeg records
that display for the whole run, captioned with the step it is on -- see
``recorder.py``. A headless run is otherwise invisible.
"""

import argparse
import hashlib
import json
import os
import sys
import time
import traceback

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from recorder import SCREEN, NullRecorder, Recorder, VirtualDisplay

# ---------------------------------------------------------------- the tutorial
SCRIPT_OWNER = "data_user"
ISSUER = "vc_issuer"
DATA_OWNER = "data_owner"

SCRIPT_ASSET = "cohort_summary_script"
EDITED_SCRIPT_ASSET = "cohort_summary_script_v2"
DATA_ASSET = "patient_cohort"
# The second half's dataset: the same cohort behind its own guardian, so the two
# policies are demonstrated side by side rather than one replacing the other.
PARTNER_ASSET = "partner_cohort"
ISSUER_NAME = "code review board"
SESSION_KEY_ISSUER = "session keys"
WALLET_NAME = "researcher_wallet"
OTHER_WALLET_NAME = "outsider_wallet"

SCRIPT_PATH = os.environ.get("TUTORIAL_SCRIPT_PATH", "/tmp/inference_script.py")
EDITED_SCRIPT_PATH = os.environ.get(
    "TUTORIAL_EDITED_SCRIPT_PATH", "/tmp/inference_script_v2.py"
)
COHORT_PATH = os.environ.get("TUTORIAL_COHORT_PATH", "/tmp/patient_cohort.csv")

SCRIPT_PORT = "7910"
EDITED_SCRIPT_PORT = "7911"
GUARDIAN_PORT = "7900"
PARTNER_GUARDIAN_PORT = "7902"

# The disease the tutorial's script declares itself for, and one it does not --
# the second is what the denial check swaps in.
ALLOWED_DISEASE = "MONDO:0005148"
OTHER_DISEASE = "MONDO:0005015"

# The institution the requester belongs to, for the second policy.
ALLOWED_INSTITUTION = "did:example:best_university"

DS_POLICY_NAME = "FL-INFERENCE-DISEASE-SPECIFIC-RESEARCH"
IS_POLICY_NAME = "FL-INFERENCE-INSTITUTION-SPECIFIC-RESTRICTION"

# A guardian deploy waits on a container coming up; a policy is several contract
# operations in a row; an inference run waits on an FL client claiming the job.
SHORT_WAIT = 30
FLOW_TIMEOUT = int(os.environ.get("WEBUI_FLOW_TIMEOUT", "600"))

# Replaces window.alert with an on-page toast. The webapp reports everything
# through alert(), which in a driven browser is a modal that blocks the page and
# is invisible in the recording. The shim is display-only -- the same messages,
# in the same order, kept where both the video and the test can read them.
ALERT_SHIM = """
(function () {
    if (window.__pdoAlertShim) { return; }
    window.__pdoAlertShim = [];
    function toast(text) {
        var el = document.getElementById('__pdo_toast__');
        if (!el) {
            el = document.createElement('div');
            el.id = '__pdo_toast__';
            el.style.cssText = 'position:fixed;top:12px;right:12px;z-index:2147483646;'
                + 'pointer-events:none;max-width:44rem;display:flex;flex-direction:column;'
                + 'gap:6px;align-items:flex-end;';
            (document.body || document.documentElement).appendChild(el);
        }
        var line = document.createElement('div');
        var bad = /^Error/i.test(text);
        line.style.cssText = 'background:' + (bad ? '#7f1d1d' : '#14532d') + ';color:#fff;'
            + 'font:500 15px/1.35 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;'
            + 'padding:9px 14px;border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,.35);';
        line.textContent = text;
        el.appendChild(line);
        setTimeout(function () { line.remove(); }, 6000);
    }
    window.alert = function (text) {
        text = String(text);
        window.__pdoAlertShim.push(text);
        try { toast(text); } catch (e) { /* before <body> exists */ }
    };
})();
"""

# One poll of a running flow: the steps the progress modal is showing, and
# whether it has finished. Read in one call so a re-render cannot hand back a
# stale element mid-read.
FLOW_STATE = """
var steps = [];
document.querySelectorAll('#progress-steps li').forEach(function (row) {
    steps.push({
        step: row.dataset.step,
        status: row.dataset.status,
        label: (row.querySelector('.progress-step-label') || {}).textContent || '',
        detail: (row.querySelector('.progress-step-detail') || {}).textContent || '',
    });
});
var close = document.getElementById('progress-close');
return {
    steps: steps,
    finished: !!(close && close.style.display !== 'none'),
    title: (document.getElementById('progress-title') || {}).textContent || '',
};
"""

REC = NullRecorder()


class StepFailed(Exception):
    pass


# ---------------------------------------------------------------- the harness
class Runner:
    """Runs the steps, reports them, and stops at the first failure."""

    def __init__(self, driver, base_url, artifacts):
        self.driver = driver
        self.base_url = base_url.rstrip("/")
        self.artifacts = artifacts
        self.passed = 0
        self.failed = None
        self.started = time.time()

    def url(self, path):
        return self.base_url + path

    def step(self, name, fn):
        if self.failed:
            return
        print(f"\n=== {name} ", flush=True)
        began = time.time()
        REC.caption(f"{self.passed + 1:02d}  {name}")
        try:
            fn()
        except Exception as error:
            self.failed = name
            print(
                f"    FAILED after {time.time() - began:.1f}s: "
                f"{type(error).__name__}: {error}",
                flush=True,
            )
            REC.caption(f"{self.passed + 1:02d}  {name} -- FAILED")
            self._capture(name)
            traceback.print_exc()
        else:
            self.passed += 1
            print(f"    ok ({time.time() - began:.1f}s)", flush=True)

    def _capture(self, name):
        """A failure in a browser is invisible unless something records it."""
        slug = "".join(c if c.isalnum() else "_" for c in name)[:60]
        try:
            os.makedirs(self.artifacts, exist_ok=True)
            shot = os.path.join(self.artifacts, f"{slug}.png")
            self.driver.save_screenshot(shot)
            html = os.path.join(self.artifacts, f"{slug}.html")
            with open(html, "w") as f:
                f.write(self.driver.page_source)
            print(f"    url  : {self.driver.current_url}", flush=True)
            print(f"    shot : {shot}", flush=True)
            print(f"    html : {html}", flush=True)
        except WebDriverException as error:
            print(f"    (could not capture page state: {error})", flush=True)

    def report(self):
        took = time.time() - self.started
        print("\n" + "=" * 60, flush=True)
        if self.failed:
            print(f"FAILED at: {self.failed}", flush=True)
            print(f"{self.passed} steps passed before it, {took:.0f}s elapsed", flush=True)
            return 1
        print(f"PASSED: {self.passed} steps in {took:.0f}s", flush=True)
        return 0


# ---------------------------------------------------------------- page helpers
def wait(driver, timeout=SHORT_WAIT):
    return WebDriverWait(driver, timeout)


def visible(driver, selector, timeout=SHORT_WAIT):
    return wait(driver, timeout).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
    )


def click(driver, selector, timeout=SHORT_WAIT):
    element = wait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
    )
    element.click()
    return element


def fill(driver, selector, value, timeout=SHORT_WAIT):
    element = visible(driver, selector, timeout)
    element.clear()
    element.send_keys(value)
    return element


def set_value(driver, selector, value):
    """Put a value into a field without typing it.

    A JSON blob typed character by character is slow and, in a textarea the page
    reformats as you go, unreliable. The input/change events the page listens for
    are dispatched by hand.
    """
    driver.execute_script(
        """
        var el = document.querySelector(arguments[0]);
        if (!el) { throw new Error('no element for ' + arguments[0]); }
        el.value = arguments[1];
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        """,
        selector,
        value,
    )


def open_page(runner, path):
    runner.driver.get(runner.url(path))
    visible(runner.driver, "nav.navbar")


def alerts(driver):
    return driver.execute_script("return window.__pdoAlertShim || [];")


def run_flow(driver, timeout=FLOW_TIMEOUT, expect_error=False):
    """Wait out a streaming flow and return the steps the modal showed.

    Every multi-step action in this webapp -- provisioning, registering,
    exposing, using -- reports through the same progress modal, so one waiter
    covers all of them. Raises unless the outcome is the one asked for.
    """
    started_at = driver.current_url
    deadline = time.time() + timeout
    state = {"steps": [], "finished": False, "title": ""}
    while time.time() < deadline:
        REC.tick()
        try:
            state = driver.execute_script(FLOW_STATE)
            here = driver.current_url
        except WebDriverException:
            # Mid-navigation: the flow finished and redirected.
            time.sleep(1.0)
            return []
        if state["finished"]:
            break
        # The flow's own terminal redirect landed before this loop saw it, so
        # there is nothing left on this page to wait for.
        if here != started_at and not state["steps"]:
            time.sleep(0.5)
            return []
        time.sleep(0.4)
    else:
        shown = ", ".join(f"{s['step']}={s['status']}" for s in state["steps"])
        raise StepFailed(f"flow did not finish within {timeout}s (steps: {shown})")

    errored = [s for s in state["steps"] if s["status"] == "error"]
    for s in state["steps"]:
        print(f"      [{s['status']:>7}] {s['label']} {s['detail']}", flush=True)

    if expect_error and not errored:
        raise StepFailed("the flow was expected to fail, and did not")
    if errored and not expect_error:
        first = errored[0]
        raise StepFailed(f"step {first['step']!r} failed: {first['detail']}")

    # A flow that redirects does so shortly after it reports done. Let that land
    # here rather than under whatever the next step has already navigated to.
    if not errored:
        time.sleep(1.5)
    return state["steps"]


def dismiss_progress(driver):
    driver.execute_script(
        "var m = document.getElementById('progress-modal');"
        "if (m) { m.classList.add('hidden'); }"
    )


def as_identity(runner, name):
    """Switch the client's identity, provisioning it the first time."""
    open_page(runner, "/")
    select = Select(visible(runner.driver, "#nav-identity-select"))
    if (select.first_selected_option.get_attribute("value") or "") == name:
        return
    select.select_by_value(name)
    run_flow(runner.driver)

    def is_current(d):
        # The page is reloading underneath this, so anything read from it can be
        # gone by the time it is read.
        try:
            element = d.find_element(By.CSS_SELECTOR, "#nav-identity-select")
            return Select(element).first_selected_option.get_attribute("value") == name
        except WebDriverException:
            return False

    wait(runner.driver, SHORT_WAIT).until(is_current)


def register_asset(runner, *, name, path, guardian_title, port):
    """Fill in the registration form and wait for the guardian behind it."""
    open_page(runner, "/assets/setup/")
    fill(runner.driver, "#id_name", name)
    fill(runner.driver, "#id_data_source", path)
    Select(visible(runner.driver, "#id_guardian_type")).select_by_visible_text(
        guardian_title
    )
    Select(visible(runner.driver, "#id_serve_on")).select_by_value("0.0.0.0")
    fill(runner.driver, "#id_port", port)
    click(runner.driver, "form[data-progress-url] button[type=submit]")
    run_flow(runner.driver)


def card_field(driver, name, part):
    """Read one field off the card with this title on a list page.

    Assets, wallets and issuers are all listed as the same card -- a title, a DID,
    and an Open link -- so one reader serves all three. ``part`` is "did" or
    "href"; an empty string means there is no such card.
    """
    return driver.execute_script(
        """
        var wanted = arguments[0], part = arguments[1], found = '';
        document.querySelectorAll('.card').forEach(function (card) {
            var title = card.querySelector('h3');
            if (!title || title.textContent.trim() !== wanted) { return; }
            var el = card.querySelector(part === 'did' ? '.did-display' : 'a.btn');
            if (el) {
                found = part === 'did' ? el.textContent.trim() : el.getAttribute('href');
            }
        });
        return found;
        """,
        name,
        part,
    )


def await_card_field(runner, name, part, what):
    """Wait for a card to appear on the current list page, then read a field.

    Creating a wallet or an issuer is a plain form POST, so the list comes back
    with the new card on it -- but the contract work happens first, and an
    external key authority makes two contracts before it answers.
    """
    try:
        wait(runner.driver, SHORT_WAIT * 8).until(
            lambda d: card_field(d, name, part)
        )
    except WebDriverException:
        raise StepFailed(f"no {what} card named {name!r} appeared")
    return card_field(runner.driver, name, part)


def open_from_list(runner, list_path, name, marker, what):
    """Open the detail page of something listed at ``list_path``."""
    open_page(runner, list_path)
    href = card_field(runner.driver, name, "href")
    if not href:
        raise StepFailed(f"no {what} card named {name!r}")
    runner.driver.get(runner.url(href))
    visible(runner.driver, marker)


def open_own_asset(runner, name):
    """Open the dashboard of an asset this identity owns, from the asset list."""
    open_from_list(runner, "/", name, "[data-asset-cid-url]", "owned asset")


def asset_did(driver):
    return visible(driver, "[data-asset-cid-url]").get_attribute("data-asset-did")


def create_issuer(runner, name, kind="manual"):
    """Create an issuer object from the Issuers page and return its DID."""
    open_page(runner, "/issuers/")
    click(runner.driver, "[data-modal-open=create-issuer-modal]")
    fill(runner.driver, "#issuer-name-input", name)
    click(runner.driver, f"#create-issuer-modal input[value={kind}]")
    click(runner.driver, "#create-issuer-modal button[type=submit]")
    return await_card_field(runner, name, "did", "issuer")


def open_issuer(runner, name):
    open_from_list(runner, "/issuers/", name, "[data-issuer-cid-url]", "issuer")


def create_wallet(runner, name):
    """Create a wallet from the Wallets page and return its DID."""
    open_page(runner, "/wallets/")
    click(runner.driver, "[data-modal-open=create-wallet-modal]")
    fill(runner.driver, "#wallet-name-input", name)
    click(runner.driver, "#create-wallet-modal button[type=submit]")
    return await_card_field(runner, name, "did", "wallet")


def open_wallet(runner, name):
    open_from_list(runner, "/wallets/", name, "[data-wallet-cid-url]", "wallet")


def sign_credential(runner, *, template, subject_did, claims):
    """Sign one credential from whichever signer's page is open.

    A manual issuer and a wallet present the same form -- what differs is the key
    behind it, which the server picks and the browser never sees.
    """
    click(runner.driver, "[data-modal-open=sign-credential-modal]")
    visible(runner.driver, "#sign-credential-modal .modal")
    Select(visible(runner.driver, "#sign-template-select")).select_by_value(template)
    fill(runner.driver, "#sign-subject-did", subject_did)
    set_value(runner.driver, "#sign-claims-input", json.dumps(claims, indent=2))
    before = len(alerts(runner.driver))
    click(runner.driver, "#sign-credential-form button[type=submit]")

    wait(runner.driver, SHORT_WAIT * 4).until(
        lambda d: len(alerts(d)) > before
    )
    message = alerts(runner.driver)[-1]
    if message.startswith("Error"):
        raise StepFailed(f"signing {template} failed: {message}")
    print(f"      {message}", flush=True)


def script_digest(path):
    """The digest naming a script, in the form the policy records."""
    with open(path, "rb") as f:
        return "sha256:" + hashlib.sha256(f.read()).hexdigest()


def set_policy_data(runner, data):
    """Rewrite a live policy's data from the asset dashboard."""
    set_value(runner.driver, "#policy-data-textarea", json.dumps(data, indent=2))
    before = len(alerts(runner.driver))
    click(runner.driver, "#update-policy-data-form button[type=submit]")
    wait(runner.driver, SHORT_WAIT * 4).until(lambda d: len(alerts(d)) > before)
    message = alerts(runner.driver)[-1]
    if message.startswith("Error"):
        raise StepFailed(f"updating the policy data failed: {message}")
    print(f"      {message}", flush=True)


def expose_asset(runner, *, asset, policy, policy_data, issuers):
    """Attach a policy to an owned asset and trust the issuers that policy reads.

    ``issuers`` is a list of ``(did, [credential_type, ...])``; each becomes one
    box in the expose form's trusted-issuer section.
    """
    open_own_asset(runner, asset)
    click(runner.driver, "[data-modal-open=expose-modal]")
    visible(runner.driver, "#expose-modal .modal")

    checked = runner.driver.execute_script(
        """
        var wanted = arguments[0];
        var hit = null;
        document.querySelectorAll('#id_policy_templates .checkbox-item').forEach(
            function (row) {
                var label = row.querySelector('label');
                if (label && label.textContent.trim() === wanted) {
                    hit = row.querySelector('input[name=policy_templates]');
                }
            });
        if (!hit) { return false; }
        hit.click();
        return true;
        """,
        policy,
    )
    if not checked:
        raise StepFailed(f"the expose form does not offer a policy named {policy!r}")

    set_value(runner.driver, "#id_policy_data", json.dumps(policy_data, indent=2))

    for did, types in issuers:
        click(runner.driver, "#expose-add-issuer")
        runner.driver.execute_script(
            """
            var did = arguments[0];
            var types = arguments[1];
            var boxes = document.querySelectorAll(
                '#expose-trusted-issuers .trusted-issuer-box');
            var box = boxes[boxes.length - 1];
            if (!box) { throw new Error('no trusted-issuer box was added'); }
            box.querySelector('.ti-did').value = did;
            var missing = [];
            types.forEach(function (t) {
                var hit = null;
                box.querySelectorAll('.ti-types .checkbox-item').forEach(function (row) {
                    if (row.textContent.trim() === t) { hit = row.querySelector('input'); }
                });
                if (hit) { hit.checked = true; } else { missing.push(t); }
            });
            if (missing.length) {
                throw new Error('credential types not offered: ' + missing.join(', '));
            }
            """,
            did,
            types,
        )

    click(runner.driver, "#expose-form button[type=submit]")
    run_flow(runner.driver)


def request_inference(runner, *, data_asset, roles, expect_error=False):
    """Click through the Use modal on someone else's asset.

    ``roles`` maps each role the policy declares to the name of the wallet or
    script asset that fills it; it is checked against what the modal actually
    asks for, so a policy that changed its mind about its roles fails here rather
    than somewhere less legible.
    """
    open_page(runner, "/")
    opened = runner.driver.execute_script(
        """
        var wanted = arguments[0];
        var hit = null;
        document.querySelectorAll('[data-action="open-use"]').forEach(function (btn) {
            if ((btn.dataset.assetName || '').trim() === wanted) { hit = btn; }
        });
        if (!hit) { return ''; }
        hit.click();
        return hit.dataset.actionLabel || '';
        """,
        data_asset,
    )
    if opened == "":
        raise StepFailed(
            f"no usable asset named {data_asset!r} -- it is either owned by this "
            "identity or has no guardian"
        )
    if opened != "Request Inference":
        raise StepFailed(f"expected an inference action, the button says {opened!r}")

    # The roles come from the policy, so the modal is empty until it has asked.
    wait(runner.driver, SHORT_WAIT * 2).until(
        lambda d: d.find_elements(By.CSS_SELECTOR, "#use-roles [data-role-select]")
    )
    asked = sorted(
        e.get_attribute("data-role")
        for e in runner.driver.find_elements(
            By.CSS_SELECTOR, "#use-roles [data-role-select]"
        )
    )
    if asked != sorted(roles):
        raise StepFailed(
            f"expected the policy to ask for {sorted(roles)}, it asks for {asked}"
        )

    for role, filled_by in roles.items():
        Select(visible(runner.driver, f"#use-wallet-{role}")).select_by_visible_text(
            filled_by
        )
    click(runner.driver, "#use-submit")
    steps = run_flow(runner.driver, expect_error=expect_error)

    if expect_error:
        return steps

    output = visible(runner.driver, "#use-result-output", SHORT_WAIT)
    title = runner.driver.find_element(By.CSS_SELECTOR, "#use-result-title").text
    if title != "Reported Metrics":
        raise StepFailed(f"expected metrics back, the result panel says {title!r}")
    try:
        metrics = json.loads(output.text)
    except json.JSONDecodeError:
        raise StepFailed(f"the metrics panel is not JSON: {output.text[:200]!r}")
    return metrics


# ---------------------------------------------------------------- the workflow
def run_workflow(runner):
    state = {"digest": script_digest(SCRIPT_PATH)}
    print(f"\nscript digest: {state['digest']}", flush=True)

    # -------------------------------------------------- Part 1: script owner
    runner.step(
        f"Become {SCRIPT_OWNER} (the script owner)",
        lambda: as_identity(runner, SCRIPT_OWNER),
    )
    runner.step(
        "Publish the script behind a public guardian",
        lambda: register_asset(
            runner,
            name=SCRIPT_ASSET,
            path=SCRIPT_PATH,
            guardian_title="Public",
            port=SCRIPT_PORT,
        ),
    )

    def read_script_did():
        open_own_asset(runner, SCRIPT_ASSET)
        state["script_did"] = asset_did(runner.driver)
        print(f"      script DID: {state['script_did']}", flush=True)

    runner.step("Read the script's DID", read_script_did)

    # ------------------------------------------------ Part 2: trusted issuer
    runner.step(
        f"Become {ISSUER} (the trusted issuer)",
        lambda: as_identity(runner, ISSUER),
    )

    def make_issuer():
        state["issuer_did"] = create_issuer(runner, ISSUER_NAME)
        print(f"      issuer DID: {state['issuer_did']}", flush=True)

    runner.step("Create the manual issuer object", make_issuer)

    runner.step(
        "Sign the ScriptHashCredential about the script",
        lambda: (
            open_issuer(runner, ISSUER_NAME),
            sign_credential(
                runner,
                template="ScriptHashCredential",
                subject_did=state["script_did"],
                claims={"scriptHash": state["digest"]},
            ),
        ),
    )
    runner.step(
        "Sign the IntendedDataUseCredential about the script",
        lambda: sign_credential(
            runner,
            template="IntendedDataUseCredential",
            subject_did=state["script_did"],
            claims={
                "useOnlyFor": {
                    "purposes": ["research"],
                    "diseases": [ALLOWED_DISEASE],
                }
            },
        ),
    )

    # ------------------------------------------------- Part 3: dataset owner
    runner.step(
        f"Become {DATA_OWNER} (the dataset owner)",
        lambda: as_identity(runner, DATA_OWNER),
    )
    runner.step(
        "Publish the cohort behind an inference guardian",
        lambda: register_asset(
            runner,
            name=DATA_ASSET,
            path=COHORT_PATH,
            guardian_title="Inference",
            port=GUARDIAN_PORT,
        ),
    )

    runner.step(
        "Attach the disease-scope policy and trust the issuer",
        lambda: expose_asset(
            runner,
            asset=DATA_ASSET,
            policy=DS_POLICY_NAME,
            policy_data={"allowedDiseases": [ALLOWED_DISEASE]},
            issuers=[
                (
                    state["issuer_did"],
                    ["ScriptHashCredential", "IntendedDataUseCredential"],
                )
            ],
        ),
    )

    # --------------------------------------------------- Part 4: the run
    runner.step(
        f"Become {SCRIPT_OWNER} again to request the run",
        lambda: as_identity(runner, SCRIPT_OWNER),
    )

    def run_inference():
        metrics = request_inference(
            runner, data_asset=DATA_ASSET, roles={"Script": SCRIPT_ASSET}
        )
        print(f"      metrics: {metrics}", flush=True)
        expected = os.path.getsize(COHORT_PATH)
        if metrics.get("samples") != expected:
            raise StepFailed(
                f"the FL client reported {metrics.get('samples')} bytes of data, "
                f"but the cohort is {expected} -- it did not get the real file"
            )

    runner.step("Request the inference run, and get metrics back", run_inference)

    # ------------------------------------------- the same request, refused
    runner.step(
        f"Become {DATA_OWNER} to narrow the policy",
        lambda: as_identity(runner, DATA_OWNER),
    )

    def narrow_policy():
        open_own_asset(runner, DATA_ASSET)
        set_policy_data(runner, {"allowedDiseases": [OTHER_DISEASE]})

    runner.step(
        f"Change the allowed disease to {OTHER_DISEASE}, which the script is not for",
        narrow_policy,
    )

    runner.step(
        f"Become {SCRIPT_OWNER} again",
        lambda: as_identity(runner, SCRIPT_OWNER),
    )

    def refused():
        steps = request_inference(
            runner,
            data_asset=DATA_ASSET,
            roles={"Script": SCRIPT_ASSET},
            expect_error=True,
        )
        failed = [s for s in steps if s["status"] == "error"]
        if failed[0]["step"] != "capability":
            raise StepFailed(
                "expected the refusal at the capability step, got it at "
                f"{failed[0]['step']!r}: {failed[0]['detail']}"
            )
        print(f"      refused: {failed[0]['detail'][:160]}", flush=True)
        dismiss_progress(runner.driver)

    runner.step("The same request is now refused by the policy", refused)

    # ------------------------------------------------------ and allowed again
    runner.step(
        f"Become {DATA_OWNER} to restore the policy",
        lambda: as_identity(runner, DATA_OWNER),
    )

    def restore_policy():
        open_own_asset(runner, DATA_ASSET)
        set_policy_data(runner, {"allowedDiseases": [ALLOWED_DISEASE]})

    runner.step("Put the allowed disease back", restore_policy)

    runner.step(
        f"Become {SCRIPT_OWNER} one last time",
        lambda: as_identity(runner, SCRIPT_OWNER),
    )

    def allowed_again():
        metrics = request_inference(
            runner, data_asset=DATA_ASSET, roles={"Script": SCRIPT_ASSET}
        )
        print(f"      metrics: {metrics}", flush=True)

    runner.step("The run is allowed again", allowed_again)

    # ------------------------------- approved code, and then different code
    # Everything the policy can see is in order, so it approves. What catches it
    # is the FL client measuring the code it actually received.
    runner.step(
        "Publish a second, edited script behind its own public guardian",
        lambda: register_asset(
            runner,
            name=EDITED_SCRIPT_ASSET,
            path=EDITED_SCRIPT_PATH,
            guardian_title="Public",
            port=EDITED_SCRIPT_PORT,
        ),
    )

    def read_edited_did():
        open_own_asset(runner, EDITED_SCRIPT_ASSET)
        state["edited_did"] = asset_did(runner.driver)
        edited = script_digest(EDITED_SCRIPT_PATH)
        if edited == state["digest"]:
            raise StepFailed("the edited script hashes the same as the original")
        print(f"      edited script DID: {state['edited_did']}", flush=True)
        print(f"      its real digest  : {edited}", flush=True)

    runner.step("Read the edited script's DID", read_edited_did)

    runner.step(
        f"Become {ISSUER} to vouch for the edited script",
        lambda: as_identity(runner, ISSUER),
    )
    runner.step(
        "Sign a ScriptHashCredential carrying the FIRST script's digest",
        lambda: (
            open_issuer(runner, ISSUER_NAME),
            sign_credential(
                runner,
                template="ScriptHashCredential",
                subject_did=state["edited_did"],
                claims={"scriptHash": state["digest"]},
            ),
        ),
    )
    runner.step(
        "Sign an in-scope IntendedDataUseCredential for the edited script",
        lambda: sign_credential(
            runner,
            template="IntendedDataUseCredential",
            subject_did=state["edited_did"],
            claims={
                "useOnlyFor": {
                    "purposes": ["research"],
                    "diseases": [ALLOWED_DISEASE],
                }
            },
        ),
    )

    runner.step(
        f"Become {SCRIPT_OWNER} to run the edited script",
        lambda: as_identity(runner, SCRIPT_OWNER),
    )

    def guardian_refuses():
        steps = request_inference(
            runner,
            data_asset=DATA_ASSET,
            roles={"Script": EDITED_SCRIPT_ASSET},
            expect_error=True,
        )
        by_id = {s["step"]: s for s in steps}
        if by_id.get("capability", {}).get("status") != "done":
            raise StepFailed(
                "the policy was expected to approve this one -- its evidence is in "
                f"order: {by_id.get('capability')}"
            )
        failed = [s for s in steps if s["status"] == "error"]
        if failed[0]["step"] != "metrics":
            raise StepFailed(
                "expected the refusal to come from the guardian, got it at "
                f"{failed[0]['step']!r}: {failed[0]['detail']}"
            )
        if "guardian refused" not in failed[0]["detail"]:
            raise StepFailed(f"unexpected failure reason: {failed[0]['detail']}")
        print(f"      refused: {failed[0]['detail'][:160]}", flush=True)
        dismiss_progress(runner.driver)

    runner.step(
        "The policy approves it, and the guardian refuses it on the digest",
        guardian_refuses,
    )

    run_institution_workflow(runner, state)


def run_institution_workflow(runner, state):
    """Part 5: the other policy -- who may run code here, not what it is for.

    FL-IS reads five credentials rather than two, and four of them are new here:
    an affiliation, a session key and a wallet key about the requester, and an
    ownership claim about the script. The last one is the interesting one -- the
    requester's own wallet signs it, so it is worth something only because the
    policy checks that signature against a key an authority attested for that same
    wallet. Which is what the denial at the end demonstrates: a well-formed,
    correctly signed ownership claim, made by the wrong wallet, is refused.

    Everything Part 2 set up is reused: the script, its digest, and the manual
    issuer that already vouched for the digest.
    """
    # ------------------------------- Part 5.1: the issuer the requester needs
    runner.step(
        f"Become {ISSUER} to add a session-key issuer",
        lambda: as_identity(runner, ISSUER),
    )

    def make_session_key_issuer():
        state["binding_did"] = create_issuer(
            runner, SESSION_KEY_ISSUER, kind="external_key_authority"
        )
        # Creating it also created the wallet key authority that attests a
        # wallet's ledger-registered key for it; the policy has to trust both.
        state["wallet_key_did"] = await_card_field(
            runner, f"{SESSION_KEY_ISSUER} (wallet keys)", "did", "issuer"
        )
        print(f"      session key issuer DID: {state['binding_did']}", flush=True)
        print(f"      wallet key issuer DID : {state['wallet_key_did']}", flush=True)

    runner.step(
        "Create the session-key issuer, and its wallet key authority with it",
        make_session_key_issuer,
    )

    # --------------------------------- Part 5.2: the requester's own evidence
    runner.step(
        f"Become {SCRIPT_OWNER} to set up a wallet",
        lambda: as_identity(runner, SCRIPT_OWNER),
    )

    def make_wallets():
        state["wallet_did"] = create_wallet(runner, WALLET_NAME)
        state["other_wallet_did"] = create_wallet(runner, OTHER_WALLET_NAME)
        print(f"      wallet DID      : {state['wallet_did']}", flush=True)
        print(f"      other wallet DID: {state['other_wallet_did']}", flush=True)

    runner.step("Create two wallets: the requester's, and a stranger's", make_wallets)

    runner.step(
        f"Become {ISSUER} to vouch for the requester's institution",
        lambda: as_identity(runner, ISSUER),
    )
    runner.step(
        "Sign an AffiliationCredential into the requester's wallet",
        lambda: (
            open_issuer(runner, ISSUER_NAME),
            sign_credential(
                runner,
                template="AffiliationCredential",
                subject_did=state["wallet_did"],
                claims={
                    "isMemberOf": ALLOWED_INSTITUTION,
                    "typeOfMembership": "faculty",
                },
            ),
        ),
    )

    runner.step(
        f"Become {SCRIPT_OWNER} to claim the script",
        lambda: as_identity(runner, SCRIPT_OWNER),
    )
    runner.step(
        "The wallet signs a ScriptOwnershipCredential with its own contract key",
        lambda: (
            open_wallet(runner, WALLET_NAME),
            sign_credential(
                runner,
                template="ScriptOwnershipCredential",
                subject_did=state["script_did"],
                claims={"ownedBy": state["wallet_did"]},
            ),
        ),
    )

    # ------------------------------------ Part 5.3: the second dataset owner
    runner.step(
        f"Become {DATA_OWNER} to publish a second cohort",
        lambda: as_identity(runner, DATA_OWNER),
    )
    runner.step(
        "Publish it behind its own inference guardian",
        lambda: register_asset(
            runner,
            name=PARTNER_ASSET,
            path=COHORT_PATH,
            guardian_title="Inference",
            port=PARTNER_GUARDIAN_PORT,
        ),
    )
    runner.step(
        "Attach the institution policy and trust all three issuers",
        lambda: expose_asset(
            runner,
            asset=PARTNER_ASSET,
            policy=IS_POLICY_NAME,
            policy_data={"allowedInstitutions": [ALLOWED_INSTITUTION]},
            issuers=[
                (state["issuer_did"], ["AffiliationCredential", "ScriptHashCredential"]),
                (state["binding_did"], ["publicKeyCredential"]),
                (state["wallet_key_did"], ["WalletVerifyingKeyCredential"]),
            ],
        ),
    )

    # --------------------------------------------------- Part 5.4: the run
    runner.step(
        f"Become {SCRIPT_OWNER} to request the run",
        lambda: as_identity(runner, SCRIPT_OWNER),
    )

    def run_institution_inference():
        metrics = request_inference(
            runner,
            data_asset=PARTNER_ASSET,
            roles={"User": WALLET_NAME, "Script": SCRIPT_ASSET},
        )
        print(f"      metrics: {metrics}", flush=True)
        expected = os.path.getsize(COHORT_PATH)
        if metrics.get("samples") != expected:
            raise StepFailed(
                f"the FL client reported {metrics.get('samples')} bytes of data, "
                f"but the cohort is {expected} -- it did not get the real file"
            )

    runner.step(
        "Request the run against the institution policy, and get metrics back",
        run_institution_inference,
    )

    # ------------------------- the self-issued claim, signed by another wallet
    # The stranger's wallet makes the same claim about the same script, correctly
    # signed with its own key. Nothing about it is malformed -- it just is not the
    # wallet the affiliation is about, so the chain no longer closes.
    runner.step(
        "The stranger's wallet claims the same script",
        lambda: (
            open_wallet(runner, OTHER_WALLET_NAME),
            sign_credential(
                runner,
                template="ScriptOwnershipCredential",
                subject_did=state["script_did"],
                claims={"ownedBy": state["other_wallet_did"]},
            ),
        ),
    )

    def refused_on_ownership():
        steps = request_inference(
            runner,
            data_asset=PARTNER_ASSET,
            roles={"User": WALLET_NAME, "Script": SCRIPT_ASSET},
            expect_error=True,
        )
        failed = [s for s in steps if s["status"] == "error"]
        if failed[0]["step"] != "capability":
            raise StepFailed(
                "expected the refusal at the capability step, got it at "
                f"{failed[0]['step']!r}: {failed[0]['detail']}"
            )
        print(f"      refused: {failed[0]['detail'][:160]}", flush=True)
        dismiss_progress(runner.driver)

    runner.step(
        "The same request is refused: the claim is not the requester's",
        refused_on_ownership,
    )

    runner.step(
        "The requester's own wallet claims the script again",
        lambda: (
            open_wallet(runner, WALLET_NAME),
            sign_credential(
                runner,
                template="ScriptOwnershipCredential",
                subject_did=state["script_did"],
                claims={"ownedBy": state["wallet_did"]},
            ),
        ),
    )

    def allowed_on_ownership():
        metrics = request_inference(
            runner,
            data_asset=PARTNER_ASSET,
            roles={"User": WALLET_NAME, "Script": SCRIPT_ASSET},
        )
        print(f"      metrics: {metrics}", flush=True)

    runner.step("And it is allowed again", allowed_on_ownership)


# ---------------------------------------------------------------- entry point
def build_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    # Chrome will not start as root, and a small /dev/shm makes it flaky.
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    # Filling the display it was given, so the recording is the browser and
    # nothing else.
    options.add_argument("--window-position=0,0")
    options.add_argument(f"--window-size={SCREEN[0]},{SCREEN[1]}")
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(120)
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument", {"source": ALERT_SHIM}
        )
    except WebDriverException:
        print("    (could not install the alert shim; alerts will block)", flush=True)
    return driver


def open_display(args, parser):
    """Where the browser draws, and whether that is somewhere recordable."""
    if args.headed:
        if not os.environ.get("DISPLAY"):
            parser.error("--headed needs a DISPLAY; drop it to record instead")
        return None, False
    if args.no_record:
        return None, True

    display = VirtualDisplay()
    try:
        display.start()
    except RuntimeError as error:
        print(f"Not recording: {error}", flush=True)
        return None, True
    return display, False


def main():
    global REC

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument(
        "--headed", action="store_true",
        help="watch it live on this machine's screen, and record nothing",
    )
    parser.add_argument(
        "--artifacts",
        default=os.environ.get("WEBUI_ARTIFACTS", "/tmp/pdo_webui_artifacts"),
    )
    parser.add_argument("--no-record", action="store_true", help="skip the video")
    parser.add_argument("--fps", type=int, default=int(os.environ.get("WEBUI_FPS", "10")))
    args = parser.parse_args()

    for path in (SCRIPT_PATH, EDITED_SCRIPT_PATH, COHORT_PATH):
        if not os.path.isfile(path):
            parser.error(f"missing tutorial file {path}; run tools/make_tutorial_files.sh")

    display, headless = open_display(args, parser)
    driver = build_driver(headless=headless)
    runner = Runner(driver, f"http://{args.host}:{args.port}", args.artifacts)

    video = None
    if display:
        REC = Recorder(
            driver, display, os.path.join(args.artifacts, "run.mp4"), fps=args.fps
        )
        REC.start()

    try:
        run_workflow(runner)
    finally:
        # Stopped before the browser goes: the last thing that happened should
        # be in the video rather than the moment it disappeared.
        video = REC.stop()
        driver.quit()
        if display:
            display.stop()

    if video:
        print(f"\nvideo: {video}", flush=True)
    return runner.report()


if __name__ == "__main__":
    sys.exit(main())
