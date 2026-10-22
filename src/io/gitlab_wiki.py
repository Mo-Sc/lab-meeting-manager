import logging
from urllib.parse import quote

import requests

from config.config import WikiConfig


def load_people() -> list[dict]:
    """
    Load name, role and meeting group of everyone in the Staff and Students tables of the wiki page.
    People without a meeting group are skipped.
    """
    with open(WikiConfig.TOKEN_FILE) as f:
        token = f.read().strip()

    response = requests.get(
        f"{WikiConfig.URL}/api/v4/projects/{quote(WikiConfig.PROJECT, safe='')}/wikis/{WikiConfig.PAGE}",
        headers={"PRIVATE-TOKEN": token},
        timeout=30,
    )
    response.raise_for_status()
    content = response.json()["content"]

    people = []
    for role, section in [("staff", "Staff"), ("student", "Students")]:
        table = content.split(f"## {section}")[1].split("\n## ")[0]
        # first row is the header, second the |---| separator
        header, _, *rows = [
            [cell.strip() for cell in line.strip().strip("|").split("|")]
            for line in table.splitlines()
            if line.startswith("|")
        ]
        for row in rows:
            person = dict(zip(header, row))
            if not person.get("Meeting Group"):
                logging.warning(f"{person['Name']} has no meeting group, skipping")
                continue
            people.append({"name": person["Name"], "role": role, "group": person["Meeting Group"]})

    return people
