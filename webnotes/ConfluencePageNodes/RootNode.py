from .Node import Node


class RootNode(Node):
    def __init__(self, content=None, version=1):
        # Initialize with parent class but override the type
        super().__init__(node_type="doc", attrs={}, content=content)

        # Add version which is a special property for the root node
        self.version = version

    def to_json(self):
        result = super().to_json()
        # Remove attrs which is not needed in root node
        if "attrs" in result:
            del result["attrs"]
        # Add version
        result["version"] = self.version
        return result
