class TextContent:
    def __init__(self, text="", marksType=None):
        self.text = text
        self.type = "text"
        self.marksType = marksType

    def to_json(self):
        return {
            "text": self.text,
            "type": self.type,
            "marks": [{"type": self.marksType}] if self.marksType else []
        }

    @staticmethod
    def create_space():
        return TextContent(" ")

    @staticmethod
    def create_empty():
        return TextContent("")
