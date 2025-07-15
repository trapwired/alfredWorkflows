from .Node import Node
from .TextContent import TextContent


class HeadingNode(Node):
    def __init__(self, level=1, text=""):
        attrs = {"level": level}

        # Create a text node as the content
        text_content = TextContent(text)

        # Initialize with the parent class
        super().__init__(node_type="heading", attrs=attrs, content=[text_content])
