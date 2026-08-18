import mcp_server as mcp
import tools.jira_tools
from mcp_trials.tools import jira_tools

# Entry point to run the server
if __name__ == "__main__":
    print(jira_tools.get_all_open_sprints())

    mcp.run()