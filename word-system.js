export let selectedWords = [];

export const WORD_BANK = [
    // Positive
    { word: "Happy",      cat: "positive" },
    { word: "Grateful",   cat: "positive" },
    { word: "Excited",    cat: "positive" },
    { word: "Hopeful",    cat: "positive" },
    { word: "Calm",       cat: "positive" },
    { word: "Motivated",  cat: "positive" },
    { word: "Content",    cat: "positive" },
    { word: "Proud",      cat: "positive" },
    { word: "Optimistic", cat: "positive" },
    { word: "Energized",  cat: "positive" },
    { word: "Connected",  cat: "positive" },
    { word: "Focused",    cat: "positive" },
    { word: "Creative",   cat: "positive" },
    { word: "Loved",      cat: "positive" },

    // Neutral
    { word: "Okay",        cat: "neutral" },
    { word: "Fine",        cat: "neutral" },
    { word: "Steady",      cat: "neutral" },
    { word: "Balanced",    cat: "neutral" },
    { word: "Normal",      cat: "neutral" },
    { word: "Neutral",     cat: "neutral" },
    { word: "Stable",      cat: "neutral" },
    { word: "Indifferent", cat: "neutral" },

    // Negative
    { word: "Anxious",     cat: "negative" },
    { word: "Sad",         cat: "negative" },
    { word: "Stressed",    cat: "negative" },
    { word: "Overwhelmed", cat: "negative" },
    { word: "Frustrated",  cat: "negative" },
    { word: "Lonely",      cat: "negative" },
    { word: "Angry",       cat: "negative" },
    { word: "Worried",     cat: "negative" },
    { word: "Tired",       cat: "negative" },
    { word: "Restless",    cat: "negative" },
    { word: "Isolated",    cat: "negative" },
    { word: "Confused",    cat: "negative" },
    { word: "Guilty",      cat: "negative" },
];

export function setActiveCategory(category) {
    // Remove selected words that don't belong to the new category
    selectedWords = selectedWords.filter(word => {
        const entry = WORD_BANK.find(w => w.word === word);
        return entry && entry.cat === category;
    });
    renderWordGrid(category);
    renderSelected();
}

export function renderWordGrid(filterCat = null) {
    const grid = document.getElementById('word-grid');
    const visible = filterCat ? WORD_BANK.filter(w => w.cat === filterCat) : WORD_BANK;

    grid.innerHTML = visible.map(({ word }) => {
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