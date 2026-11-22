(() => {
    const root = document.documentElement;
    const key = 'ddt-theme';

    try {
        const saved = localStorage.getItem(key);
        if (saved === 'light' || saved === 'dark') root.dataset.theme = saved;
    } catch {
        // Theme selection still works without storage.
    }

    root.classList.add('theme-ready');
    document.addEventListener('DOMContentLoaded', () => {
        const toggle = document.querySelector('#theme-toggle');
        const preference = window.matchMedia('(prefers-color-scheme: dark)');

        toggle.addEventListener('click', () => {
            const current = root.dataset.theme || (preference.matches ? 'dark' : 'light');
            root.dataset.theme = current === 'dark' ? 'light' : 'dark';
            try {
                localStorage.setItem(key, root.dataset.theme);
            } catch {
                // The current page keeps the selection.
            }
        });
    }, { once: true });
})();
