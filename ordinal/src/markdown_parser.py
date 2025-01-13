import os
import re
import mistune
import yaml
from datetime import datetime
from typing import List, Dict, Any
from src.base_utils import setup_logger, ensure_directory, content_dir

logger = setup_logger("markdown_parser", "logs/markdown_parser.log")


def markdown_output(md_fp: str, backlinks: Dict[str, List[str]]) -> None:
    try:
        logger.info(f"Logging Markdown output for: {md_fp}")
        with open(md_fp, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        try:
            html_content = mistune.create_markdown()(markdown_content)
        except Exception as err:
            logger.error(f"Error converting Markdown to HTML: {err}")
            return

        md_name = os.path.splitext(os.path.basename(md_fp))[0].replace(" ", "-").lower()
        file_backlinks = backlinks.get(md_name, [])

        log_file = os.path.join("logs", "markdown_output.log")
        ensure_directory(os.path.dirname(log_file))
        with open(log_file, "a", encoding="utf-8") as log:
            log.write("\n\n=== Markdown File: {} ===\n".format(md_fp))
            log.write("=== Raw Markdown Content ===\n")
            log.write(markdown_content)
            log.write("\n\n=== Converted HTML Content ===\n")
            log.write(html_content)
            log.write("\n\n=== Backlinks ===\n")
            if file_backlinks:
                log.write("\n".join(file_backlinks))
            else:
                log.write("No backlinks found.")
    except Exception as err:
        logger.error(f"Error logging Markdown output for: {md_fp}: {err}")


def parse_backlink(source: str, target: str, backlinks: Dict[str, List[str]]) -> None:
    try:
        source_key = os.path.splitext(os.path.basename(source))[0].replace(" ", "-").lower()
        target_key = target.replace(" ", "-").lower()

        if source_key == "index":
            source_key = ""

        if target_key not in backlinks:
            backlinks[target_key] = []
        if source_key not in backlinks[target_key]:
            backlinks[target_key].append(source_key)

        logger.info(f"Backlinks for '{target_key}': {backlinks[target_key]}")
    except Exception as err:
        logger.error(f"Error parsing backlink from '{source}' to '{target}': {err}")


def parse_wikilinks(source_page: str, text: str, backlinks: Dict[str, List[str]]) -> str:
    try:
        pattern = r"\[\[(.*?)\]\]"

        def replace_link(match):
            link_text = match.group(1)
            slug = link_text.replace(" ", "-").lower()
            logger.info(f"Backlinks source: {source_page}, link text: {link_text}")
            parse_backlink(source_page, link_text, backlinks)
            return f'<a href="/{slug}.html">{link_text}</a>'

        return re.sub(pattern, replace_link, text)
    except Exception as err:
        logger.error(f"Error parsing wikilinks in text: {err}")
        return text


def parse_external_links(text: str) -> str:
    try:
        pattern = r"\[(.*?)\]\((https?://.*?)\)"

        def replace_link(match):
            link_text = match.group(1)
            url = match.group(2)
            return f'<a href="{url}" target="_blank">{link_text}</a>'

        return re.sub(pattern, replace_link, text)
    except Exception as err:
        logger.error(f"Error parsing external links in text: {err}")
        return text


def parse_articles(md_content: str, page_name: str, backlinks: Dict[str, List[str]]) -> dict:
    articles = []
    current_article = None
    footnotes = {}
    toc = []

    try:
        processed_content, footnotes = parse_footnotes(md_content)

        for line in processed_content.split("\n"):
            if line.startswith("## "):
                heading_text = line[3:].strip()
                anchor = heading_text.replace(" ", "-").lower()
                toc.append({"text": heading_text, "anchor": anchor, "level": 2})
                line = f'<h2 id="{anchor}">{heading_text}</h2>'

                if current_article:
                    articles.append(current_article)
                current_article = {"header": line, "sections": []}

            elif line.startswith("### "):
                heading_text = line[4:].strip()
                anchor = heading_text.replace(" ", "-").lower()
                toc.append({"text": heading_text, "anchor": anchor, "level": 3})
                line = f'<h3 id="{anchor}">{heading_text}</h3>'

                if current_article:
                    current_article["sections"].append(line)

            elif current_article and line.strip():
                processed_line = parse_wikilinks(page_name, line.strip(), backlinks)
                processed_line = parse_external_links(processed_line)
                current_article["sections"].append(processed_line)

        if current_article:
            articles.append(current_article)

    except Exception as err:
        logger.error(f"Error parsing articles: {err}")

    return {"articles": articles, "footnotes": footnotes, "toc": toc}


def parse_frontmatter(md_fp: str) -> Dict[str, Any]:
    try:
        with open(md_fp, "r", encoding="utf-8") as f:
            md_content = f.read()

        frontmatter_match = re.match(r"---\n(.*?)\n---\n(.*)", md_content, re.S)
        if frontmatter_match:
            frontmatter = yaml.safe_load(frontmatter_match.group(1))
            content = frontmatter_match.group(2).strip()
        else:
            frontmatter = {}
            content = md_content

        for key in ["created", "last_modified"]:
            if key in frontmatter and isinstance(frontmatter[key], (datetime, str)):
                frontmatter[key] = str(frontmatter[key])

        return {"frontmatter": frontmatter, "content": content}
    except Exception as err:
        logger.error(f"Error parsing frontmatter in file {md_fp}: {err}")
        return {"frontmatter": {}, "content": ""}


def parse_footnotes(content: str):
    try:
        logger.info("Starting to extract footnotes.")

        footnote_pattern = re.compile(r"\[\^(\d+)\]: (.+)")
        footnotes = {match.group(1): match.group(2) for match in footnote_pattern.finditer(content)}
        logger.info(f"Extracted footnotes: {footnotes}")

        content = footnote_pattern.sub("", content)

        footnote_ref_pattern = re.compile(r"\[\^(\d+)\]")

        def replace_ref(match):
            ref_id = match.group(1)
            return f'<a href="#footnote-{ref_id}" id="ref-{ref_id}" class="footnote-ref">[^{ref_id}]</a>'

        content = footnote_ref_pattern.sub(replace_ref, content)
        logger.info("Replaced inline footnote references.")

        return content.strip(), footnotes
    except Exception as err:
        logger.error(f"Error processing footnotes: {err}")
        return content, {}


def parse_related(frontmatter: dict) -> list[dict]:
    try:
        related = []
        # division = frontmatter.get("division", "")
        domain = frontmatter.get("domain", "")

        # if isinstance(division, str):
        #     division = [division]
        # elif not isinstance(division, list):
        #     division = []

        if isinstance(domain, str):
            domain = [domain]
        elif not isinstance(domain, list):
            domain = []

        # division = [d.lower() for d in division if isinstance(d, str)]
        domain = [d.lower() for d in domain if isinstance(d, str)]

        # logger.debug(f"Looking for related articles with Division: {division}, Domain: {domain}.")
        logger.info(f"Looking for related articles with Domain: {domain}.")

        # if not division and not domain:
        #     logger.info("No Division or Domain specified in frontmatter. Returning empty list.")
        #     return related

        for root, _, files in os.walk(content_dir):
            for file in files:
                if file.endswith(".md"):
                    markdown_path = os.path.join(root, file)
                    try:
                        parsed_frontmatter = parse_frontmatter(markdown_path)
                        file_frontmatter = parsed_frontmatter.get("frontmatter", {})
                        # file_divisions = file_frontmatter.get("division", "")
                        file_domains = file_frontmatter.get("domain", "")

                        # if isinstance(file_divisions, str):
                        #     file_divisions = [file_divisions]
                        # elif not isinstance(file_divisions, list):
                        #     file_divisions = []

                        if isinstance(file_domains, str):
                            file_domains = [file_domains]
                        elif not isinstance(file_domains, list):
                            file_domains = []

                        # file_divisions = [div.lower() for div in file_divisions if isinstance(div, str)]
                        file_domains = [dom.lower() for dom in file_domains if isinstance(dom, str)]

                        # if set(division) & set(file_divisions):
                        #     logger.info(f"Match found for Division in file: {markdown_path}")
                        #     related.append(
                        #         {
                        #             "title": file_frontmatter.get("title", "Untitled"),
                        #             "url": markdown_path.replace(content_dir, "").replace(".md", ".html"),
                        #         }
                        #     )
                        if set(domain) & set(file_domains):
                            logger.info(f"Match found for Domain in file: {markdown_path}")
                            related.append(
                                {
                                    "title": file_frontmatter.get("title", "Untitled"),
                                    "url": markdown_path.replace(content_dir, "").replace(".md", ".html"),
                                }
                            )
                    except Exception as parse_error:
                        logger.error(f"Error parsing frontmatter for file {markdown_path}: {parse_error}")

        logger.info(f"Related articles found: {len(related)}")
        return related
    except Exception as general_error:
        logger.error(f"Error in parse_related: {general_error}", exc_info=True)
        return []
