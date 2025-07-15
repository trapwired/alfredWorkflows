class CellColors:
    def __init__(self):
        self.colors = ['#deebff', '#ffebe6', '#fffae6', '#f4f5f7', '#e3fcef', '']
        self.index = 0

    def get_next_color(self):
        color = self.colors[self.index]
        self.index = (self.index + 1) % len(self.colors)
        return color
