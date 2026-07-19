// Navbar "Generate a channel_key" button: POSTs to generate the current
// user's channel key, then reloads so the navbar shows "View your channel key"
// (the view modal is populated server-side from the stored public key).

(function () {
    function init() {
        var btn = document.getElementById('generate-channel-key-btn');
        if (!btn) return;
        btn.addEventListener('click', async function () {
            btn.disabled = true;
            try {
                var res = await window.api.post('/api/channel-key/generate/', {});
                window.flash(res.message || 'Channel key generated.', 'success');
                window.location.reload();
            } catch (err) {
                btn.disabled = false;
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
