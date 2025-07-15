from .Node import Node


class PanelNode(Node):
    def __init__(self, panelType="note", content=None):
        attrs = {"panelType": panelType}
        super().__init__(node_type="panel", attrs=attrs, content=content)
