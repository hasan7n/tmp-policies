// Asset dashboard: drives three interactions depending on whether the
// asset has been exposed yet.
//   * No policy → Expose modal posts as a regular HTML form (server
//     redirects back here on success).
//   * Has policy → Use modal (JSON) and Register Trusted Issuer modal
//     (JSON). Both reload the page on success.

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

        // ---- Register policy trusted issuer (JSON) ----
        var registerForm = document.getElementById('register-policy-issuer-form');
        if (registerForm) {
            registerForm.addEventListener('submit', async function (e) {
                e.preventDefault();
                var payload = window.formToObject(registerForm);
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
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
