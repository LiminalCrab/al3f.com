import os
from src.base_utils import content_dir, public_dir, setup_logger, ensure_directory
from src.file_manager import get_categories, generate_missing
from src.markdown_parser import parse_frontmatter, parse_related, parse_footnotes, parse_articles
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

logger = setup_logger("html_renderer", "logs/html_renderer.log")

env = Environment(loader=FileSystemLoader("src/templates"))


def render_template_context(template_name: str, context: dict) -> str:
    try:
        template = env.get_template(template_name)
        return template.render(**context)
    except TemplateNotFound as err:
        logger.error(f"Template not found: {err}")
    except Exception as err:
        logger.error(f"Error rendering template {template_name}: {err}")
    return ""


def process_file(md_fp: str, output_fp: str, template_name: str, backlinks: dict) -> None:
    try:
        logger.info(f"Processing file: {md_fp}")

        parsed_data = parse_frontmatter(md_fp)
        frontmatter = parsed_data.get("frontmatter", {})
        raw_content = parsed_data.get("content", "")

        logger.info("Parsing footnotes.")
        footnotes_content, footnotes = parse_footnotes(raw_content)

        logger.info("Parsing articles.")
        articles = parse_articles(footnotes_content, os.path.basename(md_fp), backlinks)

        logger.info("Looking for related articles.")
        related = parse_related(frontmatter)

        context = {
            "title": frontmatter.get("title", "Untitled"),
            "description": frontmatter.get("description", ""),
            "page_meta": [
                {"label": "Domain", "value": frontmatter.get("domain", "N/A")},
                {"label": "Modified", "value": frontmatter.get("last_modified", "N/A")},
                {"label": "Worked", "value": frontmatter.get("worked", "N/A")},
                {"label": "Division", "value": ", ".join(frontmatter.get("division", []))},
            ],
            "content": footnotes_content,
            "articles": articles.get("articles", []),
            "footnotes": footnotes,
            "toc": articles["toc"],
            "backlinks": backlinks.get(os.path.splitext(os.path.basename(md_fp))[0], []),
            "related_articles": related,
        }

        rendered_html = render_template_context(template_name, context)
        ensure_directory(os.path.dirname(output_fp))
        with open(output_fp, "w", encoding="utf-8") as f:
            f.write(rendered_html)

        logger.info(f"Generated: {output_fp}")
    except Exception as err:
        logger.error(f"Error processing file {md_fp}: {err}")


def generate_static_site(category="all"):
    try:
        logger.info("Starting site generation.")
        categories = get_categories()
        backlinks = {}

        logger.info("Checking and generating missing markdown files.")
        generate_missing()

        process_index(content_dir, public_dir, backlinks)

        if category == "all":
            for cat in categories:
                process_category(cat, content_dir, public_dir, backlinks)
        else:
            if category in categories:
                process_category(category, content_dir, public_dir, backlinks)
            else:
                logger.error(f"Invalid category: {category}")
    except Exception as err:
        logger.error(f"Error generating static site: {err}", exc_info=True)


def process_category(category: str, content_dir: str, public_dir: str, backlinks: dict) -> None:
    try:
        logger.info(f"Processing category: {category}")
        category_dir = os.path.join(content_dir, category)
        output_dir = os.path.join(public_dir, category)
        template_name = f"{category}.html"

        if not os.path.isdir(category_dir):
            logger.error(f"Category directory `{category_dir}` does not exist.")
            return

        for file in os.listdir(category_dir):
            if file.endswith(".md"):
                md_fp = os.path.join(category_dir, file)
                output_fp = os.path.join(output_dir, file.replace(".md", ".html"))
                process_file(md_fp, output_fp, template_name, backlinks)
    except Exception as err:
        logger.error(f"Error processing category `{category}`: {err}", exc_info=True)


def process_index(content_dir: str, public_dir: str, backlinks: dict) -> None:
    try:
        logger.info("Processing `index.md`.")
        index_md_fp = os.path.join(content_dir, "index.md")
        index_template = "index.html"
        index_output_fp = os.path.join(public_dir, "index.html")

        if not os.path.exists(index_md_fp):
            logger.error(f"`index.md` file does not exist at: {index_md_fp}")
            return

        process_file(index_md_fp, index_output_fp, index_template, backlinks)
        logger.info(f"Processed `index.md` into {index_output_fp}")
    except Exception as err:
        logger.error(f"Error processing `index.md`: {err}", exc_info=True)
