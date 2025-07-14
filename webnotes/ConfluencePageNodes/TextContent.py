class TextContent:
    """
    A class representing a simple text content object in Confluence.
    Represents a JSON object with the structure: {"text": "content", "type": "text"}
    """

    def __init__(self, text="", marksType=None):
        """
        Initialize a TextContent object.

        Args:
            text (str): The text content to be displayed
        """
        self.text = text
        self.type = "text"
        self.marksType = marksType

    def to_json(self):
        """
        Convert the TextContent object to a JSON-serializable dictionary.

        Returns:
            dict: Dictionary representation of the text content
        """
        return {
            "text": self.text,
            "type": self.type,
            "marks": [{"type": self.marksType}] if self.marksType else []
        }

    @staticmethod
    def create_space():
        """
        Creates a TextContent object with a single space.

        Returns:
            TextContent: A text content with just a space character
        """
        return TextContent(" ")

    @staticmethod
    def create_empty():
        """
        Creates an empty TextContent object.

        Returns:
            TextContent: A text content with empty text
        """
        return TextContent("")

