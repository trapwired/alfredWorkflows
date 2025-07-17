from ..Node import Node
from ..ParagraphNode import ParagraphNode
from ..TextContent import TextContent

class BulletListNode(Node):
    def __init__(self, items=None):
        # Initialize with empty content if none provided
        content = []
        super().__init__(node_type="bulletList", attrs={}, content=content)

        # Add items if provided
        if items:
            for item in items:
                self.add_item(item)

    def add_item(self, text):
        # Create a list item node
        list_item = ListItemNode(text)
        self.content.append(list_item)
        return self

    def add_items(self, items):
        for item in items:
            self.add_item(item)
        return self


class ListItemNode(Node):
    def __init__(self, text):
        # Create a paragraph with the text content
        text_content = TextContent(text)
        paragraph = ParagraphNode(content=[text_content])

        # Initialize the list item with the paragraph as content
        super().__init__(node_type="listItem", attrs={}, content=[paragraph])

    def add_sub_list(self, bullet_list):
        self.content.append(bullet_list)
        return self
