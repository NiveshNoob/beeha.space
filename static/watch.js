const params = new URLSearchParams(window.location.search);
const year = params.get("year");
const animeFolder = params.get("anime");
const requestedEpisode = Math.max(1, Number.parseInt(params.get("episode") || "1", 10) || 1);

const title = document.getElementById("title");
const status = document.getElementById("status");
const release = document.getElementById("release");
const cover = document.getElementById("cover");
const backgroundCover = document.getElementById("background-cover");
const anilist = document.getElementById("anilist");
const episodeCount = document.getElementById("episode-count");
const episodeHeadingCount = document.getElementById("episode-heading-count");
const episodeGrid = document.getElementById("episode-grid");
const episodeError = document.getElementById("episode-error");
const watchFirst = document.getElementById("watch-first");
const playerControls = document.getElementById("player-controls");
const previousEpisode = document.getElementById("previous-episode");
const nextEpisode = document.getElementById("next-episode");
const reportEpisode = document.getElementById("report-episode");
const playingEpisode = document.getElementById("playing-episode");

let anime = null;
let activeEpisode = null;

function setImageWithFallback(img, primary, fallback) {
    img.src = primary;
    img.onerror = () => {
        if (!img.dataset.fallback) {
            img.dataset.fallback = "1";
            img.src = fallback;
        }
    };
}

async function loadAnime() {
    if (!year || !animeFolder) throw new Error("Invalid anime URL.");
    const endpoint = `/api/anime/${encodeURIComponent(year)}/${encodeURIComponent(animeFolder)}`;
    const response = await fetch(endpoint, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`Anime request failed: ${response.status}`);
    anime = await response.json();

    title.textContent = anime.name || anime.folder;
    document.title = `${anime.name || anime.folder} • Beeha`;
    status.textContent = anime.status || "Unknown";
    release.textContent = anime.released_date || year;
    setImageWithFallback(cover, anime.poster, anime.poster_fallback);
    setImageWithFallback(backgroundCover, anime.poster, anime.poster_fallback);

    if (anime.anilist_link) {
        anilist.href = anime.anilist_link;
        anilist.style.display = "inline-flex";
    } else {
        anilist.style.display = "none";
    }

    const episodes = Array.isArray(anime.episodes) ? anime.episodes : [];
    const total = Number(anime.total_episodes) || episodes.length;
    episodeCount.textContent = `${total} episode${total === 1 ? "" : "s"}`;
    episodeHeadingCount.textContent = `${total} episode${total === 1 ? "" : "s"}`;

    renderEpisodes(episodes, total);

    const firstEpisode = episodes.find((item) => Number(item.episode) === 1);
    watchFirst.disabled = !firstEpisode || !(firstEpisode.server1 || firstEpisode.server2);
    watchFirst.onclick = () => firstEpisode && openEpisode(firstEpisode.episode);

}

function renderEpisodes(episodes, total) {
    episodeGrid.replaceChildren();
    const fragment = document.createDocumentFragment();

    for (let number = 1; number <= total; number += 1) {
        const data = episodes.find((item) => Number(item.episode) === number);
        const button = document.createElement("button");
        button.type = "button";
        button.className = "episode-btn";
        button.dataset.episode = String(number);
        button.disabled = !data || !(data.server1 || data.server2);
        button.innerHTML = `
            <span class="episode-number">${number}</span>
            <span class="episode-name">Episode ${number}</span>`;
        if (number === requestedEpisode) button.classList.add("selected");
        button.addEventListener("click", () => openEpisode(number));
        fragment.appendChild(button);
    }
    episodeGrid.appendChild(fragment);
}

function openEpisode(number, updateUrl = true) {
    const data = anime?.episodes?.find((item) => Number(item.episode) === Number(number));
    if (!data) return;

    const playerUrl = data.server1 || data.server2;
    if (!playerUrl) return;

    const watchUrl = `/watch?year=${encodeURIComponent(year)}&anime=${encodeURIComponent(animeFolder)}&episode=${encodeURIComponent(number)}`;
    if (updateUrl) {
        history.replaceState({}, "", watchUrl);
    }

    document.querySelectorAll(".episode-btn.selected").forEach((button) => button.classList.remove("selected"));
    document.querySelector(`.episode-btn[data-episode="${number}"]`)?.classList.add("selected");
    activeEpisode = Number(number);
    updatePlayerControls();
    window.open(playerUrl, "_blank", "noopener");
}

function playableEpisodes() {
    return (anime?.episodes || [])
        .filter((item) => item.server1 || item.server2)
        .map((item) => Number(item.episode))
        .sort((a, b) => a - b);
}

function updatePlayerControls() {
    const episodes = playableEpisodes();
    const position = episodes.indexOf(activeEpisode);
    const previous = episodes[position - 1];
    const next = episodes[position + 1];

    playerControls.classList.toggle("hidden", position === -1);
    if (position === -1) return;

    playingEpisode.textContent = `Playing episode ${activeEpisode}`;
    previousEpisode.disabled = previous === undefined;
    nextEpisode.disabled = next === undefined;
    previousEpisode.onclick = () => openEpisode(previous);
    nextEpisode.onclick = () => openEpisode(next);
    reportEpisode.onclick = () => reportProblem(activeEpisode);
}

async function reportProblem(episode) {
    const reason = window.prompt("Describe the problem:");
    if (!reason?.trim()) return;

    try {
        const response = await fetch("/api/report", {
            method: "POST",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify({
                anime: anime?.name || animeFolder,
                episode,
                page: window.location.href,
                reason: reason.trim(),
            }),
        });
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error("Report failed");
        window.alert("Report submitted. Thank you!");
    } catch (error) {
        console.error(error);
        window.alert("Failed to submit report.");
    }
}

function escapeHtml(value = "") {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}

function showError(message) {
    title.textContent = "Oops!";
    status.textContent = "Bee couldn't find this anime.";
    episodeGrid.replaceChildren();
    episodeError.textContent = message;
    episodeError.classList.remove("hidden");
}

loadAnime().catch((error) => {
    console.error(error);
    showError("Could not load this anime.");
});
