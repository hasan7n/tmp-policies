# DUO policies (Rego) for the `rego_policy_agent` contract

Each DUO is one Rego module plus a human-readable `README.md`. A data owner
selects one or more DUOs when exposing an asset; the webapp creates a
`rego_policy_agent` contract and provisions the selected modules into it with
`set_rego_policy` (as `[ [ duo_id, rego_source ], ... ]`). The contract evaluates
each selected module and combines the results.

## Folders

| DUO            | Folder       | Requires                                   |
|----------------|--------------|--------------------------------------------|
| DUO_0000022 GS | [`gs/`](gs/) | LocationCredential, publicKeyCredential    |
| DUO_0000028 IS | [`is/`](is/) | AffiliationCredential, publicKeyCredential |

Every DUO additionally requires a **publicKeyCredential** whose claim `key` is
the requester's channel public key; the module returns that key as the merged
context so the `rego_token` can hand it to the guardian.

## The contract <-> Rego contract

Every module is package `subpolicy` and exposes the two rules the
`rego_policy_agent` evaluates, each in its own regorus engine (lowest peak
memory; also why the identical package/rule names never collide).

**`data.subpolicy.requirements`** — evaluated by `set_rego_policy` with **no
input**, so it must be static. The roles and credential types this module needs:

```json
{ "User": ["LocationCredential", "publicKeyCredential"] }
```

**`data.subpolicy.result`** — evaluated by `issue_policy_credential` over the
input the contract builds:

```json
{
  "presentations": {
    "<role>": [
      { "type": "<CredentialType>", "issuer": "<did>", "subject": "<did>",
        "claims": { ... }, "index": <int> }
    ]
  },
  "trusted_issuers": { ... },
  "policy_data": { ... }
}
```

and produces:

```json
{
  "decision": true,
  "verification_tasks": [ { "index": <int> } ],
  "operation": { "name": "do_download", "parameters": { "channel_key": "<requester public key>" } }
}
```

- Presentations arrive as `{ role: VerifiablePresentation }`; the contract
  flattens each role's credentials into the array above and assigns each a global
  `index`. A `verification_task` references that index so the contract verifies
  the exact VC's signature against the registered trusted issuer.
- `decision` is a boolean. When several DUOs are selected the contract allows
  only if **every** module allowed, verifies the union of the flagged
  credentials (a failed signature forces a deny), and merges the operations.
- `operation` is `{ "name": <operation>, "parameters": { ... } }`; it is merged
  across modules and becomes the claims of the issued `policy_decision`
  credential. The `rego_token` parses it to build the guardian capability: `name`
  is the guardian operation to invoke (`do_download`) and `parameters` (the
  `channel_key`) are forwarded to it.

## Tests

```bash
./run_tests.sh        # runs `opa test` on each DUO folder independently
```

Each folder is tested on its own because all modules share package `subpolicy`;
compiling them together would be a redefinition conflict (which is exactly why
the contract isolates them per engine).
