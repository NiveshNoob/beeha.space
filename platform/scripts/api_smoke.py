"""Call FastAPI catalog routes directly and validate their response schemas."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.database import SessionLocal
from backend.app.api.catalog import (
    anime_detail, anime_episodes, anime_list, anime_seasons, discovery,
    episode_sources, genres, languages, manga_list, movie_list, search,
)
from backend.app.schemas import AnimeOut, DiscoveryOut, EpisodeOut, SearchOut, SeasonOut

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anime", default="naruto", help="Anime slug to use for detail checks (default: naruto)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        catalog = anime_list(None, None, None, None, None, False, False, 30, 0, db)
        detail = AnimeOut.model_validate(anime_detail(args.anime, db))
        seasons = [SeasonOut.model_validate(item) for item in anime_seasons(args.anime, db)]
        episodes = [EpisodeOut.model_validate(item) for item in anime_episodes(args.anime, db)]
        if not episodes:
            parser.error(f"Anime {args.anime!r} has no catalog episodes for the source check")
        sources = episode_sources(episodes[0].id, None, db)
        assert catalog and detail.seasons and seasons and episodes and sources
        assert languages(db) and genres(db)
        assert movie_list(None, None, None, None, None, 30, 0, db) is not None
        assert manga_list(None, None, None, None, None, 30, 0, db) is not None
        SearchOut.model_validate(search(args.anime, 20, db))
        DiscoveryOut.model_validate(discovery(db))
        print(f"Passed anime list/detail/season/episode/source ({args.anime}), languages, genres, movie, manga, search, and discovery API checks.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
