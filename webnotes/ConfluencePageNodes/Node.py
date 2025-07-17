class Node:
    def __init__(self, node_type=None, attrs=None, content=None):
        self.type = node_type
        self.attrs = attrs if attrs is not None else {}
        if isinstance(content, list):
            self.content = content
        elif content is not None:
            # If content is not a list, wrap it in a list
            self.content = [content]
        else:
            self.content = []

    def to_json(self):
        result = {
            "type": self.type,
            "attrs": self.attrs,
            "content": [
                node.to_json() if hasattr(node, 'to_json') else node
                for node in self.content
            ]
        }
        return result
