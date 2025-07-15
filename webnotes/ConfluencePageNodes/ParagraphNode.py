from . import TextContent
from .Node import Node
from .InlineCardNode import InlineCardNode
from .MentionNode import MentionNode
from .TextContent import *


class ParagraphNode(Node):

    def __init__(self, content=None):
        super().__init__(node_type="paragraph", attrs={}, content=content)

    @staticmethod
    def inline_card_cell(url):
        empty_node = TextContent.create_space()
        inline_card = InlineCardNode(url)
        return ParagraphNode(content=[empty_node, inline_card, empty_node])

    @staticmethod
    def mention_cell(id, name):
        empty_node = TextContent.create_space()
        mention = MentionNode(user_id=id, name=name)
        return ParagraphNode(content=[mention, empty_node])