// Generic "copy to clipboard" for any element with a data-copy attribute.
// Copies the attribute's value verbatim (already formatted server-side, e.g. a
// DID or a JSON-escaped credential claim). Falls back gracefully when the
// clipboard API is unavailable (e.g. a non-secure context).

(function () {
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-copy]');
        if (!btn) return;
        var text = btn.getAttribute('data-copy') || '';
        if (!navigator.clipboard) {
            window.flash('Clipboard unavailable in this browser context.', 'error');
            return;
        }
        navigator.clipboard.writeText(text).then(function () {
            window.flash('Copied to clipboard.', 'success');
        }, function () {
            window.flash('Copy failed.', 'error');
        });
    });
})();
