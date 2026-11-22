for (const figure of document.querySelectorAll('.tech-figure')) {
    const buttons = [...figure.querySelectorAll('[data-signal]')];
    const copper = [...figure.querySelectorAll('.tech-board [data-net]')];
    const note = figure.querySelector('.signal-note');
    const status = figure.querySelector('.signal-status');
    const rest = note.textContent;
    const spread = figure.querySelector('button[data-spread]');
    const spreadLabel = spread.firstElementChild;
    const separated = spreadLabel.textContent;
    const signals = new Map(buttons.map(button => [
        button,
        new Set((button.dataset.nets || '').split(' ')),
    ]));
    let selected = buttons[0];
    let keyboard;
    let hovered;
    let pointing = false;

    function draw() {
        const active = (pointing ? hovered || keyboard : keyboard || hovered) || selected;
        const signal = active.dataset.signal;
        if (signal) {
            figure.dataset.lit = signal;
        } else {
            delete figure.dataset.lit;
        }
        const nets = signals.get(active);
        for (const part of copper) {
            part.classList.toggle('is-lit', nets.has(part.dataset.net));
        }
        const sentence = active.dataset.note || rest;
        if (note.textContent !== sentence) note.textContent = sentence;
    }

    function select(button) {
        selected.setAttribute('aria-pressed', 'false');
        selected = button !== selected ? button : buttons[0];
        selected.setAttribute('aria-pressed', 'true');
        status.textContent = selected.dataset.note || rest;
        keyboard = undefined;
        hovered = undefined;
        draw();
    }

    for (const button of buttons) {
        button.addEventListener('pointerenter', event => {
            if (event.pointerType !== 'mouse') return;
            hovered = button;
            pointing = true;
            draw();
        });
        button.addEventListener('pointerleave', () => {
            hovered = undefined;
            draw();
        });
        button.addEventListener('focus', () => {
            keyboard = button.matches(':focus-visible') ? button : undefined;
            if (keyboard) pointing = false;
            draw();
        });
        button.addEventListener('blur', () => {
            keyboard = undefined;
            draw();
        });
        button.addEventListener('click', () => select(button));
    }

    spread.addEventListener('click', () => {
        const expanded = figure.toggleAttribute('data-spread');
        spreadLabel.textContent = expanded ? spread.dataset.stackLabel : separated;
    });
}
