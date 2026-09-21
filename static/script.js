let years = [];
let currentYear = null;
let showingAllYears = true;
let requestId = 0;
let searchController;

const animeList = document.getElementById("anime-list");
const emptyState = document.getElementById("empty-state");
const loadingState = document.getElementById("loading-state");
const searchInput = document.getElementById("search");
const clearSearch = document.getElementById("clear-search");
const yearLabel = document.getElementById("year-label");
const allYearsBtn = document.getElementById("all-years");
const previousYearBtn = document.getElementById("previous-year");
const nextYearBtn = document.getElementById("next-year");
const library = document.getElementById("library");
const resultCount = document.getElementById("result-count");

function escapeHtml(value = "") {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}

function imageWithFallback(item) {
    const img = document.createElement("img");
    img.loading = "lazy";
    img.decoding = "async";
    img.alt = item.name || item.folder;
    img.src = item.poster;
    img.onerror = () => {
        if (!img.dataset.fallback) {
            img.dataset.fallback = "1";
            img.src = item.poster_fallback;
        }
    };
    return img;
}

function render(items, search = "") {
    animeList.replaceChildren();
    loadingState.classList.add("hidden");
    emptyState.classList.toggle("hidden", items.length > 0);

    const fragment = document.createDocumentFragment();
    for (const item of items) {
        const card = document.createElement("a");
        card.className = "anime-card";
        card.href = `/watch?year=${encodeURIComponent(item.year)}&anime=${encodeURIComponent(item.folder)}`;

        const poster = document.createElement("div");
        poster.className = "anime-poster";
        poster.appendChild(imageWithFallback(item));
        const overlay = document.createElement("div");
        overlay.className = "poster-overlay";
        poster.appendChild(overlay);

        const info = document.createElement("div");
        info.className = "anime-info";
        info.innerHTML = `
            <div class="anime-title">${escapeHtml(item.name || item.folder)}</div>
            <div class="anime-meta">
                <span>${escapeHtml(String(item.released_date || item.year))}</span>
                <span class="anime-status">${escapeHtml(item.status || "")}</span>
            </div>`;

        card.append(poster, info);
        fragment.appendChild(card);
    }
    animeList.appendChild(fragment);
    const label = search.trim() ? ` for “${search.trim()}”` : "";
    resultCount.textContent = `${items.length} ${items.length === 1 ? "anime" : "anime"} found${label}`;
}

async function fetchJson(url, signal) {
    const response = await fetch(url, { signal, headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
}

async function loadYears() {
    const data = await fetchJson("/api/years");
    years = Array.isArray(data.years) ? data.years : [];
    if (!years.length) throw new Error("No years found");
    currentYear = years.includes(new Date().getFullYear()) ? new Date().getFullYear() : years[0];
    updateYearControls();
}

function updateYearControls() {
    yearLabel.textContent = showingAllYears ? "All" : (currentYear ?? "—");
    allYearsBtn.classList.toggle("active", showingAllYears);
    previousYearBtn.disabled = years.indexOf(currentYear) >= years.length - 1;
    nextYearBtn.disabled = years.indexOf(currentYear) <= 0;
}

function requestedYear(search = "") {
    // Searches deliberately span the complete catalogue, even while browsing a year.
    return (search.trim() || showingAllYears) ? null : currentYear;
}

async function loadAnime(year = currentYear, search = "") {
    const localId = ++requestId;
    searchController?.abort();
    searchController = new AbortController();
    loadingState.classList.remove("hidden");
    emptyState.classList.add("hidden");
    resultCount.textContent = search.trim() ? `Searching for “${search.trim()}”…` : "Loading anime…";
    const params = new URLSearchParams();
    if (year !== null) params.set("year", String(year));
    if (search.trim()) params.set("search", search.trim());

    try {
        const data = await fetchJson(`/api/anime?${params.toString()}`, searchController.signal);
        if (localId !== requestId) return;
        render(Array.isArray(data.items) ? data.items : [], search);
    } catch (error) {
        if (error.name === "AbortError" || localId !== requestId) return;
        console.error(error);
        loadingState.classList.add("hidden");
        animeList.replaceChildren();
        emptyState.classList.remove("hidden");
        emptyState.querySelector("h3").textContent = "Bee couldn't load the library";
        emptyState.querySelector("p").textContent = "Check that FastAPI is running and try again.";
    }
}

let searchTimer;
searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    const value = searchInput.value;
    clearSearch.style.display = value ? "block" : "none";
    searchTimer = setTimeout(() => {
        loadAnime(requestedYear(value), value).then(() => {
            if (value.trim() && value === searchInput.value) {
                library.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        });
    }, 220);
});

clearSearch.addEventListener("click", () => {
    clearTimeout(searchTimer);
    searchInput.value = "";
    clearSearch.style.display = "none";
    loadAnime(requestedYear());
    searchInput.focus();
});

searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && searchInput.value) clearSearch.click();
    if (event.key === "Enter") {
        clearTimeout(searchTimer);
        const value = searchInput.value;
        loadAnime(requestedYear(value), value).then(() => {
            library.scrollIntoView({ behavior: "smooth", block: "start" });
        });
    }
});

allYearsBtn.addEventListener("click", () => {
    showingAllYears = !showingAllYears;
    updateYearControls();
    loadAnime(requestedYear(searchInput.value), searchInput.value);
});

previousYearBtn.addEventListener("click", () => {
    const index = years.indexOf(currentYear);
    if (index < years.length - 1) {
        showingAllYears = false;
        currentYear = years[index + 1];
        updateYearControls();
        loadAnime(requestedYear(searchInput.value), searchInput.value);
    }
});

nextYearBtn.addEventListener("click", () => {
    const index = years.indexOf(currentYear);
    if (index > 0) {
        showingAllYears = false;
        currentYear = years[index - 1];
        updateYearControls();
        loadAnime(requestedYear(searchInput.value), searchInput.value);
    }
});

(async () => {
    try {
        await loadYears();
        await loadAnime(null);
    } catch (error) {
        console.error(error);
        loadingState.classList.add("hidden");
        emptyState.classList.remove("hidden");
        emptyState.querySelector("h3").textContent = "Beeha is empty";
        emptyState.querySelector("p").textContent = "Add anime with generate.py, then refresh this page.";
    }
})();
