let animeData = [];
let allAnimeData = [];
let searchIndex = [];

const START_YEAR = 2026;

let currentYear = START_YEAR;
let showingAllYears = false;

const animeList = document.getElementById("anime-list");
const emptyState = document.getElementById("empty-state");
const searchInput = document.getElementById("search");
const clearSearch = document.getElementById("clear-search");
const yearLabel = document.getElementById("year-label");

function encodePathPart(value) {
    return encodeURIComponent(value);
}

function escapeHtml(str = "") {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

async function readTextFile(path) {

    const response = await fetch(path);

    if (!response.ok) {
        throw new Error(path);
    }

    return response.text();
}

function parseMeta(text) {

    const meta = {};

    text.split(/\r?\n/).forEach(line => {

        const idx = line.indexOf(":");

        if (idx === -1) return;

        const key =
            line.slice(0, idx).trim();

        const value =
            line.slice(idx + 1).trim();

        meta[key] = value;
    });

    return meta;
}

async function loadYear(year) {

    showingAllYears = false;

    const allBtn =
        document.getElementById("all-years");

    if (allBtn) {
        allBtn.classList.remove("active");
    }

    searchInput.value = "";
    clearSearch.style.display = "none";

    currentYear = year;
    yearLabel.textContent = year;

    animeData = [];

    try {

        const indexText =
            await readTextFile(
                `data/${year}/meta.txt`
            );

        const folders =
            indexText
                .split(/\r?\n/)
                .map(v => v.trim())
                .filter(Boolean);

        for (const folder of folders) {

            try {

                const metaText =
                    await readTextFile(
                        `data/${year}/${encodePathPart(folder)}/meta.txt`
                    );

                animeData.push({
                    year,
                    folder,
                    meta: parseMeta(metaText)
                });

            } catch (err) {
                console.warn(err);
            }
        }

    } catch (err) {
        console.warn(err);
    }

    renderAnime(animeData);
}

async function loadStats() {
    const res = await fetch("/api/stats");
    const data = await res.json();

    console.log("Visitors:", data.visits);
}

async function loadAllAnime() {

    allAnimeData = [];

    const maxYear =
        new Date().getFullYear() + 1;

    for (
        let year = maxYear;
        year >= 2000;
        year--
    ) {

        try {

            const indexText =
                await readTextFile(
                    `data/${year}/meta.txt`
                );

            const folders =
                indexText
                    .split(/\r?\n/)
                    .map(v => v.trim())
                    .filter(Boolean);

            for (const folder of folders) {

                try {

                    const metaText =
                        await readTextFile(
                            `data/${year}/${encodePathPart(folder)}/meta.txt`
                        );

                    allAnimeData.push({
                        year,
                        folder,
                        meta: parseMeta(metaText)
                    });

                } catch {}
            }

        } catch {}
    }
}

function buildSearchIndex() {

    searchIndex = [];

    for (const anime of allAnimeData) {

        const meta =
            anime.meta || {};

        searchIndex.push({

            anime,

            searchText: [

                meta.name,
                meta.alt_name,
                meta.genre,
                meta.studio,
                meta.description,
                meta.status,
                meta.type,
                meta.released_date,
                anime.folder,
                anime.year

            ]
                .filter(Boolean)
                .join(" ")
                .toLowerCase()
        });
    }
}

function renderAnime(items) {

    animeList.innerHTML = "";

    if (!items.length) {

        emptyState.classList.remove(
            "hidden"
        );

        return;
    }

    emptyState.classList.add(
        "hidden"
    );

    for (const item of items) {

        const meta =
            item.meta || {};

        const year =
            item.year ?? currentYear;

        const card =
            document.createElement("div");

        card.className =
            "anime-card";

        card.innerHTML = `
            <div class="anime-poster">
                <img
                    src="data/${year}/${encodePathPart(item.folder)}/photo.jpg"
                    loading="lazy"
                    alt="${escapeHtml(meta.name || item.folder)}"
                >
                <div class="poster-overlay"></div>
            </div>

            <div class="anime-info">
                <div class="anime-title">
                    ${escapeHtml(meta.name || item.folder)}
                </div>

                <div class="anime-meta">
                    <span>
                        ${escapeHtml(meta.released_date || year)}
                    </span>

                    <span class="anime-status">
                        ${escapeHtml(meta.status || "")}
                    </span>
                </div>
            </div>
        `;

        card.onclick = () => {

            location.href =
                `watch.html?year=${year}&anime=${encodeURIComponent(item.folder)}`;
        };

        animeList.appendChild(card);
    }
}

function searchAnime(query) {

    query =
        query.trim().toLowerCase();

    if (!query) {

        clearSearch.style.display =
            "none";

        renderAnime(
            showingAllYears
                ? allAnimeData
                : animeData
        );

        return;
    }

    clearSearch.style.display =
        "block";

    const results =
        searchIndex
            .map(entry => {

                const anime =
                    entry.anime;

                const meta =
                    anime.meta || {};

                const name =
                    (
                        meta.name || ""
                    ).toLowerCase();

                let score = 0;

                if (name === query)
                    score += 1000;

                if (
                    name.startsWith(query)
                )
                    score += 500;

                if (
                    name.includes(query)
                )
                    score += 250;

                if (
                    entry.searchText.includes(
                        query
                    )
                )
                    score += 100;

                return {
                    anime,
                    score
                };
            })
            .filter(
                x => x.score > 0
            )
            .sort(
                (a, b) =>
                    b.score -
                    a.score
            )
            .map(
                x => x.anime
            );

    renderAnime(results);
}

function showAllYears() {

    showingAllYears = true;

    yearLabel.textContent =
        "All";

    const allBtn =
        document.getElementById(
            "all-years"
        );

    if (allBtn) {
        allBtn.classList.add(
            "active"
        );
    }

    searchInput.value = "";

    clearSearch.style.display =
        "none";

    renderAnime(allAnimeData);
}

let searchTimeout;

searchInput.addEventListener(
    "input",
    () => {

        clearTimeout(
            searchTimeout
        );

        searchTimeout =
            setTimeout(
                () =>
                    searchAnime(
                        searchInput.value
                    ),
                150
            );
    }
);

clearSearch.addEventListener(
    "click",
    () => {

        searchInput.value = "";

        clearSearch.style.display =
            "none";

        renderAnime(
            showingAllYears
                ? allAnimeData
                : animeData
        );
    }
);

document
    .getElementById(
        "previous-year"
    )
    .addEventListener(
        "click",
        () =>
            loadYear(
                currentYear - 1
            )
    );

document
    .getElementById(
        "next-year"
    )
    .addEventListener(
        "click",
        () =>
            loadYear(
                currentYear + 1
            )
    );

const allYearsBtn =
    document.getElementById(
        "all-years"
    );

if (allYearsBtn) {

    allYearsBtn.addEventListener(
        "click",
        showAllYears
    );
}

(async () => {

    await loadAllAnime();

    buildSearchIndex();

    await loadYear(
        START_YEAR
    );

    loadStats();

})();
