// Asset dashboard: drives four interactions depending on whether the
// asset has been exposed yet.
//   * No policy → Expose modal (HTML form, server redirects back here).
//   * Has policy → Use modal (JSON), Register Trusted Issuer modal (JSON
//     with multi-select credential types), and an inline Policy Data
//     editor that PUTs through set_policy_data.

(function () {
    function init() {
        var container = document.querySelector('[data-asset-pk]');
        if (!container) return;
        var assetPk = container.dataset.assetPk;

        // ---- Expose: prefill policy_data from selected template's schema ----
        var templateSelect = document.getElementById('id_policy_template');
        var policyDataTextarea = document.getElementById('id_policy_data');
        if (templateSelect && policyDataTextarea) {
            function prefill() {
                var opt = templateSelect.options[templateSelect.selectedIndex];
                if (!opt) return;
                try {
                    var schema = JSON.parse(opt.dataset.schema || '{}');
                    policyDataTextarea.value = JSON.stringify(schema, null, 2);
                } catch (e) { /* leave textarea untouched */ }
            }
            templateSelect.addEventListener('change', prefill);
            prefill();
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
                    out.textContent = JSON.stringify(
                        { output_file: res.output_file, issued_vc: res.issued_vc },
                        null, 2);
                    card.style.display = '';
                    card.scrollIntoView({ behavior: 'smooth' });
                    window.flash('Downloaded to ' + res.output_file, 'success');
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
                        '/api/assets/' + assetPk + '/register-policy-issuer/',
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
                        '/api/assets/' + assetPk + '/update-policy-data/',
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
