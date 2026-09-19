const params =
    new URLSearchParams(
        window.location.search
    );


const year =
    params.get("year");

const animeFolder =
    params.get("anime");


/* =========================================
   Elements
========================================= */

const title =
    document.getElementById("title");

const status =
    document.getElementById("status");

const release =
    document.getElementById("release");

const cover =
    document.getElementById("cover");

const backgroundCover =
    document.getElementById(
        "background-cover"
    );

const anilist =
    document.getElementById("anilist");

const episodeCount =
    document.getElementById(
        "episode-count"
    );

const episodeHeadingCount =
    document.getElementById(
        "episode-heading-count"
    );

const episodeGrid =
    document.getElementById(
        "episode-grid"
    );

const episodeError =
    document.getElementById(
        "episode-error"
    );

const watchFirst =
    document.getElementById(
        "watch-first"
    );


/* =========================================
   Validation
========================================= */

if (!year || !animeFolder) {

    showError(
        "Invalid anime URL."
    );

}
else {

    loadAnime();
}


/* =========================================
   Read File
========================================= */

async function readFile(path) {

    const response =
        await fetch(path);

    if (!response.ok) {

        throw new Error(
            `Could not load ${path}`
        );
    }

    return response.text();
}


/* =========================================
   Parse meta.txt
========================================= */

function parseMeta(text) {

    const meta = {};

    text
        .split(/\r?\n/)
        .forEach(line => {

            line = line.trim();

            if (!line)
                return;

            const index =
                line.indexOf(":");

            if (index === -1)
                return;

            const key =
                line
                    .slice(0, index)
                    .trim();

            let value =
                line
                    .slice(index + 1)
                    .trim();

            value =
                value
                    .replace(/^["']|["']$/g, "")
                    .replace(/,\s*$/, "");

            meta[key] = value;

        });

    return meta;
}


/* =========================================
   Load Anime
========================================= */

async function loadAnime() {

    try {

        const encodedAnime =
            encodeURIComponent(
                animeFolder
            );


        const path =
            `data/${year}/` +
            `${encodedAnime}/meta.txt`;


        const metaText =
            await readFile(path);


        const meta =
            parseMeta(metaText);


        /* Title */

        const animeTitle =
            meta.name ||
            animeFolder;

        title.textContent =
            animeTitle;


        document.title =
            `${animeTitle} • Beeha`;


        /* Status */

        status.textContent =
            meta.status ||
            "Unknown";


        /* Release */

        release.textContent =
            meta.released_date ||
            "Unknown";


        /* Poster */

        const posterBase =
            `data/${year}/` +
            `${encodedAnime}/`;


        cover.src =
            `${posterBase}photo.jpg`;

        backgroundCover.src =
            `${posterBase}photo.jpg`;


        cover.onerror = () => {

            cover.src =
                `${posterBase}photo.webp`;
        };


        backgroundCover.onerror = () => {

            backgroundCover.src =
                `${posterBase}photo.webp`;
        };


        /* AniList */

        if (meta.anilist_link) {

            anilist.href =
                meta.anilist_link;

            anilist.style.display =
                "inline-flex";

        }
        else {

            anilist.style.display =
                "none";
        }


        /* Episodes */

        const total =
            parseInt(
                meta.total_episodes,
                10
            );


        if (
            Number.isNaN(total) ||
            total <= 0
        ) {

            throw new Error(
                "total_episodes is missing or invalid."
            );
        }


        episodeCount.textContent =
            `${total} episode${total === 1 ? "" : "s"}`;


        episodeHeadingCount.textContent =
            `${total} episode${total === 1 ? "" : "s"}`;


        createEpisodes(
            total,
            encodedAnime
        );

    }
    catch (error) {

        console.error(error);

        showError(
            "Could not load this anime."
        );
    }
}


/* =========================================
   Episode Buttons
========================================= */

function createEpisodes(
    total,
    encodedAnime
) {

    episodeGrid.innerHTML = "";

    for (
        let episode = 1;
        episode <= total;
        episode++
    ) {

        const button =
            document.createElement(
                "button"
            );


        button.type = "button";

        button.className =
            "episode-btn";


        button.innerHTML = `
            <span class="episode-number">
                ${episode}
            </span>

            <span class="episode-name">
                Episode ${episode}
            </span>
        `;


        button.addEventListener(
            "click",
            () => {

                const episodePage =
                    `data/${year}/` +
                    `${encodedAnime}/` +
                    `episodes/${episode}.html`;

                window.open(
                    episodePage,
                    "_blank",
                    "noopener,noreferrer"
                );
            }
        );


        episodeGrid.appendChild(
            button
        );
    }


    /* First episode */

    watchFirst.addEventListener(
        "click",
        openFirstEpisode
    );
}


/* =========================================
   Watch First
========================================= */

function openFirstEpisode() {

    const encodedAnime =
        encodeURIComponent(
            animeFolder
        );

    const episodePage =
        `data/${year}/` +
        `${encodedAnime}/` +
        `episodes/1.html`;


    window.open(
        episodePage,
        "_blank",
        "noopener,noreferrer"
    );
}


/* =========================================
   Error
========================================= */

function showError(message) {

    episodeGrid.innerHTML = "";

    episodeError.textContent =
        message;

    episodeError.classList.remove(
        "hidden"
    );

    title.textContent =
        "Oops!";

    status.textContent =
        "Bee couldn't find this anime.";
}
