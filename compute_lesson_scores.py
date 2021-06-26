"""Script to compute a lessons gradebook for lesson completions.

Could also be useful to run multiple times with different sources (e.g., daily
lessons and weekly checkpoints). Saves a gradebook for the lessons in OUTPUT_DIR.

I tried my best to document specific syllabus choices that impact my grading (e.g., late
lessons and dropping lowest).

Must be run after downloading lessons (usually with download_lesson_results.py)
"""
import datetime
import logging
import os
import pathlib
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import yaml

from teachingtoolshed.gradebook.csv_readers import EdStemReader

sns.set()

# Logger config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("compute_lesson_scores")

# Constants
DATA_DIR = "data/lessons"
OUTPUT_DIR = "out/lesson_scores/"
IGNORE_COLUMNS = ["name", "email", "tutorial", "SIS ID", "first viewed", "total score"]
DROP_LOWEST = 3


def read_completions(lesson_name: str) -> Tuple[pd.DataFrame, List[str]]:
    """Reads a completions.csv for the given lesson identifier.

    Returns a tuple of length two:
      - A DataFrame (indexed by email) storing completions data
      - A List of column names for the slides containing slide completions
    """
    # TODO I feel like this could potentially use an abstraction like a CSV reader

    path = os.path.join(DATA_DIR, lesson_name, "completions.csv")

    # Read in data
    df = pd.read_csv(path, skiprows=2)

    # Get slide columns
    slide_columns = list(df.columns[~df.columns.isin(IGNORE_COLUMNS)])

    # Kind of a hack, but we read the data in again to parse dates correctly
    df = pd.read_csv(
        path, skiprows=2, parse_dates=slide_columns, infer_datetime_format=True
    )
    df = df.set_index("email")

    return df, slide_columns


def compute_single_lesson_score(
    lesson_metadata: Dict[str, Any],
    df: pd.DataFrame,
    slide_columns: List[str],
    due_date: datetime.datetime,
) -> pd.Series:
    """Takes a DataFrame from an Ed export of completions and a str representing the due date
    and returns a Series (indexed by email) of the students' scores for this assignment.
    """
    # Compute a binary 1/0 value for each completion if it is on time.
    # Allows a 15 minute buffer and half credit for anything up to a week late
    due_date_buffered = due_date + datetime.timedelta(minutes=15)
    late_date_buffered = due_date_buffered + datetime.timedelta(days=7)
    before_due_date = df[slide_columns] < due_date_buffered
    before_late_cutoff = df[slide_columns] < late_date_buffered

    # This formula gives 1 for on time, 0.5 for less than week late, and 0 for more than week late
    all_on_time = 0.5 * before_due_date + 0.5 * before_late_cutoff

    # Only count scores of slides students had to do work on (e.g., code and quiz)
    scores = pd.Series(0, index=df.index)
    points_total = 0
    for type in ["quiz", "code"]:
        for slide in lesson_metadata[type]:
            logging.info(f"Processing {slide['name']}")

            # Read in results. Note we want to keep the sid's as emails for simplicity
            results_file = os.path.join(
                DATA_DIR, lesson_metadata["title"], f"{slide['file']}.csv"
            )
            results = EdStemReader(
                results_file, "email", "total score", sid_is_email=False
            )
            slide_scores = results.scores[results.score_col]

            # Get points total (assume one student got max score)
            slide_out_of = slide_scores.max()

            # Get if this slide was on time for each student
            slide_on_time = all_on_time[slide["name"]]

            # Add to cumulative sum
            scores += slide_scores * slide_on_time
            points_total += slide_out_of

    return scores / points_total


def collect_all_lesson_completions(
    gradebook: pd.DataFrame, column_prefix: str, metadata: List[Dict[str, Any]]
) -> Tuple[pd.DataFrame, List[str]]:
    """Given a gradebook (DataFrame) and a list of lesson metadata, computes a score
    for each lesson and stores that in the gradebook. Saves each lesson score individually
    in a column with the format "{column_prefix}{lesson_num}" (e.g. L1, L2, L3, ...).

    Returns a tuple:
      - The gradebook with the lesson scores
      - A list of column names for the lessons
    """
    # For each lecture, add to the score
    lesson_column_names = []

    for lesson in metadata:
        logging.info(f"Computing scores for {lesson['title']}")

        # Get due date
        due_date = pd.to_datetime(lesson["due_date"])

        # Read in data
        df, slide_columns = read_completions(lesson["title"])

        # Compute score for this lesson and save in gradebook
        target_col_name = f"{column_prefix}{lesson['num']}"
        gradebook[target_col_name] = compute_single_lesson_score(
            lesson, df, slide_columns, due_date
        )
        lesson_column_names.append(target_col_name)

    return gradebook, lesson_column_names


def compute_total_score(
    gradebook: pd.DataFrame,
    lesson_column_names: List[str],
    total_col: str = "total",
    drop_lowest: int = 0,
) -> pd.DataFrame:
    """Given a gradebook and the column names for the individual lesson scores, computes
    a total score stored in total_col in gradebook. Drops the lowest drop_lowest assignments.

    Returns the new gradebook
    """
    # Sum up all the lesson scores
    gradebook[total_col] = gradebook.loc[:, lesson_column_names].sum(axis=1)

    # Drop the lowest drop_lowest assignments
    gradebook[total_col] = gradebook[total_col].clip(
        upper=len(lesson_column_names) - drop_lowest
    )

    return gradebook


def display_stats(gradebook: pd.DataFrame, total_col: str = "total"):
    """Saves statistics about the grades in total_col"""
    # Print and save stats
    print("Lesson stats")
    stats = gradebook[total_col].describe()
    print(stats)
    with open(os.path.join(OUTPUT_DIR, "stats.txt"), "w") as f:
        f.write(str(stats))

    # Make a bar chart of scores
    possible_scores = np.arange(
        0, max(gradebook[total_col]) + 2
    )  # Kind of annoying to get chart to look correct
    fig, ax = plt.subplots(1, figsize=(20, 10))
    sns.histplot(gradebook[total_col], ax=ax, bins=possible_scores)
    _ = ax.set_xlabel("Score")
    _ = ax.set_xticks(possible_scores)
    out_path = os.path.join(OUTPUT_DIR, "lessons_scores_hist.png")
    fig.savefig(out_path, bbox_inches="tight")

    # Make CDF of scores
    fig, ax = plt.subplots(1, figsize=(20, 10))
    sns.ecdfplot(data=gradebook, x=total_col, ax=ax)
    _ = ax.set_xlabel("Score")
    out_path = os.path.join(OUTPUT_DIR, "lessons_scores_cdf.png")
    fig.savefig(out_path, bbox_inches="tight")


def main():
    # Ensure output dir exists
    pathlib.Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    # Load in metadata
    metadata = yaml.load(
        open(os.path.join(DATA_DIR, "metadata.yaml"), "r"), Loader=yaml.FullLoader
    )

    # Get the students enrolled in Ed
    # Kind of a hack, but just look at last Lecture reading to get list of students
    gradebook, _ = read_completions(metadata[-1]["title"])
    gradebook = gradebook[["name", "tutorial"]]

    # Get the scores
    gradebook, lessson_columns = collect_all_lesson_completions(
        gradebook, "L{num}", metadata
    )
    gradebook = compute_total_score(gradebook, lessson_columns, drop_lowest=DROP_LOWEST)

    # Save scorebook
    result_path = os.path.join(OUTPUT_DIR, "lessons.csv")
    gradebook = gradebook.reset_index()
    gradebook.to_csv(result_path, index=False)

    # Visualize stats
    display_stats(gradebook)


if __name__ == "__main__":
    main()
