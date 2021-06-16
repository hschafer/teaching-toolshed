import pandas as pd
import datetime


class Canvas:
    def __init__(
        self, filename, student_name="Student", sid="SIS Login ID", dummy_rows=2
    ):
        self.filename = filename
        self.student_name = student_name
        self.sid = sid
        self.dummy_rows = dummy_rows

        # Useful to know which assignments we changed for reporting differences
        self.changes = []

        # Read in data
        df = pd.read_csv(filename)
        df = df[self.dummy_rows :]
        self.dummies = df[: self.dummy_rows]
        self.canvas = df.set_index(self.sid)

    def _find_column(self, col, grab_first=False):
        if col in self.canvas:
            return col
        else:
            columns = self.canvas.columns
            columns = columns[columns.str.startswith(col)]
            if len(columns) == 1 or (grab_first and len(columns) > 1):
                return columns[0]
            else:
                raise ValueError(
                    f"canvas_col ({col}) does not uniquely identify one column"
                )

    def add_grades(self, canvas_col, csv_reader, grab_first=False):
        canvas_col = self._find_column(canvas_col, grab_first=grab_first)

        self.changes.append(canvas_col)

        # Join together to get scores for this column
        self.canvas[canvas_col] = self.canvas.join(csv_reader.scores, how="left")[
            csv_reader.score_col
        ]

        # Give everyone else a 0
        self.canvas[canvas_col].fillna(0, inplace=True)

    def report_diffs(self):
        df_merged = self.original_canvas.merge(
            self.canvas, left_on=self.sid, right_on=self.sid, suffixes=("_old", "_new")
        )

        # Find rows that changed
        diffs = None
        for changed_col in self.changes:
            col_diffs = df_merged[changed_col + "_old"].astype(float) != df_merged[
                changed_col + "_new"
            ].astype(float)
            if diffs is None:
                diffs = col_diffs
            else:
                diffs = diffs | col_diffs

        if diffs.sum() == 0:
            print("No differences found! 😱")
        else:
            print(f"Found {diffs.sum()} differences")
            cols = (
                [self.student_name + "_old", self.sid]
                + [col + "_old" for col in self.changes]
                + [col + "_new" for col in self.changes]
            )
            return df_merged[diffs][cols].copy()

    def export(self, filename=None):
        if filename is None:
            filename = Canvas.export_filename()

        df = self.dummies.append(
            self.canvas.reset_index(), ignore_index=True, sort=False
        )
        df.to_csv(filename, index=False)

    @staticmethod
    def export_filename():
        now = datetime.datetime.now()
        date_format = "%Y-%b-%d-at-%H-%M"
        return f"Canvas-Export-{now.strftime(date_format)}.csv"
