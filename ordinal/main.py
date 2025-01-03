import os
import argparse
import logging
import difflib
import shutil
from datetime import datetime
from typing import List, Dict, Optional
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
import mistune
import yaml
import re

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
    os.makedirs(path, exist_ok=True)


def markdown_output(md_fp: str) -> None:
    try:
        with open(md_fp, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        html_content = mistune.create_markdown()(markdown_content)

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


def parse_frontmatter(md_fp: str) -> Dict[str, str]:
    with open(md_fp, "r", encoding="utf-8") as f:
        md_content = f.read()

    frontmatter_match = re.match(r"---\n(.*?)\n---\n(.*)", md_content, re.S)
    if frontmatter_match:
        frontmatter = yaml.safe_load(frontmatter_match.group(1))
        content = frontmatter_match.group(2)
    else:
        frontmatter = {}
        content = md_content

    content_html = mistune.create_markdown()(content)
    return {"frontmatter": frontmatter, "content": content_html}


def render_template_context(template_name: str, context: Dict[str, str]) -> str:
    try:
        template = env.get_template(template_name)
        return template.render(**context)
    except TemplateNotFound as err:
        logging.error(f"Template not found: {err}")
        raise


def process_file(md_fp: str, output_fp: str, template_name: str) -> None:
    try:
        parsed_data = parse_frontmatter(md_fp)
        frontmatter = parsed_data.get("frontmatter", {})
        content = parsed_data.get("content", "")

        articles = []
        current_article = None

        lines = content.splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith("<h2>") and line.endswith("</h2>"):
                if current_article:
                    articles.append(current_article)
                current_article = {
                    "header": line,
                    "sections": [],
                }
            elif current_article:
                current_article["sections"].append(line)

            if current_article:
                articles.append(current_article)
        context = {
            "title": frontmatter.get("title", "Default Title"),
            "description": frontmatter.get("description", "Default Description"),
            "page_meta": [
                {
                    "label": "Division",
                    "class": "division",
                    "url": "#",
                    "value": frontmatter.get("division", []),
                },
                {
                    "label": "Domain",
                    "class": "domain",
                    "url": "#",
                    "value": frontmatter.get("domain"),
                },
                {
                    "label": "Worked",
                    "class": "worked",
                    "url": "#",
                    "value": frontmatter.get("worked"),
                },
                {
                    "label": "Last Modified",
                    "class": "last-modified",
                    "url": "#",
                    "value": frontmatter.get("last_modified"),
                },
            ],
            "articles": articles,
        }

        rendered_html = render_template_context(template_name, context)
        ensure_directory(os.path.dirname(output_fp))
        with open(output_fp, "w", encoding="utf-8") as f:
            f.write(rendered_html)
        logging.info(f"Generated: {output_fp}")
    except Exception as err:
        logging.error(f"Error processing file: {md_fp}: {err}")


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
        if file.endswith(".md"):
            md_fp = os.path.join(category_dir, file)
            output_fp = os.path.join(output_dir, file.replace(".md", ".html"))
            process_file(md_fp, output_fp, template_name)


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
    source_dir = os.path.join(snapshots_dir, category) if category else snapshots_dir
    target_dir = os.path.join(public_dir, category) if category else public_dir

    if not os.path.exists(source_dir):
        logging.error(f"Snapshot directory `{source_dir}` does not exist.")
        return

    snapshots = [
        os.path.join(root, file)
        for root, _, files in os.walk(source_dir)
        for file in files
        if file.endswith(".html")
    ]

    if not snapshots:
        logging.error("No snapshots found.")
        return

    if not snapshot:
        snapshot = max(snapshots, key=os.path.getmtime)

    restored_files = 0
    for root, _, files in os.walk(source_dir):
        for file in files:
            if snapshot in file:
                rel_fp = os.path.relpath(os.path.join(root, file), source_dir)
                restore_fp = os.path.join(target_dir, rel_fp.split("_")[0] + ".html")
                ensure_directory(os.path.dirname(restore_fp))
                shutil.copy2(os.path.join(root, file), restore_fp)
                logging.info(f"Restored: {file} -> {restore_fp}")
                restored_files += 1

    if restored_files == 0:
        logging.warning(f"No files restored from snapshot: {snapshot}")
    else:
        logging.info(f"Restored {restored_files} files")


def dry_run(
    command: str, category: Optional[str] = None, snapshot: Optional[str] = None
) -> None:
    logging.info(f"Starting dry run for command: {command}")

    if command == "generate":
        if category == "all":
            logging.info("Simulating generation for all categories.")
            for cat in ["index", "articles", "notes"]:
                sim_process_category(cat)
        else:
            logging.info(f"Simulating generation for category: {category}")
            sim_process_category(category)

    elif command == "snapshot":
        logging.info("Simulating snapshot creation...")
        for root, _, files in os.walk(public_dir):
            for file in files:
                if file.endswith(".html"):
                    rel_fp = os.path.relpath(os.path.join(root, file), public_dir)
                    snapshot_fp = os.path.join(snapshots_dir, rel_fp)
                    snapshot_file = f"{os.path.splitext(file)[0]}_TIMESTAMP.html"
                    logging.info(
                        f"Would create snapshot: {rel_fp} -> {os.path.join(snapshot_fp, snapshot_file)}"
                    )

    elif command == "restore":
        logging.info(f"Simulating restore for category: {category or 'all'}")
        if category:
            logging.info(f"Simulating restore for category: {category}")
        if snapshot:
            logging.info(f"Simulating restore for snapshot: {snapshot}")
        logging.info("No files will actually be restored.")

    else:
        logging.warning(f"Unknown command for dry run: {command}")


def sim_process_category(category: str) -> None:
    category_dir = os.path.join(content_dir, category)
    template_name = f"{category}.html"
    output_dir = os.path.join(public_dir, category)

    if not os.path.exists(category_dir):
        logging.warning(
            f"Category directory '{category_dir}' does not exist. Skipping."
        )
        return

    for file in os.listdir(category_dir):
        if file.endswith(".md"):
            md_fp = os.path.join(category_dir, file)
            output_fp = os.path.join(output_dir, file.replace(".md", ".html"))
            logging.info(
                f"Would process: Markdown file: {md_fp}, Template: {template_name}, Output: {output_fp}"
            )


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
