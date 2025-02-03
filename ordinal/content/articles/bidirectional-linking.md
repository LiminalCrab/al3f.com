---
title: Bidirectional Linking
description: "Two-way connected hyerplinks"
division: ["Writing"]
domain: "Meta"
worked: "0.0h"
created: 2025-02-02 02:29:36
last_modified: 2025-02-02 02:29:36
template: "wiki.html"
---

## Bidirectional Linking

Most links on the web are one-way. Page A links to Page B, but Page B has no idea that Page A exists. This is how standard hyperlinks work. References go forward, never backward.

Bidirectional links work differently. If Page A links to Page B, Page B automatically links back to Page A. This creates a two-way connection, making it easier to track relationships between linked content.

Bidirectional links keep ideas connected without needing to manually track references. This makes it easier to see how different thoughts, notes, and pages relate to each other.

When I used Vimwiki, every link I made was one-directional unless I manually added a backlink. This meant that if I referenced an idea in another note, I had to remember to update the original note with a return link, or it would be lost in a growing collection of pages.

Dendron in VS Code was different. It automatically displayed backlinks in a sidebar, showing me everywhere a note was referenced without extra effort. It was a massive improvement. Unfortunately, Dendron is no longer actively developed, so I moved to Obsidian, which does the same thing, link a note, and it will track that connection from both sides.

I made sure to support automatic bidirectional linking. If an entry links to another, that linked entry will also display its backlinks. This keeps everything connected, making it easier to navigate ideas without manually maintaining links.

[Source](https://screensresearchhypertext.com/A-Brief-History-of-Hypertext?stackedPages=%2FBidirectional-Links)

See: [[hypertext]]
