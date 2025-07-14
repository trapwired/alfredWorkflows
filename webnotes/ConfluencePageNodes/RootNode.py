from .Node import Node


class RootNode(Node):
    """
    Root node implementation that serves as the container for all other nodes.
    Represents a JSON object with type "doc" and a version number.
    """

    def __init__(self, content=None, version=1):
        """
        Initialize a RootNode object.

        Args:
            content (list): List of Node objects representing the document content
            version (int): The version number of the document (default: 1)
        """
        # Initialize with parent class but override the type
        super().__init__(node_type="doc", attrs={}, content=content)

        # Add version which is a special property for the root node
        self.version = version

    def to_json(self):
        """
        Override to_json to include version at the top level.

        Returns:
            dict: Dictionary representation of the root node
        """
        result = super().to_json()
        # Remove attrs which is not needed in root node
        if "attrs" in result:
            del result["attrs"]
        # Add version
        result["version"] = self.version
        return result
