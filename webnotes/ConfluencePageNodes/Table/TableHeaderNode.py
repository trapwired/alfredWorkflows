from ..Node import Node

class TableHeaderNode(Node):
    def __init__(self, content=None, colwidth=None):
        if colwidth is None:
            colwidth = 568.0

        attrs = {
            "colspan": 1,
            "rowspan": 1,
            "colwidth": [colwidth]
        }

        super().__init__(node_type="tableHeader", attrs=attrs, content=content or [])
