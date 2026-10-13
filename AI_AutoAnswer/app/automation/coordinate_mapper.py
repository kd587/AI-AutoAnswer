from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    width: int
    height: int

    @property
    def center(self) -> tuple[int, int]:
        return self.left + self.width // 2, self.top + self.height // 2

    def contains(self, point: tuple[int, int]) -> bool:
        x, y = point
        return self.left <= x < self.left + self.width and self.top <= y < self.top + self.height


def screenshot_to_screen(point: tuple[int, int], window_rect: Rect,
                         screenshot_size: tuple[int, int]) -> tuple[int, int]:
    width, height = screenshot_size
    if width <= 0 or height <= 0:
        raise ValueError("Empty screenshot")
    x, y = point
    if not (0 <= x < width and 0 <= y < height):
        raise ValueError("Point outside screenshot")
    return (window_rect.left + round(x * window_rect.width / width),
            window_rect.top + round(y * window_rect.height / height))
