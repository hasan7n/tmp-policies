# End-to-End Tutorial: A Policy-Gated Inference Example

This tutorial walks you through the **entire flow using a web UI**. By the end of this tutorial, a **Script Owner** runs their code on a dataset they never see. The dataset never leaves the **Guardian** that holds it; the code travels to the data instead, and only metrics come back. The **Dataset Owner** has registered specific policies (i.e., rules) about **what code is allowed to run** on their dataset.

If you have not done the [download tutorial](tutorial.md) yet, do that one first. It introduces wallets, issuer objects, credentials and policies with a simpler flow. This tutorial assumes those terms.

---

## The story

A hospital holds a patient cohort it is not willing to hand out to anyone, under any policy. Copies cannot be recalled. But it is willing to let approved code run *inside its own environment* and release aggregate results.

That changes the question a policy has to answer. A download policy asks **who is asking**. An inference policy also has to ask **what is going to run**, because approving a requester says nothing about the code they bring.

Three personas participate in this tutorial:

- A **Trusted Issuer** who vouches for code (e.g., a data access committee, a code review board, a CI system that signs builds).
- A **Dataset Owner** who publishes the dataset behind those policies (e.g., a hospital, a biobank).
- A **Script Owner** who wants to run their analysis against the dataset (e.g., a researcher).

### The policies in this tutorial

There are two, and each is a complete lesson on its own. Parts 1–4 do the first; Part 5 does the second, on a second dataset, reusing everything you already set up.

| | Policy | The question it answers |
| --- | --- | --- |
| Parts 1–4 | **FL-DS** — disease-specific research | *what is this code for?* |
| Part 5 | **FL-IS** — institution-specific restriction | *who is running it, and do they stand behind it?* |

### The first policy: what is the code for?

**The script must be declared for an allowed disease (i.e., disease-scope rule):** the code that is about to run must carry a declaration of what it is for, and that declared disease scope must overlap the owner's **allowed diseases** — in this tutorial **`MONDO:0005148`** (type 2 diabetes mellitus).

That rule is carried by **two** credentials, and both must be about **the same script**:

| Credential | What it says about the script |
| --- | --- |
| `IntendedDataUseCredential` | the diseases this code is declared for |
| `ScriptHashCredential` | the digest identifying this code |

The digest is the part that makes the declaration mean anything. Without it, an in-scope declaration attached to one script could be presented alongside a completely different piece of code.

### What you'll do in this tutorial

1. The **Script Owner** publishes their script as its own asset, behind a **public guardian** — code that will be judged has to be code anyone can fetch and check.
2. The **Trusted Issuer** signs two credentials **about that script**: its digest, and the disease scope it is declared for.
3. The **Dataset Owner** publishes the dataset — starts an **inference guardian** that holds it, attaches the disease-scope policy, and declares that it trusts the issuer object for those two credential types.
4. The **Script Owner** requests the run. The policy approves, and the digest it approved travels with the capability to an **FL server**, then to the **FL client** running next to the guardian. That client measures the script it actually received and presents that measurement when it redeems the capability. The guardian releases the data only if the two digests agree. Metrics come back; the data does not.
5. Then, in **Part 5**, a second dataset with the **other** policy: the **Script Owner** gets a wallet, proves which institution they belong to, and signs — with their own wallet — a claim that the script is theirs.

---

## The Cast: 3 Roles

Everything runs against a single client identity at a time. This means you change roles by switching the identity in the navbar. The 3 roles are:

| Role | What they do |
| ------ | -------------- |
| **`data_user`** | is the **Script Owner**. They publish the script as an asset, and later ask for the run. In Part 5 they also get a **wallet**, which is where credentials *about them* live and which signs their claim over the script. |
| **`vc_issuer`** | is the **Trusted Issuer**. They create one issuer object and hand-sign two credentials *about the script*: its digest and its declared disease scope. In Part 5 they add a second issuer object and vouch for the requester's institution. |
| **`data_owner`** | is the **Dataset Owner**. They put the cohort behind an inference guardian, attach the policy, and decide which issuer objects to trust. |

> **🔁 "Switch identity" callout** — Whenever you see this, use the **Identity dropdown at the top-right of the navbar** and pick the username. The page reloads as that identity and returns you to the home page.

!!! note "Useful terminologies"

    - **Guardian** — the service standing in front of an asset. This tutorial uses two kinds:
        - **Public** — hands the file to anyone who asks, with no policy at all. The script lives behind one of these, because the whole point of a script is that everyone can read the code being judged.
        - **Inference** — never hands the data out. It releases it only to an FL client on its own host, and only against a capability naming the digest of the code about to run.
    - **Script asset** — a script registered as an asset. It has its own identity (a DID), and the credentials *about the code* live on it, exactly as a person's credentials live in their wallet. Its DID is also how the runner finds the public guardian to fetch the code from — one identity settles both.
    - **Digest** — `sha256:<hex>` over the script's bytes. The policy approves a digest; the FL client re-computes it from the code it actually holds.
    - **FL server** — the job board. The webapp submits `{script, capability}` to it; FL clients poll it for work. It knows nothing about PDO.
    - **FL client** — runs next to the guardian, inside the data holder's environment. It is the party that turns a *claim* about code into a *fact* about code.

---

## Part 0 — Start the demo app

### Running in cloud via GitHub Codespaces

You can launch a preinstalled [Codespace](https://github.com/features/codespaces) cloud environment by clicking this button:

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/hasan7n/tmp-policies?ref=main){ target="_blank" rel="noopener" }

The devcontainer automatically brings up the policy engine, registries, the FL server and the webapp, and creates the tutorial files for you. The first start pulls several images, so give it a few minutes — progress shows in the Codespaces log.

When it finishes, click the forwarded **port 8000** (in the **Ports** tab) to open the webapp. Hover the forwarded address and click the globe icon to open it in a browser. Then follow the steps below.

![The Ports tab listing PDO WebUI on port 8000, with the globe icon that opens the forwarded address in a browser.](assets/images/codespace_ports.png)

### The two files this tutorial uses

Both are **already created for you** — you don't need to write anything:

| File | What it is |
| --- | --- |
| `/tmp/patient_cohort.csv` | the dataset. It stays behind the inference guardian and is never handed out. |
| `/tmp/inference_script.py` | the script. It computes a cohort summary and prints aggregate metrics. |

The startup log also printed the script's digest. If you missed it, get it back with:

```bash
echo "sha256:$(sha256sum /tmp/inference_script.py | awk '{print $1}')"
```

> 📋 **Keep this as `SCRIPT_DIGEST` in your notes.**

---

## Part 1 — Script Owner: publish the script

We start with the **Script Owner**, because everything the issuer signs in Part 2 is *about the script* and needs its identity first.

> **🔁 Switch identity to `data_user`.**

### 1.1 Register the script as an asset

1. Go to **Assets** (navbar) → **+ Register Asset**.
2. Fill the form:
      - **Name:** `cohort_summary_script`
      - **Data Path:** `/tmp/inference_script.py`
      - **Guardian Type:** **Public**
      - **Serve On:** leave as `0.0.0.0`
      - **Port:** `7910`
3. Click **Register Asset**.

### 1.2 Copy the script's DID

1. Back on **Assets**, click **Open** on `cohort_summary_script`.
2. Under **Asset Info**, copy the **DID**.

> 📋 **Keep this as `SCRIPT_DID` in your notes.** The issuer uses it as the *Subject DID* of both credentials it signs in Part 2, and the runner uses it in Part 4 to fetch the code.

*What's happening in the background:* a script that is going to be judged has to be **nameable** and **fetchable**. Registering it as an asset gives it both: an identity contract (so credentials can be about it, and presented from it) and a public guardian its bytes can be pulled from. The dashboard shows *"Your asset is behind a **public** guardian running on http://‹host›:7910"* — that URL is where the code is fetched from later, and there is deliberately no policy on it.

---

## Part 2 — Trusted Issuer: vouch for the script

> **🔁 Switch identity to `vc_issuer`.**

### 2.1 Create the issuer object

1. Go to **Issuers** (navbar) → **+ Create Issuer**.
2. **Name:** e.g. `code review board`. **Issuer Type:** **Manual**. → **Create**.
3. Open it and click **Copy** next to its **DID**.

> 📋 **Keep this as `ISSUER_DID` in your notes.** You'll use it in Part 3.2, to tell the Dataset Owner to trust it.

### 2.2 Issue the **ScriptHashCredential**

1. On the issuer object's page click **Sign Credential**.
2. Fill the modal:
      - **Credential Template:** `ScriptHashCredential`
      - **Subject DID:** the `SCRIPT_DID` from step 1.2
      - **Claims:**

        ```json
        {
          "scriptHash": "sha256:PASTE_YOUR_SCRIPT_DIGEST_HERE"
        }
        ```

        Use the `SCRIPT_DIGEST` you kept in Part 0 — including the `sha256:` prefix.

3. Click **Sign & Issue**.

*What's happening in the background:* this pins the identity of the code. Everything else in this tutorial is an assertion *about a digest*; this credential is what ties that digest to a named script.

### 2.3 Issue the **IntendedDataUseCredential**

1. On the issuer object's page → **Sign Credential**.
2. Fill:
      - **Credential Template:** `IntendedDataUseCredential`
      - **Subject DID:** the same `SCRIPT_DID`
      - **Claims:**

        ```json
        {
          "useOnlyFor": {
            "purposes": ["research"],
            "diseases": ["MONDO:0005148"]
          }
        }
        ```

3. **Sign & Issue**.

*What's happening in the background:* this attests **what the code is for** — here, type 2 diabetes research. Note the subject: the declaration is attached to the *script*, not to the person asking. When the data never moves, the thing whose purpose matters is the thing that runs.

Both credentials are now stored on the script asset. (Switch to `data_user`, open `cohort_summary_script`, and you can see them under **Stored Credentials**.)

**Important**: these signed credentials alone don't unlock anything. The policy will accept them only if the claims fit **and** the credentials were signed by an issuer object that policy trusts. The Dataset Owner decides that next.

---

## Part 3 — Dataset Owner: publish the cohort behind the policy

> **🔁 Switch identity to `data_owner`.**

### 3.1 Register the dataset (and start its inference guardian)

1. Go to **Assets** (navbar) → **+ Register Asset**.
2. Fill the form:
      - **Name:** `patient_cohort`
      - **Data Path:** `/tmp/patient_cohort.csv`
      - **Guardian Type:** **Inference**
      - **Serve On:** leave as `0.0.0.0`
      - **Port:** `7900`
3. Click **Register Asset**. This takes longer than a public guardian — the app is starting a container that brings up a storage service, the guardian core, and the FL client that sits beside it, and waits for all of it to answer.

*What's happening:* registering the asset starts an **inference guardian** on `/tmp/patient_cohort.csv`. Unlike the download guardian, it has no operation that hands the file to a remote caller at all. Its one capability handler, `do_inference`, releases the data over loopback to the FL client bundled with it — and only when the digest that client reports matches the one the capability authorizes.

### 3.2 Expose the dataset behind the policy

1. Still on `patient_cohort`, click **Expose** → the **Expose Asset** modal opens.
2. Under **Policies**, check **FL-INFERENCE-DISEASE-SPECIFIC-RESEARCH**. (Use **View** to read the policy card and its Rego source.)
3. The **Policy Data** box auto-fills with the schema. Replace it with real values:

    ```json
    {
      "allowedDiseases": ["MONDO:0005148"]
    }
    ```

4. Under **Trusted Issuers**, click **+ Add a trusted issuer** **once**:
      - paste `ISSUER_DID` from step 2.1 into the DID field
      - check **`ScriptHashCredential`** and **`IntendedDataUseCredential`**
5. Click **Create Policy & Expose**.

*What's happening:* this attaches the policy to the asset — the rule, the allowed disease codes you entered, and **which issuer objects it trusts, for which credential types**. Without trusting `ISSUER_DID`, the script's credentials would be present but rejected as coming from an unknown source. And if you put a different code in `allowedDiseases`, the request will be denied, since the script in this tutorial is declared for `MONDO:0005148`.

The dataset is now published: data behind an inference guardian, gated by a policy about the code.

---

## Part 4 — Script Owner: request the run

> **🔁 Switch identity to `data_user`.**

1. Go to **Assets**. The `patient_cohort` card now shows an enabled **Use** button.
2. Click **Use** → the modal asks for one role, **Script** (this policy has no `User` role — it asks nothing about the requester). Select **`cohort_summary_script`** under **Scripts**.
3. Click **Request Inference**.
4. Watch the steps go by, then the **Reported Metrics** panel appears showing:

    ```json
    {
      "accuracy": 0.42,
      "loss": 1.23,
      "samples": 295,
      "client_id": "..."
    }
    ```

    (The FL client in this demo reports fixed numbers rather than really executing the script; `samples` is the size in bytes of the cohort it was handed. What is real is everything up to that point — the approval, the digest check, and the release.)

*What's happening in the background* (the whole handshake, end to end):

1. The app resolves `SCRIPT_DID` through the asset registry to the script's public guardian and **fetches the code**.
2. The **policy** is asked to judge. It reads the two credentials presented from the script's identity, checks each was signed by a trusted issuer object, checks the declared diseases overlap `allowedDiseases`, and checks both credentials name the same script. It approves, and issues a **capability** for the `do_inference` operation carrying the **approved digest**.
3. The app submits `{script, capability}` to the **FL server** as a job. It never contacts the guardian itself.
4. The **FL client** beside the guardian claims the job, **hashes the script it received**, and posts the capability to the guardian core over loopback with that measurement attached.
5. The **guardian core** compares the digest the capability authorized against the digest the client computed. They match, so it releases the cohort — to a process on its own host, over loopback.
6. The client runs the script over the data and reports **metrics** to the FL server. The app picks them up and shows them to you.

The dataset never left the guardian's host. Nobody but the guardian ever held it.

---

## Try it the other way: watch a denial

The interesting part of a policy is what it refuses. Two one-line changes, each showing a different half of the rule.

### The declared purpose is out of scope

As `data_owner`, open `patient_cohort`, and in the **Policy Data** box change the allowed code to something the script is not declared for:

```json
{
  "allowedDiseases": ["MONDO:0005015"]
}
```

Click **Update**. Now switch to `data_user` and request the run again — it fails at **Creating the inference capability**. The script's declaration no longer overlaps what the owner allows, so no capability is ever issued and the guardian is never even contacted.

Set it back to `MONDO:0005148` to make it pass again.

### The code is not the code that was approved

A second script is already waiting for this at **`/tmp/inference_script_v2.py`** — the same analysis with one comment line added, so it hashes to something else.

1. As `data_user`, register it exactly as in Part 1: **Name** `cohort_summary_script_v2`, **Data Path** `/tmp/inference_script_v2.py`, **Guardian Type** **Public**, **Port** `7911`. Copy its DID.
2. As `vc_issuer`, sign **two** credentials about *that* DID: an `IntendedDataUseCredential` with the same in-scope disease, and a `ScriptHashCredential` carrying the **first** script's digest — the one you kept as `SCRIPT_DIGEST`.
3. As `data_user`, request inference again, picking `cohort_summary_script_v2` for the **Script** role.

The policy **approves**. From where it sits nothing is wrong: both credentials are signed by a trusted issuer, the declared disease is in scope, and both name the same script. **Creating the inference capability** succeeds and the job is submitted.

The run fails one step later, at **Waiting for the FL client to report** — because the FL client hashed the code it actually received, the guardian compared that against the digest the capability authorized, and refused to release the cohort. `/tmp/pdo_fl_server.log` and the guardian's log show the refusal.

That is the point of the design: credentials about code prove nothing about the code that runs unless something re-measures it at the moment the data is released.

---

## Part 5 — The other policy: who is allowed to run it

Everything so far judged the **code**. The dataset owner in Parts 1–4 never asked who was asking. A different owner might not care what the code is for, but very much care **who** brought it — and want that person on record as standing behind it.

That is **FL-IS**. It reads five credentials instead of two, across the two roles:

| Role | Credential | What it says |
| --- | --- | --- |
| **User** | `AffiliationCredential` | which institution the requester belongs to |
| **User** | `publicKeyCredential` | the requester's session key, so results can reach them |
| **User** | `WalletVerifyingKeyCredential` | which key the requester's wallet is registered with on the ledger |
| **Script** | `ScriptHashCredential` | the digest identifying the code (the same one from Part 2) |
| **Script** | `ScriptOwnershipCredential` | a wallet's claim that the script is **its** script |

Four of those come from issuer objects. The fifth — the ownership claim — is signed by the requester's **own wallet**, which is the interesting part of this policy. On its own, "this script is mine" is worth nothing: anyone can say it about anything. It becomes evidence because the policy checks that signature against the key in the `WalletVerifyingKeyCredential`, which *is* from an authority. So the chain is: an authority says *this wallet holds this key*, the wallet uses that key to say *this script is mine*, and an issuer says *this wallet belongs to that institution*. All three must be about one wallet, and the ownership claim must be about the same script the digest names.

We will publish a **second** cohort behind the new policy, so the first one keeps working and you can compare them side by side.

### 5.1 Trusted Issuer: add a session-key issuer

> **🔁 Switch identity to `vc_issuer`.**

1. Go to **Issuers** → **+ Create Issuer**.
2. **Name:** `session keys`. **Issuer Type:** **Session Key**. → **Create**.
3. Back on the list you now have **two** new cards: `session keys` (*External Key Authority*) and `session keys (wallet keys)` (*Wallet Key Authority*). **Copy DID** from each.

> 📋 **Keep these as `BINDING_DID` and `WALLET_KEY_DID` in your notes.**

*What's happening in the background:* creating a session-key issuer creates two objects, because two different facts have to be attested. The **wallet key authority** reads a wallet's ledger record and certifies which verifying key that wallet is registered with — that is the `WalletVerifyingKeyCredential`, and it is what makes the wallet's own signature checkable later. The **external key authority** then uses that credential to bind a fresh session key to the wallet and issue a `publicKeyCredential` for it, automatically, at request time. Neither has a "Sign Credential" button; there is nothing to do with them by hand.

### 5.2 Script Owner: get a wallet and claim the script

> **🔁 Switch identity to `data_user`.**

1. Go to **Wallets** (navbar) → **+ Create Wallet**. **Name:** `researcher_wallet` → **Create**.
2. **Copy DID** from the new card.

> 📋 **Keep this as `WALLET_DID` in your notes.**

Now have the wallet claim the script:

3. Click **Open** on `researcher_wallet`, then **Sign Credential**.
4. Fill the modal:
      - **Credential Template:** `ScriptOwnershipCredential`
      - **Subject DID:** the `SCRIPT_DID` from step 1.2 — the claim is *about the script*
      - **Claims:**

        ```json
        {
          "ownedBy": "PASTE_YOUR_WALLET_DID_HERE"
        }
        ```

5. Click **Sign & Issue**. The credential is stored on the **script asset**, next to the `ScriptHashCredential` from Part 2 — both are facts about the script, so both travel as the **Script** role.

*What's happening in the background:* a wallet cannot issue a credential the way an issuer object does — signing *from a signing context* is what makes something an authority, and a wallet is not one. What every contract does have is the key pair PDO generated for it at creation, whose public half the ledger records in the contract's metadata. That is the key this signature uses, and it is exactly the key the wallet key authority will certify when the run is requested. Signed with anything else, the policy would have nothing to check the claim against.

### 5.3 Trusted Issuer: vouch for the requester's institution

> **🔁 Switch identity to `vc_issuer`.**

1. Open the `code review board` issuer object from Part 2 → **Sign Credential**.
2. Fill:
      - **Credential Template:** `AffiliationCredential`
      - **Subject DID:** the `WALLET_DID` from step 5.2 — this one is about the *person*, so it goes to their wallet
      - **Claims:**

        ```json
        {
          "isMemberOf": "did:example:best_university",
          "typeOfMembership": "faculty"
        }
        ```

3. **Sign & Issue**.

### 5.4 Dataset Owner: publish a second cohort behind FL-IS

> **🔁 Switch identity to `data_owner`.**

1. **Assets** → **+ Register Asset**:
      - **Name:** `partner_cohort`
      - **Data Path:** `/tmp/patient_cohort.csv` (the same file; a second guardian, its own policy)
      - **Guardian Type:** **Inference**
      - **Serve On:** `0.0.0.0`
      - **Port:** `7902`
2. **Register Asset**, then **Open** it and click **Expose**.
3. Under **Policies**, check **FL-INFERENCE-INSTITUTION-SPECIFIC-RESTRICTION**.
4. **Policy Data:**

    ```json
    {
      "allowedInstitutions": ["did:example:best_university"]
    }
    ```

5. Under **Trusted Issuers**, click **+ Add a trusted issuer** **three times**:
      - **First box:** `ISSUER_DID` (step 2.1) — check **`AffiliationCredential`** and **`ScriptHashCredential`**
      - **Second box:** `BINDING_DID` (step 5.1) — check **`publicKeyCredential`**
      - **Third box:** `WALLET_KEY_DID` (step 5.1) — check **`WalletVerifyingKeyCredential`**
6. Click **Create Policy & Expose**.

Note what is *not* in that list: the requester's wallet. It never becomes a trusted issuer, and it does not need to be — the policy hands its key to the contract along with the credential, and the check happens against that key directly.

### 5.5 Script Owner: request the run

> **🔁 Switch identity to `data_user`.**

1. **Assets** → **Use** on `partner_cohort`.
2. This time the modal asks for **two** roles:
      - **Script** → `cohort_summary_script` (under **Scripts**)
      - **User** → `researcher_wallet` (under **Wallets**)
3. **Request Inference**. Metrics come back exactly as before.

*What's happening in the background:* the app notices the policy wants a `publicKeyCredential` and the wallet has none, so it asks the trusted session-key issuer for one — which first gets a `WalletVerifyingKeyCredential` for the wallet from the wallet key authority, then binds a fresh session key. Both land in the wallet. The policy then reads all five credentials, checks the four issued ones against their trusted issuers, checks the ownership claim against the wallet key it was just handed, checks that affiliation, session key, wallet key and ownership all name **one** wallet and that the ownership claim and the digest name **one** script — and only then issues the capability.

### Try it the other way: someone else's claim

The ownership credential is the only piece here that is not backed by an authority, so it is the one worth attacking.

1. As `data_user`, create a second wallet: **Wallets** → **+ Create Wallet**, **Name** `outsider_wallet`. Copy its DID.
2. Open it → **Sign Credential** → `ScriptOwnershipCredential`, **Subject DID** = `SCRIPT_DID`, claims `{"ownedBy": "<the outsider wallet's DID>"}`. **Sign & Issue** — this replaces the ownership claim stored on the script.
3. Request the run again with **Script** → `cohort_summary_script` and **User** → `researcher_wallet`.

It fails at **Creating the inference capability**. Nothing about the new credential is malformed: it is a correctly signed claim, and it verifies against the key of the wallet that made it. It just is not the wallet the affiliation is about, so the chain does not close and no capability is issued.

Sign the ownership credential again from `researcher_wallet` (step 5.2) and the run passes once more.

---

## End of Tutorial: What you just built

```text
issuer object ──signs──►  ScriptHashCredential       (digest)
              ──signs──►  IntendedDataUseCredential  (declared diseases)
                          │ both stored on
                          ▼
                          the script asset  ──published by──► public guardian
                          │ presented as the "Script" role      (anyone can fetch the code)
                          ▼
                          Policy (disease-scope rule)
                          │ trusts the issuer object
                          │ checks the claims, and that both name one script
                          ▼
                     capability { do_inference, script_digest }
                          │ submitted with the code
                          ▼
                       FL server  ──job──►  FL client (on the guardian's host)
                                             │ re-hashes the code it received
                                             ▼
                                            inference guardian
                                             │ releases the data ONLY if
                                             │ measured digest == approved digest
                                             ▼
data_user  ◄──────── metrics ────────  the run, on the owner's host
```

The **Dataset Owner** never reviewed the requester, the **Guardian** never evaluated the policy, the **Policy** never saw the data, and the dataset never moved. What crossed the boundary was a digest on the way in and a handful of numbers on the way out.

And in Part 5, the same machinery answering a different question:

```text
issuer object       ──signs──►  AffiliationCredential          (institution)
wallet key authority──signs──►  WalletVerifyingKeyCredential   (this wallet's key)
session key issuer  ──signs──►  publicKeyCredential            (a fresh session key)
                                │ all three stored in
                                ▼
                                researcher_wallet  ── the "User" role
                                │ signs, with the very key
                                │ the authority just certified
                                ▼
issuer object ──signs──►  ScriptHashCredential  ──┐
                          ScriptOwnershipCredential │ both stored on
                                                    ▼
                                the script asset  ── the "Script" role
                                                    │
                                                    ▼
                          Policy (institution rule)
                          │ trusts three issuer objects — and NOT the wallet
                          │ checks the wallet's own claim against the certified key
                          │ checks one wallet and one script throughout
                          ▼
                     capability { do_inference, script_digest, channel_key }
```

The wallet is never an authority. It gets to assert something about itself only because someone else, independently, put its key on the record.

---
