from teachingtoolshed.gradebook.canvas import Canvas
from teachingtoolshed.gradebook.csv_readers import CSVReader, EdStemReader, GradescopeReader





def main():
    # One student has their personal Gmail in EdStem instead of their UWNetID
    renames = {
        'example_students_personal_gmail': 'example_uw_netid'
    }

    # Read Canvas CSV Export
    canvas = Canvas('CanvasGradebook.csv')

    #hw7 = Ed('HW7 - k-means with Text Data results latest-with-feedback.csv',
    #         sid_col='email', score_col='feedback grade', sid_is_email=True,
    #         rename_index=renames)
    #canvas.add_grades('HW7 - Coding', hw7, grab_first=True)

    #hw8 = Ed('HW8 - Recommendation with Text Data results latest-with-feedback.csv',
    #         sid_col='email', score_col='feedback grade', sid_is_email=True,
    #         rename_index=renames)
    # canvas.add_grades('HW8 - Coding', hw8, grab_first=True)

    lessons = CSVReader('lessons.csv', sid_col='email', score_col='total', sid_is_email=True)
    canvas.add_grades('Checkpoint Completion', lessons)

    # Save grades
    canvas.export()


if __name__ == '__main__':
    main()
