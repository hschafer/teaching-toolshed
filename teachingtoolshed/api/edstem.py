"""
Module defining access to the EdStem API

Note that the EdStem API is still under development and there is no promise for
its stability. Use at your own risk.

Every request requires you authenticate. In order to do this, you will need your
authentication token from EdStem. You can access your token by looking at network requests
on EdStem and finding a request with an x-token header.
"""
import itertools
import json
from typing import Any, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Special type to indicate only a 0 or 1 should be passed
BinaryFlag = int

API_URL = f"https://us.edstem.org/api/"


def url_join(*parts):
    """Combines parts of a URL into a fully path.

    Removes any additional trailing or leading "/" characters.

    Example:
      url_join('abc.com', 'path/', 'file.txt) -> 'abc.com/path/file.txt'

    Args:
        *parts: Any sequence of parts of a URL to join

    Returns:
        Concatenate the parts of the URL together, separated by "/".
    """
    return "/".join(str(part).strip("/") for part in parts)


def api_url(*parts):
    """
    Same as url_join but prepends parts with the API_URL
    """
    return url_join(API_URL, *parts)


class EdStemAPI:
    def __init__(
        self,
        course_id: int,
        token: str,
        max_retries: int = 10,
        retry_factor: float = 0.5,
        allowed_retry_statuses: List[int] = [429],
        allowed_retry_methods: List[str] = None,
    ):
        """Initializes access to the EdStem API for a course with the given ID.


        Args:
            course_id: An integer course ID for the course to access. See EdStem URL.
            token: Your EdStem authentication token
            max_retires: In the case of a rate limit, how many times we retry the request (default 10)
            retry_factor: Controls the spacing of time between retries. If the i^th retry fails, will wait
                          retry_factor * (2 ** i) seconds
            allowed_retry_statuses: List of status codes to retry (default [429])
            allowed_retry_methods: List of methods to retry (default None which allows all methods to be retried)
        """
        # Note to self: Okay to use the list default param here because we don't modify it. Take care though.

        self._course_id = course_id
        self._token = token

        # Initialize requests with retry
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=retry_factor,
            status_forcelist=allowed_retry_statuses,
            allowed_methods=allowed_retry_methods,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)

        self._requests = requests.Session()
        self._requests.mount("http://", adapter=adapter)
        self._requests.mount("https://", adapter=adapter)

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
        response = self._requests.get(
            url, params=query_params, headers={"Authorization": "Bearer " + self._token}
        )
        response.raise_for_status()
        return response.json()

    def _ed_post_request(
        self, url: str, query_params: Dict[str, Any] = {}, json: Dict[str, Any] = {}
    ) -> bytes:
        """Sends a POST request to EdStem.

        Args:
            url: URL endpoint to hit
            query_params: A dictionary of query parameters and values
            json: A dictionary of parameters and values to pass as the payload

        Returns:
            A binary string containing response content

        Raises:
            HTTPError: If there was an error with the HTTP request
        """
        response = self._requests.post(
            url,
            params=query_params,
            json=json,
            headers={"Authorization": "Bearer " + self._token},
        )
        response.raise_for_status()
        return response.content

    def _ed_put_request(
        self,
        url: str,
        query_params: Dict[str, Any] = {},
        json: Dict[str, Any] = {},
        data: Dict[str, Any] = {},
    ) -> bytes:
        """Sends a PUT request to EdStem.

        Args:
            url: URL endpoint to hit
            query_params: A dictionary of query parameters and values
            json: A dictionary of parameters and values to pass as the payload

        Returns:
            A binary string containing response content

        Raises:
            HTTPError: If there was an error with the HTTP request
        """
        response = self._requests.put(
            url,
            params=query_params,
            json=json,
            data=data,
            headers={"Authorization": "Bearer " + self._token},
        )
        response.raise_for_status()
        return response.content

    def _ed_delete_request(
        self,
        url: str,
        query_params: Dict[str, Any] = {},
        json: Dict[str, Any] = {},
        data: Dict[str, Any] = {},
    ) -> bytes:
        """Sends a DELETE request to EdStem.

        Args:
            url: URL endpoint to hit
            query_params: A dictionary of query parameters and values
            json: A dictionary of parameters and values to pass as the payload

        Returns:
            A binary string containing response content

        Raises:
            HTTPError: If there was an error with the HTTP request
        """
        response = self._requests.delete(
            url,
            params=query_params,
            json=json,
            data=data,
            headers={"Authorization": "Bearer " + self._token},
        )
        response.raise_for_status()
        return response.content

    # Enrollment info
    def get_users(self):
        admin_path = api_url("courses", self._course_id, "admin")
        admin_info = self._ed_get_request(admin_path)
        return admin_info["users"]

    # Get lesson info
    def get_all_lessons(self) -> List[Dict[str, Any]]:
        """Gets all lessons for a course. Endpoint: /courses/{course_id}/lessons

        Returns:
            A list of JSON objects, one for each lesson.
        """
        lessons_path = api_url("courses", self._course_id, "lessons")
        lessons = self._ed_get_request(lessons_path)
        return lessons["lessons"]

    # Get module info
    def get_all_modules(self) -> List[Dict[str, Any]]:
        """Gets all modules for a course. Endpoint: /courses/{course_id}/lessons

        Returns:
            A list of JSON objects, one for each module.
        """
        lessons_path = api_url("courses", self._course_id, "lessons")
        lessons = self._ed_get_request(lessons_path)
        return lessons["modules"]

    def get_lesson(self, lesson_id: int) -> Dict[str, Any]:
        """Gets metadata for a single lesson. Endpoint: /lessons/{lesson_id}

        Args:
            lesson_id: Identifier for lesson

        Returns:
            A JSON object with the specified lesson's metadata
        """
        lesson_path = api_url("lessons", lesson_id)
        lesson = self._ed_get_request(lesson_path)["lesson"]
        return lesson

    def get_slide(self, slide_id: int) -> Dict[str, Any]:
        """Gets metadata for a single slide. Endpoint: /lessons/slides/{slide_id}

        Args:
            slide_id: Identifier for slide

        Returns:
            A JSON object with the specified slide's metadata
        """
        slide_path = api_url("lessons", "slides", slide_id)
        slide = self._ed_get_request(slide_path)["slide"]
        return slide

    def get_rubric(self, rubric_id: int) -> Dict[str, Any]:
        """Gets metadata for a single rubric. Endpoint: /rubrics/{slide_id}

        Args:
            rubric_id: Identifier for rubric

        Returns:
            A JSON object with the specified rubric's metadata
        """
        rubric_path = api_url("rubrics", rubric_id)
        rubric = self._ed_get_request(rubric_path)["rubric"]
        return rubric

    def create_lesson(
        self, title: str = None, options: Dict[str, Any] = {}
    ) -> Dict[str, Any]:
        """Creates a new Ed lesson. Endpoint: /courses/{course_id}/lessons

        Args:
            title: Title for the new lesson
            options: Dictionary of options to set on the lesson

        Returns:
            A JSON object with the new lesson's metadata
        """
        lessons_path = api_url("courses", self._course_id, "lessons")
        lesson_dict = {"lesson": ({"title": title} | options)}
        lesson = json.loads(self._ed_post_request(lessons_path, json=lesson_dict))[
            "lesson"
        ]
        return lesson

    def edit_lesson(
        self, lesson_id: int, options: Dict[str, Any] = {}
    ) -> Dict[str, Any]:
        """Modifies an existing Ed lesson. Endpoint: /lessons/{lesson_id}

        Args:
            lesson_id: Identifier for lesson
            options: Dictionary of options to set on the lesson

        Returns:
            A JSON object with the updated lesson's metadata
        """
        lesson = self.get_lesson(lesson_id)
        lesson_path = api_url("lessons", lesson_id)
        lesson_dict = {"lesson": lesson | options}
        lesson = json.loads(self._ed_put_request(lesson_path, json=lesson_dict))[
            "lesson"
        ]
        return lesson

    def clone_slide(
        self,
        slide_id: int,
        lesson_id: int,
        is_hidden: bool = False,
    ) -> Dict[str, Any]:
        """Clones an existing Ed slide into a new lesson. Endpoint: /lessons/slides/{slide_id}/clone

        Args:
            slide_id: Identifier for slide to clone
            lesson_id: Identifier for lesson to clone into

        Returns:
            A JSON object with the cloned slide's metadata
        """

        clone_path = api_url("lessons", "slides", slide_id, "clone")
        payload = {"lesson_id": lesson_id, "is_hidden": is_hidden}
        slide = json.loads(self._ed_post_request(clone_path, json=payload))["slide"]
        return slide

    def edit_slide(self, slide_id: int, options: Dict[str, Any] = {}) -> Dict[str, Any]:
        """Modifies an existing Ed slide. Endpoint: /lessons/slides/{slide_id}

        Args:
            slide_id: Identifier for slide
            options: Dictionary of options to set on the slide

        Returns:
            A JSON object with the updated slide's metadata
        """
        slide = self.get_slide(slide_id)
        slide_path = api_url("lessons", "slides", slide_id)
        slide_dict = slide | options
        slide = json.loads(
            self._ed_put_request(slide_path, data={"slide": json.dumps(slide_dict)})
        )["slide"]
        return slide

    def delete_slide(self, slide_id: int) -> None:
        """Deletes the given slide with this id. Endpoint /lessons/slides/{slide_id}

        Args:
            slide_id: Identifier for a slide

        Returns:
            None
        """
        delete_path = url_join(API_URL, "lessons", "slides", slide_id)
        self._ed_delete_request(delete_path)

    def get_questions(self, slide_id: int) -> List[Dict[str, Any]]:
        """Gets metadata for a single Quiz slide's questions. Endpoint: /lessons/slides/{slide_id}/questions

        Args:
            slide_id: Identifier for slide

        Returns:
            A JSON object with the specified lesson's metadata
        """
        questions_path = url_join(API_URL, "lessons", "slides", slide_id, "questions")
        questions = self._ed_get_request(questions_path)["questions"]
        return questions

    def edit_question(
        self, question_id: int, question_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Edits the question with the given id with the updated question data.

        Endpoint: /lessons/slides/questions/{question_id}

        Args:
            question_id: Identifier for question
            question_data: Dict containing information to update in the queston

        Returns:
            The updated JSON object for the question
        """
        update_question_path = url_join(
            API_URL, "lessons", "slides", "questions", question_id
        )

        # API call requires the data to be the value of a "question" key
        if "question" not in question_data:
            question_data = {"question": question_data}

        response = self._ed_put_request(update_question_path, json=question_data)
        return json.loads(response)["question"]

    def delete_question(self, question_id: int) -> None:
        """Deletes the given question with this id. Endpoint /lessons/slides/questions/{question_id}

        Args:
            question_id: Identifier for question

        Returns:
            None
        """
        delete_path = url_join(API_URL, "lessons", "slides", "questions", question_id)
        self._ed_delete_request(delete_path)

    def update_challenge(self, challenge_id: int, type: str) -> None:
        """Updates given challenge for the given type of resource (scaffold, check, solution, testbase)

        Currently only used to update a challenge after copying new files to one resources (e.g., updating tests)
        """
        valid_types = ["scaffold", "check", "solution", "testbase"]
        if type not in valid_types:
            raise ValueError(
                f"Invalid resource type {type} (should be one of {valid_types})"
            )

        update_path = url_join(API_URL, "challenges", challenge_id, "update", type)
        self._ed_post_request(update_path)

    def remark_challenge(
        self, challenge_id: int, type: str, steps: Optional[int] = None
    ) -> None:
        """Remarks all submissions for this challenge.

        Arguments:
        - type: Indicator for which lessons to remark (latest, best, feedback)
                feedback = "Latest with Feedback"
        - steps: If latest, can specify the last steps submissions to remark.
                If not latest, should be None
        """
        remark_path = url_join(API_URL, "challenges", challenge_id, "remark")

        query_params = {"type": type} | ({"steps": steps} if type == "latest" else {})
        self._ed_post_request(remark_path, query_params=query_params)

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
        points: BinaryFlag = 0,
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
            points: Check; "Include points row header"
        Returns:
            Bytes content of the result file. Usually will be used to save to a file.
        """
        lesson_completion_path = url_join(API_URL, "lessons", lesson_id, "results.csv")
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
                "points": points,
            },
        )
        return result

    def get_challenge_results(
        self,
        challenge_id: int,
        students: BinaryFlag = 1,
        include_all: BinaryFlag = 1,
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
            include_all: Check; "
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
        challenge_path = url_join(API_URL, "challenges", challenge_id, "results")
        result = self._ed_post_request(
            challenge_path,
            {
                "students": students,
                "include_all": include_all,
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
        self,
        quiz_id: int,
        students: BinaryFlag = 1,
        no_attempt: BinaryFlag = 1,
        rubrics: BinaryFlag = 1,
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
            rubrics: Check; "Rubric criteria columns"

        Returns:
            Bytes content of the result file. Usually will be used to save to a file.

        """
        quiz_path = url_join(API_URL, "lessons/slides", quiz_id, "questions/results")
        result = self._ed_post_request(
            quiz_path,
            {"students": students, "noAttempt": no_attempt, "rubrics": rubrics},
        )
        return result

    def get_final_lesson_attempt(
        self, lesson_id: int, user_id: int
    ) -> dict[str, Any] | None:
        url = api_url("lessons", lesson_id, "attempts", user_id)
        response = self._ed_get_request(url)

        final_attempts = [
            attempt
            for attempt in response["attempts"]
            if attempt["id"] == response["final_id"]
        ]
        if len(final_attempts) == 1:
            return final_attempts[0]
        else:
            return None

    def get_rubric(self, rubric_id: int) -> dict[str, Any]:
        url = api_url("rubrics", rubric_id)
        return self._ed_get_request(url)["rubric"]

    def get_quiz_responses(
        self, attempt_id: int, question_id: int
    ) -> list[dict[str, Any]]:
        url = api_url("attempts", attempt_id, "quiz_responses", question_id)
        return self._ed_get_request(url)["responses"]

    def get_marking_status(self, lesson_id: int) -> dict[str, Any]:
        url = api_url("lessons", lesson_id, "marking_status")
        return self._ed_get_request(url)

    def mark(self, lesson_mark_id: int, items: dict[int, bool]):
        url = api_url("rubrics", "selected", lesson_mark_id)
        return self._ed_put_request(url, json={"items": items})

    def post_grades(
        self,
        submission_id: int,
        grades: List[Dict[str, Any]],
        comment: str = '<document version="2.0"><paragraph/></document>',
    ):
        """
        Posts feedback to the given submission id with the given grades and optional comment.

        Args:
            submission_id: ID for submission
            grades: List of marks to apply, one per criteria (see example below).
        Optiona Args:
            comments: Contents for the overall feedback. **Note: Must be a proper XML document**

        Example:
        >>> ed.post_grades(123,
        >>>     [[{name: "Stacks/Queues", description: "Excellent", mark: "E"}],
        >>>     '<document version="2.0"><paragraph>Nice job!</paragraph></document>')
        """
        path = url_join(API_URL, "challenges", "submissions", submission_id, "feedback")

        data = {
            "feedback": {
                "mark": None,
                "formatted": True,
                "criteria": grades,
                "content": comment,
            }
        }
        return self._ed_put_request(path, json=data)

    def connect_user_to_workspace(self, challenge_id, user_id):
        connect_path = api_url("challenges", challenge_id, "connect")
        self._ed_post_request(connect_path, json={"user_id": user_id})

    def submit_all_challenge(self, challenge_id):
        submit_path = url_join(API_URL, "challenges", challenge_id, "submit_all")
        self._ed_post_request(submit_path)

    def submit_all_quiz(self, slide_id):
        submit_path = url_join(
            API_URL, "lessons", "slides", slide_id, "questions", "submit_all"
        )
        self._ed_post_request(submit_path)

    def get_all_users_for_challenge(self, challenge_id):
        users_path = api_url("challenges", challenge_id, "users")

        result = self._ed_get_request(users_path)["users"]
        return result

    def get_all_users(self):
        users = self._ed_get_request(
            api_url("courses", self._course_id, "analytics", "users")
        )["users"]
        return users

    def get_all_tutorials(self):
        users = self.get_all_users()
        groups = itertools.groupby(
            sorted(users, key=lambda x: x["tutorial"] if x["tutorial"] else ""),
            key=lambda x: x["tutorial"],
        )

        tutorials = []
        for k, _ in groups:
            tutorials.append(k)
        return tutorials

    def get_all_submissions(
        self,
        challenge_id: int,
        students: BinaryFlag = 1,
        type: str = "optimised",
        tz: str = "America/Los_Angeles",
    ):
        # TODO also add ability to specify before date
        submission_path = url_join(API_URL, "challenges", challenge_id, "submissions")
        result = self._ed_post_request(
            submission_path,
            query_params={"studuents": students, "type": type, "tz": tz},
        )
        return result

    def get_all_submissions_for_user(
        self,
        challenge_id,
        user_id,
    ):
        submission_path = url_join(
            API_URL,
            "users",
            user_id,
            "challenges",
            challenge_id,
            "submissions",
        )

        result = self._ed_get_request(submission_path)["submissions"]
        return result

    def get_all_attempts(self, lesson_id: int, user_id: int):
        url = api_url("lessons", lesson_id, "attempts", user_id)
        return self._ed_get_request(url)["attempts"]

    def delete_submission(self, sub_id):
        delete_path = api_url("challenges", "submissions", sub_id)
        return self._ed_delete_request(delete_path)
