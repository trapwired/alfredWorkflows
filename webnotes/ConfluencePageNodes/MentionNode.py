from .Node import Node
import uuid


class MentionNode(Node):
    def __init__(self, user_id, name):
        # Generate a local ID if not provided
        local_id = str(uuid.uuid4())

        attrs = {
            "id": user_id,
            "localId": local_id,
            "text": f'@{name}'
        }

        # Initialize with parent class
        super().__init__(node_type="mention", attrs=attrs)

    def to_json(self):
        result = {
            "type": self.type,
            "attrs": self.attrs
        }
        return result
