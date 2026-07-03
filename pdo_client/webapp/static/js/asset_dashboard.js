// Asset dashboard: drives four interactions depending on whether the
// asset has been exposed yet.
//   * No policy → Expose modal (HTML form, server redirects back here).
//   * Has policy → Use modal (JSON), Register Trusted Issuer modal (JSON
//     with multi-select credential types), and an inline Policy Data
//     editor that PUTs through set_policy_data.

(function () {
    function init() {
        var container = document.querySelector('[data-asset-cid-url]');
        if (!container) return;
        // URL-safe contract id (server-side encoding, see app/url_safe_id.py).
        var cidUrl = container.dataset.assetCidUrl;

        // ---- Expose: merge policy_data schema from the selected policies ----
        // Multiple policies can be chosen; each becomes a Rego subpolicy. The
        // policy_data textarea is prefilled with the union of the checked
        // policies' data schemas (e.g. allowedCountries + allowedInstitutions).
        var policyChecks = document.querySelectorAll('input[name="policy_templates"]');
        var policyDataTextarea = document.getElementById('id_policy_data');
        if (policyChecks.length && policyDataTextarea) {
            function mergeSchemas() {
                var merged = {};
                policyChecks.forEach(function (cb) {
                    if (!cb.checked) return;
                    try {
                        Object.assign(merged, JSON.parse(cb.dataset.schema || '{}'));
                    } catch (e) { /* skip malformed schema */ }
                });
                policyDataTextarea.value = JSON.stringify(merged, null, 2);
            }
            policyChecks.forEach(function (cb) {
                cb.addEventListener('change', mergeSchemas);
            });
            mergeSchemas();
        }

        // ---- Expose: "View" a policy's rego source + README in a popup ----
        var detailsEl = document.getElementById('policy-details-data');
        var policyDetails = detailsEl ? JSON.parse(detailsEl.textContent) : {};
        document.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-action="view-policy"]');
            if (!btn) return;
            var d = policyDetails[btn.dataset.policyId];
            if (!d) return;
            document.getElementById('policy-detail-title').textContent =
                (d.name || 'Policy') + ' policy';
            document.getElementById('policy-detail-readme').textContent =
                d.readme || '(no README)';
            document.getElementById('policy-detail-rego').textContent =
                d.rego_source || '(no rego source)';
            document.getElementById('policy-detail-modal').classList.remove('hidden');
        });

        // ---- Expose: dynamic "trusted issuers" boxes ----
        // Each box collects an issuer DID + chosen credential types. On submit
        // they're serialized into a hidden field the expose view reads.
        var addIssuerBtn = document.getElementById('expose-add-issuer');
        var issuersContainer = document.getElementById('expose-trusted-issuers');
        var issuersHidden = document.getElementById('expose-trusted-issuers-json');
        var exposeForm = document.getElementById('expose-form');
        if (addIssuerBtn && issuersContainer && issuersHidden && exposeForm) {
            var ctEl = document.getElementById('expose-credential-types-data');
            var credentialTypes = ctEl ? JSON.parse(ctEl.textContent) : [];

            function addIssuerBox() {
                var box = document.createElement('div');
                box.className = 'trusted-issuer-box';
                box.style.cssText =
                    'border:1px solid #ddd;border-radius:4px;padding:0.5rem;margin-bottom:0.5rem';

                var row = document.createElement('div');
                row.style.cssText = 'display:flex;align-items:center;gap:0.5rem';
                var did = document.createElement('input');
                did.type = 'text';
                did.className = 'ti-did';
                did.placeholder = 'did:pdo:<contract_id>#<signing_context>';
                did.style.flex = '1';
                var del = document.createElement('button');
                del.type = 'button';
                del.className = 'btn btn-sm';
                del.title = 'Remove';
                del.textContent = '🗑';
                del.addEventListener('click', function () { box.remove(); });
                row.appendChild(did);
                row.appendChild(del);
                box.appendChild(row);

                var types = document.createElement('div');
                types.className = 'ti-types checkbox-list';
                types.style.marginTop = '0.5rem';
                if (!credentialTypes.length) {
                    types.innerHTML =
                        '<p style="color:#999;margin:0">No credential templates available.</p>';
                } else {
                    credentialTypes.forEach(function (t) {
                        var label = document.createElement('label');
                        label.className = 'checkbox-item';
                        var cb = document.createElement('input');
                        cb.type = 'checkbox';
                        cb.value = t;
                        var span = document.createElement('span');
                        span.textContent = t;
                        label.appendChild(cb);
                        label.appendChild(span);
                        types.appendChild(label);
                    });
                }
                box.appendChild(types);
                issuersContainer.appendChild(box);
            }

            addIssuerBtn.addEventListener('click', addIssuerBox);

            // Serialize the boxes just before the native form submit.
            exposeForm.addEventListener('submit', function () {
                var out = [];
                issuersContainer
                    .querySelectorAll('.trusted-issuer-box')
                    .forEach(function (box) {
                        var d = (box.querySelector('.ti-did').value || '').trim();
                        var chosen = Array.from(
                            box.querySelectorAll('.ti-types input:checked')
                        ).map(function (cb) { return cb.value; });
                        if (d && chosen.length) {
                            out.push({ did: d, credential_types: chosen });
                        }
                    });
                issuersHidden.value = JSON.stringify(out);
            });
        }

        // ---- Use: POST to /api/assets/use/, render result inline ----
        var useForm = document.getElementById('use-form');
        if (useForm) {
            useForm.addEventListener('submit', async function (e) {
                e.preventDefault();
                var payload = window.formToObject(useForm);
                try {
                    var res = await window.api.post('/api/assets/use/', payload);
                    document.getElementById('use-modal').classList.add('hidden');
                    var card = document.getElementById('use-result-card');
                    var out = document.getElementById('use-result-output');
                    out.textContent = res.data;
                    card.style.display = '';
                    card.scrollIntoView({ behavior: 'smooth' });
                    window.flash('Data downloaded and decrypted.', 'success');
                } catch (err) {
                    window.flash(err.message, 'error');
                }
            });
        }

        // ---- Register policy trusted issuer (checkbox credential types) ----
        var registerForm = document.getElementById('register-policy-issuer-form');
        if (registerForm) {
            registerForm.addEventListener('submit', async function (e) {
                e.preventDefault();
                var credentialTypes = Array.from(
                    registerForm.querySelectorAll(
                        'input[name="credential_types"]:checked'
                    )
                ).map(function (cb) { return cb.value; });
                if (credentialTypes.length === 0) {
                    window.flash('Select at least one credential type.', 'error');
                    return;
                }
                var payload = {
                    issuer_did: document.getElementById('rpi-issuer-did').value.trim(),
                    credential_types: credentialTypes,
                };
                try {
                    var res = await window.api.post(
                        '/api/assets/' + cidUrl + '/register-policy-issuer/',
                        payload
                    );
                    window.flash(res.message || 'Issuer registered.', 'success');
                    window.location.reload();
                } catch (err) {
                    window.flash(err.message, 'error');
                }
            });
        }

        // ---- Update policy data ----
        var policyDataForm = document.getElementById('update-policy-data-form');
        if (policyDataForm) {
            policyDataForm.addEventListener('submit', async function (e) {
                e.preventDefault();
                var raw = (document.getElementById('policy-data-textarea').value || '').trim();
                var policyData;
                try {
                    policyData = raw ? JSON.parse(raw) : {};
                } catch (err) {
                    window.flash('Invalid JSON: ' + err.message, 'error');
                    return;
                }
                if (typeof policyData !== 'object' || Array.isArray(policyData)) {
                    window.flash('Policy data must be a JSON object.', 'error');
                    return;
                }
                try {
                    var res = await window.api.post(
                        '/api/assets/' + cidUrl + '/update-policy-data/',
                        { policy_data: policyData }
                    );
                    window.flash(res.message || 'Policy data updated.', 'success');
                } catch (err) {
                    window.flash(err.message, 'error');
                }
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
