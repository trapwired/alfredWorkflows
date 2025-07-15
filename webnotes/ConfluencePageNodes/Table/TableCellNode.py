from ..Node import Node

class TableCellNode(Node):
    def __init__(self, content=None, colwidth=None, color=None):
        if colwidth is None:
            colwidth = 568.0

        attrs = {
            "colspan": 1,
            "rowspan": 1,
            "colwidth": [colwidth]
        }

        if color:
            attrs["background"] = color

        super().__init__(node_type="tableCell", attrs=attrs, content=content or [])
