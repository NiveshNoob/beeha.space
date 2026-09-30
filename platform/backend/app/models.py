from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Table, Text, UniqueConstraint, Column, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

def now():
    return datetime.now(timezone.utc)

anime_genres = Table("anime_genres", Base.metadata, Column("anime_id", ForeignKey("anime.id", ondelete="CASCADE"), primary_key=True), Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True))
movie_genres = Table("movie_genres", Base.metadata, Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True), Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True))
manga_genres = Table("manga_genres", Base.metadata, Column("manga_id", ForeignKey("manga.id", ondelete="CASCADE"), primary_key=True), Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True))
anime_languages = Table("anime_languages", Base.metadata, Column("anime_id", ForeignKey("anime.id", ondelete="CASCADE"), primary_key=True), Column("language_id", ForeignKey("languages.id", ondelete="CASCADE"), primary_key=True))
movie_languages = Table("movie_languages", Base.metadata, Column("movie_id", ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True), Column("language_id", ForeignKey("languages.id", ondelete="CASCADE"), primary_key=True))
manga_languages = Table("manga_languages", Base.metadata, Column("manga_id", ForeignKey("manga.id", ondelete="CASCADE"), primary_key=True), Column("language_id", ForeignKey("languages.id", ondelete="CASCADE"), primary_key=True))
chapter_languages = Table("chapter_languages", Base.metadata, Column("chapter_id", ForeignKey("manga_chapters.id", ondelete="CASCADE"), primary_key=True), Column("language_id", ForeignKey("languages.id", ondelete="CASCADE"), primary_key=True))

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now, nullable=False)

class Language(Base):
    __tablename__ = "languages"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    native_name: Mapped[str] = mapped_column(String(100))

class Genre(Base):
    __tablename__ = "genres"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)

class Anime(TimestampMixin, Base):
    __tablename__ = "anime"
    __table_args__ = (Index("ix_anime_year_status", "year", "status"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    slug: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    anilist_id: Mapped[int | None] = mapped_column(Integer, index=True)
    anilist_url: Mapped[str] = mapped_column(String(1000), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    japanese_name: Mapped[str] = mapped_column(String(300), default="")
    synonyms: Mapped[str] = mapped_column(Text, default="")
    total_episodes: Mapped[int] = mapped_column(Integer, default=0)
    year: Mapped[int | None] = mapped_column(Integer, index=True)
    season: Mapped[str] = mapped_column(String(30), default="")
    status: Mapped[str] = mapped_column(String(40), default="Unknown", index=True)
    type: Mapped[str] = mapped_column(String(40), default="")
    age_rating: Mapped[str] = mapped_column(String(40), default="")
    studio: Mapped[str] = mapped_column(String(200), default="")
    poster_url: Mapped[str] = mapped_column(String(1000), default="")
    banner_url: Mapped[str] = mapped_column(String(1000), default="")
    popularity: Mapped[int] = mapped_column(Integer, default=0)
    seasons: Mapped[list["Season"]] = relationship(back_populates="anime", cascade="all, delete-orphan", order_by="Season.season_number")
    languages: Mapped[list[Language]] = relationship(secondary=anime_languages)
    genres: Mapped[list[Genre]] = relationship(secondary=anime_genres)

class Season(TimestampMixin, Base):
    __tablename__ = "seasons"
    __table_args__ = (UniqueConstraint("anime_id", "season_number", name="uq_season_number"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    anime_id: Mapped[int] = mapped_column(ForeignKey("anime.id", ondelete="CASCADE"), index=True)
    season_number: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(200), default="")
    anime: Mapped[Anime] = relationship(back_populates="seasons")
    episodes: Mapped[list["Episode"]] = relationship(back_populates="season", cascade="all, delete-orphan", order_by="Episode.episode_number")

class Episode(TimestampMixin, Base):
    __tablename__ = "episodes"
    __table_args__ = (UniqueConstraint("season_id", "episode_number", name="uq_episode_number_per_season"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id", ondelete="CASCADE"), index=True)
    episode_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300), default="")
    duration: Mapped[int | None] = mapped_column(Integer)
    season: Mapped[Season] = relationship(back_populates="episodes")
    sources: Mapped[list["EpisodeSource"]] = relationship(back_populates="episode", cascade="all, delete-orphan", order_by="EpisodeSource.priority")

class EpisodeSource(TimestampMixin, Base):
    __tablename__ = "episode_sources"
    __table_args__ = (Index("ix_episode_source_language_active", "episode_id", "language_id", "active", "priority"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    episode_id: Mapped[int] = mapped_column(ForeignKey("episodes.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"), index=True)
    provider: Mapped[str] = mapped_column(String(100), index=True)
    url: Mapped[str] = mapped_column(String(2000))
    priority: Mapped[int] = mapped_column(Integer, default=100)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    episode: Mapped[Episode] = relationship(back_populates="sources")
    language: Mapped[Language] = relationship()

class Movie(TimestampMixin, Base):
    __tablename__ = "movies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    slug: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    anilist_id: Mapped[int | None] = mapped_column(Integer)
    anilist_url: Mapped[str] = mapped_column(String(1000), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[int | None] = mapped_column(Integer, index=True)
    duration: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40), default="Unknown", index=True)
    type: Mapped[str] = mapped_column(String(40), default="Movie")
    poster_url: Mapped[str] = mapped_column(String(1000), default="")
    banner_url: Mapped[str] = mapped_column(String(1000), default="")
    languages: Mapped[list[Language]] = relationship(secondary=movie_languages)
    genres: Mapped[list[Genre]] = relationship(secondary=movie_genres)
    sources: Mapped[list["MovieSource"]] = relationship(back_populates="movie", cascade="all, delete-orphan")

class MovieSource(TimestampMixin, Base):
    __tablename__ = "movie_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"), index=True)
    provider: Mapped[str] = mapped_column(String(100), index=True)
    url: Mapped[str] = mapped_column(String(2000))
    priority: Mapped[int] = mapped_column(Integer, default=100)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    movie: Mapped[Movie] = relationship(back_populates="sources")
    language: Mapped[Language] = relationship()

class Manga(TimestampMixin, Base):
    __tablename__ = "manga"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300), index=True)
    slug: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    anilist_id: Mapped[int | None] = mapped_column(Integer)
    anilist_url: Mapped[str] = mapped_column(String(1000), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    author: Mapped[str] = mapped_column(String(200), default="")
    artist: Mapped[str] = mapped_column(String(200), default="")
    year: Mapped[int | None] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(40), default="Unknown", index=True)
    type: Mapped[str] = mapped_column(String(40), default="Manga")
    poster_url: Mapped[str] = mapped_column(String(1000), default="")
    banner_url: Mapped[str] = mapped_column(String(1000), default="")
    languages: Mapped[list[Language]] = relationship(secondary=manga_languages)
    genres: Mapped[list[Genre]] = relationship(secondary=manga_genres)
    chapters: Mapped[list["MangaChapter"]] = relationship(back_populates="manga", cascade="all, delete-orphan", order_by="MangaChapter.chapter_number")

class MangaChapter(TimestampMixin, Base):
    __tablename__ = "manga_chapters"
    __table_args__ = (UniqueConstraint("manga_id", "chapter_number", name="uq_manga_chapter_number"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    manga_id: Mapped[int] = mapped_column(ForeignKey("manga.id", ondelete="CASCADE"), index=True)
    chapter_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300), default="")
    manga: Mapped[Manga] = relationship(back_populates="chapters")
    languages: Mapped[list[Language]] = relationship(secondary=chapter_languages)
    sources: Mapped[list["ChapterSource"]] = relationship(back_populates="chapter", cascade="all, delete-orphan")

class ChapterSource(TimestampMixin, Base):
    __tablename__ = "chapter_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(ForeignKey("manga_chapters.id", ondelete="CASCADE"), index=True)
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"), index=True)
    provider: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(2000))
    priority: Mapped[int] = mapped_column(Integer, default=100)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    chapter: Mapped[MangaChapter] = relationship(back_populates="sources")
    language: Mapped[Language] = relationship()
