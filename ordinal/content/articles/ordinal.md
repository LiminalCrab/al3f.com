---
title: Ordinal
description: "This page is under construction."
division: ["Writing"]
domain: "Unknown"
worked: "0.0h"
created: 2025-01-30 11:49:56
last_modified: 2025-01-30 11:49:56
template: "wiki.html"
---

## Ordinal

Ordinal is a static site generator designed for **speed**, **reliability**, and **accessibility**. It is written in Python and generates a structured, interlinked wiki from Markdown without dependencies beyond a standard POSIX environment. The system is optimized for offline use, requires no JavaScript and relying entirely on static assets.

The generator handles wikilinks, backlinks, frontmatter metadata, and template-driven rendering, ensuring that every document is self-contained and properly linked. Markdown files are automatically converted into structured HTML pages, while the directory layout is preserved in the output.

Ordinal enforces link correctness, resolving all internal references at build time. Broken links are automatically detected and resolved, with missing pages generated as placeholders. The system tracks backlinks dynamically, ensuring that referenced pages always display their incoming links.

The build process is atomic. Each regeneration ensures that stale content is never served, with last-modified timestamps enforcing strict reprocessing when Markdown files or templates change. Navigation is deterministic, with all internal links resolving relative to `/ordinal/public/`