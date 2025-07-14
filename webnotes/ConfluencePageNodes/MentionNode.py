from .Node import Node
import uuid


class MentionNode(Node):
    """
    Mention node implementation for user mentions in Confluence.
    Represents a JSON object with type "mention" and user identification attributes.
    """

    def __init__(self, user_id, name):
        """
        Initialize a MentionNode object.

        Args:
            user_id (str): The user ID for the mention (e.g., "557058:ae5a880c-75c2-4768-83f8-f5676e200987")
            name (str): The display text for the mention (e.g., "@Conrad Hofer")
        """
        # Generate a local ID if not provided
        local_id = str(uuid.uuid4())

        attrs = {
            "id": user_id,
            "localId": local_id,
            "text": f'@{name}'
        }

        # Initialize with parent class
        super().__init__(node_type="mention", attrs=attrs)

    def to_json(self):
        """
        Override to_json to exclude the content attribute from the output.

        Returns:
            dict: Dictionary representation of the mention without content
        """
        result = {
            "type": self.type,
            "attrs": self.attrs
        }
        return result
