class Printer:

    def __init__(self):
        self._output = ''

    def print_output(self, output):
        self._output += output

    def print_line(self, x1, y1, x2, y2, color=0, width=1):
        self.print_output(_svg_line(x1, y1, x2, y2, color=color, width=width))

    def print_circle(self, x, y, r, color=0, width=1, border_color=0):
        self.print_output(_svg_circle(x, y, r, color=color, width=width, border_color=border_color))

    def print_square(self, x, y, a, color=0, width=1, border_color=0):
        self.print_output(_svg_rectangle(x, y, a, a, color=color, width=width, border_color=border_color))

    def print_text(self, x, y, text, color=0, font_size=12):
        self.print_output(_svg_text(x, y, text, color=color, font_size=font_size))

    def to_file(self, filename):
        with open(filename, 'w') as f:
            f.write(str(self))

    def __str__(self):
        return """<svg width="100%" height="100%" version="1.1" xmlns="http://www.w3.org/2000/svg">
        {}
        </svg>
        """.format(self._output)


def _svg_line(x1, y1, x2, y2, color, width):
    color = _svg_color(color)
    return '<line x1="{}" y1="{}" x2="{}" y2="{}" style="stroke-linecap:round;stroke:{};stroke-width:{};" />\n'.format(x1, y1, x2, y2, color, width)

def _svg_circle(x, y, r, color, width, border_color):
    color = _svg_color(color)
    border_color = _svg_color(color)
    return '<circle cx="{}" cy="{}" r="{}" style="fill:{}; stroke:{}; stroke-width:{};" />\n'.format(x, y, r, color, border_color, width)

def _svg_rectangle(x, y, a, b, color, width, border_color):
    color = _svg_color(color)
    border_color = _svg_color(border_color)
    return '<rect x="{}" y="{}" width="{}" height="{}" style="fill:{}; stroke:{}; stroke-width:{};" />\n'.format(x, y, a, b, color, border_color, width)

def _svg_text(x, y, text, color, font_size):
    color = _svg_color(color)
    return '<text x="{}" y="{}" font-family="Nimbus Sans L" font-size="{}" fill="{}">{}</text>\n'.format(x, y, font_size, color, text)

def _svg_color(color):
    if isinstance(color, str):
        return color
    return 'rgb({}, {}, {})'.format(color, color, color)
