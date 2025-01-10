# MIT License

# Copyright (c) 2024 Aleph Ohara

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import argparse
import logging
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Any
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import mistune
import yaml
import re


base_dir = os.path.dirname(os.path.abspath(__file__))
content_dir = os.path.join(base_dir, "content")
templates_dir = os.path.join(base_dir, "src", "templates")
public_dir = os.path.join(base_dir, "public")
snapshots_dir = os.path.join(base_dir, "snapshots")
backlinks = {}
# external_links = {}

env = Environment(loader=FileSystemLoader(templates_dir))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("main.log"),
        logging.StreamHandler(),
    ],
)


def ensure_directory(path: str) -> None:
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as err:
        logging.error(f"Error ensuring directory {path}: {err}")


def markdown_output(md_fp: str, backlinks: Dict[str, List[str]]) -> None:
    try:
        with open(md_fp, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        try:
            html_content = mistune.create_markdown()(markdown_content)
        except Exception as err:
            logging.error(f"Error converting Markdown to HTML: {err}")
            return

        md_name = os.path.splitext(os.path.basename(md_fp))[0].replace(" ", "-").lower()
        file_backlinks = backlinks.get(md_name, [])

        log_file = os.path.join(base_dir, "markdown_output.log")
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
        print(f"Error logging Markdown output for: {md_fp}")
        logging.error(f"Error logging Markdown output from {md_fp}: {err}")


# def convert_markdown(md_fp: str) -> str:
#     with open(md_fp, "r", encoding="utf-8") as f:
#         markdown_content = f.read()
#     return mistune.create_markdown()(markdown_content)


def generate_missing() -> None:
    template_fp = os.path.join(base_dir, "src", "templates", "template.md")
    try:
        if not os.path.exists(template_fp):
            logging.error(f"Template file not found: {template_fp}")
            return

        with open(tem, "r", encoding="utf-8") as template_file:
            template_content = template_file.read()

        for root, _, files in os.walk(content_dir):
            for file in files:
                if file.endswith(".md"):
                    md_fp = os.path.join(root, file)
                    with open(md_fp, "r", encoding="utf-8") as f:
                        markdown_content = f.read()

                    pattern = r"\[\[(.*?)\]\]"
                    wikilinks = re.findall(pattern, markdown_content)

                    if wikilinks:
                        parent_dir = os.path.basename(os.path.dirname(md_fp))
                        default_category = "articles"
                        category = (
                            parent_dir if parent_dir != "content" else default_category
                        )
                        category_dir = os.path.join(content_dir, category)

                        ensure_directory(category_dir)

                        for link in wikilinks:
                            filename = f"{link.replace(' ', '-').lower()}.md"
                            filepath = os.path.join(category_dir, filename)

                            if not os.path.exists(filepath):
                                title = link.title()
                                frontmatter = template_content.format(
                                    title=title,
                                    created=datetime.now().strftime(
                                        "%Y-%m-%d %H:%M:%S"
                                    ),
                                    last_modified=datetime.now().strftime(
                                        "%Y-%m-%d %H:%M:%S"
                                    ),
                                )
                                with open(filepath, "w", encoding="utf-8") as new_file:
                                    new_file.write(frontmatter)
                                logging.info(f"Created missing file: {filepath}")
                            else:
                                logging.info(f"File already exists: {filepath}")

    except Exception as err:
        logging.error(f"Error during generate_missing: {err}")


def kill_orphans(content_dir: str, public_dir: str) -> None:
    """
    This deletes HTML files if the corresponding markdown files no longer exists...
    """
    try:
        md_files = {
            os.path.splittext(file)[0]
            for root, _, files in os.walk(content_dir)
            for file in files
            if file.endswith(".md")
        }

        for root, _, files in os.walk(public_dir):
            for file in files:
                if file.endswith(".html"):
                    html_basename = os.path.splitext(file)[0]
                    if html_basename not in md_files:
                        orphan_html_fp = os.path.join(root, file)
                        os.remove(orphan_html_fp)
                        logging.info(f"Deleted orphaned HTML file: {orphan_html_fp}")
    except Exception as err:
        logging.error(f"Error during cleanup of orphaned HTMl files: {err}")


def get_categories() -> List[str]:
    """
    A valid category must be a directory with a .md file inside it that matches the directory name.
    """
    categories = []
    try:
        if not os.path.exists(content_dir):
            logging.warning(f"Content directory does not exist: {content_dir}")
            return categories

        for item in os.listdir(content_dir):
            try:
                item_path = os.path.join(content_dir, item)
                if os.path.isdir(item_path):
                    category_md_file = os.path.join(item_path, f"{item}.md")
                    if os.path.isfile(category_md_file):
                        categories.append(item)
            except Exception as err:
                logging.error(
                    f"Error processing item '{item}' in content directory: {err}"
                )
    except Exception as err:
        logging.error(f"Error accessing content directory '{content_dir}': {err}")

    return categories


def merge_image_dir() -> None:
    source_dir = os.path.join(content_dir, "images")
    dest_dir = os.path.join(public_dir, "images")

    if not os.path.exists(source_dir):
        logging.info(f"Source images directory does not exist: {source_dir}. Skipping.")
        return

    ensure_directory(dest_dir)

    try:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                source_file = os.path.join(root, file)
                rel_path = os.path.relpath(source_file, source_dir)
                destination_file = os.path.join(dest_dir, rel_path)

                destination_dir_path = os.path.dirname(destination_file)
                ensure_directory(destination_dir_path)

                shutil.copy2(source_file, destination_file)
                logging.info(f"Copied image: {source_file} -> {dest_dir}")
    except Exception as err:
        logging.error(f"Error merging images directory: {err}")


def parse_external_links(text: str) -> str:
    try:
        pattern = r"\[(.*?)\]\((https?://.*?)\)"

        def replace_link(match):
            link_text = match.group(1)
            url = match.group(2)
            return f'<a href="{url}" target="_blank">{link_text}</a>'

        return re.sub(pattern, replace_link, text)
    except Exception as err:
        logging.error(f"Error parsing external links in text: {err}")
        return text


def parse_backlink(source: str, target: str) -> None:
    try:
        source_key = (
            os.path.splitext(os.path.basename(source))[0].replace(" ", "-").lower()
        )
        target_key = target.replace(" ", "-").lower()

        if source_key == "index":
            source_key = ""

        if target_key not in backlinks:
            backlinks[target_key] = []
        if source_key not in backlinks[target_key]:
            backlinks[target_key].append(source_key)

        logging.info(f"Backlinks for '{target_key}': {backlinks[target_key]}")
    except Exception as err:
        logging.error(f"Error parsing backlink from '{source}' to '{target}': {err}")


def parse_wikilinks(source_page: str, text: str) -> str:
    try:
        pattern = r"\[\[(.*?)\]\]"

        def replace_link(match):
            link_text = match.group(1)
            slug = link_text.replace(" ", "-").lower()
            logging.info(f"Backlinks source: {source_page}, link text: {link_text}")
            parse_backlink(source_page, link_text)
            return f'<a href="/{slug}.html">{link_text}</a>'

        return re.sub(pattern, replace_link, text)
    except Exception as err:
        logging.error(f"Error parsing wikilinks in text: {err}")
        return text


def parse_articles(md_content: str, page_name: str) -> List[Dict[str, Any]]:
    articles = []
    lines = md_content.split("\n")
    current_article = None

    try:
        for line in lines:
            if line.startswith("## "):
                if current_article:
                    articles.append(current_article)
                current_article = {
                    "header": f"<h2>{line[3:].strip()}</h2>",
                    "sections": [],
                }
            elif current_article and line.strip():
                processed_line = parse_wikilinks(page_name, line.strip())
                processed_line = parse_external_links(processed_line)
                current_article["sections"].append(processed_line)

        if current_article:
            articles.append(current_article)
    except Exception as err:
        logging.error(f"Error parsing articles: {err}")
    return articles


def parse_frontmatter(md_fp: str) -> Dict[str, Any]:
    try:
        with open(md_fp, "r", encoding="utf-8") as f:
            md_content = f.read()

        frontmatter_match = re.match(r"---\n(.*?)\n---\n(.*)", md_content, re.S)
        if frontmatter_match:
            frontmatter = yaml.safe_load(frontmatter_match.group(1))
            content = frontmatter_match.group(2)
        else:
            frontmatter = {}
            content = md_content

        for key in ["created", "last_modified"]:
            if key in frontmatter and isinstance(frontmatter[key], (datetime, str)):
                frontmatter[key] = str(frontmatter[key])

        page_name = os.path.splitext(os.path.basename(md_fp))[0]
        articles = parse_articles(content, page_name)
        return {"frontmatter": frontmatter, "articles": articles}
    except Exception as err:
        logging.error(f"Error parsing frontmatter in file {md_fp}: {err}")
        return {"frontmatter": {}, "articles": []}


def render_template_context(template_name: str, context: Dict[str, str]) -> str:
    try:
        template = env.get_template(template_name)
        return template.render(**context)
    except TemplateNotFound as err:
        logging.error(f"Template not found: {err}")
    except Exception as err:
        logging.error(f"Error rendering template {template_name}: {err}")
    return ""


def process_file(md_fp: str, output_fp: str, template_name: str) -> None:
    try:
        page_name = (
            os.path.splitext(os.path.basename(md_fp))[0].replace(" ", "-").lower()
        )
        parsed_data = parse_frontmatter(md_fp)
        frontmatter = parsed_data.get("frontmatter", {})
        articles = parsed_data.get("articles", [])

        if page_name == "index":
            page_name = ""

        logging.info(
            f"Final backlinks for page '{page_name}': {backlinks.get(page_name)}"
        )
        # more debugging
        markdown_output(md_fp, backlinks)

        context = {
            "title": frontmatter.get("title", "Default Title"),
            "description": frontmatter.get("description", "Default Description"),
            "page_meta": [
                {
                    "label": "Division",
                    "value": ", ".join(frontmatter.get("division", [])),
                },
                {"label": "Domain", "value": frontmatter.get("domain", "N/A")},
                {"label": "Time", "value": frontmatter.get("worked", "N/A")},
                {"label": "Modified", "value": frontmatter.get("last_modified", "N/A")},
            ],
            "articles": articles,
            "backlinks": backlinks.get(page_name, []),
        }

        rendered_html = render_template_context(template_name, context)
        ensure_directory(os.path.dirname(output_fp))
        with open(output_fp, "w", encoding="utf-8") as f:
            f.write(rendered_html)

        logging.info(f"Generated: {output_fp}")
    except Exception as err:
        logging.error(f"Error processing file {md_fp}: {err}")


def process_index() -> None:
    index_md_fp = os.path.join(content_dir, "index.md")
    index_template = "index.html"
    index_output_fp = os.path.join(public_dir, "index.html")

    if not os.path.exists(index_md_fp):
        logging.error(f"`index.md` file does not exist at: {index_md_fp}")
        return

    # debugging
    markdown_output(index_md_fp)

    try:
        process_file(index_md_fp, index_output_fp, index_template)
        logging.info(f"Processed `index.md` into {index_output_fp}")
    except Exception as err:
        logging.error(f"Error processing `index.md`: {err}")


def process_category(category: str) -> None:
    try:
        if category == "index":
            process_index()
            return

        category_dir = os.path.join(content_dir, category)
        output_dir = os.path.join(public_dir, category)
        template_name = f"{category}.html"

        if not os.path.isdir(category_dir):
            logging.error(f"Category directory `{category_dir}` does not exist.")
            return

        for file in os.listdir(category_dir):
            try:
                if file.endswith(".md"):
                    md_fp = os.path.join(category_dir, file)
                    output_fp = os.path.join(output_dir, file.replace(".md", ".html"))
                    process_file(md_fp, output_fp, template_name)
            except Exception as err:
                logging.error(
                    f"Error processing file {file} in category `{category}`: {err}"
                )
    except Exception as err:
        logging.error(f"Error processing category `{category}`: {err}")


def cleanup() -> None:
    """
    Remove orphaned HTML files from the 'public' directory if their corresponding
    Markdown files are missing in the 'content' directory.
    """
    try:
        user_input = (
            input("Would you like to create a snapshot before cleanup? (yes/no): ")
            .strip()
            .lower()
        )
        if user_input in ["yes", "y"]:
            logging.info("Creating snapshot before cleanup.")
            snapshot_site()
            logging.info("Snapshot created successfully.")
        elif user_input in ["no", "n"]:
            logging.info("Skipping snapshot creation.")
        else:
            logging.warning("Invalid input. Cleanup aborted.")
            return

        categories = get_categories()
        logging.info(f"Identified categories: {categories}")

        for category in categories:
            category_content_dir = os.path.join(content_dir, category)
            category_public_dir = os.path.join(public_dir, category)

            if not os.path.exists(category_public_dir):
                logging.info(
                    f"No public directory for category `{category}`. Skipping."
                )
                continue

            for file in os.listdir(category_public_dir):
                if file.endswith(".html"):
                    markdown_file = os.path.join(
                        category_content_dir, file.replace(".html", ".md")
                    )
                    html_file = os.path.join(category_public_dir, file)
                    if not os.path.exists(markdown_file):
                        try:
                            os.remove(html_file)
                            logging.info(f"Removed orphaned HTML file: {html_file}")
                        except Exception as err:
                            logging.error(f"Error removing file `{html_file}`: {err}")

        logging.info("Cleanup completed.")
    except Exception as err:
        logging.error(f"Error during cleanup: {err}")


def cleanup_snapshots() -> None:
    try:
        if not os.path.exists(snapshots_dir):
            print("No snapshots available to delete.")
            logging.warning(
                "Snapshots directory does not exist. No snapshots to delete."
            )
            return

        snapshots = [
            os.path.join(root, file)
            for root, _, files in os.walk(snapshots_dir)
            for file in files
            if file.endswith(".html")
        ]

        if not snapshots:
            print("No snapshots available to delete.")
            logging.info("No snapshots found.")
            return

        print("Available snapshots for deletion:")
        snapshot_dict = {}
        for i, snapshot in enumerate(snapshots, start=1):
            relative_path = os.path.relpath(snapshot, snapshots_dir)
            print(f"{i}. {relative_path}")
            snapshot_dict[i] = snapshot

        user_input = (
            input(
                "Enter the numbers of the snapshots to delete (comma separated), or 'all' to delete all: "
            )
            .strip()
            .lower()
        )

        if user_input == "all":
            confirmation = (
                input("Are you sure you want to delete all snapshots? (yes/no): ")
                .strip()
                .lower()
            )
            if confirmation not in ["yes", "y"]:
                print("Deletion aborted.")
                logging.info("Deletion aborted by user.")
                return

            for snapshot in snapshots:
                try:
                    os.remove(snapshot)
                    logging.info(f"Deleted snapshot: {snapshot}")
                except Exception as err:
                    logging.error(f"Error deleting snapshot `{snapshot}`: {err}")
            print("All snapshots have been deleted.")

        else:
            try:
                indices = [int(x.strip()) for x in user_input.split(",")]
                selected_snapshots = [
                    snapshot_dict[i] for i in indices if i in snapshot_dict
                ]
                if not selected_snapshots:
                    raise ValueError("Invalid selection.")
            except (ValueError, KeyError):
                print("Invalid input. Deletion aborted.")
                logging.warning("Invalid input for snapshot deletion. Aborting.")
                return

            confirmation = (
                input(
                    f"Are you sure you want to delete {len(selected_snapshots)} selected snapshots? (yes/no): "
                )
                .strip()
                .lower()
            )
            if confirmation not in ["yes", "y"]:
                print("Deletion cancelled.")
                logging.info("Deletion cancelled by user.")
                return

            for snapshot in selected_snapshots:
                try:
                    os.remove(snapshot)
                    logging.info(f"Deleted snapshot: {snapshot}")
                except Exception as err:
                    logging.error(f"Error deleting snapshot `{snapshot}`: {err}")
            print(f"{len(selected_snapshots)} snapshots have been deleted.")

    except Exception as err:
        logging.error(f"Error during snapshot deletion: {err}")


def snapshot_site() -> None:
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for root, _, files in os.walk(public_dir):
            for file in files:
                if file.endswith(".html"):
                    rel_fp = os.path.relpath(os.path.join(root, file), public_dir)
                    snapshot_fp = os.path.join(snapshots_dir, rel_fp)
                    snapshot_dir = os.path.dirname(snapshot_fp)
                    ensure_directory(snapshot_dir)
                    snapshot_file = f"{os.path.splitext(file)[0]}_{timestamp}.html"
                    shutil.copy2(
                        os.path.join(root, file),
                        os.path.join(snapshot_dir, snapshot_file),
                    )
                    logging.info(
                        f"Snapshot: {rel_fp} -> {os.path.join(snapshot_dir, snapshot_file)}"
                    ),
    except Exception as err:
        logging.error(f"Error creating snapshot: {err}")


def restore_site(
    category: Optional[str] = None, snapshot: Optional[str] = None
) -> None:
    try:
        source_dir = (
            os.path.join(snapshots_dir, category) if category else snapshots_dir
        )
        target_dir = os.path.join(public_dir, category) if category else public_dir

        if not os.path.exists(source_dir):
            logging.error(f"Snapshot directory `{source_dir}` does not exist.")
            return

        try:
            snapshots = [
                os.path.join(root, file)
                for root, _, files in os.walk(source_dir)
                for file in files
                if file.endswith(".html")
            ]
        except Exception as err:
            logging.error(f"Error listing snapshots in `{source_dir}`: {err}")
            return

        if not snapshots:
            logging.error("No snapshots found.")
            return

        if not snapshot:
            snapshot = max(snapshots, key=os.path.getmtime)

        restored_files = 0
        for root, _, files in os.walk(source_dir):
            for file in files:
                if snapshot in file:
                    try:
                        rel_fp = os.path.relpath(os.path.join(root, file), source_dir)
                        restore_fp = os.path.join(
                            target_dir, rel_fp.split("_")[0] + ".html"
                        )
                        ensure_directory(os.path.dirname(restore_fp))
                        shutil.copy2(os.path.join(root, file), restore_fp)
                        logging.info(f"Restored: {file} -> {restore_fp}")
                        restored_files += 1
                    except Exception as err:
                        logging.error(f"Error restoring file `{file}`: {err}")

        if restored_files == 0:
            logging.warning(f"No files restored from snapshot: {snapshot}")
        else:
            logging.info(f"Restored {restored_files} files")
    except Exception as err:
        logging.error(f"Error in restore_site: {err}")


def dry_run(
    command: str, category: Optional[str] = None, snapshot: Optional[str] = None
) -> None:
    try:
        logging.info(f"Starting dry run for command: {command}")

        if command == "generate":
            if category == "all":
                logging.info("Simulating generation for all categories.")
                for cat in ["index", "articles", "notes"]:
                    try:
                        sim_process_category(cat)
                    except Exception as err:
                        logging.error(f"Error simulating category `{cat}`: {err}")
            else:
                try:
                    logging.info(f"Simulating generation for category: `{category}`")
                    sim_process_category(category)
                except Exception as err:
                    logging.error(f"Error simulating category `{category}`: {err}")

        elif command == "snapshot":
            try:
                logging.info("Simulating snapshot creation...")
                for root, _, files in os.walk(public_dir):
                    for file in files:
                        try:
                            if file.endswith(".html"):
                                rel_fp = os.path.relpath(
                                    os.path.join(root, file), public_dir
                                )
                                snapshot_fp = os.path.join(snapshots_dir, rel_fp)
                                snapshot_file = (
                                    f"{os.path.splitext(file)[0]}_TIMESTAMP.html"
                                )
                                logging.info(
                                    f"Would create snapshot: {rel_fp} -> {os.path.join(snapshot_fp, snapshot_file)}"
                                )
                        except Exception as err:
                            logging.error(
                                f"Error simulating snapshot creation for file `{file}`: {err}"
                            )
            except Exception as err:
                logging.error(f"Error during snapshot dry run: `{err}`")

        elif command == "restore":
            try:
                logging.info(f"Simulating restore for category: {category or 'all'}")
                if category:
                    logging.info(f"Simulating restore for category: `{category}`")
                if snapshot:
                    logging.info(f"Simulating restore for snapshot: `{snapshot}`")
                logging.info("No files will actually be restored.")
            except Exception as err:
                logging.error(f"Error during restore dry run: {err}")

        else:
            logging.warning(f"Unknown command for dry run: `{command}`")
    except Exception as err:
        logging.error(f"Error in dry_run for command `{command}`: {err}")


def sim_process_category(category: str) -> None:
    try:
        category_dir = os.path.join(content_dir, category)
        template_name = f"{category}.html"
        output_dir = os.path.join(public_dir, category)

        if not os.path.exists(category_dir):
            logging.warning(
                f"Category directory `{category_dir}` does not exist. Skipping."
            )
            return

        for file in os.listdir(category_dir):
            try:
                if file.endswith(".md"):
                    md_fp = os.path.join(category_dir, file)
                    output_fp = os.path.join(output_dir, file.replace(".md", ".html"))
                    logging.info(
                        f"Would process: Markdown file: {md_fp}, Template: {template_name}, Output: {output_fp}"
                    )
            except Exception as err:
                logging.error(
                    f"Error processing file `{file}` in category `{category}`: {err}"
                )
    except Exception as err:
        logging.error(f"Error in sim_process_category for category `{category}`: {err}")


def setup() -> None:
    required_dirs = [
        content_dir,
        templates_dir,
        public_dir,
        snapshots_dir,
    ]

    for dir in required_dirs:
        try:
            if not os.path.exists(dir):
                ensure_directory(dir)
                logging.info(f"Created directory: {dir}")
            else:
                logging.info(f"Directory already exists:{dir}")
        except Exception as err:
            logging.error(f"Error creating directory:{dir}: {err}")

    required_dirs = [content_dir, templates_dir, public_dir, snapshots_dir]
    for category in ["articles", "notes"]:
        required_dirs.append(os.path.join(content_dir, category))
        required_dirs.append(os.path.join(public_dir, category))

    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            ensure_directory(dir_path)
            logging.info(f"Created missing directory: {dir_path}")
        else:
            logging.info(f"Directory already exists: {dir_path}")


def snapshot_category(category: str) -> None:
    try:
        category_dir = os.path.join(public_dir, category)

        if not os.path.exists(category_dir):
            print(f"Category `{category}` does not exist in the public directory.")
            logging.error(f"Category `{category}` not found in public directory.")
            return

        category_snapshot_dir = os.path.join(snapshots_dir, category)
        ensure_directory(category_snapshot_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_count = 0

        for root, _, files in os.walk(category_dir):
            for file in files:
                if file.endswith(".html"):
                    rel_fp = os.path.relpath(os.path.join(root, file), category_dir)
                    snapshot_fp = os.path.join(
                        category_snapshot_dir, f"{rel_fp}_{timestamp}.html"
                    )
                    ensure_directory(os.path.dirname(snapshot_fp))
                    shutil.copy2(os.path.join(root, file), snapshot_fp)
                    logging.info(f"Snapshot created: {rel_fp} -> {snapshot_fp}")
                    snapshot_count += 1
        if snapshot_count == 0:
            print(f"No HTML files found for category `{category}`.")
            logging.warning(f"No HTML files found in category `{category}`.")
        else:
            print(
                f"Snapshot created for {snapshot_count} file(s) in category `{category}`."
            )

    except Exception as err:
        logging.error(
            f"Error during snapshot creation for category `{category}`: {err}"
        )


def main() -> None:
    categories = get_categories()
    parser = argparse.ArgumentParser(description="Static Site Generator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("setup", help="Set up the necessary directory structure.")

    generate_parser = subparsers.add_parser(
        "generate", help="Generate the static site."
    )
    generate_parser.add_argument(
        "--category",
        choices=categories + ["all"],
        default="all",
        help="Specify which category to process.",
    )

    snapshots_parser = subparsers.add_parser(
        "snapshot", help="Manage snapshots: `create`, `restore`, or `delete`."
    )
    snapshots_parser.add_argument(
        "--create",
        type=str,
        choices=categories + ["all"],
        help="Create a snapshot for all categories or a specific category.",
    )
    snapshots_parser.add_argument(
        "--restore",
        action="store_true",
        help="Restore a snapshot from the snapshots directory.",
    )
    snapshots_parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete selected snapshots or all snapshots.",
    )
    snapshots_parser.add_argument(
        "--snapshot",
        type=str,
        help="Specify a specific snapshot file to restore or delete.",
    )

    cleanup_parser = subparsers.add_parser(
        "cleanup", help="Remove orphaned HTML files."
    )
    cleanup_parser.set_defaults(func=cleanup)

    sim_parser = subparsers.add_parser(
        "dry_run", help="Simulate processes without making changes."
    )
    sim_parser.add_argument(
        "--command",
        choices=["generate", "snapshot", "restore"],
        required=True,
        help="Specify the command to simulate (generate, snapshot, restore).",
    )
    sim_parser.add_argument(
        "--category",
        choices=categories + ["all"],
        help="Category to process.",
    )
    sim_parser.add_argument(
        "--snapshot",
        type=str,
        help="Specify the snapshot to simulate restore.",
    )

    args = parser.parse_args()

    if args.command == "setup":
        setup()

    elif args.command == "generate":
        generate_missing()
        if args.category == "all":
            for category in categories:
                process_category(category)
        else:
            process_category(args.category)
        merge_image_dir()

    elif args.command == "snapshot":
        if args.create:
            if args.create == "all":
                print("Creating a snapshot for all categories.")
                snapshot_site()
            else:
                print(f"Creating a snapshot for category: {args.create}")
                snapshot_category(args.create)
        elif args.restore:
            restore_site(args.category, args.snapshot)
        elif args.delete:
            cleanup_snapshots()

    elif args.command == "dry_run":
        dry_run(args.command, args.category, args.snapshot)

    elif args.command == "cleanup":
        cleanup()


if __name__ == "__main__":
    main()
