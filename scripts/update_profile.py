"""Genera la tarjeta estilo terminal (dark_mode.svg / light_mode.svg)
y actualiza la sección de últimos commits del README.

Edita PROFILE con tus datos. Se ejecuta desde GitHub Actions.
"""
import datetime
import json
import os
import re
import urllib.request
from xml.sax.saxutils import escape

USER = "mateore1330-commits"
TOKEN = os.environ.get("PROFILE_TOKEN") or os.environ["GITHUB_TOKEN"]

# ---------- Tus datos (edita aquí) ----------
PROFILE = [
    ("Ubicación", "España"),
    ("Rol", "Full Stack Developer"),
    ("Empresa", "[TU_EMPRESA], software a medida"),
    ("Formación", "4Geeks Academy, FS PT-139"),
    ("Idiomas", "Español, Inglés"),
    None,
    ("Stack.Frontend", "React, Vite, Bootstrap"),
    ("Stack.Backend", "Python, Flask, SQLAlchemy"),
    ("Stack.Datos", "PostgreSQL"),
    ("Stack.IA", "Claude API, Gemini API, MCP"),
    None,
    "Contacto",
    ("Email", "[TU_EMAIL]"),
    ("LinkedIn", "in/[TU_LINKEDIN]"),
    None,
    "GitHub Stats",
]

ASCII = [
    " ███╗   ███╗",
    " ████╗ ████║",
    " ██╔████╔██║",
    " ██║╚██╔╝██║",
    " ██║ ╚═╝ ██║",
    " ╚═╝     ╚═╝",
    "",
    "  ┌───────┐",
    "  │ >_ fs │",
    "  └───────┘",
]

THEMES = {
    "dark_mode.svg": {"bg": "#161b22", "border": "#30363d", "text": "#c9d1d9",
                      "key": "#ffa657", "value": "#a5d6ff", "dots": "#616e7f"},
    "light_mode.svg": {"bg": "#f6f8fa", "border": "#d0d7de", "text": "#24292f",
                       "key": "#953800", "value": "#0a3069", "dots": "#c2cfde"},
}

WIDTH_CHARS = 56
LINE_H = 20


def gql(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"Error de la API de GitHub: {data['errors']}")
    return data["data"]


QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes { stargazerCount }
    }
    recent: repositories(first: 10, ownerAffiliations: OWNER, privacy: PUBLIC,
                         orderBy: {field: PUSHED_AT, direction: DESC}) {
      nodes {
        name
        url
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 1) { nodes { messageHeadline committedDate url } }
            }
          }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar { totalContributions }
    }
  }
}
"""


def kv_line(key, value):
    dots = max(2, WIDTH_CHARS - len(key) - len(value) - 3)
    return [("key", key), ("dots", ": " + "." * dots + " "), ("value", value)]


def header_line(title):
    return [("key", "- " + title + " "), ("dots", "─" * (WIDTH_CHARS - len(title) - 3))]


def build_lines(stats):
    lines = [[("key", "mateo"), ("dots", "@"), ("key", "github")],
             [("dots", "─" * WIDTH_CHARS)]]
    for item in PROFILE:
        if item is None:
            lines.append([])
        elif isinstance(item, str):
            lines.append(header_line(item))
        else:
            lines.append(kv_line(*item))
    lines.append(kv_line("Repos", stats["repos"]))
    lines.append(kv_line("Stars", stats["stars"]))
    lines.append(kv_line("Seguidores", stats["followers"]))
    lines.append(kv_line("Commits (último año)", stats["commits"]))
    lines.append(kv_line("Contribuciones (último año)", stats["contribs"]))
    return lines


def render_svg(lines, theme):
    height = len(lines) * LINE_H + 40
    ascii_top = 20 + (height - 40 - len(ASCII) * LINE_H) // 2
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,Menlo,\'DejaVu Sans Mono\',\'Courier New\',monospace" '
        f'width="985px" height="{height}px" font-size="16px">',
        "<title>Mateo, Full Stack Developer</title>",
        "<style>"
        f".key{{fill:{theme['key']}}}.value{{fill:{theme['value']}}}.dots{{fill:{theme['dots']}}}"
        "text{font-family:ConsolasFallback,Consolas,Menlo,'DejaVu Sans Mono','Courier New',monospace}"
        f"text,tspan{{white-space:pre}}"
        "</style>",
        f'<rect width="983px" height="{height - 2}px" x="1" y="1" rx="12" fill="{theme["bg"]}" stroke="{theme["border"]}"/>',
        f'<text x="30" y="{ascii_top}" fill="{theme["key"]}">',
    ]
    for i, a in enumerate(ASCII):
        out.append(f'<tspan x="30" y="{ascii_top + i * LINE_H}">{escape(a)}</tspan>')
    out.append("</text>")
    out.append(f'<text x="390" y="30" fill="{theme["text"]}">')
    for i, segs in enumerate(lines):
        y = 30 + i * LINE_H
        if not segs:
            continue
        parts = "".join(f'<tspan class="{cls}">{escape(txt)}</tspan>' for cls, txt in segs)
        out.append(f'<tspan x="390" y="{y}">{parts}</tspan>')
    out.append("</text></svg>")
    return "\n".join(out)


def recent_commits(nodes, limit=4):
    items = []
    for repo in nodes:
        if repo["name"].lower() == USER.lower():
            continue
        ref = repo.get("defaultBranchRef") or {}
        hist = ((ref.get("target") or {}).get("history") or {}).get("nodes") or []
        if not hist:
            continue
        c = hist[0]
        msg = re.sub(r"[\[\]|<>]", "", c["messageHeadline"])[:60]
        date = datetime.datetime.fromisoformat(c["committedDate"].replace("Z", "+00:00")).strftime("%d/%m/%Y")
        items.append(f"- [**{repo['name']}**]({repo['url']}): [{msg}]({c['url']}) <sub>{date}</sub>")
        if len(items) == limit:
            break
    return "\n".join(items) or "- Sin commits públicos recientes"


def main():
    user = gql(QUERY, {"login": USER})["user"]
    stats = {
        "repos": str(user["repositories"]["totalCount"]),
        "stars": str(sum(n["stargazerCount"] for n in user["repositories"]["nodes"])),
        "followers": str(user["followers"]["totalCount"]),
        "commits": str(user["contributionsCollection"]["totalCommitContributions"]),
        "contribs": str(user["contributionsCollection"]["contributionCalendar"]["totalContributions"]),
    }
    lines = build_lines(stats)
    for filename, theme in THEMES.items():
        with open(filename, "w", encoding="utf-8") as f:
            f.write(render_svg(lines, theme))

    with open("README.md", encoding="utf-8") as f:
        readme = f.read()
    block = f"<!-- COMMITS:START -->\n{recent_commits(user['recent']['nodes'])}\n<!-- COMMITS:END -->"
    readme = re.sub(r"<!-- COMMITS:START -->.*?<!-- COMMITS:END -->", lambda _: block, readme, flags=re.S)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme)
    print("Perfil actualizado:", stats)


if __name__ == "__main__":
    main()
