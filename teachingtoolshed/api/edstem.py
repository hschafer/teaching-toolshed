"""
Module defining access to the EdStem API

Note that the EdStem API is still under development and there is no promise for
its stability. Use at your own risk.

Every request requires you authenticate. In order to do this, you will need your
authentication token from EdStem. You can access your token by looking at network requests
on EdStem and finding a request with an x-token header.
"""
from typing import Any, Dict, List

import requests

# Special type to indicate only a 0 or 1 should be passed
BinaryFlag = int


def urljoin(*parts):
    """Combines parts of a URL into a fully path.

    Removes any additional trailing or leading "/" characters.

    Example:
      urljoin('abc.com', 'path/', 'file.txt) -> 'abc.com/path/file.txt'

    Args:
        *parts: Any sequence of parts of a URL to join

    Returns:
        Concatenate the parts of the URL together, separated by "/".
    """
    return "/".join(str(part).strip("/") for part in parts)


class EdStemAPI:
    API_URL = f"https://us.edstem.org/api/"

    def __init__(self, course_id: int, token: str):
        """Initializes access to the EdStem API for a course with the given ID.


        Args:
            course_id: An integer course ID for the course to access. See EdStem URL.
            token: Your EdStem authentication token
        """
        self._course_id = course_id
        self._token = token

    # General functions for GET/POST
    def _ed_get_request(
        self, url: str, query_params: Dict[str, Any] = {}
    ) -> Dict[str, Any]:
        """Sends a GET request to EdStem.

        Args:
            url: URL endpoint to hit
            query_params: A dictionary of query parameters and values

        Returns:
            A JSON response from the endpoint

        Raises:
            HTTPError: If there was an error with the HTTP request
        """
        response = requests.get(
            url, params=query_params, headers={"x-token": self._token}
        )
        response.raise_for_status()
        return response.json()

    def _ed_post_request(self, url: str, query_params: Dict[str, Any] = {}) -> bytes:
        """Sends a POST request to EdStem.

        Args:
            url: URL endpoint to hit
            query_params: A dictionary of query parameters and values

        Returns:
            A binary string containing response content

        Raises:
            HTTPError: If there was an error with the HTTP request
        """
        response = requests.post(url, params=query_params, data={"_token": self._token})
        response.raise_for_status()
        return response.content

    # Enrollment info
    def get_users(self):
        admin_path = urljoin(EdStemAPI.API_URL, f"courses/{self._course_id}/admin")
        admin_info = self._ed_get_request(admin_path)
        return admin_info["users"]

    # Get lesson info
    def get_all_lessons(self) -> List[Dict[str, Any]]:
        """Gets all lessons for a course. Endpoint: /courses/{course_id}/lessons

        Returns:
            A list of JSON objects, one for each lesson.
        """
        lessons_path = urljoin(EdStemAPI.API_URL, f"courses/{self._course_id}/lessons")
        lessons = self._ed_get_request(lessons_path)
        return lessons["lessons"]

    def get_lesson(self, lesson_id: int) -> Dict[str, Any]:
        """Gets metadata for a single lesson. Endpoint: /lessons/{lesson_id}

        Args:
            lesson_id: Identifier for lesson

        Returns:
            A JSON object with the specified lesson's metadata
        """
        lesson_path = urljoin(EdStemAPI.API_URL, "lessons", lesson_id)
        lesson = self._ed_get_request(lesson_path)["lesson"]
        return lesson

    def get_questions(self, slide_id: int) -> List[Dict[str, Any]]:
        """Gets metadata for a single Quiz slide's questions. Endpoint: /lessons/slides/{slide_id}/questions

        Args:
            slide_id: Identifier for slide

        Returns:
            A JSON object with the specified lesson's metadata
        """
        questions_path = urljoin(
            EdStemAPI.API_URL, "lessons", "slides", slide_id, "questions"
        )
        questions = self._ed_get_request(questions_path)["questions"]
        return questions

    # Methods for getting information about lesson/assignment completion
    def get_lesson_completions(
        self,
        lesson_id: int,
        completions: BinaryFlag = 1,
        numbers: BinaryFlag = 1,
        scores: BinaryFlag = 1,
        students: BinaryFlag = 1,
        strategy: str = "latest",
        ignore_late: BinaryFlag = 0,
        late_no_points: BinaryFlag = 0,
        tz: str = "America/Los_Angeles",
    ) -> bytes:
        """Gets completion information for a single lesson. Endpoint: /lessons/{lesson_id}/results.csv

        Same as using the "Download Lesson Results..." (completions=0) or
        "Download Lesson Completions..." (completions=1) option in the lesson menu.
        Our documentation is in terms of the options seen in this popup. Checkboxes correspond to
        BinaryFlag values 1 for checked and 0 for unchecked.

        Args:
            lesson_id: Identifier for lesson
        Optional Args:
            completions: If 1, gets completions and if 0 gets results. Completions show timestamps
              for when each slide was finished. Results shows scores.
            numbers: Check; "Slide numbers: Include a header row with the number of each slide"
            scores: Check; "Slide scores: Include a header row with the score for each slide"
            students: Check; "Include students only: Only student results will be included in the report"
            strategy: Indicate which submissions should be downloaded
              Currently supports: 'best' and 'latest'
            ignore_late: Check; "Ignore late submissions"
            late_no_points: Check; "Late submissions are worth 0 points"
            tz: Timezone for datetimes

        Returns:
            Bytes content of the result file. Usually will be used to save to a file.
        """
        lesson_completion_path = urljoin(
            EdStemAPI.API_URL, "lessons", lesson_id, "results.csv"
        )
        result = self._ed_post_request(
            lesson_completion_path,
            {
                "numbers": numbers,
                "scores": scores,
                "students": students,
                "completions": completions,
                "strategy": strategy,
                "ignore_late": ignore_late,
                "late_no_points": late_no_points,
                "tz": tz,
            },
        )
        return result

    def get_challenge_results(
        self,
        challenge_id: int,
        students: BinaryFlag = 1,
        feedback: BinaryFlag = 0,
        type: str = "optimised",
        score_type: str = "pertestcase",
        numbers: BinaryFlag = 0,
        scores: BinaryFlag = 0,
        tz: str = "America/Los_Angeles",
    ) -> bytes:
        """Gets results for a single coding challenge. Endpoint: /challenges/{challenge_id}/results.csv

        Note that both lesson coding challenges (including the Jupyter type) and assignments
        are both considered coding challenges. The challenge_id is NOT the same as the slide_id for a
        challenge slide.

        Same as using the "Download Results..." assessments menu.
        Our documentation is in terms of the options seen in this popup. Checkboxes correspond to
        BinaryFlag values 1 for checked and 0 for unchecked.

        Args:
            challenge_id: Identifier for challenge (not the same as a slide_id)
        Optional Args:
            students: Check; "Include students only"
            feedback: Check; "Include feedback criteria columns and comment"
            type: Dropdown; "Choose which submissions will be included in the report"
                Options: 'latest', 'latest-with-feedback', 'optimised, 'all'
            numbers: Currently not specifiable in the UI
            scores: Currently not specifiable in the UI
            score_type: Radio; "Choose how testcases scores are reported"
                Options: 'pertestcase' and 'passfail'
            tz: Timezone for datetimes

        Returns:
            Bytes content of the result file. Usually will be used to save to a file.
        """
        challenge_path = urljoin(
            EdStemAPI.API_URL, "challenges", challenge_id, "results"
        )
        result = self._ed_post_request(
            challenge_path,
            {
                "students": students,
                "type": type,
                "numbers": numbers,
                "scores": scores,
                "score_type": score_type,
                "feedback": feedback,
                "tz": tz,
            },
        )
        return result

    def get_quiz_results(
        self, quiz_id: int, students: BinaryFlag = 1, no_attempt: BinaryFlag = 1
    ):
        """Gets results for a single quiz. Endpoint: /lessons/slides/{quiz_id}/questions/results

        Note that the quiz_id is not the same as the slide_id for a quiz slide

        Same as using the "Download Quiz Responses..." quiz slide menu.
        Our documentation is in terms of the options seen in this popup. Checkboxes correspond to
        BinaryFlag values 1 for checked and 0 for unchecked.

        Args:
            challenge_id: Identifier for challenge (not the same as a slide_id)
        Optional Args:
            students: Check; "Include students only: Only student responses will be included in the report"
            no_attempt: Check; "Show empty attempts: Create a row for the user in the results even if the user has not attempted the quiz"

        Returns:
            Bytes content of the result file. Usually will be used to save to a file.

        """
        quiz_path = urljoin(
            EdStemAPI.API_URL, "lessons/slides", quiz_id, "questions/results"
        )
        result = self._ed_post_request(
            quiz_path,
            {
                "students": students,
                "noAttempt": no_attempt,
            },
        )
        return result

    def get_all_users(self, challenge_id):
        users_path = urljoin(EdStemAPI.API_URL, "challenges", challenge_id, "users")

        result = self._ed_get_request(users_path)["users"]
        return result

    def get_all_submissions(
        self,
        challenge_id,
        user_id,
    ):
        submission_path = urljoin(
            EdStemAPI.API_URL,
            "users",
            user_id,
            "challenges",
            challenge_id,
            "submissions",
        )

        result = self._ed_get_request(submission_path)["submissions"]
        return result
