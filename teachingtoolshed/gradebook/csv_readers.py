from typing import Any, Callable, Dict, Hashable, List, Mapping, Optional, Union

import pandas as pd

# Simple CSV Readers that read a single score column from various formatted CSVs


class CSVReader:
    def __init__(
        self,
        filename: str,
        sid_col: str,
        score_col: Union[str, List[str]],
        sid_is_email: bool = False,
        dummy_rows: int = 0,
    ):
        """Reads in a CSV containing scores for an assignment.

        Almost any grading tool outputs a CSV of scores for an assignment. This class
        is responsible for part of the process of moving the scores from an export CSV
        to your course gradebook (i.e., Canvas). Some systems store UW emails instead of
        UW NetID, so sid_is_email controls if the trailing part of the email ('@uw.edu')
        should be removed.

        Args:
            filename: Filename containing scores for an assignment
            sid_col: Name of the column in this CSV that identifies a student (e.g., a UW NetID)
            score_col: Name of the column in this CSV that has student scores for this assignment or a list of columns
            sid_is_email: Optional; If True, removes the suffix of the sid_col values related to an
              email address (i.e., '@uw.edu')
            dummy_rows: Optional; Number of rows to skip in the CSV at the beginning
        """
        self.filename: str = filename
        self.dummy_rows: int = dummy_rows
        self.score_col: Union[str, List[str]] = score_col
        self.sid_col: str = sid_col  # Might modify after reading in data

        # Read in data
        self.scores: pd.DataFrame = pd.read_csv(filename, skiprows=self.dummy_rows)

        # Change sid_col to store just UW Net IDs if they are emails
        if sid_is_email:
            self.scores[self.sid_col] = self.scores[self.sid_col].str.split(
                "@", expand=True
            )[0]

        # Make the data frame indexed by net id
        self.scores = self.scores.set_index(self.sid_col)

        # Drop all columns that aren't the score column. Keep as DataFrame
        if type(score_col) is str:
            score_columns = [score_col]
        else:  # type is list
            score_columns = score_col

        self.scores = self.scores[score_columns]


class GradescopeReader(CSVReader):
    def __init__(
        self,
        filename: str,
        sid_col: str,
        score_col: Union[str, List[str]] = "Total Score",
        dummy_rows: int = 0,
    ):
        """Helper class for common type of CSV export. See documentation for CSVReader"""
        super().__init__(filename, sid_col, score_col, dummy_rows=dummy_rows)


class EdStemReader(CSVReader):
    def __init__(
        self,
        filename: str,
        sid_col: str,
        score_col: Union[str, List[str]] = "feedback grade",
        sid_is_email: bool = True,
        dummy_rows: int = 0,
        rename_index: Dict[str, str] = {},
    ):
        """Helper class for common type of CSV export. See documentation for CSVReader.

        EdStem stores emails rather than a student id (by default). Some students use their
        personal email as their account email so we use rename_index to map these few
        students to their proper student ID

        Args:
            See CSVReader for most arguments
            rename_index: dict from personal email (without email suffix) to correct student ID
        """
        super().__init__(
            filename,
            sid_col,
            score_col,
            sid_is_email=sid_is_email,
            dummy_rows=dummy_rows,
        )
        self.scores = self.scores.rename(index=rename_index)  # type: ignore


# More complicated CSV Readers
