import uuid

from .. import ParagraphNode, TextContent
from ..Node import Node
from ...JiraInterface import JiraIssue
from .CellColors import CellColors
from .TableRowNode import TableRowNode
from .TableHeaderNode import TableHeaderNode
from .TableCellNode import TableCellNode


class TableNode(Node):
    def __init__(self, num_cols, col_sizes=None, layout="full-width", width=1800.0):
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

    def add_formated_table_row(self, row_values):
        if len(row_values) != self.number_of_columns:
            raise ValueError("Number of column titles must match the number of rows in the table.")
        col_nodes = []
        for title, size in zip(row_values, self.column_sizes):
            paragraph = ParagraphNode(content=[TextContent(text=title)])
            header = TableCellNode(content=[paragraph], colwidth=size)
            col_nodes.append(header)

        table_row = TableRowNode(content=col_nodes)
        self.add_row(table_row)

    def add_table_row(self, row_values):
        if len(row_values) != self.number_of_columns:
            raise ValueError("Number of column titles must match the number of rows in the table.")
        col_nodes = []
        for content, size in zip(row_values, self.column_sizes):
            header = TableCellNode(content=content, colwidth=size)
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
