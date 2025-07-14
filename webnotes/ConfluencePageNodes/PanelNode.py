from .Node import Node


class PanelNode(Node):
    """
    Panel node implementation that creates a panel with specified type and content.
    Represents a JSON object with type "panel" and panelType attribute.
    """

    def __init__(self, panelType="note", content=None):
        """
        Initialize a PanelNode object.

        Args:
            panelType (str): The type of panel (e.g., "note", "info", "warning", etc.)
            content (list): List of Node objects representing the panel content
        """
        attrs = {"panelType": panelType}
        super().__init__(node_type="panel", attrs=attrs, content=content)
