# -*- coding: utf-8 -*-
"""
SmartSafe Enterprise — Premium Dark Theme System
=================================================
Central design token module.  Every UI file MUST import colors, fonts,
and spacing from here — never hardcode hex values.
"""
import customtkinter as ctk

# ═══════════════════════════════════════════════════════════════════════════════
#  COLOR PALETTE  — Premium Dark Mode
# ═══════════════════════════════════════════════════════════════════════════════

# Backgrounds (layered depth — darkest → lightest)
BG_DARK          = "#0b141a"          # deepest background / overlays
BG_COLOR         = "#111b21"          # primary window / main content
BG_ELEVATED      = "#16232b"          # elevated sections
CHAT_BG_COLOR    = "#0b141a"          # specific background for chat timeline

# Surfaces
SURFACE_COLOR    = "#1a2730"          # cards, panels, sidebar
SURFACE_LIGHT    = "#1f3040"          # elevated cards on hover
INPUT_COLOR      = "#233040"          # text inputs, textboxes
HOVER_COLOR      = "#1c3045"          # hover state for interactive elements
ACTIVE_COLOR     = "#1a3a50"          # active/selected state (richer blue tint)

# Accents
ACCENT_COLOR     = "#00a884"          # primary CTA (WhatsApp green)
ACCENT_HOVER     = "#00c298"          # lighter hover state
ACCENT_PRESSED   = "#056162"          # pressed / ripple state
ACCENT_SUBTLE    = "#0a3d36"          # subtle accent background tint
ACCENT_GLOW      = "#00a88430"        # 18% transparent accent for glow effects

# Secondary Accents
BLUE_ACCENT      = "#2d8cf0"          # info / outbound metrics
BLUE_HOVER       = "#4da3ff"
PURPLE_ACCENT    = "#8b5cf6"          # analytics / premium badges
PURPLE_HOVER     = "#a78bfa"
ORANGE_ACCENT    = "#f59e0b"          # warnings / active metrics
ORANGE_HOVER     = "#fbbf24"
PINK_ACCENT      = "#ec4899"          # notifications / highlights

# Text
TEXT_COLOR        = "#e9edef"          # primary text
TEXT_SECONDARY    = "#8696a0"          # secondary / muted text
SUB_TEXT_COLOR    = "#8696a0"         # alias for backward compat
TEXT_DISABLED     = "#5a6670"         # disabled text
TEXT_INVERSE      = "#111b21"         # text on accent backgrounds

# Status / Semantic
ERROR_COLOR      = "#ef4444"          # errors, destructive actions
ERROR_HOVER      = "#f87171"
ERROR_BG         = "#3b1515"          # error background tint
WARNING_COLOR    = "#eab308"          # warnings
WARNING_BG       = "#3b3515"
SUCCESS_COLOR    = "#22c55e"          # success confirmations
INFO_COLOR       = "#3b82f6"          # info banners

# Chat
SENT_BUBBLE_COLOR     = "#005c4b"     # outgoing messages (WhatsApp Green)
SENT_BUBBLE_HOVER     = "#006d5b"
RECEIVED_BUBBLE_COLOR = "#202c33"     # incoming messages (WhatsApp Dark Grey)
HEADER_FOOTER_COLOR   = "#202c33"     # chat header / footer
DIVIDER_COLOR         = "#222d34"     # thin separators

# Status badge palette
STATUS_COLORS = {
    "OPEN":     "#00a884",
    "PENDING":  "#e9c46a",
    "RESOLVED": "#8696a0",
    "CLOSED":   "#ef4444",
}

# Avatar palette — rich, vibrant, deterministic
AVATAR_PALETTE = [
    "#7c3aed", "#2d8cf0", "#10b981", "#f59e0b",
    "#ef4444", "#ec4899", "#06b6d4", "#84cc16",
    "#8b5cf6", "#14b8a6", "#f97316", "#a855f7",
]

# Analytics card strip colors
ANALYTICS_COLORS = {
    "outbound":  "#2d8cf0",
    "inbound":   "#00a884",
    "active":    "#f59e0b",
    "contacts":  "#8b5cf6",
    "leads":     "#f59e0b",
    "customers": "#00a884",
    "contracts": "#8b5cf6",
}

# ═══════════════════════════════════════════════════════════════════════════════
#  TYPOGRAPHY
# ═══════════════════════════════════════════════════════════════════════════════

FONT_3XL = 30         # page titles
FONT_2XL = 24         # section headings
FONT_XL  = 20         # card headings
FONT_LG  = 16         # subheadings, important labels
FONT_MD  = 14         # body text, inputs
FONT_SM  = 12         # secondary info
FONT_XS  = 11         # captions, badges
FONT_2XS = 10         # tiny labels

def get_font(size: int = 14, weight: str = "normal", slant: str = "roman") -> ctk.CTkFont:
    """Helper to create standardized fonts."""
    return ctk.CTkFont(size=size, weight=weight, slant=slant)

def heading_font(size: int = FONT_2XL) -> ctk.CTkFont:
    return ctk.CTkFont(size=size, weight="bold")

def body_font(size: int = FONT_MD) -> ctk.CTkFont:
    return ctk.CTkFont(size=size)

def caption_font(size: int = FONT_XS) -> ctk.CTkFont:
    return ctk.CTkFont(size=size)

def badge_font() -> ctk.CTkFont:
    return ctk.CTkFont(size=FONT_2XS, weight="bold")

# ═══════════════════════════════════════════════════════════════════════════════
#  SPACING & LAYOUT
# ═══════════════════════════════════════════════════════════════════════════════

PAD_2XS = 2
PAD_XS  = 4
PAD_SM  = 8
PAD_MD  = 12
PAD_LG  = 16
PAD_XL  = 20
PAD_2XL = 24
PAD_3XL = 30

CARD_RADIUS     = 14
CARD_RADIUS_SM  = 10
PILL_RADIUS     = 20
INPUT_RADIUS    = 10
BUTTON_RADIUS   = 10
AVATAR_RADIUS   = 21     # fully round for 42px

SIDEBAR_WIDTH   = 240
HEADER_HEIGHT   = 62
INPUT_HEIGHT    = 42
BUTTON_HEIGHT   = 40
BUTTON_HEIGHT_SM = 32

# Border
BORDER_WIDTH    = 1
BORDER_COLOR    = "#1c2e38"

# ═══════════════════════════════════════════════════════════════════════════════
#  UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_avatar_color(name: str) -> str:
    """Pick a deterministic color from the palette based on the contact name."""
    return AVATAR_PALETTE[hash(name or "?") % len(AVATAR_PALETTE)]

def get_status_color(status: str) -> str:
    return STATUS_COLORS.get(status.upper(), SUB_TEXT_COLOR)

def get_analytics_color(variant: str) -> str:
    return ANALYTICS_COLORS.get(variant, ACCENT_COLOR)

def get_media_icon(path: str) -> str:
    """Return an emoji icon based on file extension."""
    if not path: return "📎"
    ext = str(path).lower().split('.')[-1]
    if ext in ['png', 'jpg', 'jpeg', 'gif', 'bmp']: return "📷"
    elif ext in ['mp4', 'avi', 'mov', 'wmv']: return "🎬"
    elif ext in ['mp3', 'wav', 'ogg', 'm4a']: return "🎵"
    elif ext in ['pdf', 'txt', 'doc', 'docx', 'csv', 'xlsx']: return "📄"
    return "📎"

# ═══════════════════════════════════════════════════════════════════════════════
#  PREMIUM WIDGET FACTORIES
# ═══════════════════════════════════════════════════════════════════════════════

def create_section_header(parent, title: str, subtitle: str = "") -> ctk.CTkFrame:
    """Creates a consistent page/section header with optional subtitle."""
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(
        frame, text=title,
        font=heading_font(FONT_3XL),
        text_color=TEXT_COLOR,
    ).pack(side="left")
    if subtitle:
        ctk.CTkLabel(
            frame, text=f" | {subtitle}",
            font=body_font(FONT_MD),
            text_color=TEXT_SECONDARY,
        ).pack(side="left", padx=(PAD_MD, 0), pady=(6, 0))
    return frame

def create_premium_card(parent, **kwargs) -> ctk.CTkFrame:
    """Creates an elevated dark card with premium corner radius."""
    defaults = dict(fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
    defaults.update(kwargs)
    return ctk.CTkFrame(parent, **defaults)

def create_analytics_card(parent, title: str, value: str, variant: str = "default") -> ctk.CTkFrame:
    """Creates a premium stat card with colored accent strip."""
    card = ctk.CTkFrame(parent, fg_color=SURFACE_COLOR, corner_radius=CARD_RADIUS)
    color = get_analytics_color(variant)

    # Accent strip
    ctk.CTkFrame(card, height=4, fg_color=color, corner_radius=2).pack(
        fill="x", padx=PAD_LG, pady=(PAD_LG, 0)
    )
    # Title
    ctk.CTkLabel(
        card, text=title.upper(),
        font=ctk.CTkFont(size=FONT_XS, weight="bold"),
        text_color=TEXT_SECONDARY,
    ).pack(anchor="w", pady=(PAD_SM, 0), padx=PAD_LG)
    # Value
    value_label = ctk.CTkLabel(
        card, text=value,
        font=ctk.CTkFont(size=36, weight="bold"),
        text_color=TEXT_COLOR,
    )
    value_label.pack(anchor="w", pady=(0, PAD_XL), padx=PAD_LG)
    card.value_label = value_label
    return card

def create_premium_button(parent, text: str, command=None, variant: str = "primary", **kwargs) -> ctk.CTkButton:
    """Creates a styled button with consistent theming."""
    styles = {
        "primary": dict(fg_color=ACCENT_COLOR, hover_color=ACCENT_HOVER, text_color="#ffffff"),
        "secondary": dict(fg_color="transparent", hover_color=HOVER_COLOR, text_color=ACCENT_COLOR, border_width=1, border_color=ACCENT_COLOR),
        "danger": dict(fg_color="transparent", hover_color=ERROR_BG, text_color=ERROR_COLOR, border_width=1, border_color=ERROR_COLOR),
        "ghost": dict(fg_color="transparent", hover_color=HOVER_COLOR, text_color=TEXT_SECONDARY),
    }
    style = dict(height=BUTTON_HEIGHT, corner_radius=BUTTON_RADIUS,
                 font=ctk.CTkFont(size=FONT_MD, weight="bold"))
    style.update(styles.get(variant, styles["primary"]))
    style.update(kwargs)
    return ctk.CTkButton(
        parent, text=text, command=command,
        **style,
    )

def create_premium_input(parent, placeholder: str, show: str = "", **kwargs) -> ctk.CTkEntry:
    """Creates a premium text entry."""
    defaults = dict(
        placeholder_text=placeholder, show=show,
        fg_color=INPUT_COLOR, text_color=TEXT_COLOR,
        placeholder_text_color=TEXT_SECONDARY,
        border_width=0, corner_radius=INPUT_RADIUS,
        height=INPUT_HEIGHT, font=body_font(FONT_MD),
    )
    defaults.update(kwargs)
    return ctk.CTkEntry(parent, **defaults)

def create_divider(parent, **kwargs) -> ctk.CTkFrame:
    """Creates a thin horizontal separator."""
    defaults = dict(height=1, fg_color=DIVIDER_COLOR)
    defaults.update(kwargs)
    return ctk.CTkFrame(parent, **defaults)
