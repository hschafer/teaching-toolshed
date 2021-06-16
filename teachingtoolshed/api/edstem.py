import requests


def urljoin(*parts):
    return "/".join(str(part).strip("/") for part in parts)


class EdStem:
    API = f"https://us.edstem.org/api/"

    def __init__(self, course_id, token):
        self._course_id = course_id
        self._token = token

    # General functions for GET/POST
    def _ed_get_request(self, path, query_params={}):
        return requests.get(
            path, params=query_params, headers={"x-token": self._token}
        ).json()

    def _ed_post_request(self, path, query_params={}):
        return requests.post(
            path, params=query_params, data={"_token": self._token}
        ).content

    # Get lesson info
    def get_all_lessons(self):
        lessons_path = urljoin(EdStem.API, f"courses/{self._course_id}/lessons")
        lessons = self._ed_get_request(lessons_path)
        return lessons["lessons"]

    def get_lesson(self, lesson_id):
        lesson_path = urljoin(EdStem.API, "lessons", lesson_id)
        lesson = self._ed_get_request(lesson_path)["lesson"]
        return lesson

    def get_questions(self, slide_id):
        questions_path = urljoin(EdStem.API, "lessons", "slides", slide_id, "questions")
        questions = self._ed_get_request(questions_path)["questions"]
        return questions

    # Lesson completions
    def get_lesson_completions(self, lesson_id):
        lesson_completion_path = urljoin(
            EdStem.API, "lessons", lesson_id, "results.csv"
        )
        result = self._ed_post_request(
            lesson_completion_path,
            {
                "numbers": 1,
                "scores": 1,
                "students": 1,
                "completions": 1,
                "strategy": "best",
                "ignore_late": 0,
                "late_no_points": 0,
                "tz": "America%2FLos_Angeles",
            },
        )
        return result

    def get_challenge_results(self, challenge_id):
        challenge_path = urljoin(EdStem.API, "challenges", challenge_id, "results")
        result = self._ed_post_request(
            challenge_path,
            {
                "students": 1,
                "type": "optimised",
                "numbers": 0,
                "scores": 0,
                "score_type": "pertestcase",
                "feedback": 0,
                "tz": "America/Los_Angeles",
            },
        )
        return result

    def get_quiz_results(self, quiz_id):
        quiz_path = urljoin(EdStem.API, "lessons/slides", quiz_id, "questions/results")
        result = self._ed_post_request(quiz_path, {"students": 1, "noAttempt": 1,},)
        return result
