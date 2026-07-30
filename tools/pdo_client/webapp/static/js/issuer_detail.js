// Issuer dashboard: three JSON-POST actions (register signing context, add
// VC, sign credential). Each modal form submits via window.api.post; on
// success we either reload the page (mutating actions) or show the result
// inline (sign). "Sign Credential" only exists in the DOM for manual issuers
// (see issuers/detail.html) — an external_key_authority's sign_credential op
// does something else entirely (binds a session key to a wallet).

(function () {
    function init() {
        var container = document.querySelector('[data-issuer-cid-url]');
        if (!container) return;
        // URL-safe contract id (server-side encoding, see app/url_safe_id.py).
        var cidUrl = container.dataset.issuerCidUrl;

        // ---- Register signing context ----
        var registerForm = document.getElementById('register-issuer-form');
        registerForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            var payload = window.formToObject(registerForm);
            try {
                var res = await window.api.post(
                    '/api/issuers/' + cidUrl + '/register-signing-context/', payload);
                window.flash(res.message || 'Signing context registered.', 'success');
                window.location.reload();
            } catch (err) {
                window.flash(err.message, 'error');
            }
        });

        // ---- Add VC ----
        var addVcForm = document.getElementById('add-vc-form');
        addVcForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            var raw = (document.getElementById('vc-json-input').value || '').trim();
            if (!raw) { window.flash('VC JSON is required.', 'error'); return; }
            var vc;
            try { vc = JSON.parse(raw); }
            catch (err) { window.flash('Invalid JSON: ' + err.message, 'error'); return; }
            try {
                await window.api.post(
                    '/api/issuers/' + cidUrl + '/add-vc/', { vc: vc });
                window.flash('Credential added.', 'success');
                window.location.reload();
            } catch (err) {
                window.flash(err.message, 'error');
            }
        });

        // ---- Sign credential (manual issuers only) ----
        // The "Sign Credential" buttons on each issuer row open the modal
        // and stash the issuer's path; on submit we POST to the sign
        // endpoint and render the signed VC inline.
        var signForm = document.getElementById('sign-credential-form');
        if (!signForm) return;

        var templateSelect = document.getElementById('sign-template-select');
        var claimsTextarea = document.getElementById('sign-claims-input');
        function prefillClaims() {
            if (!templateSelect || !claimsTextarea) return;
            var opt = templateSelect.options[templateSelect.selectedIndex];
            if (!opt) return;
            try {
                var schema = JSON.parse(opt.dataset.schema || '{}');
                claimsTextarea.value = JSON.stringify(schema, null, 2);
            } catch (e) { /* leave textarea untouched */ }
        }
        if (templateSelect) templateSelect.addEventListener('change', prefillClaims);

        document.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-action="open-sign"]');
            if (!btn) return;
            document.getElementById('sign-signing-context').value = btn.dataset.path;
            document.getElementById('sign-issuer-name').textContent = btn.dataset.path;
            document.getElementById('sign-credential-modal').classList.remove('hidden');
            prefillClaims();
        });

        signForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            var raw = (document.getElementById('sign-claims-input').value || '').trim();
            var claims = {};
            if (raw) {
                try { claims = JSON.parse(raw); }
                catch (err) {
                    window.flash('Invalid claims JSON: ' + err.message, 'error');
                    return;
                }
            }
            var payload = {
                signing_context: document.getElementById('sign-signing-context').value,
                template_type: document.getElementById('sign-template-select').value,
                subject_did: document.getElementById('sign-subject-did').value.trim(),
                claims: claims,
            };
            try {
                var res = await window.api.post(
                    '/api/issuers/' + cidUrl + '/sign-credential/', payload);
                document.getElementById('sign-credential-modal').classList.add('hidden');
                window.flash(res.message || 'Credential issued.', 'success');
            } catch (err) {
                window.flash(err.message, 'error');
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
