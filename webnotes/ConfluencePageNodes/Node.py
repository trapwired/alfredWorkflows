class Node:
    """
    Base class for wrapper objects for JSON objects with structure:
    {"type": "definedInChild", "attrs": dict, "content": a list of Nodes}
    """

    def __init__(self, node_type=None, attrs=None, content=None):
        """
        Initialize a Node object.

        Args:
            node_type (str): The type of the node, typically defined in child classes
            attrs (dict): Dictionary of attributes for the node
            content (list): List of Node objects representing child content
        """
        self.type = node_type
        self.attrs = attrs if attrs is not None else {}
        self.content = content if content is not None else []

    def to_json(self):
        """
        Convert the Node object to a JSON-serializable dictionary.

        Returns:
            dict: Dictionary representation of the node with type, attrs, and content
        """
        result = {
            "type": self.type,
            "attrs": self.attrs,
            "content": [
                node.to_json() if hasattr(node, 'to_json') else node
                for node in self.content
            ]
        }
        return result

