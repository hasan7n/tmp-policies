// Assets page: clicking "Use" opens a modal pre-filled with the asset's
// DID + name. Submit streams the download flow through window.progress and
// renders the decrypted result inline in #use-result-card.

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
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            var payload = window.formToObject(form);
            document.getElementById('use-modal').classList.add('hidden');
            window.progress.run('/api/assets/use/stream/', payload, {
                title: 'Using the asset…',
                onComplete: function (term) {
                    var card = document.getElementById('use-result-card');
                    var out = document.getElementById('use-result-output');
                    out.textContent = (term.result || {}).data || '';
                    card.style.display = '';
                    card.scrollIntoView({ behavior: 'smooth' });
                },
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
