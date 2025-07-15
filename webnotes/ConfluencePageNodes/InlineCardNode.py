from .Node import Node


class InlineCardNode(Node):
    def __init__(self, url):
        attrs = {
            "url": url
        }

        # Initialize with parent class
        super().__init__(node_type="inlineCard", attrs=attrs)

    def to_json(self):
        result = {
            "type": self.type,
            "attrs": self.attrs
        }
        return result
