export let selectedWords = [];
export let WORD_BANK = [];

export function setWordBank(words) {
    WORD_BANK = words;
}

export function renderWordGrid() {
    const grid = document.getElementById('word-grid');

    grid.innerHTML = WORD_BANK.map(({ word }) => {
        const isSelected = selectedWords.includes(word);
        const isDisabled = !isSelected && selectedWords.length >= 3;

        const safeWord = word.replace(/'/g, "\\'");

        return `<button
            class="word-chip ${isSelected ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}"
            onclick="toggleWord('${safeWord}')"
        >${word}</button>`;
    }).join('');
}

export function toggleWord(word) {
    if (selectedWords.includes(word)) {
        selectedWords = selectedWords.filter(w => w !== word);
    } else if (selectedWords.length < 3) {
        selectedWords.push(word);
    }

    renderWordGrid();
    renderSelected();
}

export function renderSelected() {
    const container = document.getElementById('selected-pills');
    const counter = document.getElementById('slot-counter');

    counter.textContent = `${selectedWords.length} / 3 selected`;

    if (selectedWords.length === 0) {
        container.innerHTML = '<span class="slot-empty">No words selected yet</span>';
        return;
    }

    container.innerHTML = selectedWords.map(word => {
        const safeWord = word.replace(/'/g, "\\'");
        return `
            <div class="selected-pill">
                ${word}
                <button onclick="toggleWord('${safeWord}')">✕</button>
            </div>
        `;
    }).join('');

    const submitBtn = document.getElementById('submit-btn');
    if (submitBtn) {
        submitBtn.disabled = selectedWords.length === 0;
    }
}

window.toggleWord = toggleWord;