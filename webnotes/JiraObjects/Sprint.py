from datetime import datetime


class Sprint:
    """
    Represents a Jira Sprint with all its properties
    """

    def __init__(self, json_data):
        """
        Initialize a Sprint object from JSON data returned by Jira API

        Args:
            json_data (dict): The JSON data representing a sprint
        """
        self.id = json_data.get('id')
        self.self_url = json_data.get('self')
        self.state = json_data.get('state')
        self.name = json_data.get('name')

        # Parse dates if they exist
        self.start_date = self._parse_date(json_data.get('startDate'))
        self.end_date = self._parse_date(json_data.get('endDate'))
        self.complete_date = self._parse_date(json_data.get('completeDate'))

        self.origin_board_id = json_data.get('originBoardId')
        self.goal = json_data.get('goal')

    def _parse_date(self, date_string):
        """
        Parse date string to datetime object

        Args:
            date_string (str): Date string in ISO format

        Returns:
            datetime: Parsed datetime object or None if date_string is None
        """
        if date_string:
            try:
                return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            except ValueError:
                # Handle Jira's format with timezone information
                return datetime.strptime(date_string[:-5], '%Y-%m-%dT%H:%M:%S.%f')
        return None

    def __str__(self):
        """String representation of the Sprint object"""
        return f"Sprint: {self.name} (ID: {self.id}, State: {self.state})"

    def __repr__(self):
        """Detailed representation of the Sprint object"""
        return (f"Sprint(id={self.id}, name='{self.name}', state='{self.state}', "
                f"start_date={self.start_date}, end_date={self.end_date})")
