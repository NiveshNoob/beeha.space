import json
import requests

API_KEY = "Ml9bLaGqTzwyTk7G0MhvOl9CfzcvdF5f7cQhgrk6IaWxgRSvJG98jzIbeH6ZVQd7"

all_files = []
page = 1

while True:
    data = requests.get(
        f"https://voe.sx/api/file/list?key={API_KEY}&page={page}&per_page=100"
    ).json()

    files = data["result"]["data"]

    if not files:
        break

    for file in files:
        all_files.append({
            "title": file["title"],
            "code": file["filecode"],
            "embed": f"https://voe.sx/e/{file['filecode']}"
        })

    page += 1

with open("voe_links.json", "w", encoding="utf-8") as f:
    json.dump(all_files, f, ensure_ascii=False, indent=2)

print(f"Saved {len(all_files)} entries to voe_links.json")
