import datetime
import json
import logging
import os
import pathlib
import random
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import yaml
from pytz import timezone

sns.set()

# Logger config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("compute_lesson_scores")

# Constants
DATA_DIR = "data/lessons"
OUTPUT_DIR = "out/lesson_scores/"
STUDENT_INFO_COLUMNS = ["name", "email", "tutorial", "SIS ID"]
IGNORE_COLUMNS = STUDENT_INFO_COLUMNS + ["first viewed", "total score"]
DROP_LOWEST = 3


def read_completions(lesson_name):
    path = os.path.join(DATA_DIR, lesson_name, "completions.csv")

    # Read in data
    df = pd.read_csv(path, skiprows=2)

    # Get slide columns
    slide_columns = df.columns[~df.columns.isin(IGNORE_COLUMNS)]

    # Kind of a hack, but we read the data in again to parse dates correctly
    df = pd.read_csv(
        path, skiprows=2, parse_dates=list(slide_columns), infer_datetime_format=True
    )
    df = df.set_index("email")

    return df, slide_columns


def parse_due_date(due_date_str):
    """
    Takes a str for a datetime and converts it to a
    timezone aware datetime
    """
    # dt = pd.Series([f"{due_date_str}"])
    # dt = pd.to_datetime(dt)
    # return dt.iloc[0]
    return pd.to_datetime(due_date_str)


def find_practice_column(df, name):
    """
    Given
    """
    columns = df.columns
    columns = columns[columns.str.contains("🚧") & columns.str.contains(name)]
    assert len(
        columns == 1
    ), f"Expected 1 column, found {len(columns)}: {columns}\nSearching for {name} in {df.columns}"
    return columns[0]


def compute_ed_scores(lesson, df, slide_columns, due_date, compute_score):
    """
    Takes a DataFrame from an Ed export of completions and a str representing the due date
    and returns a Series (indexed by email) of the students' scores for this assignment
    """

    # Compute the score for this reading
    buffer_date = due_date + datetime.timedelta(minutes=15)
    print(buffer_date, type(buffer_date))
    print(df[slide_columns])
    print(df[slide_columns].dtypes)
    before_due_date = ~(df[slide_columns] > buffer_date)
    before_late_cutoff = ~(
        df[slide_columns] > (buffer_date + datetime.timedelta(days=7))
    )

    all_on_time = 0.5 * before_due_date + 0.5 * before_late_cutoff

    # All or nothing
    if compute_score == "all_or_nothing":
        all_on_time = np.floor(before_due_date.sum(axis=1) / len(slide_columns))
        all_correct = (df["total score"] == df["total score"].max()).astype(int)
        return all_on_time * all_correct

    elif compute_score == "partial_credit_by_score":
        lesson_path = os.path.join(DATA_DIR, lesson["title"])

        # Quizzes
        quiz_scores = pd.Series(0, index=df.index)
        for quiz in lesson["quiz"]:
            logging.info(quiz)
            quiz_file = os.path.join(lesson_path, f"{quiz['file']}.csv")
            scores_df = pd.read_csv(quiz_file).set_index("email")

            quiz_on_time = all_on_time[
                find_practice_column(before_due_date, quiz["name"])
            ]
            max_score = scores_df["total score"].max()

            quiz_scores += (scores_df["total score"] * quiz_on_time) / max_score

        return quiz_scores / len(lesson["quiz"])


def collect_completions(gradebook, column_prefix, metadata, compute_score):

    # For each lecture, add to the score
    for lesson in metadata:
        logging.info(f"Computing scores for {lesson['title']}")

        # Get due date
        due_date = parse_due_date(lesson["due_date"])

        # Read in data
        df, slide_columns = read_completions(lesson["title"])

        # Find columns with completions

        target_col_name = f"{column_prefix}{lesson['num']}"
        gradebook[target_col_name] = compute_ed_scores(
            lesson, df, slide_columns, due_date, compute_score=compute_score,
        )

    return gradebook


def compute_overall_score(metadata, lessons_gradebook, total_col="total"):
    score_cols = ~lessons_gradebook.columns.isin(STUDENT_INFO_COLUMNS)
    # Sum up all the lesson scores
    lessons_gradebook[total_col] = lessons_gradebook.loc[:, score_cols].sum(axis=1)

    # Drop the lowest 3 assignments
    lessons_gradebook[total_col] = lessons_gradebook[total_col].clip(
        upper=len(metadata) - DROP_LOWEST
    )


def display_stats(lessons_gradebook, total_col="total"):
    # Print and save stats
    print("Lesson stats")
    stats = lessons_gradebook[total_col].describe()
    print(stats)
    with open(os.path.join(OUTPUT_DIR, "stats.txt"), "w") as f:
        f.write(str(stats))

    # Make a bar chart of scores
    possible_scores = np.arange(
        0, max(lessons_gradebook[total_col]) + 2
    )  # Kind of annoying to get chart to look correct
    fig, ax = plt.subplots(1, figsize=(20, 10))
    sns.histplot(lessons_gradebook[total_col], ax=ax, bins=possible_scores)
    _ = ax.set_xlabel("Score")
    _ = ax.set_xticks(possible_scores)
    out_path = os.path.join(OUTPUT_DIR, "lessons_scores_hist.png")
    fig.savefig(out_path, bbox_inches="tight")

    # Make CDF of scores
    fig, ax = plt.subplots(1, figsize=(20, 10))
    sns.ecdfplot(data=lessons_gradebook, x=total_col, ax=ax)
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
    lessons_gradebook, _ = read_completions(metadata[-1]["title"])
    lessons_gradebook = lessons_gradebook[["name", "tutorial"]]

    collect_completions(
        lessons_gradebook, "L{num}", metadata, compute_score="partial_credit_by_score"
    )  # , weights=20)

    compute_overall_score(metadata, lessons_gradebook)

    # Save scorebook
    result_path = os.path.join(OUTPUT_DIR, "lessons.csv")
    lessons_gradebook = lessons_gradebook.reset_index()
    lessons_gradebook.to_csv(result_path, index=False)

    # Visualize stats
    display_stats(lessons_gradebook)


if __name__ == "__main__":
    main()
