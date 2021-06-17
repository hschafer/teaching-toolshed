import logging
import os
import pathlib
import re
import unicodedata

import yaml

from teachingtoolshed.api.edstem import EdStemAPI

# Logger config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("download_lesson_results")


# Define constants

COURSE_ID = 4914
with open(os.path.expanduser("~/.secrets/ed_token")) as f:
    TOKEN = f.read().strip()

OUTPUT_DIR = "data/"


# Define helper functions


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
    value = re.sub(r"[^\w\s-]", "", value.lower())
    return re.sub(r"[-\s]+", "-", value).strip("-_")


def save_file(file_name, content):
    """
    Saves the given binary content to the given file_name
    """
    with open(file_name, "wb") as fd:
        fd.write(content)


def get_lesson_metadata(lesson_data):
    # To avoid slashes in titles
    title = slugify(lesson_data["title"])

    logger.info(f'Lesson {lesson_data["id"]} {title}')

    # Metadata
    lesson_metadata = {
        "title": title,
        "due_date": lesson_data["due_at"],
        "late_cutoff": lesson_data["locked_at"],
        "quiz": [],
        "code": [],
    }
    return lesson_metadata


def save_lesson(ed, lesson_data, lesson_metadata):
    # Make folder for lesson
    lesson_folder = os.path.join(OUTPUT_DIR, lesson_metadata["title"])
    pathlib.Path(lesson_folder).mkdir(parents=True, exist_ok=True)

    # Download lesson completions
    completion_file = os.path.join(lesson_folder, "completions.csv")
    if not os.path.exists(completion_file):
        logger.info(f'Completions {lesson_data["id"]}')
        data = ed.get_lesson_completions(lesson_data["id"])
        save_file(completion_file, data)

    # Get each lesson results
    for slide in lesson_data["slides"]:
        slide_title = slugify(slide["title"])
        result_path = os.path.join(lesson_folder, f"{slide_title}.csv")

        if not os.path.exists(result_path):
            if slide["type"] in ["code", "jupyter"]:
                logger.info(f'Coding Challenge {slide["id"]}')
                data = ed.get_challenge_results(slide["challenge_id"])
                save_file(result_path, data)

                lesson_metadata["code"].append(slide_title)

            elif slide["type"] in ["quiz"]:
                logger.info(f'Quiz Challenge {slide["id"]}')
                data = ed.get_quiz_results(slide["id"])
                save_file(result_path, data)

                lesson_metadata["quiz"].append(slide_title)


def main():
    ed = EdStemAPI(COURSE_ID, TOKEN)

    metadata = []
    for lesson in ed.get_all_lessons():
        if "📚 Lecture" in lesson["title"]:
            lesson_data = ed.get_lesson(lesson["id"])
            lesson_metadata = get_lesson_metadata(lesson_data)
            save_lesson(ed, lesson_data, lesson_metadata)
            metadata.append(lesson_metadata)

    # Save metadata file
    metadata.sort(key=lambda d: d["due_date"])
    yaml.dump(metadata, open(os.path.join(OUTPUT_DIR, "metadata.yaml"), "w"))


if __name__ == "__main__":
    main()
