import os
import re
from datetime import datetime
import shutil
from src.base_utils import (
    ensure_directory,
    setup_logger,
    content_dir,
    templates_dir,
    public_dir,
    snapshots_dir,
)

logger = setup_logger("file_manager", "logs/file_manager.log")
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")


def get_categories() -> list[str]:
    try:
        logger.info("Fetching categories from content directory.")
        if not os.path.exists(content_dir):
            logger.warning(f"Content directory does not exist: {content_dir}")
            return []

        categories = []
        for item in os.listdir(content_dir):
            item_path = os.path.join(content_dir, item)
            if os.path.isdir(item_path):
                category_md_file = os.path.join(item_path, f"{item}.md")
                if os.path.isfile(category_md_file):
                    categories.append(item)
        logger.info(f"Categories found: {categories}")
        return categories
    except Exception as err:
        logger.error(f"Error fetching categories: {err}")
        return []


def setup_project() -> None:
    try:
        logger.info("Setting up project directories.")
        required_dirs = [
            content_dir,
            templates_dir,
            public_dir,
            snapshots_dir,
            logs_dir,
        ]

        try:
            categories = get_categories()
            for category in categories:
                required_dirs.append(os.path.join(content_dir, category))
                required_dirs.append(os.path.join(public_dir, category))
        except Exception as err:
            logger.error(f"Error retrieving categories: {err}")

        for directory in required_dirs:
            try:
                ensure_directory(directory)
                logger.info(f"Verified or created directory: {directory}")
            except Exception as err:
                logger.error(f"Error creating or verifying directory {directory}: {err}")
    except Exception as err:
        logger.error(f"Unexpected error in setup_project: {err}")


def generate_missing() -> None:
    template_fp = os.path.join(content_dir, "../src/templates/template.md")
    try:
        if not os.path.exists(template_fp):
            logger.error(f"Template file not found: {template_fp}")
            return

        with open(template_fp, "r", encoding="utf-8") as template_file:
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
                        category = parent_dir if parent_dir != "content" else default_category
                        category_dir = os.path.join(content_dir, category)

                        ensure_directory(category_dir)

                        for link in wikilinks:
                            filename = f"{link.replace(' ', '-').lower()}.md"
                            filepath = os.path.join(category_dir, filename)

                            if not os.path.exists(filepath):
                                title = link.title()
                                frontmatter = template_content.format(
                                    title=title,
                                    created=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    last_modified=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                )
                                with open(filepath, "w", encoding="utf-8") as new_file:
                                    new_file.write(frontmatter)
                                logger.info(f"Created missing file: {filepath}")
                            else:
                                logger.info(f"File already exists: {filepath}")

    except Exception as err:
        logger.error(f"Error during generate_missing: {err}")


def cleanup_orphans() -> None:
    """
    Deletes HTML files in the public directory if their corresponding Markdown files
    no longer exist in the content directory.
    """
    try:
        logger.info("Starting orphan cleanup process.")
        md_files = {
            os.path.splitext(file)[0]
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
                        logger.info(f"Deleted orphaned HTML file: {orphan_html_fp}")
    except Exception as err:
        logger.error(f"Error during cleanup of orphaned HTML files: {err}")


def merge_image_dir() -> None:
    source_dir = os.path.join(content_dir, "images")
    dest_dir = os.path.join(public_dir, "images")

    if not os.path.exists(source_dir):
        logger.info(f"Source images directory does not exist: {source_dir}. Skipping.")
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
                logger.info(f"Copied image: {source_file} -> {destination_file}")
    except Exception as err:
        logger.error(f"Error merging images directory: {err}")
