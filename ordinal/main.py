import os
import argparse
import logging
import difflib
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Any
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import mistune
import yaml
import re
import json


base_dir = os.path.dirname(os.path.abspath(__file__))
content_dir = os.path.join(base_dir, "content")
templates_dir = os.path.join(base_dir, "src", "templates")
public_dir = os.path.join(base_dir, "public")
snapshots_dir = os.path.join(base_dir, "snapshots")


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


def markdown_output(md_fp: str) -> None:
    try:
        with open(md_fp, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        try:
            html_content = mistune.create_markdown()(markdown_content)
        except Exception as err:
            logging.error(f"Error converting Markdown to HTML: {err}")
            return

        log_file = "markdown_output.log"
        with open(log_file, "w", encoding="utf-8") as log:
            log.write("=== Raw Markdown Content ===\n")
            log.write(markdown_content)
            log.write("\n\n=== Converted HTML Content ===\n")
            log.write(html_content)

        logging.info(f"Markdown output logged to {log_file}")
    except Exception as err:
        logging.error(f"Error logging Markdown output from {md_fp}: {err}")


# def convert_markdown(md_fp: str) -> str:
#     with open(md_fp, "r", encoding="utf-8") as f:
#         markdown_content = f.read()
#     return mistune.create_markdown()(markdown_content)


def parse_articles(md_content: str) -> List[Dict[str, Any]]:
    try:
        articles = []
        lines = md_content.split("\n")
        current_article = None

        for line in lines:
            if line.startswith("## "):
                if current_article:
                    articles.append(current_article)
                current_article = {
                    "header": f"<h2>{line[3:].strip()}</h2>",
                    "sections": [],
                }
            elif current_article and line.strip():
                current_article["sections"].append(line.strip())

        if current_article:
            articles.append(current_article)

        return articles
    except Exception as err:
        logging.error(f"Error parsing articles: {err}")
        return []


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

        articles = parse_articles(content)
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
        parsed_data = parse_frontmatter(md_fp)
        frontmatter = parsed_data.get("frontmatter", {})
        articles = parsed_data.get("articles", [])

        logging.info("Frontmatter Data: %s", json.dumps(frontmatter, indent=4))
        logging.info("Parsed Articles Data: %s", json.dumps(articles, indent=4))

        context = {
            "title": frontmatter.get("title", "Default Title"),
            "description": frontmatter.get("description", "Default Description"),
            "page_meta": [
                {
                    "label": "Division",
                    "class": "division",
                    "url": "#",
                    "value": ", ".join(frontmatter.get("division", [])),
                },
                {
                    "label": "Domain",
                    "class": "domain",
                    "url": "#",
                    "value": frontmatter.get("domain", "N/A"),
                },
                {
                    "label": "Time",
                    "class": "worked",
                    "url": "#",
                    "value": frontmatter.get("worked", "N/A"),
                },
                {
                    "label": "Modified",
                    "class": "last-modified",
                    "url": "#",
                    "value": frontmatter.get("last_modified", "N/A"),
                },
            ],
            "articles": articles,
        }

        logging.info("Rendering with context: %s", json.dumps(context, indent=4))

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
                        logging.error(f"Error simulating category '{cat}': {err}")
            else:
                try:
                    logging.info(f"Simulating generation for category: {category}")
                    sim_process_category(category)
                except Exception as err:
                    logging.error(f"Error simulating category '{category}': {err}")

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
                                f"Error simulating snapshot creation for file '{file}': {err}"
                            )
            except Exception as err:
                logging.error(f"Error during snapshot dry run: {err}")

        elif command == "restore":
            try:
                logging.info(f"Simulating restore for category: {category or 'all'}")
                if category:
                    logging.info(f"Simulating restore for category: {category}")
                if snapshot:
                    logging.info(f"Simulating restore for snapshot: {snapshot}")
                logging.info("No files will actually be restored.")
            except Exception as err:
                logging.error(f"Error during restore dry run: {err}")

        else:
            logging.warning(f"Unknown command for dry run: {command}")
    except Exception as err:
        logging.error(f"Error in dry_run for command '{command}': {err}")


def sim_process_category(category: str) -> None:
    try:
        category_dir = os.path.join(content_dir, category)
        template_name = f"{category}.html"
        output_dir = os.path.join(public_dir, category)

        if not os.path.exists(category_dir):
            logging.warning(
                f"Category directory '{category_dir}' does not exist. Skipping."
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
                    f"Error processing file '{file}' in category '{category}': {err}"
                )
    except Exception as err:
        logging.error(f"Error in sim_process_category for category '{category}': {err}")


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Static Site Generator")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("setup", help="Set up the necessary directory structure.")

    generate_parser = subparsers.add_parser(
        "generate", help="Generate the static site."
    )
    generate_parser.add_argument(
        "--category",
        choices=["articles", "notes", "index", "all"],
        default="all",
        help="Specify which category to process.",
    )

    subparsers.add_parser("snapshot", help="Create a snapshot of the public site.")

    restore_parser = subparsers.add_parser("restore", help="Restore a snapshot.")
    restore_parser.add_argument("--category", help="Category to restore.")
    restore_parser.add_argument("--snapshot", help="Specific snapshot file to restore.")

    sim_parser = subparsers.add_parser(
        "dry_run", help="Simulate proccesses without making changes"
    )

    sim_parser.add_argument(
        "--command",
        choices=["generate", "snapshot", "restore"],
        required=True,
        help="Specify the command to simulate (generate, snapshot, restore).",
    )

    sim_parser.add_argument(
        "--category",
        choices=["index", "articles", "notes", "all"],
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
        if args.category == "all":
            for category in ["index", "articles", "notes"]:
                process_category(category)
        else:
            process_category(args.category)

    elif args.command == "snapshot":
        snapshot_site()

    elif args.command == "restore":
        restore_site(args.category, args.snapshot)

    elif args.command == "dry_run":
        dry_run(args.command, args.category, args.snapshot)


if __name__ == "__main__":
    main()
