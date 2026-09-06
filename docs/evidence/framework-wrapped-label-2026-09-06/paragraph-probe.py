import sys
from saga2d import Scene, TextStyle
from saga2d.testing import render_scene
class Paragraph(Scene):
    background_color = (17, 25, 36, 255)
    def draw(self):
        for n, (text, font, size, width) in enumerate([
            ('Words wrap around a measured column and keep their geometry.', 'Arial', 17, 250),
            ('Authored line\n\nBlank line\n', 'Georgia', 22, 300),
            ('VeryLongUnbrokenDescriptionTokenWithoutWhitespace', 'Verdana', 14, 130),
        ]):
            h = self.draw_paragraph(text, 30 + n * 280, 40, width,
                style=TextStyle(size, (242, 222, 173, 255), font))
            self.draw_rect(30 + n * 280, 40 + h, width, 2, (40, 200, 170, 255))
render_scene(lambda game: game.push(Paragraph()), resolution=(900, 600), tick_count=2).save(sys.argv[1])
