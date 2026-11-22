for (const figure of document.querySelectorAll('[data-trace]')) {
    const buttons = [...figure.querySelectorAll('[data-signal]')];
    const parts = [...figure.querySelectorAll('[data-net], [data-stage]')].map(part => [
        part, part.dataset.net || part.dataset.stage,
    ]);
    const note = figure.querySelector('.signal-note');
    const status = figure.querySelector('.signal-status');
    const rest = note.textContent;
    const spread = figure.querySelector('button[data-spread]');
    const signals = new Map(buttons.map(button => [
        button,
        new Set((button.dataset.targets || '').split(' ')),
    ]));
    const reset = buttons.find(button => !button.dataset.signal);
    let selected = reset;
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
        const targets = signals.get(active);
        for (const [part, target] of parts) {
            part.classList.toggle('is-lit', targets.has(target));
        }
        const sentence = active.dataset.note || rest;
        if (note.textContent !== sentence) note.textContent = sentence;
    }

    function select(button) {
        selected.setAttribute('aria-pressed', 'false');
        selected = button !== selected ? button : reset;
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

    if (spread) {
        const separateLabel = spread.textContent;
        spread.addEventListener('click', () => {
            const expanded = figure.toggleAttribute('data-spread');
            spread.textContent = expanded ? spread.dataset.stackLabel : separateLabel;
        });
    }
}


for (const figure of document.querySelectorAll('[data-gateway]')) {
    const buttons = [...figure.querySelectorAll('[data-gateway-route]')];
    for (const button of buttons) {
        button.addEventListener('click', () => {
            const route = button.dataset.gatewayRoute;
            if (route) {
                figure.dataset.route = route;
            } else {
                delete figure.dataset.route;
            }
            for (const choice of buttons) {
                choice.setAttribute('aria-pressed', String(choice === button));
            }
        });
    }
}
