#!/usr/bin/env python3
"""Generate a GitHub contribution history image."""

import argparse
import datetime
import subprocess
import sys

import requests
from PIL import Image, ImageDraw, ImageFont

SCALE = 2
CELL_SIZE = 11 * SCALE
CELL_GAP = 3 * SCALE
CELL_STRIDE = CELL_SIZE + CELL_GAP
GRID_COLS = 53
GRID_ROWS = 7
GRID_WIDTH = GRID_COLS * CELL_STRIDE - CELL_GAP
GRID_HEIGHT = GRID_ROWS * CELL_STRIDE - CELL_GAP
CORNER_RADIUS = 3 * SCALE

THEMES = {
    "dark": {
        "bg": "#0d1117",
        "text": "#8b949e",
        "levels": {
            "NONE": "#161b22",
            "FIRST_QUARTILE": "#0e4429",
            "SECOND_QUARTILE": "#006d32",
            "THIRD_QUARTILE": "#26a641",
            "FOURTH_QUARTILE": "#39d353",
        },
    },
    "light": {
        "bg": "#ffffff",
        "text": "#57606a",
        "levels": {
            "NONE": "#ebedf0",
            "FIRST_QUARTILE": "#9be9a8",
            "SECOND_QUARTILE": "#40c463",
            "THIRD_QUARTILE": "#30a14e",
            "FOURTH_QUARTILE": "#216e39",
        },
    },
}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

GRAPHQL_URL = "https://api.github.com/graphql"


def hex_to_rgb(hex_str):
    h = hex_str.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def get_token(args):
    if args.token:
        return args.token

    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        print("GitHub CLI is installed but not authenticated.\n")
        print("  Run:  gh auth login\n")
        print("Then re-run this script.")
        sys.exit(1)
    except FileNotFoundError:
        pass
    except subprocess.TimeoutExpired:
        pass

    print("GitHub CLI (gh) is required for authentication.\n")
    print("To set it up:\n")
    print("  1. Install:  brew install gh")
    print("  2. Log in:   gh auth login\n")
    print("Then re-run this script.\n")
    print("Alternatively, pass a token directly: --token YOUR_TOKEN")
    sys.exit(1)


def graphql_query(token, query, variables=None):
    headers = {
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    resp = requests.post(GRAPHQL_URL, json=payload, headers=headers)

    if resp.status_code == 401:
        print("Authentication failed. Your token may be invalid or expired.")
        print("Run: gh auth login")
        sys.exit(1)

    resp.raise_for_status()
    data = resp.json()

    if "errors" in data:
        for err in data["errors"]:
            print(f"GitHub API error: {err.get('message', err)}")
        sys.exit(1)

    return data["data"]


def get_viewer_info(token):
    data = graphql_query(token, "query { viewer { login createdAt } }")
    return data["viewer"]


def get_contributions_for_year(token, username, year):
    today = datetime.date.today()
    from_date = f"{year}-01-01T00:00:00Z"
    if year == today.year:
        to_date = f"{today.isoformat()}T23:59:59Z"
    else:
        to_date = f"{year}-12-31T23:59:59Z"

    query = """
    query($username: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $username) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                contributionLevel
              }
            }
          }
        }
      }
    }
    """

    data = graphql_query(token, query, {"username": username, "from": from_date, "to": to_date})

    if not data.get("user"):
        print(f"User '{username}' not found.")
        sys.exit(1)

    calendar = data["user"]["contributionsCollection"]["contributionCalendar"]
    return {
        "year": year,
        "total": calendar["totalContributions"],
        "weeks": calendar["weeks"],
    }


def fetch_all_contributions(token, username, years):
    years_data = []
    for year in years:
        print(f"  {year}...", end=" ", flush=True)
        year_data = get_contributions_for_year(token, username, year)
        print(f"{year_data['total']} contributions")
        years_data.append(year_data)
    return years_data


def load_font(size):
    for path in [
        "/System/Library/Fonts/Avenir Next.ttc",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def render_contributions(years_data, theme_name, output_path):
    theme = THEMES[theme_name]
    bg_color = hex_to_rgb(theme["bg"])
    text_color = hex_to_rgb(theme["text"])
    level_colors = {k: hex_to_rgb(v) for k, v in theme["levels"].items()}

    title_font = load_font(16 * SCALE)
    month_font = load_font(13 * SCALE)

    padding_x = 20 * SCALE
    padding_top = 15 * SCALE
    padding_bottom = 20 * SCALE
    title_height = 24 * SCALE
    gap_after_title = 6 * SCALE
    month_label_height = 16 * SCALE
    gap_after_months = 5 * SCALE
    year_block_height = title_height + gap_after_title + month_label_height + gap_after_months + GRID_HEIGHT
    gap_between_years = 28 * SCALE

    num_years = len(years_data)
    img_width = padding_x + GRID_WIDTH + padding_x
    img_height = (
        padding_top
        + num_years * year_block_height
        + (num_years - 1) * gap_between_years
        + padding_bottom
    )

    img = Image.new("RGB", (img_width, img_height), bg_color)
    draw = ImageDraw.Draw(img)

    for i, year_data in enumerate(years_data):
        y_base = padding_top + i * (year_block_height + gap_between_years)

        year = year_data["year"]
        total = year_data["total"]
        suffix = "Contribution" if total == 1 else "Contributions"
        draw.text((padding_x, y_base), f"{year}: {total} {suffix}", fill=text_color, font=title_font)

        month_y = y_base + title_height + gap_after_title
        grid_y = month_y + month_label_height + gap_after_months

        month_cols = {}
        for col_idx, week in enumerate(year_data["weeks"]):
            for day in week["contributionDays"]:
                month = int(day["date"][5:7]) - 1
                if month not in month_cols:
                    month_cols[month] = col_idx

        for month_idx, col_idx in month_cols.items():
            x = padding_x + col_idx * CELL_STRIDE
            draw.text((x, month_y), MONTHS[month_idx], fill=text_color, font=month_font)

        for col_idx, week in enumerate(year_data["weeks"]):
            for day in week["contributionDays"]:
                d = datetime.date.fromisoformat(day["date"])
                row_idx = d.isoweekday() % 7  # Sunday=0 .. Saturday=6

                x = padding_x + col_idx * CELL_STRIDE
                y = grid_y + row_idx * CELL_STRIDE

                color = level_colors.get(day["contributionLevel"], level_colors["NONE"])

                draw.rounded_rectangle(
                    [x, y, x + CELL_SIZE, y + CELL_SIZE],
                    radius=CORNER_RADIUS,
                    fill=color,
                )

    img.save(output_path, "PNG")


def main():
    parser = argparse.ArgumentParser(description="Generate a GitHub contribution history image.")
    parser.add_argument("--token", help="GitHub token (default: auto-detect via gh CLI)")
    parser.add_argument("--user", help="GitHub username (default: auto-detect)")
    parser.add_argument("--start-year", type=int, help="Earliest year to include")
    parser.add_argument("--years", help="Comma-separated list of specific years (e.g. 2022,2025)")
    parser.add_argument("--output", default="contributions.png", help="Output file (default: contributions.png)")
    parser.add_argument("--theme", choices=["dark", "light"], default="dark", help="Color theme (default: dark)")

    args = parser.parse_args()
    token = get_token(args)

    print("Fetching user info...")
    viewer = get_viewer_info(token)
    username = args.user or viewer["login"]
    created_year = int(viewer["createdAt"][:4])

    if args.years:
        selected_years = sorted([int(y.strip()) for y in args.years.split(",")], reverse=True)
    else:
        start_year = args.start_year or created_year
        end_year = datetime.date.today().year
        selected_years = list(range(end_year, start_year - 1, -1))

    print(f"Fetching contributions for {username} ({', '.join(str(y) for y in selected_years)})...")
    years_data = fetch_all_contributions(token, username, selected_years)

    if not years_data:
        print("No contribution data found.")
        sys.exit(1)

    print(f"Rendering {len(years_data)} years...")
    render_contributions(years_data, args.theme, args.output)
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
