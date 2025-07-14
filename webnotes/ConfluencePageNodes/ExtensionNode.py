from .Node import Node
import uuid


class ExtensionNode(Node):
    """
    Extension node implementation for Confluence macros and extensions.
    Represents a JSON object with type "extension" and the specified attributes.
    """

    def __init__(self, layout="default", extensionKey="", macroParameters=None,title="", extensionType="com.atlassian.confluence.macro.core"):
        """
        Initialize an ExtensionNode object.

        Args:
            layout (str): Layout of the extension (default: "default")
            extensionKey (str): Key identifying the extension type (e.g., "toc" for Table of Contents)
            macroParameters (dict): Parameters specific to the macro (default: empty dict)
            macroId (str): Unique ID for the macro (generated if not provided)
            title (str): Title of the extension
            localId (str): Local ID for the extension (generated if not provided)
            extensionType (str): Type of extension (default: "com.atlassian.confluence.macro.core")
        """

        macroId = str(uuid.uuid4())
        localId = str(uuid.uuid4())

        # Initialize macro parameters
        if macroParameters is None:
            macroParameters = {}

        # Build the attrs structure
        attrs = {
            "layout": layout,
            "extensionType": extensionType,
            "extensionKey": extensionKey,
            "parameters": {
                "macroParams": macroParameters,
                "macroMetadata": {
                    "macroId": {
                        "value": macroId
                    },
                    "schemaVersion": {
                        "value": "1"
                    }
                }
            },
            "localId": localId
        }

        # Add title if provided
        if title:
            attrs["parameters"]["macroMetadata"]["title"] = {
                "value": title
            }

        # Initialize with parent class
        super().__init__(node_type="extension", attrs=attrs)

    def to_json(self):
        """
        Override to_json to exclude the content attribute from the output.

        Returns:
            dict: Dictionary representation of the extension node without content
        """
        result = {
            "type": self.type,
            "attrs": self.attrs
        }
        return result

    @staticmethod
    def get_toc_extension():
        """
        Creates a Table of Contents extension with predefined values.

        Returns:
            ExtensionNode: A configured TOC extension instance
        """
        return ExtensionNode(
            layout="default",
            extensionKey="toc",
            title="Table of Contents",
        )

    @staticmethod
    def get_jira_filter_extension(filter_query):
        """
        Creates a Jira filter extension with predefined values.

        Returns:
            ExtensionNode: A configured Jira filter extension instance
        """
        # Define the macro parameters for the Jira filter
        jira_macro_params = {
            "server": {
                "value": "Jira"
            },
            "columns": {
                "value": "key,summary,status,fixVersions,reporter,assignee,Sprint"
            },
            "columnIds": {
                "value": "issuekey,summary,status,fixVersions,reporter,assignee,customfield_10130"
            },
            "maximumIssues": {
                "value": "1000"
            },
            "jqlQuery": {
                "value": filter_query
            },
            "serverId": {
                "value": "12beaa74-5ed9-3d9a-9890-c39d8121dbdb"
            }
        }

        # Create the extension
        extension = ExtensionNode(
            layout="full-width",
            extensionKey="jira",
            macroParameters=jira_macro_params,
            title="Jira Legacy",
        )

        # Add the placeholder which has a special structure
        placeholder = [
            {
                "type": "image",
                "data": {
                    "url": "/download/resources/confluence.extra.jira/jira-table.png"
                }
            }
        ]
        extension.attrs["parameters"]["macroMetadata"]["placeholder"] = placeholder

        return extension
