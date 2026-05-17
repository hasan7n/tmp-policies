// Assets page: clicking "Use" opens a modal pre-filled with the asset's
// DID + name. Submit posts JSON to /api/assets/use/ and renders the
// download result inline in #use-result-card.

(function () {
    function init() {
        // Open the modal and stash the clicked asset's DID/name.
        document.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-action="open-use"]');
            if (!btn) return;
            document.getElementById('use-asset-did').value = btn.dataset.assetDid || '';
            document.getElementById('use-asset-name').textContent = btn.dataset.assetName || '';
            document.getElementById('use-modal').classList.remove('hidden');
        });

        var form = document.getElementById('use-form');
        if (!form) return;
        form.addEventListener('submit', async function (e) {
            e.preventDefault();
            var payload = window.formToObject(form);
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

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
