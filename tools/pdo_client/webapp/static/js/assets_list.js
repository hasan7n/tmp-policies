// Assets page: clicking "Use" opens a modal pre-filled with the asset's
// DID + name. Submit streams the download flow through window.progress and
// shows the decrypted result in its own popup (#use-result-modal).

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
            window.progress.run('/api/assets/use/stream/', payload, {
                title: 'Using the asset…',
                onComplete: function (term) {
                    // The progress modal has done its job once the flow
                    // completes — dismiss it instead of leaving it sitting
                    // on screen, and show the decrypted data in its own modal.
                    document.getElementById('progress-modal').classList.add('hidden');
                    document.getElementById('use-result-output').textContent =
                        (term.result || {}).data || '';
                    document.getElementById('use-result-modal').classList.remove('hidden');
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
