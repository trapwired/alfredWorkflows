from .Node import Node
import uuid


class InlineExtensionNode(Node):
    def __init__(self, extensionKey="", macroParameters=None, title="",
                 extensionType="com.atlassian.confluence.macro.core"):
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
        result = {
            "type": self.type,
            "attrs": self.attrs
        }
        return result

    @staticmethod
    def get_upcoming_phx_initiatives():
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
