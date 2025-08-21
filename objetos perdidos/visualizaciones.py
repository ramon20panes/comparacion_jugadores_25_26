# utils/visualizaciones.py
from mplsoccer import Pitch

def draw_opta_pitch(ax=None, pitch_color="#05A94A", line_color="white", linewidth=0.95):
    """
    Dibuja un campo tipo Opta en el eje dado y devuelve el objeto Pitch y el eje.
    """
    pitch = Pitch(
        pitch_type="opta",
        pitch_color=pitch_color,
        line_color=line_color,
        linewidth=linewidth,
        corner_arcs=True
    )
    if ax is None:
        fig, ax = pitch.draw()
        return pitch, ax
    pitch.draw(ax=ax)
    return pitch, ax
