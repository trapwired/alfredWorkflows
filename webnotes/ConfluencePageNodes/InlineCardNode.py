from .Node import Node


class InlineCardNode(Node):
    """
    InlineCard node implementation for Confluence link cards.
    Represents a JSON object with type "inlineCard" and the URL attribute.
    """

    def __init__(self, url):
        """
        Initialize an InlineCardNode object.

        Args:
            url (str): The URL for the inline card (e.g., Jira issue URL)
        """
        attrs = {
            "url": url
        }

        # Initialize with parent class
        super().__init__(node_type="inlineCard", attrs=attrs)

    def to_json(self):
        """
        Override to_json to exclude the content attribute from the output.

        Returns:
            dict: Dictionary representation of the inline card without content
        """
        result = {
            "type": self.type,
            "attrs": self.attrs
        }
        return result
