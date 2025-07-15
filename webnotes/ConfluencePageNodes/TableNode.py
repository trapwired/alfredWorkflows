import uuid

from . import ParagraphNode, TextContent
from .Node import Node
from ..JiraInterface import JiraIssue


class TableNode(Node):
    """
    Table node implementation that creates a table structure.
    Represents a JSON object with type "table" and layout, width, localId attributes.
    """

    def __init__(self, num_cols, col_sizes=None, layout="full-width", width=1800.0):
        """
        Initialize a TableNode object.

        Args:
            layout (str): Layout of the table (default: "full-width")
            width (float): Width of the table in pixels (default: 1800.0)
        """

        localId = str(uuid.uuid4())

        attrs = {
            "layout": layout,
            "width": width,
            "localId": localId
        }

        if not col_sizes:
            col_sizes = [width / num_cols] * num_cols

        self.column_sizes = col_sizes
        self.number_of_columns = num_cols

        self.cell_colors = {}
        self.cell_color_iterator = CellColors()

        super().__init__(node_type="table", attrs=attrs, content=[])

    def add_row(self, row):
        """
        Add a TableRowNode to the table.

        Args:
            row (TableRowNode): A row to add to the table
        """
        self.content.append(row)

    def add_title_row(self, col_titles):
        if len(col_titles) != self.number_of_columns:
            raise ValueError("Number of column titles must match the number of rows in the table.")
        col_nodes = []
        for title, size in zip(col_titles, self.column_sizes):
            paragraph = ParagraphNode(content=[TextContent(text=title, marksType='strong')])
            header = TableHeaderNode(content=[paragraph], colwidth=size)
            col_nodes.append(header)

        table_row = TableRowNode(content=col_nodes)
        self.add_row(table_row)

    def add_table_row(self, row_values):
        if len(row_values) != self.number_of_columns:
            raise ValueError("Number of column titles must match the number of rows in the table.")
        col_nodes = []
        for title, size in zip(row_values, self.column_sizes):
            paragraph = ParagraphNode(content=[TextContent(text=title)])
            header = TableCellNode(content=[paragraph], colwidth=size)
            col_nodes.append(header)

        table_row = TableRowNode(content=col_nodes)
        self.add_row(table_row)

    def add_jira_table_row(self, data: JiraIssue):
        cell1 = TableCellNode(content=[ParagraphNode.inline_card_cell(data.get_link())], colwidth=self.column_sizes[0])
        cell_color = self.get_cell_color(data.parent_topic)
        cell2 = TableCellNode(content=[ParagraphNode(content=[TextContent(text=data.parent_topic)])],
                              colwidth=self.column_sizes[1], color=cell_color)
        cell3 = TableCellNode(content=[ParagraphNode()], colwidth=self.column_sizes[2])
        cell4 = TableCellNode(content=[ParagraphNode.mention_cell(data.reporter[0], data.reporter[1])],
                              colwidth=self.column_sizes[3])
        cell5 = TableCellNode(content=[ParagraphNode.mention_cell(data.assignee[0], data.assignee[1])],
                              colwidth=self.column_sizes[4])
        table_row = TableRowNode(content=[cell1, cell2, cell3, cell4, cell5])
        self.add_row(table_row)

    def get_cell_color(self, parent_topic):
        if parent_topic:
            if parent_topic not in self.cell_colors:
                self.cell_colors[parent_topic] = self.cell_color_iterator.get_next_color()
            return self.cell_colors[parent_topic]
        return None

class CellColors:
    def __init__(self):
        self.colors = ['#deebff', '#ffebe6', '#fffae6', '#f4f5f7', '#e3fcef', '']
        self.index = 0

    def get_next_color(self):
        color = self.colors[self.index]
        self.index = (self.index + 1) % len(self.colors)
        return color


class TableRowNode(Node):
    """
    Table row node implementation that represents a row in a table.
    Represents a JSON object with type "tableRow" and content (list of cells).
    """

    def __init__(self, content=None):
        """
        Initialize a TableRowNode object.

        Args:
            content (list): List of TableHeaderNode or TableCellNode objects representing cells in this row
        """
        super().__init__(node_type="tableRow", attrs={}, content=content or [])

    def add_cell(self, cell):
        """
        Add a cell (header or regular) to the row.

        Args:
            cell (TableHeaderNode or TableCellNode): A cell to add to this row
        """
        self.content.append(cell)

    def to_json(self):
        """
        Override to_json to exclude the attrs attribute from the output.

        Returns:
            dict: Dictionary representation of the table row node without attrs
        """
        result = {
            "type": self.type,
            "content": [
                node.to_json() if hasattr(node, 'to_json') else node
                for node in self.content
            ]
        }
        return result


class TableHeaderNode(Node):
    """
    Table header node implementation that represents a header cell in a table.
    Represents a JSON object with type "tableHeader" and specific attributes.
    """

    def __init__(self, content=None, colwidth=None):
        """
        Initialize a TableHeaderNode object.

        Args:
            content (list): List of nodes (typically ParagraphNode) representing the cell content
            colspan (int): Number of columns this cell spans (default: 1)
            rowspan (int): Number of rows this cell spans (default: 1)
            colwidth (list): Width of columns in pixels (default: [568.0])
        """
        if colwidth is None:
            colwidth = 568.0

        attrs = {
            "colspan": 1,
            "rowspan": 1,
            "colwidth": [colwidth]
        }

        super().__init__(node_type="tableHeader", attrs=attrs, content=content or [])


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
