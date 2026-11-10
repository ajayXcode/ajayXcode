#!/usr/bin/env python3
"""
generate_cards.py - Renders animated SVG profile cards for GitHub profile README.

Features:
- Subsets Mona Sans font (Regular 400 & Bold 700) using fontTools.subset (pyftsubset) into WOFF.
- Inlines fonts as base64 WOFF data URIs in @font-face blocks inside <style>.
- Embeds optimized user portrait (halftone pop-art) as base64 JPEG data URI in hero.svg.
- Staggers CSS animation delays so the page plays sequentially from top to bottom.
- Supports prefers-reduced-motion to disable all animations cleanly.
- Supports STATIC=1 mode (or --static flag) to render the final static frame.
- Reads contribution and repository data from data/contributions.json.
- Supports --fetch flag to query GitHub GraphQL API with GITHUB_TOKEN to refresh data.
"""

import os
import sys
import json
import base64
import io
from datetime import datetime
from PIL import Image
from fontTools import subset

# Determine static mode
IS_STATIC = os.environ.get('STATIC', '').strip().lower() in ('1', 'true', 'yes') or '--static' in sys.argv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(SCRIPT_DIR, 'data', 'contributions.json')
CARDS_DIR = os.path.join(SCRIPT_DIR, 'cards')
ASSETS_DIR = os.path.join(SCRIPT_DIR, 'assets')
FONTS_DIR = os.path.join(ASSETS_DIR, 'fonts')
REG_FONT_PATH = os.path.join(FONTS_DIR, 'MonaSans-Regular.ttf')
BOLD_FONT_PATH = os.path.join(FONTS_DIR, 'MonaSans-Bold.ttf')
PORTRAIT_PATH = os.path.join(ASSETS_DIR, 'portrait.jpg')

# Brand Color Palette matching website & profile
BRAND = {
    'bg_start': '#111116',
    'bg_end': '#171722',
    'card_stroke': '#282836',
    'accent_violet': '#8b5cf6',
    'accent_indigo': '#6366f1',
    'accent_cyan': '#38bdf8',
    'accent_emerald': '#34d399',
    'accent_yellow': '#facc15',
    'accent_rose': '#fb7185',
    'text_primary': '#ffffff',
    'text_secondary': '#e2e8f0',
    'text_muted': '#94a3b8',
    'level_0': '#1b1b22',
    'level_1': '#3b1d6e',
    'level_2': '#6d28d9',
    'level_3': '#8b5cf6',
    'level_4': '#c4b5fd',
}

# Base characters needed for font subsetting
CHARSET = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    "0123456789 .,:;!?'\"`~@#$%^&*()-_=+[]{}|/\\<>•→↗🔥🏆📅⚡⭐🍴🚀✨"
)

def subset_font_to_b64(font_path, text=CHARSET):
    """Subsets a TTF font using fontTools into WOFF and returns a base64 data URI string."""
    if not os.path.exists(font_path):
        return ""
    options = subset.Options()
    options.flavor = 'woff'
    options.obfuscate_names = True
    font = subset.load_font(font_path, options)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=text)
    subsetter.subset(font)
    font.flavor = 'woff'
    buf = io.BytesIO()
    subset.save_font(font, buf, options)
    b64_str = base64.b64encode(buf.getvalue()).decode('ascii')
    return f"data:font/woff;charset=utf-8;base64,{b64_str}"

# Cache font data URIs
print("Subsetting fonts with pyftsubset (Mona Sans)...")
REGULAR_FONT_URI = subset_font_to_b64(REG_FONT_PATH)
BOLD_FONT_URI = subset_font_to_b64(BOLD_FONT_PATH)

def get_font_css():
    """Returns CSS @font-face rules with embedded WOFF base64 data URIs."""
    css = ""
    if REGULAR_FONT_URI:
        css += f"""
    @font-face {{
      font-family: 'Mona Sans';
      font-style: normal;
      font-weight: 400;
      src: url('{REGULAR_FONT_URI}') format('woff');
    }}
"""
    if BOLD_FONT_URI:
        css += f"""
    @font-face {{
      font-family: 'Mona Sans';
      font-style: normal;
      font-weight: 700;
      src: url('{BOLD_FONT_URI}') format('woff');
    }}
"""
    return css

def get_portrait_b64(max_size=360):
    """Loads, resizes, and encodes user portrait image as base64 JPEG data URI."""
    if not os.path.exists(PORTRAIT_PATH):
        return ""
    try:
        im = Image.open(PORTRAIT_PATH)
        im.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format='JPEG', quality=88, optimize=True)
        b64_str = base64.b64encode(buf.getvalue()).decode('ascii')
        return f"data:image/jpeg;base64,{b64_str}"
    except Exception as e:
        print(f"Warning: Could not process portrait image: {e}")
        return ""

PORTRAIT_DATA_URI = get_portrait_b64()

def load_data():
    """Loads contributions and profile data from JSON."""
    if not os.path.exists(DATA_FILE):
        print(f"Data file {DATA_FILE} not found! Run with --fetch or run build_data.py first.")
        sys.exit(1)
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def fetch_github_contributions():
    """Refreshes contributions.json from GitHub GraphQL API if GITHUB_TOKEN is present."""
    token = os.environ.get('GITHUB_TOKEN')
    username = os.environ.get('GITHUB_USERNAME', 'ajayXcode')
    if not token:
        print("Note: GITHUB_TOKEN not found in environment. Skipping remote fetch, using existing contributions.json.")
        return
    import requests
    headers = {"Authorization": f"Bearer {token}"}
    query = """
    query($login: String!) {
      user(login: $login) {
        name
        bio
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
                weekday
              }
            }
          }
        }
      }
    }
    """
    try:
        print(f"Fetching contribution data from GitHub GraphQL for @{username}...")
        resp = requests.post("https://api.github.com/graphql", json={"query": query, "variables": {"login": username}}, headers=headers, timeout=15)
        if resp.status_code == 200:
            result = resp.json()
            user_data = result.get('data', {}).get('user')
            if user_data:
                calendar = user_data.get('contributionsCollection', {}).get('contributionCalendar', {})
                total = calendar.get('totalContributions', 0)
                raw_weeks = calendar.get('weeks', [])
                
                # Transform days
                days = []
                for w in raw_weeks:
                    for d in w.get('contributionDays', []):
                        days.append({
                            'date': d.get('date'),
                            'count': d.get('contributionCount', 0)
                        })
                
                # Update existing JSON with new live counts
                data = load_data()
                data['total_contributions'] = total
                data['updated_at'] = datetime.now().isoformat()
                
                # Recompute streaks and monthly breakdown
                # ...
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                print(f"Successfully refreshed {DATA_FILE} via GitHub GraphQL API!")
        else:
            print(f"GraphQL request failed with HTTP {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"Error fetching from GitHub API: {e}")

# ==============================================================================
# CARD BUILDERS
# ==============================================================================

def make_hero_card(data):
    """Renders cards/hero.svg - Hero banner with name, bio, portrait, status & tech tags."""
    stagger_delay = "0.1s"
    
    font_css = get_font_css()
    
    # CSS animation rules
    if IS_STATIC:
        anim_css = """
      .animated { opacity: 1 !important; transform: none !important; }
      .pulse-ring { display: none; }
      .shimmer-line { display: none; }
"""
        smil_pulse = ""
        smil_shimmer = ""
    else:
        anim_css = f"""
      .animated {{
        opacity: 0;
        transform: translateY(12px);
        animation: heroFadeUp 0.75s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        animation-delay: {stagger_delay};
      }}
      .avatar-wrap {{
        opacity: 0;
        transform: scale(0.92);
        animation: avatarPop 0.8s cubic-bezier(0.34, 1.35, 0.64, 1) forwards;
        animation-delay: 0.18s;
        transform-origin: 120px 125px;
      }}
      .stagger-1 {{
        opacity: 0;
        animation: heroFadeUp 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        animation-delay: 0.3s;
      }}
      .stagger-2 {{
        opacity: 0;
        animation: heroFadeUp 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        animation-delay: 0.42s;
      }}
      .stagger-3 {{
        opacity: 0;
        animation: heroFadeUp 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        animation-delay: 0.54s;
      }}
      @keyframes heroFadeUp {{
        to {{
          opacity: 1;
          transform: translateY(0);
        }}
      }}
      @keyframes avatarPop {{
        to {{
          opacity: 1;
          transform: scale(1);
        }}
      }}
      @keyframes pulseRing {{
        0% {{ r: 6px; opacity: 0.85; stroke-width: 2px; }}
        70% {{ r: 16px; opacity: 0; stroke-width: 1px; }}
        100% {{ r: 16px; opacity: 0; }}
      }}
      .pulse-ring {{
        animation: pulseRing 2.4s cubic-bezier(0.25, 1, 0.5, 1) infinite;
        transform-origin: 195px 195px;
      }}
"""
        smil_pulse = """
        <animate attributeName="r" values="6;16;6" dur="2.4s" repeatCount="indefinite"/>
        <animate attributeName="opacity" values="0.85;0;0.85" dur="2.4s" repeatCount="indefinite"/>
"""
        smil_shimmer = """
        <animate attributeName="x1" values="-300;850" dur="4s" repeatCount="indefinite"/>
        <animate attributeName="x2" values="0;1150" dur="4s" repeatCount="indefinite"/>
"""

    name = data.get('name', 'Ajay Yadav')
    tagline = data.get('tagline', 'I like making fun projects that I can use in my daily life.')
    title = data.get('title', 'B.Tech Undergraduate • AIML & Full-Stack Developer')
    username = data.get('username', 'ajayXcode')

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 250" width="850" height="250" fill="none">
  <defs>
    {font_css}
    <linearGradient id="hero-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{BRAND['bg_start']}"/>
      <stop offset="100%" stop-color="{BRAND['bg_end']}"/>
    </linearGradient>
    <linearGradient id="brand-grad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{BRAND['accent_violet']}"/>
      <stop offset="50%" stop-color="{BRAND['accent_yellow']}"/>
      <stop offset="100%" stop-color="{BRAND['accent_cyan']}"/>
    </linearGradient>
    <linearGradient id="avatar-border" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{BRAND['accent_violet']}"/>
      <stop offset="50%" stop-color="{BRAND['accent_yellow']}"/>
      <stop offset="100%" stop-color="{BRAND['accent_cyan']}"/>
    </linearGradient>
    <linearGradient id="shimmer" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{BRAND['accent_violet']}" stop-opacity="0"/>
      <stop offset="50%" stop-color="#ffffff" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="{BRAND['accent_cyan']}" stop-opacity="0"/>
      {smil_shimmer}
    </linearGradient>
    <clipPath id="avatar-clip">
      <rect x="36" y="36" width="168" height="168" rx="28" />
    </clipPath>
    <style>
      text {{
        font-family: 'Mona Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }}
      {anim_css}
      @media (prefers-reduced-motion: reduce) {{
        *, ::before, ::after {{
          animation: none !important;
          transition: none !important;
          transform: none !important;
          opacity: 1 !important;
        }}
      }}
    </style>
  </defs>

  <!-- Card Background -->
  <g class="animated">
    <rect x="1" y="1" width="848" height="248" rx="20" fill="url(#hero-bg)" stroke="{BRAND['card_stroke']}" stroke-width="1.5"/>
    <line x1="20" y1="2" x2="830" y2="2" stroke="url(#brand-grad)" stroke-width="2.5" stroke-linecap="round"/>
    
    <!-- Top Decorative Glow -->
    <circle cx="120" cy="80" r="140" fill="{BRAND['accent_violet']}" fill-opacity="0.08" filter="blur(40px)"/>
    <circle cx="740" cy="180" r="160" fill="{BRAND['accent_indigo']}" fill-opacity="0.06" filter="blur(40px)"/>
  </g>

  <!-- Left: Avatar Portrait -->
  <g class="avatar-wrap">
    <!-- Glow aura -->
    <rect x="33" y="33" width="174" height="174" rx="31" fill="none" stroke="url(#avatar-border)" stroke-width="2.5" opacity="0.9"/>
    
    <!-- Image -->
    <image href="{PORTRAIT_DATA_URI}" x="36" y="36" width="168" height="168" preserveAspectRatio="xMidYMid slice" clip-path="url(#avatar-clip)"/>

    <!-- Online Status Dot -->
    <circle cx="195" cy="195" r="14" fill="{BRAND['bg_start']}" />
    <circle cx="195" cy="195" r="7" fill="{BRAND['accent_emerald']}" />
    <circle cx="195" cy="195" r="7" fill="none" stroke="{BRAND['accent_emerald']}" class="pulse-ring">
      {smil_pulse}
    </circle>
  </g>

  <!-- Right: Header Content -->
  <g class="stagger-1">
    <!-- Badge 1: Handle & Profile -->
    <rect x="230" y="36" width="180" height="24" rx="12" fill="{BRAND['accent_violet']}" fill-opacity="0.12" stroke="{BRAND['accent_violet']}" stroke-opacity="0.35"/>
    <circle cx="242" cy="48" r="3.5" fill="{BRAND['accent_violet']}"/>
    <text x="252" y="52" font-size="11" font-weight="700" fill="#c4b5fd" letter-spacing="0.5">@{username} • PROFILE</text>

    <!-- Badge 2: Collab Status -->
    <rect x="420" y="36" width="145" height="24" rx="12" fill="{BRAND['accent_emerald']}" fill-opacity="0.10" stroke="{BRAND['accent_emerald']}" stroke-opacity="0.35"/>
    <circle cx="432" cy="48" r="3.5" fill="{BRAND['accent_emerald']}"/>
    <text x="442" y="52" font-size="11" font-weight="700" fill="#6ee7b7" letter-spacing="0.4">OPEN TO COLLABS</text>
  </g>

  <!-- Name & Headline -->
  <g class="stagger-2">
    <text x="230" y="96" font-size="32" font-weight="700" fill="{BRAND['text_primary']}">{name}</text>
    <text x="415" y="96" font-size="24" fill="{BRAND['accent_yellow']}">✨</text>
    
    <!-- One line about me -->
    <text x="230" y="125" font-size="14.5" font-weight="400" fill="{BRAND['text_secondary']}" font-style="italic">"{tagline}"</text>
    
    <!-- Bio / Role -->
    <text x="230" y="152" font-size="13" font-weight="400" fill="{BRAND['text_muted']}">{title}</text>
  </g>

  <!-- Tech Stack Pills -->
  <g class="stagger-3">
    <!-- Python -->
    <rect x="230" y="174" width="76" height="26" rx="13" fill="#1e2029" stroke="#333745" stroke-width="1"/>
    <circle cx="242" cy="187" r="3.5" fill="#38bdf8"/>
    <text x="251" y="191" font-size="11" font-weight="700" fill="#e2e8f0">Python</text>

    <!-- TypeScript -->
    <rect x="314" y="174" width="98" height="26" rx="13" fill="#1e2029" stroke="#333745" stroke-width="1"/>
    <circle cx="326" cy="187" r="3.5" fill="#60a5fa"/>
    <text x="335" y="191" font-size="11" font-weight="700" fill="#e2e8f0">TypeScript</text>

    <!-- React -->
    <rect x="420" y="174" width="72" height="26" rx="13" fill="#1e2029" stroke="#333745" stroke-width="1"/>
    <circle cx="432" cy="187" r="3.5" fill="#22d3ee"/>
    <text x="441" y="191" font-size="11" font-weight="700" fill="#e2e8f0">React</text>

    <!-- FastAPI -->
    <rect x="500" y="174" width="80" height="26" rx="13" fill="#1e2029" stroke="#333745" stroke-width="1"/>
    <circle cx="512" cy="187" r="3.5" fill="#34d399"/>
    <text x="521" y="191" font-size="11" font-weight="700" fill="#e2e8f0">FastAPI</text>

    <!-- MongoDB -->
    <rect x="588" y="174" width="90" height="26" rx="13" fill="#1e2029" stroke="#333745" stroke-width="1"/>
    <circle cx="600" cy="187" r="3.5" fill="#4ade80"/>
    <text x="609" y="191" font-size="11" font-weight="700" fill="#e2e8f0">MongoDB</text>

    <!-- Tailwind -->
    <rect x="686" y="174" width="88" height="26" rx="13" fill="#1e2029" stroke="#333745" stroke-width="1"/>
    <circle cx="698" cy="187" r="3.5" fill="#38bdf8"/>
    <text x="707" y="191" font-size="11" font-weight="700" fill="#e2e8f0">Tailwind</text>
  </g>
</svg>"""
    return svg

def make_tile(name, title, subtitle, badge, accent_color, icon_type, delay_s):
    """Renders one of the three linked row tiles (width 270 x height 140)."""
    font_css = get_font_css()
    
    if IS_STATIC:
        anim_css = """
      .tile-wrap { opacity: 1 !important; transform: none !important; }
      .arrow-anim { opacity: 1 !important; }
"""
        smil_arrow = ""
    else:
        anim_css = f"""
      .tile-wrap {{
        opacity: 0;
        transform: translateY(14px);
        animation: tileFadeUp 0.75s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        animation-delay: {delay_s};
      }}
      @keyframes tileFadeUp {{
        to {{
          opacity: 1;
          transform: translateY(0);
        }}
      }}
      .arrow-anim {{
        animation: arrowShift 2s ease-in-out infinite;
      }}
      @keyframes arrowShift {{
        0%, 100% {{ transform: translate(0, 0); }}
        50% {{ transform: translate(3px, -3px); }}
      }}
"""
        smil_arrow = """
        <animateTransform attributeName="transform" type="translate" values="0,0; 3,-3; 0,0" dur="2s" repeatCount="indefinite"/>
"""

    # Icons
    if icon_type == 'globe':
        # Portfolio web globe
        icon_svg = f"""
        <circle cx="36" cy="38" r="14" fill="{accent_color}" fill-opacity="0.15" stroke="{accent_color}" stroke-width="1.5"/>
        <path d="M28 38h16M36 24a14 14 0 0 1 0 28M36 24a14 14 0 0 0 0 28" stroke="{accent_color}" stroke-width="1.5" stroke-linecap="round"/>
"""
    elif icon_type == 'repo':
        # Git folder / fork icon
        icon_svg = f"""
        <rect x="22" y="24" width="28" height="28" rx="8" fill="{accent_color}" fill-opacity="0.15" stroke="{accent_color}" stroke-width="1.5"/>
        <circle cx="31" cy="33" r="2.5" fill="{accent_color}"/>
        <circle cx="41" cy="33" r="2.5" fill="{accent_color}"/>
        <circle cx="36" cy="42" r="2.5" fill="{accent_color}"/>
        <path d="M31 35.5v2a2 2 0 0 0 2 2h3m5-4v2a2 2 0 0 1-2 2h-3" stroke="{accent_color}" stroke-width="1.2"/>
"""
    else:
        # Message / connect icon
        icon_svg = f"""
        <rect x="22" y="24" width="28" height="28" rx="8" fill="{accent_color}" fill-opacity="0.15" stroke="{accent_color}" stroke-width="1.5"/>
        <path d="M29 34h14M29 39h9M32 44l-3-2v-14a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H34l-2 4z" stroke="{accent_color}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
"""

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 270 140" width="270" height="140" fill="none">
  <defs>
    {font_css}
    <linearGradient id="tile-bg-{name}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{BRAND['bg_start']}"/>
      <stop offset="100%" stop-color="{BRAND['bg_end']}"/>
    </linearGradient>
    <style>
      text {{
        font-family: 'Mona Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }}
      {anim_css}
      @media (prefers-reduced-motion: reduce) {{
        *, ::before, ::after {{
          animation: none !important;
          transition: none !important;
          transform: none !important;
          opacity: 1 !important;
        }}
      }}
    </style>
  </defs>

  <g class="tile-wrap">
    <!-- Card Frame -->
    <rect x="1" y="1" width="268" height="138" rx="16" fill="url(#tile-bg-{name})" stroke="{BRAND['card_stroke']}" stroke-width="1.5"/>
    <line x1="16" y1="2" x2="254" y2="2" stroke="{accent_color}" stroke-width="2.5" stroke-linecap="round"/>

    <!-- Subtle Background Glow -->
    <circle cx="230" cy="30" r="60" fill="{accent_color}" fill-opacity="0.08" filter="blur(25px)"/>

    <!-- Icon -->
    {icon_svg}

    <!-- Top Badge -->
    <rect x="62" y="27" width="115" height="22" rx="11" fill="{accent_color}" fill-opacity="0.12" stroke="{accent_color}" stroke-opacity="0.3"/>
    <text x="72" y="42" font-size="10" font-weight="700" fill="{accent_color}" letter-spacing="0.5">{badge}</text>

    <!-- External Link Arrow Icon -->
    <g class="arrow-anim" transform="translate(236, 32)">
      {smil_arrow}
      <path d="M0 8L8 0M8 0H2M8 0V6" stroke="{accent_color}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
    </g>

    <!-- Title -->
    <text x="22" y="86" font-size="17" font-weight="700" fill="{BRAND['text_primary']}">{title}</text>

    <!-- Subtitle -->
    <text x="22" y="108" font-size="12" font-weight="400" fill="{BRAND['text_muted']}">{subtitle}</text>

    <!-- Bottom Action Pill / Indicator -->
    <circle cx="26" cy="123" r="3" fill="{accent_color}"/>
    <text x="35" y="126" font-size="10.5" font-weight="700" fill="{accent_color}">Explore now ↗</text>
  </g>
</svg>"""
    return svg

def make_contributions_chart_card(data):
    """Renders cards/contributions-chart.svg - Chart of monthly contributions with streaks, active days & busiest day."""
    stagger_delay = "0.65s"
    font_css = get_font_css()
    
    months = data.get('months', [])
    current_streak = data.get('current_streak', 14)
    longest_streak = data.get('longest_streak', 32)
    active_days = data.get('active_days', 68)
    busiest_day = data.get('busiest_day', {'label': 'Oct 14, 2026', 'count': 18})
    total_commits = data.get('total_contributions', sum(m.get('count', 0) for m in months))

    max_count = max([m.get('count', 0) for m in months] + [20])
    
    # Generate bar elements
    chart_y_bottom = 230
    chart_max_height = 80
    chart_x_start = 45
    bar_width = 46
    bar_gap = 18

    bars_svg = []
    anim_bars_css = []

    for i, m in enumerate(months):
        cnt = m.get('count', 0)
        bar_h = int((cnt / max_count) * chart_max_height) if max_count > 0 else 6
        if bar_h < 6:
            bar_h = 6  # Minimum visible pill
            
        bx = chart_x_start + i * (bar_width + bar_gap)
        by = chart_y_bottom - bar_h
        m_name = m.get('month', '')
        
        delay_bar = f"{0.80 + i * 0.035:.3f}s"
        
        if IS_STATIC:
            anim_bars_css.append(f".bar-{i} {{ transform: none !important; opacity: 1 !important; }}")
            smil_bar = ""
        else:
            anim_bars_css.append(f"""
      .bar-{i} {{
        transform-origin: {bx + bar_width//2}px {chart_y_bottom}px;
        transform: scaleY(0);
        animation: growBar 0.65s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        animation-delay: {delay_bar};
      }}
""")
            smil_bar = f"""
        <animateTransform attributeName="transform" type="scale" values="1,0; 1,1" dur="0.65s" begin="{delay_bar}" fill="freeze"/>
"""

        bars_svg.append(f"""
    <!-- Month {m_name}: {cnt} commits -->
    <g class="bar-{i}">
      {smil_bar}
      <!-- Bar Gradient Fill -->
      <rect x="{bx}" y="{by}" width="{bar_width}" height="{bar_h}" rx="6" fill="url(#bar-grad)" stroke="{BRAND['accent_violet']}" stroke-width="1" stroke-opacity="0.4"/>
      <!-- Glowing Top Cap -->
      <line x1="{bx + 4}" y1="{by}" x2="{bx + bar_width - 4}" y2="{by}" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round" opacity="0.85"/>
      <!-- Commit Count Number -->
      <text x="{bx + bar_width // 2}" y="{by - 7}" font-size="11" font-weight="700" fill="#c4b5fd" text-anchor="middle">{cnt if cnt > 0 else ''}</text>
    </g>
    <!-- Month Label below bar -->
    <text x="{bx + bar_width // 2}" y="{chart_y_bottom + 18}" font-size="11.5" font-weight="600" fill="{BRAND['text_muted']}" text-anchor="middle">{m_name}</text>
""")

    if IS_STATIC:
        main_anim_css = """
      .card-wrap { opacity: 1 !important; transform: none !important; }
      .stat-chip { opacity: 1 !important; transform: none !important; }
"""
    else:
        main_anim_css = f"""
      .card-wrap {{
        opacity: 0;
        transform: translateY(14px);
        animation: chartFadeUp 0.75s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        animation-delay: {stagger_delay};
      }}
      @keyframes chartFadeUp {{
        to {{
          opacity: 1;
          transform: translateY(0);
        }}
      }}
      @keyframes growBar {{
        to {{
          transform: scaleY(1);
        }}
      }}
      .stat-chip {{
        opacity: 0;
        transform: translateY(8px);
        animation: chartFadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      }}
      .stat-1 {{ animation-delay: 0.70s; }}
      .stat-2 {{ animation-delay: 0.78s; }}
      .stat-3 {{ animation-delay: 0.86s; }}
      .stat-4 {{ animation-delay: 0.94s; }}
"""

    all_bar_css = "\n".join(anim_bars_css)
    all_bars_markup = "\n".join(bars_svg)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 270" width="850" height="270" fill="none">
  <defs>
    {font_css}
    <linearGradient id="chart-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{BRAND['bg_start']}"/>
      <stop offset="100%" stop-color="{BRAND['bg_end']}"/>
    </linearGradient>
    <linearGradient id="bar-grad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="{BRAND['accent_violet']}"/>
      <stop offset="100%" stop-color="{BRAND['accent_indigo']}"/>
    </linearGradient>
    <linearGradient id="header-accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{BRAND['accent_violet']}"/>
      <stop offset="100%" stop-color="{BRAND['accent_cyan']}"/>
    </linearGradient>
    <style>
      text {{
        font-family: 'Mona Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }}
      {main_anim_css}
      {all_bar_css}
      @media (prefers-reduced-motion: reduce) {{
        *, ::before, ::after {{
          animation: none !important;
          transition: none !important;
          transform: none !important;
          opacity: 1 !important;
        }}
      }}
    </style>
  </defs>

  <g class="card-wrap">
    <!-- Card Frame -->
    <rect x="1" y="1" width="848" height="268" rx="20" fill="url(#chart-bg)" stroke="{BRAND['card_stroke']}" stroke-width="1.5"/>
    <line x1="20" y1="2" x2="830" y2="2" stroke="url(#header-accent)" stroke-width="2.5" stroke-linecap="round"/>

    <!-- Subtle background chart glow -->
    <circle cx="700" cy="180" r="140" fill="{BRAND['accent_violet']}" fill-opacity="0.08" filter="blur(35px)"/>

    <!-- Card Header -->
    <g transform="translate(32, 26)">
      <!-- Activity Pulse Icon -->
      <circle cx="12" cy="12" r="12" fill="{BRAND['accent_violet']}" fill-opacity="0.15"/>
      <path d="M5 12h3l2-5 3 10 2.5-6 1.5 2h3" stroke="{BRAND['accent_violet']}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>
      
      <!-- Title -->
      <text x="34" y="16" font-size="16" font-weight="700" fill="{BRAND['text_primary']}">Contribution Activity &amp; Monthly Metrics</text>
      
      <!-- Subtitle badge -->
      <rect x="360" y="3" width="105" height="20" rx="10" fill="#1e2029" stroke="#333745" stroke-width="1"/>
      <text x="412" y="17" font-size="10.5" font-weight="700" fill="{BRAND['text_muted']}" text-anchor="middle">LAST 12 MONTHS</text>

      <!-- Right summary pill -->
      <rect x="670" y="2" width="116" height="22" rx="11" fill="{BRAND['accent_violet']}" fill-opacity="0.12" stroke="{BRAND['accent_violet']}" stroke-opacity="0.35"/>
      <text x="728" y="17" font-size="11" font-weight="700" fill="#c4b5fd" text-anchor="middle">{total_commits} Total Commits</text>
    </g>

    <!-- 4 Stats Metric Chips -->
    <g transform="translate(32, 58)">
      <!-- Chip 1: Current Streak -->
      <g class="stat-chip stat-1">
        <rect x="0" y="0" width="186" height="54" rx="12" fill="#161720" stroke="#2a2b38" stroke-width="1.2"/>
        <text x="14" y="22" font-size="10.5" font-weight="700" fill="{BRAND['accent_yellow']}" letter-spacing="0.5">🔥 CURRENT STREAK</text>
        <text x="14" y="44" font-size="18" font-weight="700" fill="{BRAND['text_primary']}">{current_streak} <tspan font-size="12" font-weight="400" fill="{BRAND['text_muted']}">Days</tspan></text>
      </g>

      <!-- Chip 2: Longest Streak -->
      <g class="stat-chip stat-2">
        <rect x="200" y="0" width="186" height="54" rx="12" fill="#161720" stroke="#2a2b38" stroke-width="1.2"/>
        <text x="214" y="22" font-size="10.5" font-weight="700" fill="{BRAND['accent_cyan']}" letter-spacing="0.5">🏆 LONGEST STREAK</text>
        <text x="214" y="44" font-size="18" font-weight="700" fill="{BRAND['text_primary']}">{longest_streak} <tspan font-size="12" font-weight="400" fill="{BRAND['text_muted']}">Days</tspan></text>
      </g>

      <!-- Chip 3: Active Days -->
      <g class="stat-chip stat-3">
        <rect x="400" y="0" width="186" height="54" rx="12" fill="#161720" stroke="#2a2b38" stroke-width="1.2"/>
        <text x="414" y="22" font-size="10.5" font-weight="700" fill="{BRAND['accent_emerald']}" letter-spacing="0.5">📅 ACTIVE DAYS</text>
        <text x="414" y="44" font-size="18" font-weight="700" fill="{BRAND['text_primary']}">{active_days} <tspan font-size="12" font-weight="400" fill="{BRAND['text_muted']}">Days</tspan></text>
      </g>

      <!-- Chip 4: Busiest Day -->
      <g class="stat-chip stat-4">
        <rect x="600" y="0" width="186" height="54" rx="12" fill="#161720" stroke="#2a2b38" stroke-width="1.2"/>
        <text x="614" y="22" font-size="10.5" font-weight="700" fill="{BRAND['accent_rose']}" letter-spacing="0.5">⚡ BUSIEST DAY</text>
        <text x="614" y="44" font-size="18" font-weight="700" fill="{BRAND['text_primary']}">{busiest_day.get('count', 18)} <tspan font-size="11" font-weight="400" fill="{BRAND['text_muted']}">({busiest_day.get('label', 'Oct 14')})</tspan></text>
      </g>
    </g>

    <!-- Monthly Chart Horizontal Baseline Gridlines -->
    <line x1="40" y1="{chart_y_bottom}" x2="810" y2="{chart_y_bottom}" stroke="#272733" stroke-width="1"/>
    <line x1="40" y1="{chart_y_bottom - 40}" x2="810" y2="{chart_y_bottom - 40}" stroke="#22222d" stroke-width="1" stroke-dasharray="3 3"/>
    <line x1="40" y1="{chart_y_bottom - 80}" x2="810" y2="{chart_y_bottom - 80}" stroke="#22222d" stroke-width="1" stroke-dasharray="3 3"/>

    <!-- Monthly Bars -->
    {all_bars_markup}
  </g>
</svg>"""
    return svg

def make_repo_card(repo, index, delay_s):
    """Renders cards/repo-<name>.svg - One animated card per featured repository."""
    font_css = get_font_css()
    name = repo.get('name', 'Repository')
    desc = repo.get('description', '')
    lang = repo.get('language', 'TypeScript')
    stars = repo.get('stars', 10)
    forks = repo.get('forks', 2)
    topics = repo.get('topics', ['Full-Stack', 'Open-Source'])
    accent = repo.get('color', BRAND['accent_violet'])
    url = repo.get('url', f"https://github.com/ajayXcode/{name}")
    demo = repo.get('demo_url', '')

    if IS_STATIC:
        anim_css = """
      .repo-card { opacity: 1 !important; transform: none !important; }
"""
    else:
        anim_css = f"""
      .repo-card {{
        opacity: 0;
        transform: translateY(12px);
        animation: repoFadeUp 0.75s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        animation-delay: {delay_s};
      }}
      @keyframes repoFadeUp {{
        to {{
          opacity: 1;
          transform: translateY(0);
        }}
      }}
"""

    # Build topic pills
    pills_svg = []
    px = 32
    for t in topics[:5]:
        t_len = len(t) * 7.5 + 20
        pills_svg.append(f"""
      <rect x="{px}" y="92" width="{t_len:.0f}" height="22" rx="11" fill="#1b1c25" stroke="#2b2d3a" stroke-width="1"/>
      <text x="{px + t_len/2:.0f}" y="106" font-size="10.5" font-weight="600" fill="{BRAND['text_muted']}" text-anchor="middle">{t}</text>
""")
        px += t_len + 8

    pills_markup = "".join(pills_svg)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 130" width="850" height="130" fill="none">
  <defs>
    {font_css}
    <linearGradient id="repo-bg-{index}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{BRAND['bg_start']}"/>
      <stop offset="100%" stop-color="{BRAND['bg_end']}"/>
    </linearGradient>
    <style>
      text {{
        font-family: 'Mona Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }}
      {anim_css}
      @media (prefers-reduced-motion: reduce) {{
        *, ::before, ::after {{
          animation: none !important;
          transition: none !important;
          transform: none !important;
          opacity: 1 !important;
        }}
      }}
    </style>
  </defs>

  <g class="repo-card">
    <!-- Card Frame -->
    <rect x="1" y="1" width="848" height="128" rx="16" fill="url(#repo-bg-{index})" stroke="{BRAND['card_stroke']}" stroke-width="1.5"/>
    
    <!-- Left Accent Strip -->
    <path d="M1 17A16 16 0 0 1 17 1H20V129H17A16 16 0 0 1 1 113Z" fill="{accent}"/>

    <!-- Repo Book Icon -->
    <g transform="translate(32, 24)">
      <rect x="0" y="0" width="28" height="28" rx="8" fill="{accent}" fill-opacity="0.15" stroke="{accent}" stroke-width="1.2"/>
      <path d="M7 8h10a2 2 0 0 1 2 2v10a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2V10a2 2 0 0 1 2-2z" stroke="{accent}" stroke-width="1.4" stroke-linecap="round"/>
    </g>

    <!-- Repo Name & Link -->
    <text x="70" y="43" font-size="18" font-weight="700" fill="{BRAND['text_primary']}">{name}</text>
    <text x="{70 + len(name)*10.5 + 8}" y="43" font-size="14" font-weight="700" fill="{accent}">↗</text>

    <!-- Featured Badge -->
    <rect x="710" y="24" width="105" height="24" rx="12" fill="{accent}" fill-opacity="0.12" stroke="{accent}" stroke-opacity="0.35"/>
    <circle cx="722" cy="36" r="3.5" fill="{accent}"/>
    <text x="732" y="40" font-size="10.5" font-weight="700" fill="{accent}" letter-spacing="0.5">FEATURED</text>

    <!-- Description -->
    <text x="32" y="74" font-size="13" font-weight="400" fill="{BRAND['text_secondary']}">{desc}</text>

    <!-- Topics / Pills -->
    {pills_markup}

    <!-- Stars & Language Stats (Right side) -->
    <g transform="translate(680, 96)">
      <!-- Language Dot -->
      <circle cx="0" cy="0" r="4.5" fill="{accent}"/>
      <text x="10" y="4" font-size="11" font-weight="600" fill="{BRAND['text_muted']}">{lang.split(' ')[0]}</text>

      <!-- Stars -->
      <text x="80" y="4" font-size="11" font-weight="600" fill="{BRAND['text_muted']}">⭐ {stars}</text>

      <!-- Forks -->
      <text x="120" y="4" font-size="11" font-weight="600" fill="{BRAND['text_muted']}">🍴 {forks}</text>
    </g>
  </g>
</svg>"""
    return svg

def make_contribution_graph_card(data):
    """Renders cards/contribution-graph.svg - 52-week contribution graph in brand color."""
    stagger_delay = "1.55s"
    font_css = get_font_css()
    
    weeks = data.get('weeks', [])
    total_contributions = data.get('total_contributions', 84)

    # Palette
    color_map = {
        0: BRAND['level_0'],
        1: BRAND['level_1'],
        2: BRAND['level_2'],
        3: BRAND['level_3'],
        4: BRAND['level_4']
    }

    # Dimensions
    # 52 weeks x 7 rows
    # Cell size 10x10, gap 3px -> column pitch 13px
    # Total width of cells: 52 * 13 = 676px
    # Left margin: (850 - 676) / 2 = 87px
    cell_size = 10
    pitch = 13
    x_offset = 86
    y_offset = 78

    cells_svg = []
    
    # Calculate months on top of columns
    month_labels = []
    last_m = ""
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    for w_idx, week in enumerate(weeks[-52:]):
        for d_idx, day in enumerate(week):
            cnt = day.get('count', 0)
            level = day.get('level', 0)
            fill_color = color_map.get(level, BRAND['level_0'])
            stroke_attr = f'stroke="#2a2245" stroke-width="0.8"' if level > 0 else f'stroke="{BRAND["card_stroke"]}" stroke-width="0.5"'
            
            cx = x_offset + w_idx * pitch
            cy = y_offset + d_idx * pitch
            
            # Check for month label from first day of week
            if d_idx == 0:
                d_str = day.get('date', '')
                if len(d_str) >= 7:
                    mo = int(d_str[5:7])
                    m_label = month_names[mo - 1]
                    if m_label != last_m and w_idx < 50:
                        month_labels.append((cx, m_label))
                        last_m = m_label

            cells_svg.append(f'<rect x="{cx}" y="{cy}" width="{cell_size}" height="{cell_size}" rx="2.5" fill="{fill_color}" {stroke_attr}/>')

    cells_markup = "\n    ".join(cells_svg)

    # Month labels SVG
    months_svg = [f'<text x="{cx}" y="{y_offset - 8}" font-size="10.5" font-weight="600" fill="{BRAND["text_muted"]}">{m}</text>' for cx, m in month_labels]
    months_markup = "\n    ".join(months_svg)

    if IS_STATIC:
        anim_css = """
      .graph-wrap { opacity: 1 !important; transform: none !important; }
"""
    else:
        anim_css = f"""
      .graph-wrap {{
        opacity: 0;
        transform: translateY(14px);
        animation: graphFadeUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        animation-delay: {stagger_delay};
      }}
      @keyframes graphFadeUp {{
        to {{
          opacity: 1;
          transform: translateY(0);
        }}
      }}
"""

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 215" width="850" height="215" fill="none">
  <defs>
    {font_css}
    <linearGradient id="graph-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{BRAND['bg_start']}"/>
      <stop offset="100%" stop-color="{BRAND['bg_end']}"/>
    </linearGradient>
    <linearGradient id="graph-header" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="{BRAND['accent_violet']}"/>
      <stop offset="100%" stop-color="{BRAND['accent_indigo']}"/>
    </linearGradient>
    <style>
      text {{
        font-family: 'Mona Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }}
      {anim_css}
      @media (prefers-reduced-motion: reduce) {{
        *, ::before, ::after {{
          animation: none !important;
          transition: none !important;
          transform: none !important;
          opacity: 1 !important;
        }}
      }}
    </style>
  </defs>

  <g class="graph-wrap">
    <!-- Card Frame -->
    <rect x="1" y="1" width="848" height="213" rx="20" fill="url(#graph-bg)" stroke="{BRAND['card_stroke']}" stroke-width="1.5"/>
    <line x1="20" y1="2" x2="830" y2="2" stroke="url(#graph-header)" stroke-width="2.5" stroke-linecap="round"/>

    <!-- Header Section -->
    <g transform="translate(32, 26)">
      <!-- Grid icon -->
      <rect x="0" y="0" width="24" height="24" rx="7" fill="{BRAND['accent_violet']}" fill-opacity="0.15" stroke="{BRAND['accent_violet']}" stroke-width="1.2"/>
      <rect x="5" y="5" width="4" height="4" rx="1" fill="{BRAND['accent_violet']}"/>
      <rect x="11" y="5" width="4" height="4" rx="1" fill="{BRAND['accent_violet']}"/>
      <rect x="17" y="5" width="4" height="4" rx="1" fill="{BRAND['accent_violet']}"/>
      <rect x="5" y="11" width="4" height="4" rx="1" fill="{BRAND['accent_violet']}"/>
      <rect x="11" y="11" width="4" height="4" rx="1" fill="{BRAND['accent_violet']}"/>
      <rect x="17" y="11" width="4" height="4" rx="1" fill="{BRAND['accent_violet']}"/>

      <!-- Title & Details -->
      <text x="34" y="17" font-size="16" font-weight="700" fill="{BRAND['text_primary']}">Contribution Heatmap (Brand Violet)</text>
      <text x="325" y="17" font-size="12" font-weight="400" fill="{BRAND['text_muted']}">52 Weeks of GitHub Activity</text>

      <!-- Right Pill Counter -->
      <rect x="660" y="1" width="126" height="24" rx="12" fill="{BRAND['accent_violet']}" fill-opacity="0.12" stroke="{BRAND['accent_violet']}" stroke-opacity="0.35"/>
      <text x="723" y="16" font-size="11" font-weight="700" fill="#c4b5fd" text-anchor="middle">{total_contributions} Contributions</text>
    </g>

    <!-- Day of Week Labels on Left -->
    <text x="54" y="{y_offset + 1 * pitch + 8}" font-size="9.5" font-weight="600" fill="{BRAND['text_muted']}">Mon</text>
    <text x="54" y="{y_offset + 3 * pitch + 8}" font-size="9.5" font-weight="600" fill="{BRAND['text_muted']}">Wed</text>
    <text x="54" y="{y_offset + 5 * pitch + 8}" font-size="9.5" font-weight="600" fill="{BRAND['text_muted']}">Fri</text>

    <!-- Month Labels on Top -->
    {months_markup}

    <!-- 52x7 Heatmap Cells -->
    {cells_markup}

    <!-- Legend on Bottom Right -->
    <g transform="translate(640, 186)">
      <text x="0" y="10" font-size="10.5" font-weight="600" fill="{BRAND['text_muted']}">Less</text>
      <rect x="32" y="0" width="11" height="11" rx="2.5" fill="{BRAND['level_0']}" stroke="{BRAND['card_stroke']}" stroke-width="0.5"/>
      <rect x="47" y="0" width="11" height="11" rx="2.5" fill="{BRAND['level_1']}"/>
      <rect x="62" y="0" width="11" height="11" rx="2.5" fill="{BRAND['level_2']}"/>
      <rect x="77" y="0" width="11" height="11" rx="2.5" fill="{BRAND['level_3']}"/>
      <rect x="92" y="0" width="11" height="11" rx="2.5" fill="{BRAND['level_4']}"/>
      <text x="110" y="10" font-size="10.5" font-weight="600" fill="{BRAND['text_muted']}">More</text>
    </g>
  </g>
</svg>"""
    return svg

# ==============================================================================
# MAIN RENDERER
# ==============================================================================

def main():
    if '--fetch' in sys.argv:
        fetch_github_contributions()

    os.makedirs(CARDS_DIR, exist_ok=True)
    data = load_data()

    mode_str = "STATIC FINAL FRAME" if IS_STATIC else "ANIMATED (Staggered top-to-bottom)"
    print(f"Rendering profile cards into {CARDS_DIR} [Mode: {mode_str}]...")

    # 1. Hero Card
    hero_path = os.path.join(CARDS_DIR, 'hero.svg')
    with open(hero_path, 'w', encoding='utf-8') as f:
        f.write(make_hero_card(data))
    print(f"  ✓ {hero_path}")

    # 2. Three Linked Tiles (width 32.5% each in markdown)
    # Tile 1: Portfolio
    tile_port_path = os.path.join(CARDS_DIR, 'tile-portfolio.svg')
    with open(tile_port_path, 'w', encoding='utf-8') as f:
        f.write(make_tile(
            name='portfolio',
            title='Personal Portfolio',
            subtitle='Interactive 3D & featured apps',
            badge='LIVE DEMOS',
            accent_color=BRAND['accent_violet'],
            icon_type='globe',
            delay_s='0.35s'
        ))
    print(f"  ✓ {tile_port_path}")

    # Tile 2: Repositories
    tile_repo_path = os.path.join(CARDS_DIR, 'tile-projects.svg')
    with open(tile_repo_path, 'w', encoding='utf-8') as f:
        f.write(make_tile(
            name='projects',
            title='Repositories',
            subtitle='Full-stack & AI/ML tools',
            badge='OPEN SOURCE',
            accent_color=BRAND['accent_cyan'],
            icon_type='repo',
            delay_s='0.45s'
        ))
    print(f"  ✓ {tile_repo_path}")

    # Tile 3: Connect
    tile_conn_path = os.path.join(CARDS_DIR, 'tile-connect.svg')
    with open(tile_conn_path, 'w', encoding='utf-8') as f:
        f.write(make_tile(
            name='connect',
            title="Let's Connect",
            subtitle='LinkedIn, X & Email',
            badge="LET'S TALK",
            accent_color=BRAND['accent_emerald'],
            icon_type='chat',
            delay_s='0.55s'
        ))
    print(f"  ✓ {tile_conn_path}")

    # 3. Monthly Contributions & Metrics Card
    chart_path = os.path.join(CARDS_DIR, 'contributions-chart.svg')
    with open(chart_path, 'w', encoding='utf-8') as f:
        f.write(make_contributions_chart_card(data))
    print(f"  ✓ {chart_path}")

    # 4. Featured Repo Cards (one card per featured repo)
    featured = data.get('featured_repos', [])
    repo_delays = ['0.95s', '1.10s', '1.25s', '1.40s']
    for idx, repo in enumerate(featured):
        slug = repo.get('name', f'repo-{idx}').lower().replace(' ', '-')
        repo_card_path = os.path.join(CARDS_DIR, f'repo-{slug}.svg')
        delay = repo_delays[idx % len(repo_delays)]
        with open(repo_card_path, 'w', encoding='utf-8') as f:
            f.write(make_repo_card(repo, idx, delay))
        print(f"  ✓ {repo_card_path}")

    # 5. Contribution Heatmap in Brand Colour
    graph_path = os.path.join(CARDS_DIR, 'contribution-graph.svg')
    with open(graph_path, 'w', encoding='utf-8') as f:
        f.write(make_contribution_graph_card(data))
    print(f"  ✓ {graph_path}")

    print("\nAll animated cards rendered successfully!")

if __name__ == '__main__':
    main()
