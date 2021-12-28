import datetime
from typing import List

import pandas as pd
from teachingtoolshed.gradebook.csv_readers import CSVReader


class Canvas:
    def __init__(
        self,
        filename: str,
        student_name_col: str = "Student",
        sid_col: str = "SIS Login ID",
        dummy_rows: int = 2,
        out_dir: str = "out",
    ):
        """Class that manages state and changes to a Canvas Gradebook export.

        Args:
            filename: A filename to a Canvas Gradebook export to use as the starting grades.
            student_name_col: Column name in Gradebook that contains the student name
            sid: Column name in Gradebook that contains students UW Net ID (or whatever you will
              use to identify students)
            dummy_rows: Optional; The number of rows to skip in the Gradebook before the column
              header rows. These rows will be preserved in the output but need to parsed separately
              from the students and regular column headers.
        """
        self.filename: str = filename
        self.student_name_col: str = student_name_col
        self.sid_col: str = sid_col
        self.dummy_rows: int = dummy_rows
        self.out_dir = out_dir

        # Useful to know which assignments we changed for reporting differences
        self.changes: List[str] = []

        # Read in data
        df = pd.read_csv(filename)
        self.original_canvas: pd.DataFrame = df[self.dummy_rows :]
        self.dummies: pd.DataFrame = df[: self.dummy_rows]
        self.canvas: pd.DataFrame = self.original_canvas.set_index(self.sid_col)

    def _find_column(self, col_name_prefix: str, grab_first: bool = False) -> str:
        """Given the prefix of a column name, returns a full column name that matches this prefix.

        Useful for specifying a short prefix of a name rather than the whole Canvas Column
        (which contains an arbitrary identifier). If the prefix does not uniquely identify one
        column, will raise an error (unless grab_first is True, in which case it returns the first)

        Args:
            col_name_prefix: The prefix of a column name
            grade_first: Determines behavior in the case where more than one column has
              col_name_prefix. If True, returns the first. If False, raises an ValueError.
        """
        if col_name_prefix in self.canvas:
            return col_name_prefix
        else:
            columns = self.canvas.columns
            potential_columns = columns[columns.str.startswith(col_name_prefix)]
            if len(potential_columns) == 1 or (
                grab_first and len(potential_columns) > 1
            ):
                return potential_columns[0]
            else:
                raise ValueError(
                    f"canvas_col ({col_name_prefix}) does not uniquely identify one column"
                )

    def add_grades(
        self, canvas_col_name: str, csv_reader: CSVReader, grab_first: bool = False
    ):
        """Adds the scores from csv_reader to the Gradebook column canvas_col_name.

        The CSVReader and its subclasses read in student grades from other sources and
        are indexed by some unique student identifier (e.g., UW NetID). Note the values
        in the csv_reader's identifiers must match the sid values in this class.

        Args:
            canvas_col_name: The prefix or full name of a column in the Canvas Gradebook
            csv_reader: A CSVReader containing scores from another source
            grade_first: Determines behavior in the case where more than one column has
              col_name_prefix. If True, returns the first. If False, raises an ValueError.
        """
        canvas_col_name = self._find_column(canvas_col_name, grab_first=grab_first)

        self.changes.append(canvas_col_name)

        # Join together to get scores for this column
        self.canvas[canvas_col_name] = self.canvas.join(csv_reader.scores, how="left")[
            csv_reader.score_col
        ]

        # Give everyone else a 0
        self.canvas[canvas_col_name].fillna(0, inplace=True)

    def set_grade(
        self,
        student_id: str,
        canvas_col_name: str,
        score: float,
        grab_first: bool = False,
    ):
        """
        Sets the grade for the given student for the given assignment to a particular value
        """
        canvas_col_name = self._find_column(canvas_col_name, grab_first=grab_first)
        self.canvas.loc[student_id, canvas_col_name] = score

    def get_grade(
        self, student_id: str, canvas_col_name: str, grab_first: bool = False
    ):
        canvas_col_name = self._find_column(canvas_col_name, grab_first=grab_first)
        return self.canvas.loc[student_id, canvas_col_name]

    def report_diffs(self, verbose=False):
        """Utility method to report differences for assignments added"""

        df_merged = self.original_canvas.merge(
            self.canvas,
            left_on=self.sid_col,
            right_on=self.sid_col,
            suffixes=("_old", "_new"),
        )

        # Find rows that changed
        diffs = None
        for changed_col in self.changes:
            col_diffs = df_merged[changed_col + "_old"].astype(float) != df_merged[
                changed_col + "_new"
            ].astype(float)

            if verbose and col_diffs.any():
                print(f"Changes for {changed_col}")
                print(
                    df_merged.loc[
                        col_diffs,
                        [
                            self.student_name_col + "_old",
                            self.sid_col,
                            changed_col + "_old",
                            changed_col + "_new",
                        ],
                    ]
                )

            if diffs is None:
                diffs = col_diffs
            else:
                diffs = diffs | col_diffs

        if diffs.sum() == 0:
            print("No differences found! 😱")
        else:
            print(f"Found {diffs.sum()} differences")
            cols = (
                [self.student_name_col + "_old", self.sid_col]
                + [col + "_old" for col in self.changes]
                + [col + "_new" for col in self.changes]
            )

            if verbose and diffs.sum() > 0:
                print("All Changes")
                print(df_merged.loc[diffs, cols])
            return df_merged[diffs][cols].copy()

    def export(self, filename: str = None):
        """Saves the current Gradebook to a new filename

        Args:
            filename: Optional; File name to save to. If None,
              generates a timestamped filename.
        """
        if filename is None:
            filename = self.export_filename()

        df = self.dummies.append(
            self.canvas.reset_index(), ignore_index=True, sort=False
        )
        df.to_csv(filename, index=False)

    def export_filename(self) -> str:
        """Returns a timestamped filename for exporting"""
        now = datetime.datetime.now()
        date_format = "%Y-%b-%d-at-%H-%M"
        return f"{self.out_dir}/Canvas-Export-{now.strftime(date_format)}.csv"
