# Using relative import to access the MCP server and webnotes
import sys
import os
from datetime import datetime

# Add the parent directory to sys.path to make mcp_server.py accessible
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Add the workspace root to make webnotes accessible
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import mcp_server as mcp
import webnotes.JiraInterface


def _serialize_datetime(dt):
    """
    Convert datetime object to ISO format string for JSON serialization.

    Args:
        dt: datetime object or None

    Returns:
        str: ISO format string or None
    """
    if dt is None:
        return None
    return dt.isoformat()


def _sprint_to_dict(sprint):
    """
    Convert a Sprint object to a serializable dictionary.

    Args:
        sprint: Sprint object

    Returns:
        dict: Serializable dictionary representation of the Sprint
    """
    return f"{sprint.id}, {sprint.name}, {sprint.state}, {sprint.start_date}, {sprint.end_date}"


@mcp.tool()
def get_all_open_sprints() -> list:
    """
    Retrieves all active and future sprints from the Jira board.

    This function connects to the Jira API using credentials from the config file,
    queries for all sprints with status 'active' or 'future', and returns them
    as a list of Sprint objects. Each Sprint object contains information like
    sprint ID, name, state, start date, end date, etc.

    Returns:
        list: A list of dictionaries representing all open sprints in the Jira board.
              Returns an empty list if no sprints are found or if there's an API error.
    """
    sprints = webnotes.JiraInterface.get_all_open_sprints()
    # Convert Sprint objects to serializable dictionaries
    serializable_sprints = [_sprint_to_dict(sprint) for sprint in sprints]
    return serializable_sprints

@mcp.tool()
def calc_domi_sum(a: int, b: int) -> int:
    """"
    Calculates the domi-sum of two integers and returns the result.
    """
    return int(str(a) + str(b))