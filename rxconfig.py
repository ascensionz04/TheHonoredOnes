import reflex as rx

config = rx.Config(
    app_name="predictor",
    default_color_mode="light",
    telemetry_enabled=False,
    disable_plugins=[rx.plugins.SitemapPlugin],
)
