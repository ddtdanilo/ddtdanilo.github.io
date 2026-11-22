(() => {
    const root = document.documentElement;
    const key = 'ddt-theme';

    try {
        const saved = localStorage.getItem(key);
        if (saved === 'light' || saved === 'dark') {
            root.dataset.theme = saved;
            document.querySelector('meta[name="color-scheme"]').content = saved;
        }
    } catch {
        // Theme selection still works without storage.
    }

    root.classList.add('theme-ready', 'js');
    document.addEventListener('DOMContentLoaded', () => {
        const toggle = document.querySelector('#theme-toggle');
        toggle.addEventListener('click', () => {
            root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
            try {
                localStorage.setItem(key, root.dataset.theme);
            } catch {
                // The current page keeps the selection.
            }
        });
    }, { once: true });
})();
