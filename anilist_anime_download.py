#!/usr/bin/env python3

import time
import requests

URL = "https://graphql.anilist.co"

QUERY = """
query ($page: Int, $year: Int) {
  Page(page: $page, perPage: 500) {
    pageInfo {
      hasNextPage
    }

    media(
      type: ANIME
      seasonYear: $year
      sort: TITLE_ROMAJI
    ) {
      title {
        english
        romaji
        native
      }

      startDate {
        year
      }
    }
  }
}
"""


def graphql_request(page, year):
    while True:
        try:
            response = requests.post(
                URL,
                json={
                    "query": QUERY,
                    "variables": {
                        "page": page,
                        "year": year,
                    },
                },
                timeout=60,
            )

            if response.status_code == 429:
                retry_after = int(
                    response.headers.get("Retry-After", 60)
                )

                print(
                    f"[RATE LIMIT] Waiting {retry_after}s..."
                )

                time.sleep(retry_after + 2)
                continue

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] {e}")
            print("Retrying in 10 seconds...")
            time.sleep(10)


def get_title(media):
    return (
        media["title"]["english"]
        or media["title"]["romaji"]
        or media["title"]["native"]
        or "Unknown"
    )


def main():
    year = int(input("Year: ").strip())

    anime = set()
    page = 1

    while True:
        print(f"Page {page}")

        data = graphql_request(page, year)
        page_data = data["data"]["Page"]

        for media in page_data["media"]:
            anime.add(get_title(media).strip())

        if not page_data["pageInfo"]["hasNextPage"]:
            break

        page += 1
        time.sleep(2)

    anime = sorted(anime)

    output_file = f"{year}.txt"

    with open(output_file, "w", encoding="utf-8") as f:
        for title in anime:
            f.write(f"{title} | {year}\n")

    print(f"\nSaved {len(anime)} anime to {output_file}")


if __name__ == "__main__":
    main()
