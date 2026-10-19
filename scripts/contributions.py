"""Render aggregate GitHub activity; no repository details are queried.

Run with Python and authenticated GitHub CLI. Actions uses GH_TOKEN.
"""
import json
import math
import os
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUERY = """query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""


def fetch_calendar():
    result = subprocess.run(
        ['gh', 'api', 'graphql', '-f', f'query={QUERY}', '-f',
         f'login={os.environ.get("PROFILE_USERNAME", "pplulee")}'],
        check=True, capture_output=True, text=True,
    )
    payload = json.loads(result.stdout)
    if payload.get('errors'):
        raise RuntimeError(payload['errors'])
    return payload['data']['user']['contributionsCollection']['contributionCalendar']


def render(calendar, dark):
    bg, fg, muted, grid = (
        ('#0d1117', '#e6edf3', '#8b949e', '#212b36') if dark else
        ('#ffffff', '#1f2937', '#6b7280', '#e8edf2')
    )
    palettes = [('#a7f3d0', '#34d399', '#059669'),
                ('#6ee7b7', '#10b981', '#047857'),
                ('#34d399', '#059669', '#065f46'),
                ('#2dd4bf', '#0d9488', '#115e59')]
    days = [day for week in calendar['weeks'] for day in week['contributionDays']]
    if not days:
        raise ValueError('Empty contribution calendar')
    peak = max(day['contributionCount'] for day in days)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="450" viewBox="0 0 1100 450" role="img" aria-labelledby="title desc">',
        '<title id="title">最近一年的 GitHub 贡献</title>',
        f'<desc id="desc">{calendar["totalContributions"]:,} 次贡献，时间为 {days[0]["date"]} 至 {days[-1]["date"]}。每个方块代表一天，高度使用平方根缩放。</desc>',
        f'<rect x="1" y="1" width="1098" height="448" rx="20" fill="{bg}" stroke="{grid}"/>',
        f'<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Microsoft YaHei,sans-serif" fill="{fg}">',
        f'<text x="42" y="52" font-size="23" font-weight="600">{calendar["totalContributions"]:,} 次贡献</text>',
        f'<text x="42" y="78" font-size="13" fill="{muted}">{days[0]["date"]} — {days[-1]["date"]}</text>',
    ]

    def polygon(points, color):
        coords = ' '.join(f'{x:.1f},{y:.1f}' for x, y in points)
        return f'<polygon points="{coords}" fill="{color}" stroke="{bg}" stroke-width="0.5" stroke-linejoin="round"/>'

    cells = []
    for w, week in enumerate(calendar['weeks']):
        for day in week['contributionDays']:
            d = (date.fromisoformat(day['date']).weekday() + 1) % 7
            cells.append((w + d, w, d, day))
    # Painter order: distant blocks first; partial weeks leave gaps.
    for _, w, d, day in sorted(cells):
        count = day['contributionCount']
        ratio = math.sqrt(count / peak) if peak else 0
        height = 3 + 90 * ratio
        x, y = 142 + w * 16.3 - d * 12, 190 + w * 2.35 + d * 8
        top, right, left = palettes[min(3, int(ratio * 4))] if count else (grid, grid, grid)
        a, b, c, e = (x, y-height), (x+14, y+2-height), (x+4, y+8-height), (x-10, y+6-height)
        parts.append(f'<g><title>{day["date"]}: {count} 次贡献</title>')
        parts.append(polygon([e, c, (x+4, y+8), (x-10, y+6)], left))
        parts.append(polygon([c, b, (x+14, y+2), (x+4, y+8)], right))
        parts.append(polygon([a, b, c, e], top))
        parts.append('</g>')
    parts.extend([
        f'<text x="42" y="411" font-size="12" fill="{muted}">每个方块代表一天</text>',
        f'<text x="1058" y="411" text-anchor="end" font-size="12" fill="{muted}">GitHub 贡献记录</text>',
        '</g></svg>',
    ])
    return '\n'.join(parts) + '\n'


def main():
    calendar = fetch_calendar()
    target = ROOT / 'assets'
    target.mkdir(exist_ok=True)
    for theme in ('light', 'dark'):
        (target / f'contributions-{theme}.svg').write_text(
            render(calendar, theme == 'dark'), encoding='utf-8')
    print(f'Rendered both themes: {calendar["totalContributions"]} contributions')


if __name__ == '__main__':
    main()
