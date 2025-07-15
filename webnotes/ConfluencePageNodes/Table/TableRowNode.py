from ..Node import Node

class TableRowNode(Node):
    def __init__(self, content=None):
        super().__init__(node_type="tableRow", attrs={}, content=content or [])

    def add_cell(self, cell):
        self.content.append(cell)

    def to_json(self):
        result = {
            "type": self.type,
            "content": [
                node.to_json() if hasattr(node, 'to_json') else node
                for node in self.content
            ]
        }
        return result
