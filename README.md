# SEO Operating System

AI-powered SEO and content intelligence system for news-theworld.com.

## Overview

SEO Operating System is a Python-based platform designed to collect website data, analyze SEO opportunities, research keywords, generate article structures, and prepare content for publication.

## Current Features

- Blogger data collection
- Google Search Console integration
- Sitemap analysis
- SEO site reporting
- Content opportunity analysis
- AI-assisted article generation
- Local fallback when AI is unavailable
- Knowledge base for SEO rules and writing style
- Article templates
- SQLite database

## Architecture

```text
SEO OS
│
├── agents/
│   ├── blogger_connector.py
│   ├── gsc_connector.py
│   ├── research_engine.py
│   ├── site_report.py
│   ├── sitemap_parser.py
│   └── writing_engine.py
│
├── config/
├── knowledge/
├── templates/
├── main.py
└── requirements.txt
