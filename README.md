# am-i-active

Generate an image of your full GitHub contribution history — every year of green squares, stacked in one PNG.

## Prerequisites

- Python 3.8+
- [GitHub CLI (`gh`)](https://cli.github.com/) — used for authentication

## Setup

1. **Install dependencies**

   ```bash
   pip install Pillow requests
   ```

2. **Install and authenticate the GitHub CLI**

   ```bash
   brew install gh
   gh auth login
   ```

   Follow the prompts to log in via browser. That's it — the script picks up your token automatically.

## Usage

```bash
python3 am_i_active.py
```

This fetches your contribution history from the year you created your GitHub account to today, and saves `contributions.png` in the current directory.

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--theme dark\|light` | Color theme | `dark` |
| `--years 2022,2025` | Specific years to include (comma-separated) | All years |
| `--start-year YEAR` | Earliest year to include | Account creation year |
| `--user USERNAME` | GitHub username to fetch | Authenticated user |
| `--output FILE` | Output file path | `contributions.png` |
| `--token TOKEN` | GitHub token (skips `gh` CLI) | Auto-detect |

### Examples

```bash
# Light theme
python3 am_i_active.py --theme light

# Only recent years
python3 am_i_active.py --start-year 2020

# Only specific years
python3 am_i_active.py --years 2022,2025

# Someone else's contributions
python3 am_i_active.py --user octocat

# Custom output path
python3 am_i_active.py --output ~/Desktop/my-contributions.png
```
