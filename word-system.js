export let selectedWords = [];
let currentCategory = null;

export const WORD_BANK = [ // Good job fixing the word bank duplication, it helps fulfill SRS!
    // Good — mild positive
    { word: "Content",      cat: "good" },
    { word: "Hopeful",      cat: "good" },
    { word: "Calm",         cat: "good" },
    { word: "Grateful",     cat: "good" },
    { word: "Comfortable",  cat: "good" },
    { word: "Pleased",      cat: "good" },
    { word: "Relieved",     cat: "good" },
    { word: "Peaceful",     cat: "good" },
    { word: "Cheerful",     cat: "good" },
    { word: "Settled",      cat: "good" },
    { word: "Satisfied",    cat: "good" },
    { word: "Rested",       cat: "good" },
    { word: "Safe",         cat: "good" },
    { word: "Encouraged",   cat: "good" },
    { word: "Appreciated",  cat: "good" },

    // Great — strong positive
    { word: "Happy",        cat: "great" },
    { word: "Excited",      cat: "great" },
    { word: "Motivated",    cat: "great" },
    { word: "Energized",    cat: "great" },
    { word: "Connected",    cat: "great" },
    { word: "Focused",      cat: "great" },
    { word: "Proud",        cat: "great" },
    { word: "Optimistic",   cat: "great" },
    { word: "Creative",     cat: "great" },
    { word: "Loved",        cat: "great" },
    { word: "Confident",    cat: "great" },
    { word: "Refreshed",    cat: "great" },
    { word: "Engaged",      cat: "great" },
    { word: "Capable",      cat: "great" },
    { word: "Fulfilled",    cat: "great" },
    { word: "Uplifted",     cat: "great" },

    // Exceptional — peak positive
    { word: "Joyful",       cat: "exceptional" },
    { word: "Elated",       cat: "exceptional" },
    { word: "Thriving",     cat: "exceptional" },
    { word: "Inspired",     cat: "exceptional" },
    { word: "Empowered",    cat: "exceptional" },
    { word: "Radiant",      cat: "exceptional" },
    { word: "Vibrant",      cat: "exceptional" },
    { word: "Enthusiastic", cat: "exceptional" },
    { word: "Exhilarated",  cat: "exceptional" },
    { word: "Unstoppable",  cat: "exceptional" },
    { word: "Alive",        cat: "exceptional" },
    { word: "Blissful",     cat: "exceptional" },
    { word: "Ecstatic",     cat: "exceptional" },
    { word: "Euphoric",     cat: "exceptional" },
    { word: "Glowing",      cat: "exceptional" },
    { word: "Overjoyed",    cat: "exceptional" },


    // Neutral
    { word: "Okay",         cat: "neutral" },
    { word: "Fine",         cat: "neutral" },
    { word: "Steady",       cat: "neutral" },
    { word: "Balanced",     cat: "neutral" },
    { word: "Normal",       cat: "neutral" },
    { word: "Neutral",      cat: "neutral" },
    { word: "Stable",       cat: "neutral" },
    { word: "Indifferent",  cat: "neutral" },
    { word: "Composed",     cat: "neutral" },
    { word: "Unbothered",   cat: "neutral" },
    { word: "Present",      cat: "neutral" },
    { word: "Accepting",    cat: "neutral" },
    { word: "Even-keeled",  cat: "neutral" },
    { word: "Detached",     cat: "neutral" },
    { word: "Mellow",       cat: "neutral" },
    { word: "Passive",      cat: "neutral" },
    { word: "Measured",     cat: "neutral" },
    { word: "Unaffected",   cat: "neutral" },

    // Low — mildly negative
    { word: "Tired",        cat: "low" },
    { word: "Restless",     cat: "low" },
    { word: "Confused",     cat: "low" },
    { word: "Distracted",   cat: "low" },
    { word: "Drained",      cat: "low" },
    { word: "Unmotivated",  cat: "low" },
    { word: "Flat",         cat: "low" },
    { word: "Sluggish",     cat: "low" },
    { word: "Off",          cat: "low" },
    { word: "Bored",        cat: "low" },
    { word: "Apathetic",    cat: "low" },
    { word: "Disengaged",   cat: "low" },
    { word: "Heavy",        cat: "low" },
    { word: "Worn Out",     cat: "low" },

    // Rough — moderately negative
    { word: "Anxious",      cat: "rough" },
    { word: "Stressed",     cat: "rough" },
    { word: "Frustrated",   cat: "rough" },
    { word: "Worried",      cat: "rough" },
    { word: "Lonely",       cat: "rough" },
    { word: "Sad",          cat: "rough" },
    { word: "Tense",        cat: "rough" },
    { word: "Uneasy",       cat: "rough" },
    { word: "Irritable",    cat: "rough" },
    { word: "Overwhelmed",  cat: "rough" },
    { word: "Pressured",    cat: "rough" },
    { word: "Apprehensive", cat: "rough" },
    { word: "Melancholy",   cat: "rough" },
    { word: "Disheartened", cat: "rough" },

    // Abysmal — severely negative
    { word: "Hopeless",     cat: "abysmal" },
    { word: "Devastated",   cat: "abysmal" },
    { word: "Isolated",     cat: "abysmal" },
    { word: "Numb",         cat: "abysmal" },
    { word: "Angry",        cat: "abysmal" },
    { word: "Guilty",       cat: "abysmal" },
    { word: "Ashamed",      cat: "abysmal" },
    { word: "Defeated",     cat: "abysmal" },
    { word: "Empty",        cat: "abysmal" },
    { word: "Trapped",      cat: "abysmal" },
    { word: "Broken",       cat: "abysmal" },
    { word: "Helpless",     cat: "abysmal" },
    { word: "Lost",         cat: "abysmal" },
    { word: "Anguished",    cat: "abysmal" },
];

// kysen code review: This function updates state, filters selected words, AND triggers two renders.
// Consider splitting into setCategory(category) for state + a separate filterSelectedToCategory().
export function setActiveCategory(category) {
    currentCategory = category;
    selectedWords = selectedWords.filter(word => {
        const entry = WORD_BANK.find(w => w.word === word);
        return entry && entry.cat === category;
    });
    renderWordGrid();
    renderSelected();
}

export function renderWordGrid() {
    const grid = document.getElementById('word-grid');
    const visible = currentCategory ? WORD_BANK.filter(w => w.cat === currentCategory) : WORD_BANK;

    // This is good but I think some error handling would be nice in case something goes wrong
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

// kysen code review: toggleWord handles both state mutation and triggering re-renders.
// Separating the state update from the render call would make each easier to test independently.
export function toggleWord(word) {
    if (selectedWords.includes(word)) {
        selectedWords = selectedWords.filter(w => w !== word);
    } else if (selectedWords.length < 3) {
        selectedWords.push(word);
    }

    renderWordGrid();
    renderSelected();
}

// kysen code review: renderSelected renders the pill list AND updates the submit button state.
// The button enable/disable logic is a separate concern — consider extracting updateSubmitButton().
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