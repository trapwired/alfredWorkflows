from .Node import Node
import uuid


class ExtensionNode(Node):
    def __init__(self, layout="default", extensionKey="", macroParameters=None,title="", extensionType="com.atlassian.confluence.macro.core"):
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
        result = {
            "type": self.type,
            "attrs": self.attrs
        }
        return result

    @staticmethod
    def get_toc_extension():
        return ExtensionNode(
            layout="default",
            extensionKey="toc",
            title="Table of Contents",
        )

    @staticmethod
    def get_jira_filter_extension(filter_query):
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

        extension = ExtensionNode(
            layout="full-width",
            extensionKey="jira",
            macroParameters=jira_macro_params,
            title="Jira Legacy",
        )

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
