import pandas as pd


class CSVReader:
    def __init__(self, fname, sid_col, score_col, sid_is_email=False, dummy_rows=0):
        self.fname = fname
        self.dummy_rows = dummy_rows
        self.score_col = score_col
        self.sid_col = sid_col  # Might modify after reading in data

        # Read in data
        self.scores = pd.read_csv(fname, skiprows=self.dummy_rows)

        # Change sid_col to store just UW Net IDs if they are emails
        if sid_is_email:
            self.scores[self.sid_col] = self.scores[self.sid_col].str.split("@").str[0]

        # Make the data frame indexed by net id
        self.scores = self.scores.set_index(self.sid_col)

        # Drop all columns that aren't the score column. Keep as DataFrame
        self.scores = self.scores[[self.score_col]]


class GradescopeReader(CSVReader):
    def __init__(self, fname, sid_col, score_col="Total Score", dummy_rows=0):
        super().__init__(fname, sid_col, score_col, dummy_rows=dummy_rows)


class EdStemReader(CSVReader):
    def __init__(
        self,
        fname,
        sid_col,
        score_col="feedback grade",
        sid_is_email=True,
        dummy_rows=0,
        rename_index={},
    ):
        super().__init__(
            fname, sid_col, score_col, sid_is_email=sid_is_email, dummy_rows=dummy_rows
        )
        self.scores = self.scores.rename(index=rename_index)
