from .Node import Node
from .TextContent import TextContent


class HeadingNode(Node):
    """
    Heading node implementation that creates a heading with specified level and text.
    Represents a JSON object with type "heading" and level attribute.
    """

    def __init__(self, level=1, text=""):
        """
        Initialize a HeadingNode object.

        Args:
            level (int): The heading level (1-6)
            text (str): The heading text content
        """
        attrs = {"level": level}

        # Create a text node as the content
        text_content = TextContent(text)

        # Initialize with the parent class
        super().__init__(node_type="heading", attrs=attrs, content=[text_content])
