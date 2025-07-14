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
        """
        Create a paragraph node with an inline card link.

        Args:
            url (str): The URL for the inline card (e.g., Jira issue URL)

        Returns:
            ParagraphNode: A paragraph containing an inline card
        """
        empty_node = TextContent.create_space()
        inline_card = InlineCardNode(url)
        return ParagraphNode(content=[empty_node, inline_card, empty_node])

    @staticmethod
    def mention_cell(id, name):
        """
        Create a paragraph node with a user mention.

        Args:
            id (str): The user ID for the mention
            name (str): The display text for the mention

        Returns:
            ParagraphNode: A paragraph containing a user mention
        """
        empty_node = TextContent.create_space()
        mention = MentionNode(user_id=id, name=name)
        return ParagraphNode(content=[mention, empty_node])