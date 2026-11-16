"""Read the active Omarchy theme and turn it into QML-friendly colours."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

# Ethereal, Omarchy's current stock theme, used when no theme can be read.
FALLBACK = {
    "mode": "dark",
    "accent": "#7d82d9",
    "selection": "#252e56",
    "muted": "#6d7db6",
    "background": "#060b1e",
    "dark_background": "#040816",
    "darker_background": "#030610",
    "lighter_background": "#131a3a",
    "foreground": "#ffcead",
    "dark_foreground": "#6d7db6",
    "light_foreground": "#c9b8a6",
    "bright_foreground": "#ffcead",
    "red": "#ed5b5a",
    "yellow": "#e9bb4f",
    "orange": "#eb8b54",
    "green": "#92a593",
    "cyan": "#a3bfd1",
    "blue": "#7d82d9",
    "magenta": "#c89dc1",
}


def _state_home() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))


def _theme_candidates() -> list[Path]:
    override = os.environ.get("CONCERT_LOG_COLORS")
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override).expanduser())

    state = _state_home() / "omarchy" / "current"
    candidates.append(state / "theme" / "colors.toml")
    candidates.append(Path.home() / ".config/omarchy/current/theme/colors.toml")

    # Fall back to resolving the current theme name ourselves. This keeps the
    # app useful on Omarchy releases that lay the state directory out a little
    # differently.
    try:
        slug = (state / "theme.name").read_text(encoding="utf-8").strip()
    except OSError:
        slug = ""
    if slug:
        candidates.extend(
            [
                Path.home() / ".config/omarchy/themes" / slug / "colors.toml",
                Path("/usr/share/omarchy/themes") / slug / "colors.toml",
            ]
        )
    return candidates


def _read_colors() -> dict[str, str]:
    for path in _theme_candidates():
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError):
            continue
        return {str(key): str(value) for key, value in data.items() if isinstance(value, str)}
    return dict(FALLBACK)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)
    if len(value) == 8:  # already #AARRGGBB
        value = value[2:]
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(part))) for part in rgb))


def _blend(first: str, second: str, amount: float) -> str:
    """Mix `amount` of second into first (0..1)."""
    a, b = _hex_to_rgb(first), _hex_to_rgb(second)
    return _rgb_to_hex(tuple(a[i] + (b[i] - a[i]) * amount for i in range(3)))  # type: ignore[arg-type]


def _alpha(value: str, alpha: float) -> str:
    """Return #AARRGGBB, the alpha-first form QML understands."""
    rgb = _hex_to_rgb(value)
    return "#{:02x}{:02x}{:02x}{:02x}".format(
        max(0, min(255, round(alpha * 255))), *rgb
    )


def _luminance(value: str) -> float:
    red, green, blue = (part / 255 for part in _hex_to_rgb(value))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _pick(colors: dict[str, str], *keys: str, default: str) -> str:
    for key in keys:
        value = colors.get(key)
        if value:
            return value
    return default


def load_theme() -> dict[str, Any]:
    """Return the palette consumed by the QML side as `theme`."""
    colors = _read_colors()

    background = _pick(colors, "background", "color0", default=FALLBACK["background"])
    foreground = _pick(colors, "foreground", "color7", default=FALLBACK["foreground"])
    accent = _pick(colors, "accent", "color4", default=FALLBACK["accent"])
    muted = _pick(
        colors, "muted", "dark_foreground", "color8", default=_blend(foreground, background, 0.42)
    )
    surface = _pick(colors, "lighter_background", default=_blend(background, foreground, 0.055))
    surface_raised = _pick(
        colors, "selection", default=_blend(background, foreground, 0.10)
    )

    red = _pick(colors, "red", "color1", default=FALLBACK["red"])
    green = _pick(colors, "green", "color2", default=FALLBACK["green"])
    yellow = _pick(colors, "yellow", "color3", default=FALLBACK["yellow"])
    orange = _pick(colors, "orange", default=yellow)
    cyan = _pick(colors, "cyan", "color6", default=FALLBACK["cyan"])
    magenta = _pick(colors, "magenta", "color5", default=FALLBACK["magenta"])

    return {
        # Core surfaces
        "background": background,
        "backgroundDeep": _pick(
            colors, "darker_background", default=_blend(background, "#000000", 0.35)
        ),
        "surface": surface,
        "surfaceRaised": surface_raised,
        "inputBackground": _blend(background, surface, 0.55),
        "hover": _alpha(foreground, 0.06),
        "pressed": _alpha(foreground, 0.11),
        "selection": _alpha(accent, 0.20),
        "border": _alpha(foreground, 0.12),
        "borderStrong": _alpha(foreground, 0.22),
        "scrim": _alpha(background, 0.72),
        # Text
        "foreground": foreground,
        "foregroundMuted": muted,
        "foregroundDim": _blend(foreground, background, 0.55),
        "onAccent": background if _luminance(accent) > 0.52 else "#ffffff",
        # Accents
        "accent": accent,
        "accentHover": _blend(accent, "#ffffff", 0.14),
        "accentPressed": _blend(accent, "#000000", 0.12),
        "accentSoft": _alpha(accent, 0.16),
        "accentBorder": _alpha(accent, 0.45),
        "red": red,
        "green": green,
        "yellow": yellow,
        "orange": orange,
        "cyan": cyan,
        "magenta": magenta,
        "dangerSoft": _alpha(red, 0.13),
        "dangerBorder": _alpha(red, 0.45),
        "successSoft": _alpha(green, 0.13),
        "successBorder": _alpha(green, 0.45),
    }


def font_family(families: list[str]) -> str:
    """Pick the most Omarchy-ish installed font from a QFontDatabase list."""
    available = set(families)
    for name in (
        "CaskaydiaMono Nerd Font",
        "CaskaydiaMono Nerd Font Mono",
        "JetBrainsMono Nerd Font",
        "JetBrainsMono",
        "Adwaita Sans",
        "DejaVu Sans",
        "Sans Serif",
    ):
        if name in available:
            return name
    return families[0] if families else "Sans Serif"
