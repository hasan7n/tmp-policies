// Wallet dashboard: JSON-POST actions (update name, add VC). On success we
// reload the page.

(function () {
    function init() {
        var container = document.querySelector('[data-wallet-cid-url]');
        if (!container) return;
        // URL-safe contract id (server-side encoding, see app/url_safe_id.py).
        var cidUrl = container.dataset.walletCidUrl;

        // ---- Update name ----
        var updateNameForm = document.getElementById('update-name-form');
        updateNameForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            var payload = window.formToObject(updateNameForm);
            try {
                var res = await window.api.post(
                    '/api/wallets/' + cidUrl + '/update-name/', payload);
                window.flash(res.message || 'Name updated.', 'success');
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
                    '/api/wallets/' + cidUrl + '/add-vc/', { vc: vc });
                window.flash('Credential added.', 'success');
                window.location.reload();
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
