import unittest

from freezegun import freeze_time

from webnotes.utilities import get_current_sprint


class TestGetCurrentSprint(unittest.TestCase):
    """
    Test class for the get_current_sprint function in utilities.py

    The reference sprint data:
    - Sprint 378 starts on July 1, 2025 (a Tuesday) at 12:00 PM (noon)
    - Each sprint lasts 2 weeks, starting on Tuesdays at 12:00 PM
    - Sprints end at 11:59 AM on the Tuesday two weeks later
    """

    @freeze_time("2025-08-25 08:08:08")
    def test_reference_date_random_sprint(self):
        sprint = get_current_sprint()
        self.assertEqual(sprint, 381)

    @freeze_time("2025-08-26 11:59:59")
    def test_reference_date_before_noon(self):
        sprint = get_current_sprint()
        self.assertEqual(sprint, 381)

    @freeze_time("2025-08-26 12:00:00")
    def test_reference_date_at_noon(self):
        sprint = get_current_sprint()
        self.assertEqual(sprint, 382)

    @freeze_time("2025-08-28 08:08:08")
    def test_reference_date_random_sprint_2(self):
        sprint = get_current_sprint()
        self.assertEqual(sprint, 382)
