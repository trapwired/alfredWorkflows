from .Node import Node
import uuid


class InlineExtensionNode(Node):
    """
    Inline extension node implementation for Confluence macros that display inline.
    Represents a JSON object with type "inlineExtension" and the specified attributes.
    """

    def __init__(self, extensionKey="", macroParameters=None, title="",
                 extensionType="com.atlassian.confluence.macro.core"):
        """
        Initialize an InlineExtensionNode object.

        Args:
            extensionKey (str): Key identifying the extension type (e.g., "excerpt-include")
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
        super().__init__(node_type="inlineExtension", attrs=attrs)

    def to_json(self):
        """
        Override to_json to exclude the content attribute from the output.

        Returns:
            dict: Dictionary representation of the inline extension node without content
        """
        result = {
            "type": self.type,
            "attrs": self.attrs
        }
        return result

    @staticmethod
    def get_upcoming_phx_initiatives():
        """
        Creates an excerpt include inline extension with predefined values.

        Returns:
            InlineExtensionNode: A configured excerpt include extension instance
        """
        # Define the macro parameters for the excerpt include
        excerpt_macro_params = {
            "": {
                "value": "Übersicht laufende und kommende Initiativen"
            },
            "name": {
                "value": "PHX Current Initiatives"
            },
            "nopanel": {
                "value": "true"
            }
        }

        # Create the inline extension
        return InlineExtensionNode(
            extensionKey="excerpt-include",
            macroParameters=excerpt_macro_params,
            title="Insert excerpt",
        )
