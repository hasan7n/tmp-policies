# End-to-End Tutorial: Policy-Gated Data Sharing

This guide walks you through the **entire flow by hand in the web UI**. By the end, a **data user** will download a file that a **data owner** published, but only because the data user holds credentials — issued by a trusted **VC issuer** — that satisfy the owner's policy.

---

## The story

Imagine a dataset its owner is happy to share — but only with the right people. Rather than vetting each requester by hand, the owner attaches **rules** to the data and lets the system enforce them automatically.

Three people take part:

- A **trusted issuer** who can vouch for people (think of a university registrar or an identity provider).
- A **data owner** who publishes the dataset behind those rules.
- A **data user** who wants the data and asks the issuer to vouch for them.

### The rules on this asset

In this tutorial the owner attaches **two rules** to the dataset, and **both** must hold for a download to go through:

1. **Where you are (geographic rule):** the requester must be located in an **allowed country** — we'll allow the **US**.
2. **Who you're with (institution rule):** the requester must belong to an **allowed institution** — we'll allow a sample **`did:example:university`**.

### What you'll do, end to end

1. **The user** sets up a wallet and generates a personal channel key. Think of the wallet as the container that will hold verifiable credentials of the user. The channel key is needed to recieve the dataset at the end; it is used to establish a secure encrypted channel between the user and the asset guardian holding the dataset.
2. **The issuer** vouches for the user by signing three credentials: a credential claiming that the user is in a certain location (US), a credential claiming that the user belongs to a certain institution (did:example:university)m and a credential claiming that the user owns a certain channel key. **Important**: the signed credentials alone don't unlock access to the dataset. The policy object protecting the dataset will unlock access to the dataset only if the credentials contain suitable claims AND if the credentials are signed (i.e. vouched by) an issuer trusted by this policy object.
3. **The owner** publishes the dataset — starts a **guardian** to hold the data file, attaches the two rules, and declares that it trusts the issuer.
4. **The user** requests the data file. The rules are checked automatically; because the user qualifies, the file comes back encrypted for their channel key and is decrypted for them on screen.

Everything below is just these steps, in detail.

---

## The cast (three roles, one browser)

Everything runs against a single client identity at a time. You "become" each role by switching the identity in the navbar. The three roles are:

| Role | What they do |
|------|--------------|
| **`vc_issuer`** | A trusted authority. Vouches for the user by signing credentials (public key, location, affiliation). |
| **`data_owner`** | Owns the data. Publishes it behind a guardian and a set of rules, and decides which issuers to trust. |
| **`data_user`** | Wants the data. Presents their credentials, and if the rules are satisfied, downloads and decrypts the file. |

> **🔁 "Switch identity" callout** — Whenever you see this, use the **Identity dropdown at the top-right of the navbar** and pick the username. The page reloads as that identity and returns you to the home page.

### A few words you'll meet

- **Wallet** — your personal container for signing keys and credentials; owners, issuers, and users each have wallets. It has a unique id (a **DID**) like `did:pdo:…`.
- **Signing context** — a labeled signing key an issuer signs with (e.g. `poc`), written as `did:pdo:…#poc`.
- **Credential** — a signed statement about someone (e.g. "this person is in the US").
- **Channel key** — a personal key pair the *user* generates. Data is encrypted to the **public** half; only the user's **private** half can open it.
- **Guardian** — a service that holds the actual data file and hands it out (encrypted) only once a request has been approved.
- **Policy** — the owner's rules, enforced automatically. When a user asks for the data, the policy checks their credentials and, if they qualify, approves download.

---

## Part 0 — Start the WebUI

Open this repository in a **GitHub Codespace** (green **Code** button → **Create codespace**). The devcontainer automatically brings up the ledger, services, registries, and the webapp, and creates the tutorial data file for you. The first start pulls several images, so give it a few minutes — progress shows in the Codespaces log.

When it's ready, open the forwarded **port 8000** (the **Ports** tab) to reach the WebUI, then follow the steps below.

---

## Part 1 — Data user: create a wallet and a channel key

We start with the user because the issuer (Part 2) needs two things from the user before it can issue credentials: the user's **wallet DID** (who the credential is about) and the user's **channel public key** (what goes inside the public-key credential).

> **🔁 Switch identity to `data_user`.**

### 1.1 Create the user's wallet

1. Go to **Wallets** (navbar) → **+ Create Wallet**.
2. Name it `user_wallet` → **Create**.

*What's happening:* this creates the user's **wallet** — their identity on the policy engine, and the place their credentials will live.

### 1.2 Copy the wallet's DID

1. On the Wallets page, click **Open** on `user_wallet`.
2. Under **Wallet Info**, click **Copy** next to the **DID**.

> 📋 **Keep this as `USER_DID` in your notes.** The issuer uses it as the *Subject DID* of every credential it signs for the user.

### 1.3 Generate the channel key

1. In the **top-right of the navbar**, click **Generate a channel_key**.
2. The button changes to **View your channel key**. Click it, then click **Copy**.

> 📋 **Keep this as `USER_PUBLIC_KEY`** (paste it into your notes). You'll paste it into a credential's `key` field in Part 2.3.

*What's happening:* the app generated an RSA key pair for `data_user` and stored it locally. Only the **public** key is shown; the **private** key stays on disk and is used later to decrypt the download. The public key is the same key that goes into the user's public-key credential (next part), so the guardian encrypts the data using this public key so that only the private key holder (the user) can actually decrypt and see the downloaded data.

---

## Part 2 — VC issuer: set up and issue the user's credentials

The issuer is the authority the owner will trust. It signs three credentials about `data_user`, each proving something the policy cares about.

> **🔁 Switch identity to `vc_issuer`.**

### 2.1 Create the issuer's wallet

1. **Wallets** → **+ Create Wallet** → name it `issuer_wallet` → **Create**.
2. Click **Open** on it, then click **Copy** next to its **DID**.

*What's happening:* the issuer now has its own **wallet**. The wallet, as we discussed before, can be used to as a container to store a user credentials. But also, the wallet plays another crucial role: it holds signing keys so that the wallet owner (in this case, the vc_issuer) can issue credentials by signing them. Anything it signs can be traced back to it and checked for authenticity.

### 2.2 Register a signing context

1. On `issuer_wallet` → **Signing Contexts** → **+ Register Signing Context**.
2. Name: `poc`. Description: anything (e.g. `poc issuer`). → **Register**.
3. In the new `poc` row, click **Copy** — this copies the full context id `ISSUER_DID#poc`. **Keep it as `ISSUER_CONTEXT_DID`** in your notes. You will configure the owner at a later step to trust this issuer (i.e., only accept credentials signed by this issuer using this `poc` signing context)

*What's happening:* `poc` is a named signing key inside the issuer's wallet. Every credential below is signed with it, and it's identified to the world as `ISSUER_DID#poc`.

### 2.3 Issue the **publicKeyCredential** (the channel key)

1. In the **Signing Contexts** table, on the `poc` row click **Sign Credential**.
2. Fill the modal:
   - **Credential Template:** `publicKeyCredential`
   - **Subject DID:** The `USER_DID` that you kept in your notes (from step 1.2)
   - **Claims:**

     ```json
     { "key": "USER_PUBLIC_KEY" }
     ```

     Paste your copied key from step 1.3 in place of `USER_PUBLIC_KEY` (between the quotes).
3. Click **Sign & Issue** — the credential is signed and stored in the data user's wallet automatically.

*What's happening:* the issuer is attesting "the subject `USER_DID` controls this public key". This key will later travel to the asset guardian through the capability package, so that the guardian will encrypt the data to exactly this key.

### 2.4 Issue the **LocationCredential**

1. `poc` row → **Sign Credential**.
2. Fill:
   - **Credential Template:** `LocationCredential`
   - **Subject DID:** The `USER_DID` that you kept in your notes (from step 1.2)
   - **Claims:**

     ```json
     {
       "locatedAt": {
         "street": "1 Main",
         "zipCode": "00000",
         "state": "MA",
         "country": "US"
       }
     }
     ```

3. **Sign & Issue** — stored in the data user's wallet automatically.

*What's happening:* this attests the subject's country is **US** — which must be in the owner's allowed-country list for the geographic policy (GS) to pass.

### 2.5 Issue the **AffiliationCredential**

1. `poc` row → **Sign Credential**.
2. Fill:
   - **Credential Template:** `AffiliationCredential`
   - **Subject DID:** The `USER_DID` that you kept in your notes (from step 1.2)
   - **Claims:**

     ```json
     {
       "isMemberOf": "did:example:university",
       "typeOfMembership": "member"
     }
     ```

3. **Sign & Issue** — stored in the user's wallet automatically.

*What's happening:* this attests the subject belongs to `did:example:university` — which must be in the owner's allowed-institution list for the institution policy (IS) to pass.

All three credentials are now in `data_user`'s wallet. (Switch to `data_user` and open `user_wallet` if you want to see them under **Stored Credentials**.)

**Important**: the signed credentials alone don't unlock access to the dataset. The policy object protecting the dataset will unlock access to the dataset only if the credentials contain suitable claims AND if the credentials are signed (i.e. vouched by) an issuer trusted by this policy object. You will, acting as the data owner, setup the policy object in the next step.

---

## Part 3 — Data owner: publish the data behind a policy

Now the owner puts data on offer, stands up a guardian for it, and defines the rules for who may download it.

> **🔁 Switch identity to `data_owner`.**

### 3.0 The data file

For the tutorial's sake, the dataset is a single small file. **It is already created for you at `/tmp/asset_data.txt`** — you don't need to create anything.

### 3.1 Register the asset (and start its guardian)

1. Go to **Assets** (navbar) → **+ Register Asset**.
2. **Name:** `data1`. **Data Path:** `/tmp/asset_data.txt` → **Register Asset**.
3. Registration takes a few seconds — the app is also starting a **guardian** for the data and waiting for it to come up.

*What's happening:* registering the asset also starts a **guardian** that serves `/tmp/asset_data.txt` (encrypting each response to the requester's channel key). Open `data1` and you'll see *"Your asset is behind the guardian running on http://‹host›:‹port›."* The asset still needs a policy before anyone can use it — that's next.

### 3.2 Expose the asset behind the policy

1. Still on `data1`, click **Expose** → the **Expose Asset** modal opens.
2. Under **Policies**, check **GS** and **IS**. (Use **View** to read what each does.)
3. The **Policy Data** box auto-fills with the merged schema. Replace it with real values:

   ```json
   {
     "allowedCountries": ["US"],
     "allowedInstitutions": ["did:example:university"]
   }
   ```

4. Click **Create Policy & Expose**.

*What's happening:* this attaches the **policy** to the asset — the two rules plus the allowed values you entered — so every future request is checked automatically. The geographic rule asks for a location in an allowed country **plus** the user's channel key; the institution rule asks for membership in an allowed institution **plus** the channel key — and both must describe the **same person**.

### 3.3 Trust the issuer

The policy knows the *rules* but not yet *whose signatures to believe*.

1. On the (now exposed) `data1` dashboard → **Trusted Issuers** → **+ Register Issuer**.
2. **Issuer DID:** paste `ISSUER_CONTEXT_DID` from step 2.2 (it's `ISSUER_DID#poc`).
3. Check **all three** credential types: `publicKeyCredential`, `LocationCredential`, `AffiliationCredential`.
4. Click **Register**.

*What's happening:* you're telling the **policy** "credentials of these types, signed by `ISSUER_DID#poc`, are trustworthy." Without this, the user's credentials would be present but rejected as coming from an unknown source.

The asset is now fully published: data behind a guardian, gated by a policy that trusts the issuer.

---

## Part 4 — Data user: use the asset

Finally, the user requests the data.

> **🔁 Switch identity to `data_user`.**

1. Go to **Assets**. The `data1` card now shows an enabled **Use** button.
2. Click **Use** → in the modal, select **`user_wallet`** → **Request Download**.
3. After a moment, the **Decrypted Data** panel appears showing:

   ```
   The eagle lands at midnight.
   ```

*What's happening* (the whole handshake, end to end):

1. The app gathers the user's credentials (channel key, location, affiliation) into a single request.
2. The **policy** checks that each credential is signed by the trusted issuer and that both rules pass — and since the same person satisfies both, it **approves** the request and issues a capability package containing the user's channel key.
3. That capability package goes to the **guardian**, which encrypts the file to the user's channel key and returns it.
4. The app decrypts it with `data_user`'s **private** channel key and shows you the data.

---

## What you just built

```
vc_issuer  ──signs──►  3 credentials (channel key · location · affiliation)
                              │ stored in
                              ▼
data_user's wallet  ──presents──►  Policy (geographic + institution rules)
                                        │ trusts vc_issuer
                                        │ checks the rules
                                        ▼
                                    capability ──────────►  guardian
                                                             │ encrypts the file to
                                                             │ data_user's channel key
                                                             ▼
data_user  ◄── decrypt with private channel key ──────  encrypted file
```

The owner never saw the user's credentials by hand, the guardian never had to judge the rules itself, and the data only ever left the guardian encrypted to a key only the compliant user holds.

---

## Troubleshooting

- **Use button is disabled** — the asset isn't behind a guardian. The guardian is started while you register the asset (Part 3.1); if it failed to come up, registration would have reported an error — re-register the asset.
- **"You need to generate a channel key…"** on download — do Part 1.3 as `data_user`.
- **Download fails / decrypts to garbage** — the `publicKeyCredential` in the user's wallet must carry the *same* channel key the user currently holds. If you regenerated the channel key after issuing the credential, re-issue the public-key credential (Part 2.3) with the new key.
- **Policy denies the download** — check that `LocationCredential.country` and `AffiliationCredential.isMemberOf` exactly match the owner's `allowedCountries` and `allowedInstitutions`, and that the issuer is trusted for all three types (Part 3.3).
- **Guardian unreachable** — the guardian is started when you register the asset; if downloads fail, check that it's running and see the guardian deploy log.
