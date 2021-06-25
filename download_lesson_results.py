"""Script to download completions and results for every lesson in EdStem

Makes a folder (OUTPUT_DIR) where each lesson will have its own sub-folder.
Each lesson folder will store:
- completions.csv: The completions CSV containing timestamps when a student completed each slide.
- X.csv: The results CSV from quiz or coding challenge named X. There will be one CSV for every
  quiz or coding slide.

Will also save a YAML file called metadata.yaml in OUTPUT_DIR that will store all information
downloaded for every lesson. Useful file for downstream scripts that want to get a list of all
lessons, their associated slides, and the respective files to get the info you want for that
lesson.
"""
import logging
import os
import pathlib
import re
import unicodedata

import pandas as pd
import yaml

from teachingtoolshed.api.edstem import EdStemAPI

# Logger config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("download_lesson_results")


# Define constants

COURSE_ID = 4914
with open(os.path.expanduser("~/.secrets/ed_token")) as f:
    TOKEN = f.read().strip()

OUTPUT_DIR = "data/lessons"


# Download logic


def slugify(value, allow_unicode=False):
    """Taken from https://github.com/django/django/blob/master/django/utils/text.py
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
    """Saves the given binary content to the given file_name"""
    with open(file_name, "wb") as fd:
        fd.write(content)


def convert_timestamp_to_pst(due_date_str):
    """Takes a str for a datetime and converts it to a
    timezone aware datetime
    """
    if due_date_str:
        dt = pd.to_datetime(pd.Series([f"{due_date_str}"]))
        dt = dt.iloc[0]

        # Time stamp is in a fixed-offset format. Convert it to PST
        dt = dt.tz_convert("America/Los_Angeles")

        return str(dt)
    else:
        return None


def get_lesson_metadata(lesson_data):
    """For the given lesson API result, returns metadata about the lesson
    as a dictionary.

    Returns None if this is not a Lesson we should download (e.g., a section)
    """
    # All of my lessons for lecture start with this prefix
    if "📚 Lecture" not in lesson_data["title"]:
        return None

    # Extrace lecture number from title
    lecture_num = re.match(r"📚 Lecture (\d+)", lesson_data["title"]).group(1)
    lecture_num = int(lecture_num)

    # To avoid slashes in titles
    title = slugify(lesson_data["title"])
    logger.info(f'Lesson {lesson_data["id"]} {title}')

    # Metadata
    lesson_metadata = {
        "title": title,
        "num": lecture_num,
        "due_date": convert_timestamp_to_pst(lesson_data["due_at"]),
        "late_cutoff": convert_timestamp_to_pst(lesson_data["locked_at"]),
        "quiz": [],
        "code": [],
    }
    return lesson_metadata


def save_lesson(ed, lesson_data, lesson_metadata):
    """For the given lesson_data (from EdStem) and lesson_metadata
    (computed by us), save a folder with the completions and results
    for this lesson.

    Needs an EdStem API (ed) to gather results from quiz/code slides
    """
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
        # Compute metadata for slide
        slide_title = slugify(slide["title"])
        result_path = os.path.join(lesson_folder, f"{slide_title}.csv")
        slide_metadata = {"name": slide["title"], "file": slide_title}

        # Go fetch results depending on type
        if slide["type"] in ["code", "jupyter"]:
            logger.info(f'Coding Challenge {slide["id"]}')

            data = ed.get_challenge_results(slide["challenge_id"])
            save_file(result_path, data)

            lesson_metadata["code"].append(slide_metadata)

        elif slide["type"] in ["quiz"]:
            logger.info(f'Quiz Challenge {slide["id"]}')

            data = ed.get_quiz_results(slide["id"])
            save_file(result_path, data)

            lesson_metadata["quiz"].append(slide_metadata)


def main():
    # Create EdStem API
    ed = EdStemAPI(COURSE_ID, TOKEN)

    metadata = []
    for lesson in ed.get_all_lessons():
        # All of my lessons with the prefix shown below are the lessons I want to download
        lesson_data = ed.get_lesson(lesson["id"])
        lesson_metadata = get_lesson_metadata(lesson_data)
        if lesson_metadata is not None:
            save_lesson(ed, lesson_data, lesson_metadata)
            metadata.append(lesson_metadata)

    # Save metadata file
    metadata.sort(key=lambda d: d["num"])
    with open(os.path.join(OUTPUT_DIR, "metadata.yaml"), "w") as f:
        yaml.dump(metadata, f, sort_keys=False)


if __name__ == "__main__":
    main()
