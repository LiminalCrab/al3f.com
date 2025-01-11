import argparse
from src.command_parser import parse_commands
from src.base_utils import setup_logger

logger = setup_logger("main", "logs/master.log")


def main() -> None:
    try:
        logger.info("Starting the static site generator.")

        parser = argparse.ArgumentParser(description="Static Site Generator")
        parse_commands(parser)

        args = parser.parse_args()

        if hasattr(args, "func") and callable(args.func):
            logger.info(f"Executing command: {args.command}")
            args.func(args)
        else:
            parser.print_help()
    except Exception as err:
        logger.error(f"An unexpected error occurred: {err}", exc_info=True)


if __name__ == "__main__":
    main()
