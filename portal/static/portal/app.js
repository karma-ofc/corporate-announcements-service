"use strict";

const searchInput = document.querySelector("#announcement-search");
const results = document.querySelector("#announcement-results");
const emptyMessage = document.querySelector("#search-empty");

if (searchInput && results && emptyMessage) {
    const cards = Array.from(results.querySelectorAll(".announcement-card"));

    searchInput.addEventListener("input", () => {
        const query = searchInput.value.trim().toLocaleLowerCase("ru");
        let visibleCount = 0;

        for (const card of cards) {
            const matches = card.textContent
                .toLocaleLowerCase("ru")
                .includes(query);
            card.hidden = !matches;
            visibleCount += Number(matches);
        }

        emptyMessage.hidden = visibleCount > 0;
    });
}
