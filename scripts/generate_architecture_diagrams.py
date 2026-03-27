from __future__ import annotations

import html
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
MERMAID_DIR = DOCS_DIR / "diagrams"
ASSET_DIR = DOCS_DIR / "assets" / "diagrams"


@dataclass(frozen=True)
class Panel:
    title: str
    x: int
    y: int
    w: int
    h: int
    fill: str = "#f8fafc"
    stroke: str = "#cbd5e1"


@dataclass(frozen=True)
class Box:
    key: str
    text: str
    x: int
    y: int
    w: int
    h: int
    fill: str = "#ffffff"
    stroke: str = "#94a3b8"
    text_color: str = "#0f172a"


@dataclass(frozen=True)
class Arrow:
    points: tuple[tuple[int, int], ...]
    label: str = ""
    color: str = "#64748b"
    dashed: bool = False


FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\msyhbd.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\arial.ttf"),
]


def ensure_dirs() -> None:
    MERMAID_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)


def find_font_path() -> Path | None:
    for path in FONT_CANDIDATES:
        if path.exists():
            return path
    return None


FONT_PATH = find_font_path()


@lru_cache(maxsize=32)
def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if FONT_PATH:
        return ImageFont.truetype(str(FONT_PATH), size=size)
    return ImageFont.load_default()


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def wrap_text(draw: ImageDraw.ImageDraw, text: str, current_font, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.replace("<br/>", "\n").split("\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append("")
            continue
        buffer = ""
        for char in paragraph:
            candidate = f"{buffer}{char}"
            width = draw.textbbox((0, 0), candidate, font=current_font)[2]
            if buffer and width > max_width:
                lines.append(buffer)
                buffer = char
            else:
                buffer = candidate
        if buffer:
            lines.append(buffer)
    return lines or [text]


def rounded_rectangle(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: str,
    outline: str,
    width: int = 2,
    radius: int = 18,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=hex_to_rgb(fill), outline=hex_to_rgb(outline), width=width)


def draw_multiline_center(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    text: str,
    *,
    fill: str = "#0f172a",
    size: int = 22,
) -> None:
    current_font = font(size)
    lines = wrap_text(draw, text, current_font, max_width=w - 28)
    line_height = size + 6
    total_h = len(lines) * line_height
    start_y = y + (h - total_h) / 2
    for index, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=current_font)
        text_w = bbox[2] - bbox[0]
        draw.text((x + (w - text_w) / 2, start_y + index * line_height), line, font=current_font, fill=hex_to_rgb(fill))


def draw_panel_png(draw: ImageDraw.ImageDraw, panel: Panel) -> None:
    rounded_rectangle(draw, (panel.x, panel.y, panel.x + panel.w, panel.y + panel.h), panel.fill, panel.stroke, width=2, radius=24)
    draw.rounded_rectangle(
        (panel.x + 2, panel.y + 2, panel.x + panel.w - 2, panel.y + 44),
        radius=20,
        fill=hex_to_rgb("#e2e8f0"),
        outline=hex_to_rgb("#e2e8f0"),
    )
    draw.text((panel.x + 18, panel.y + 12), panel.title, font=font(24), fill=hex_to_rgb("#0f172a"))


def draw_box_png(draw: ImageDraw.ImageDraw, box: Box) -> None:
    rounded_rectangle(draw, (box.x, box.y, box.x + box.w, box.y + box.h), box.fill, box.stroke, width=3, radius=20)
    draw_multiline_center(draw, box.x, box.y, box.w, box.h, box.text, fill=box.text_color, size=20)


def draw_arrow_head(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], color: str) -> None:
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    arrow_len = 14
    spread = math.pi / 7
    p1 = (end[0] - arrow_len * math.cos(angle - spread), end[1] - arrow_len * math.sin(angle - spread))
    p2 = (end[0] - arrow_len * math.cos(angle + spread), end[1] - arrow_len * math.sin(angle + spread))
    draw.polygon([end, p1, p2], fill=hex_to_rgb(color))


def draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: str,
    dash: int = 10,
    gap: int = 6,
) -> None:
    total_length = math.dist(start, end)
    if total_length == 0:
        return
    dx = (end[0] - start[0]) / total_length
    dy = (end[1] - start[1]) / total_length
    current = 0.0
    while current < total_length:
        next_end = min(current + dash, total_length)
        s = (start[0] + dx * current, start[1] + dy * current)
        e = (start[0] + dx * next_end, start[1] + dy * next_end)
        draw.line([s, e], fill=hex_to_rgb(color), width=4)
        current = next_end + gap


def draw_arrow_png(draw: ImageDraw.ImageDraw, arrow: Arrow) -> None:
    points = list(arrow.points)
    if arrow.dashed:
        for start, end in zip(points, points[1:]):
            draw_dashed_line(draw, start, end, arrow.color)
    else:
        draw.line(points, fill=hex_to_rgb(arrow.color), width=4)
    draw_arrow_head(draw, points[-2], points[-1], arrow.color)


def wrap_svg_text(text: str, width: int, size: int = 20) -> list[str]:
    avg_char = max(10, int(size * 0.95))
    capacity = max(4, width // avg_char)
    lines: list[str] = []
    for paragraph in text.replace("<br/>", "\n").split("\n"):
        if not paragraph:
            lines.append("")
            continue
        start = 0
        while start < len(paragraph):
            lines.append(paragraph[start : start + capacity])
            start += capacity
    return lines


def svg_text(lines: list[str], x: int, y: int, width: int, height: int, *, size: int = 20, fill: str = "#0f172a") -> str:
    line_height = size + 6
    total_h = len(lines) * line_height
    start_y = y + (height - total_h) / 2 + size
    parts = []
    for index, line in enumerate(lines):
        parts.append(
            f'<text x="{x + width / 2}" y="{start_y + index * line_height}" text-anchor="middle" font-size="{size}" fill="{fill}" font-family="Microsoft YaHei, Arial, sans-serif">{html.escape(line)}</text>'
        )
    return "".join(parts)


def draw_panel_svg(panel: Panel) -> str:
    return (
        f'<rect x="{panel.x}" y="{panel.y}" rx="24" ry="24" width="{panel.w}" height="{panel.h}" fill="{panel.fill}" stroke="{panel.stroke}" stroke-width="2" />'
        f'<rect x="{panel.x + 2}" y="{panel.y + 2}" rx="20" ry="20" width="{panel.w - 4}" height="44" fill="#e2e8f0" stroke="none" />'
        f'<text x="{panel.x + 18}" y="{panel.y + 31}" font-size="24" fill="#0f172a" font-family="Microsoft YaHei, Arial, sans-serif">{html.escape(panel.title)}</text>'
    )


def draw_box_svg(box: Box) -> str:
    lines = wrap_svg_text(box.text, box.w - 28)
    return (
        f'<rect x="{box.x}" y="{box.y}" rx="20" ry="20" width="{box.w}" height="{box.h}" fill="{box.fill}" stroke="{box.stroke}" stroke-width="3" />'
        + svg_text(lines, box.x, box.y, box.w, box.h, size=20, fill=box.text_color)
    )


def draw_arrow_svg(arrow: Arrow) -> str:
    polyline = " ".join(f"{x},{y}" for x, y in arrow.points)
    dash = ' stroke-dasharray="10 6"' if arrow.dashed else ""
    start = arrow.points[-2]
    end = arrow.points[-1]
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    arrow_len = 14
    spread = math.pi / 7
    p1 = (end[0] - arrow_len * math.cos(angle - spread), end[1] - arrow_len * math.sin(angle - spread))
    p2 = (end[0] - arrow_len * math.cos(angle + spread), end[1] - arrow_len * math.sin(angle + spread))
    return (
        f'<polyline points="{polyline}" fill="none" stroke="{arrow.color}" stroke-width="4"{dash} />'
        f'<polygon points="{end[0]},{end[1]} {p1[0]},{p1[1]} {p2[0]},{p2[1]}" fill="{arrow.color}" />'
    )


def render_base_png(size: tuple[int, int], title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", size, hex_to_rgb("#f8fafc"))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, size[0], 120), fill=hex_to_rgb("#e2e8f0"))
    draw.text((44, 28), title, font=font(38), fill=hex_to_rgb("#0f172a"))
    draw.text((44, 74), subtitle, font=font(20), fill=hex_to_rgb("#334155"))
    return image, draw


def render_base_svg(size: tuple[int, int], title: str, subtitle: str, content: str) -> str:
    width, height = size
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="{width}" height="{height}" fill="#f8fafc" />
<rect x="0" y="0" width="{width}" height="120" fill="#e2e8f0" />
<text x="44" y="66" font-size="38" fill="#0f172a" font-family="Microsoft YaHei, Arial, sans-serif">{html.escape(title)}</text>
<text x="44" y="100" font-size="20" fill="#334155" font-family="Microsoft YaHei, Arial, sans-serif">{html.escape(subtitle)}</text>
{content}
</svg>'''


def write_mermaid_sources() -> None:
    source_doc = DOCS_DIR / "architecture-diagrams.md"
    content = source_doc.read_text(encoding="utf-8")
    segments = content.split("```mermaid")
    filenames = ["module-relationship.mmd", "request-sequence.mmd", "data-flow.mmd"]
    for filename, segment in zip(filenames, segments[1:4], strict=False):
        target = MERMAID_DIR / filename
        if target.exists():
            continue
        diagram = segment.split("```", 1)[0].strip() + "\n"
        target.write_text(diagram, encoding="utf-8")


def build_module_diagram() -> tuple[tuple[int, int], list[Panel], list[Box], list[Arrow], str, str]:
    size = (2400, 1480)
    panel_w = 340
    gap = 34
    left = 36
    top = 150
    panel_h = 1260
    titles = ["前端展示层", "前端状态 / 路由层", "API 层", "应用编排层", "服务 / 支撑层", "资源层"]
    panels = [Panel(title, left + i * (panel_w + gap), top, panel_w, panel_h) for i, title in enumerate(titles)]
    x = [panel.x + 20 for panel in panels]
    boxes = [
        Box("AppFrame", "AppFrame\n应用框架与导航", x[0], 230, 300, 104, fill="#eef2ff", stroke="#6366f1"),
        Box("QueryWorkspace", "QueryWorkspace / QueryPanel\n主查询工作台", x[0], 372, 300, 120, fill="#eef2ff", stroke="#6366f1"),
        Box("DevPages", "Trace / Logs / ModelConfig / MapConfig\n开发者页面", x[0], 536, 300, 120, fill="#f5f3ff", stroke="#8b5cf6"),
        Box("ResultCards", "结果卡片 / Timeline / Debug 面板", x[0], 700, 300, 96, fill="#eef2ff", stroke="#6366f1"),
        Box("AppRouter", "AppRouter\n用户路由 + 开发者守卫", x[1], 230, 300, 110, fill="#ecfeff", stroke="#0891b2"),
        Box("Session", "WeatherWearSession\n会话状态 / 查询提交 / 历史收藏联动", x[1], 376, 300, 128, fill="#dbeafe", stroke="#2563eb"),
        Box("FrontAPI", "shared/api.ts\nfetch API 封装", x[1], 548, 300, 96, fill="#ecfeff", stroke="#0891b2"),
        Box("BrowserStorage", "sessionStorage /\nlocalStorage", x[1], 684, 300, 96, fill="#fff7ed", stroke="#f97316"),
        Box("Server", "server.py\nFastAPI 路由与请求入口", x[2], 250, 300, 120, fill="#dbeafe", stroke="#2563eb"),
        Box("Schemas", "schemas.py\n请求 / 响应契约", x[2], 414, 300, 96, fill="#eff6ff", stroke="#60a5fa"),
        Box("Coordinator", "MultiAgentCoordinator\n查询总编排器", x[3], 250, 300, 120, fill="#dbeafe", stroke="#2563eb"),
        Box("Workflow", "workflow.py\nLangGraph / 兼容工作流", x[3], 416, 300, 96, fill="#dbeafe", stroke="#2563eb"),
        Box("Presentation", "presentation.py\nCoordinatorResult -> view_model", x[3], 552, 300, 110, fill="#dbeafe", stroke="#2563eb"),
        Box("CityResolver", "city_resolver.py\n地点解析与候选确认", x[4], 210, 300, 110, fill="#ecfeff", stroke="#0f766e"),
        Box("WeatherSvc", "weather_service.py\n天气查询 / geocoding / demo 降级", x[4], 356, 300, 120, fill="#ecfeff", stroke="#0f766e"),
        Box("Knowledge", "fashion_knowledge.py\n规则检索 / 向量检索 / rerank", x[4], 514, 300, 120, fill="#ecfeff", stroke="#0f766e"),
        Box("Fashion", "fashion_agent.py\n穿搭建议生成 / 规则兜底", x[4], 672, 300, 120, fill="#ecfeff", stroke="#0f766e"),
        Box("Health", "health_check.py\n运行时健康检查", x[4], 832, 300, 96, fill="#f0fdf4", stroke="#16a34a"),
        Box("LLM", "llm_support.py\nLLM / embedding 配置与调用", x[4], 966, 300, 110, fill="#f0fdf4", stroke="#16a34a"),
        Box("MapSupport", "map_support.py\n地图配置与测试", x[4], 1116, 300, 96, fill="#f0fdf4", stroke="#16a34a"),
        Box("Obs", "observability + logs_support\ntrace / metrics / 结构化事件", x[4], 1250, 300, 110, fill="#f0fdf4", stroke="#16a34a"),
        Box("RuntimeStore", "runtime_storage.py\n.runtime/state + .runtime/logs", x[4], 1400, 300, 110, fill="#f0fdf4", stroke="#16a34a"),
        Box("UserStore", "user_state_store.py\nhistory / favorites 读写", x[4], 1544, 300, 96, fill="#f0fdf4", stroke="#16a34a"),
        Box("OpenWeather", "OpenWeather API", x[5], 300, 300, 92, fill="#fff7ed", stroke="#f97316"),
        Box("KnowledgeJSONL", "resources/fashion_knowledge/*.jsonl", x[5], 442, 300, 96, fill="#fff7ed", stroke="#f97316"),
        Box("RuntimeFiles", ".runtime/state/*.json\n.runtime/logs/*.log\napp.events.jsonl", x[5], 590, 300, 120, fill="#fff7ed", stroke="#f97316"),
    ]
    pos = {box.key: box for box in boxes}
    arrows = [
        Arrow(((pos["AppRouter"].x + 300, 285), (pos["AppFrame"].x, 285)), color="#475569"),
        Arrow(((pos["AppFrame"].x + 300, 430), (pos["QueryWorkspace"].x, 430)), color="#475569"),
        Arrow(((pos["AppFrame"].x + 300, 594), (pos["DevPages"].x, 594)), color="#475569"),
        Arrow(((pos["QueryWorkspace"].x + 300, 442), (pos["Session"].x, 442)), color="#2563eb"),
        Arrow(((pos["DevPages"].x + 300, 594), (pos["Session"].x, 480)), color="#8b5cf6", dashed=True),
        Arrow(((pos["QueryWorkspace"].x + 300, 748), (pos["ResultCards"].x, 748)), color="#475569"),
        Arrow(((pos["Session"].x + 300, 610), (pos["FrontAPI"].x, 610)), color="#2563eb"),
        Arrow(((pos["Session"].x + 300, 732), (pos["BrowserStorage"].x, 732)), color="#f97316"),
        Arrow(((pos["FrontAPI"].x + 300, 596), (pos["Server"].x, 596)), color="#2563eb"),
        Arrow(((pos["Server"].x + 300, 316), (pos["Coordinator"].x, 316)), color="#2563eb"),
        Arrow(((pos["Server"].x + 300, 462), (pos["Schemas"].x, 462)), color="#475569"),
        Arrow(((pos["Server"].x + 300, 612), (pos["Presentation"].x, 612)), color="#2563eb"),
        Arrow(((pos["Coordinator"].x + 300, 464), (pos["Workflow"].x, 464)), color="#2563eb"),
        Arrow(((pos["Workflow"].x + 300, 264), (pos["CityResolver"].x, 264)), color="#0f766e"),
        Arrow(((pos["Workflow"].x + 300, 416), (pos["WeatherSvc"].x, 416)), color="#0f766e"),
        Arrow(((pos["Workflow"].x + 300, 736), (pos["Fashion"].x, 736)), color="#0f766e"),
        Arrow(((pos["Fashion"].x, 732), (pos["Knowledge"].x + 300, 732)), color="#0f766e"),
        Arrow(((pos["CityResolver"].x + 300, 410), (pos["WeatherSvc"].x, 410)), color="#475569"),
        Arrow(((pos["WeatherSvc"].x + 300, 416), (pos["OpenWeather"].x, 346)), color="#f97316"),
        Arrow(((pos["Knowledge"].x + 300, 574), (pos["KnowledgeJSONL"].x, 490)), color="#f97316"),
        Arrow(((pos["Knowledge"].x + 300, 620), (pos["LLM"].x, 1024)), color="#16a34a"),
        Arrow(((pos["Fashion"].x + 300, 730), (pos["LLM"].x, 1024)), color="#16a34a"),
        Arrow(((pos["Presentation"].x + 300, 606), (pos["Session"].x, 440)), color="#2563eb"),
        Arrow(((pos["Server"].x + 300, 840), (pos["Health"].x, 880)), color="#16a34a"),
        Arrow(((pos["Server"].x + 300, 1320), (pos["Obs"].x, 1320)), color="#16a34a"),
        Arrow(((pos["Server"].x + 300, 1584), (pos["UserStore"].x, 1584)), color="#16a34a"),
        Arrow(((pos["UserStore"].x + 300, 1592), (pos["RuntimeStore"].x, 1454)), color="#16a34a"),
        Arrow(((pos["RuntimeStore"].x + 300, 1454), (pos["RuntimeFiles"].x, 652)), color="#f97316"),
        Arrow(((pos["Obs"].x + 300, 1306), (pos["RuntimeStore"].x, 1454)), color="#16a34a"),
        Arrow(((pos["Health"].x + 300, 880), (pos["LLM"].x, 1020)), color="#16a34a", dashed=True),
        Arrow(((pos["Health"].x + 300, 912), (pos["Knowledge"].x + 150, 634)), color="#16a34a", dashed=True),
        Arrow(((pos["MapSupport"].x + 300, 1164), (pos["RuntimeStore"].x, 1454)), color="#16a34a"),
    ]
    return size, panels, boxes, arrows, "WeatherWear 模块关系图", "主查询链路 + 开发者功能侧链 + 运行时支撑侧链"


def build_data_flow_diagram() -> tuple[tuple[int, int], list[Panel], list[Box], list[Arrow], str, str]:
    size = (2400, 1180)
    panel_w = 340
    gap = 34
    left = 36
    top = 150
    panel_h = 960
    titles = ["阶段 1：输入采集", "阶段 2：请求载荷", "阶段 3：领域状态", "阶段 4：外部 / 本地数据源", "阶段 5：结果模型", "阶段 6：持久化 / 观测"]
    panels = [Panel(title, left + i * (panel_w + gap), top, panel_w, panel_h) for i, title in enumerate(titles)]
    x = [panel.x + 20 for panel in panels]
    boxes = [
        Box("UserInput", "用户输入\nquery_text", x[0], 250, 300, 96, fill="#eff6ff", stroke="#3b82f6"),
        Box("MapInput", "地图输入\nselected_coords", x[0], 390, 300, 96, fill="#eff6ff", stroke="#3b82f6"),
        Box("ModeInput", "交互选项\nconfirmation_mode / locale /\ngender / occasion / target_date", x[0], 530, 300, 130, fill="#eff6ff", stroke="#3b82f6"),
        Box("QueryRequest", "QueryRequest\n前后端请求契约", x[1], 280, 300, 110, fill="#eff6ff", stroke="#3b82f6"),
        Box("QueryState", "QueryState\n工作流运行态", x[1], 436, 300, 96, fill="#ecfdf5", stroke="#10b981"),
        Box("QueryPlan", "QueryPlan\nplanner 或 fast path 生成", x[1], 572, 300, 96, fill="#ecfdf5", stroke="#10b981"),
        Box("CityResult", "CityResolutionResult", x[2], 220, 300, 88, fill="#ecfdf5", stroke="#10b981"),
        Box("WeatherResult", "WeatherResult", x[2], 348, 300, 88, fill="#ecfdf5", stroke="#10b981"),
        Box("KnowledgeHits", "KnowledgeHit[]", x[2], 476, 300, 88, fill="#ecfdf5", stroke="#10b981"),
        Box("FashionAdvice", "FashionAdviceResult", x[2], 604, 300, 88, fill="#ecfdf5", stroke="#10b981"),
        Box("CoordinatorResult", "CoordinatorResult", x[2], 744, 300, 96, fill="#ecfdf5", stroke="#10b981"),
        Box("OpenWeather", "OpenWeather API", x[3], 260, 300, 88, fill="#fff7ed", stroke="#f59e0b"),
        Box("JSONL", "resources/fashion_knowledge/*.jsonl", x[3], 394, 300, 96, fill="#fff7ed", stroke="#f59e0b"),
        Box("LLMConfig", "LLM / Embedding 配置", x[3], 536, 300, 88, fill="#fff7ed", stroke="#f59e0b"),
        Box("MapConfig", "地图配置", x[3], 670, 300, 88, fill="#fff7ed", stroke="#f59e0b"),
        Box("ViewModel", "view_model\n结果页 + Clarification + Timeline + Debug", x[4], 300, 300, 120, fill="#ecfdf5", stroke="#10b981"),
        Box("UIRender", "UI 渲染\n结果卡片 / 候选确认 / Trace 面板", x[4], 468, 300, 110, fill="#ecfdf5", stroke="#10b981"),
        Box("DebugViews", "开发者视图\nTrace / Logs / ModelConfig / MapConfig", x[4], 620, 300, 110, fill="#ecfdf5", stroke="#10b981"),
        Box("History", "history.json", x[5], 290, 300, 88, fill="#fff7ed", stroke="#f59e0b"),
        Box("Favorites", "favorites.json", x[5], 420, 300, 88, fill="#fff7ed", stroke="#f59e0b"),
        Box("EventLog", "app.events.jsonl", x[5], 550, 300, 88, fill="#fff7ed", stroke="#f59e0b"),
        Box("BrowserStore", "sessionStorage /\nlocalStorage", x[5], 680, 300, 96, fill="#fff7ed", stroke="#f59e0b"),
    ]
    pos = {box.key: box for box in boxes}
    arrows = [
        Arrow(((pos["UserInput"].x + 300, 298), (pos["QueryRequest"].x, 336)), color="#3b82f6"),
        Arrow(((pos["MapInput"].x + 300, 438), (pos["QueryRequest"].x, 336)), color="#3b82f6"),
        Arrow(((pos["ModeInput"].x + 300, 595), (pos["QueryRequest"].x, 360)), color="#3b82f6"),
        Arrow(((pos["QueryRequest"].x + 300, 336), (pos["QueryState"].x, 484)), color="#10b981"),
        Arrow(((pos["QueryRequest"].x + 300, 336), (pos["QueryPlan"].x, 620)), color="#10b981"),
        Arrow(((pos["QueryPlan"].x + 300, 620), (pos["QueryState"].x + 150, 532)), color="#10b981"),
        Arrow(((pos["QueryState"].x + 300, 484), (pos["CityResult"].x, 264)), color="#10b981"),
        Arrow(((pos["QueryState"].x + 300, 484), (pos["WeatherResult"].x, 392)), color="#10b981"),
        Arrow(((pos["QueryState"].x + 300, 484), (pos["KnowledgeHits"].x, 520)), color="#10b981"),
        Arrow(((pos["QueryState"].x + 300, 484), (pos["FashionAdvice"].x, 648)), color="#10b981"),
        Arrow(((pos["CityResult"].x + 300, 264), (pos["CoordinatorResult"].x, 792)), color="#10b981"),
        Arrow(((pos["WeatherResult"].x + 300, 392), (pos["CoordinatorResult"].x, 792)), color="#10b981"),
        Arrow(((pos["KnowledgeHits"].x + 300, 520), (pos["CoordinatorResult"].x, 792)), color="#10b981"),
        Arrow(((pos["FashionAdvice"].x + 300, 648), (pos["CoordinatorResult"].x, 792)), color="#10b981"),
        Arrow(((pos["CoordinatorResult"].x + 300, 792), (pos["ViewModel"].x, 360)), color="#10b981"),
        Arrow(((pos["ViewModel"].x + 300, 360), (pos["UIRender"].x, 522)), color="#10b981"),
        Arrow(((pos["ViewModel"].x + 300, 360), (pos["DebugViews"].x, 676)), color="#10b981"),
        Arrow(((pos["ViewModel"].x + 300, 408), (pos["BrowserStore"].x, 730)), color="#f59e0b"),
        Arrow(((pos["ViewModel"].x + 300, 430), (pos["History"].x, 334)), color="#f59e0b"),
        Arrow(((pos["ViewModel"].x + 300, 458), (pos["Favorites"].x, 464)), color="#f59e0b"),
        Arrow(((pos["QueryState"].x + 300, 505), (pos["EventLog"].x, 594)), color="#f59e0b"),
        Arrow(((pos["CoordinatorResult"].x + 300, 820), (pos["EventLog"].x, 594)), color="#f59e0b"),
        Arrow(((pos["QueryState"].x + 300, 454), (pos["OpenWeather"].x, 304)), color="#f59e0b", dashed=True),
        Arrow(((pos["KnowledgeHits"].x + 300, 520), (pos["JSONL"].x, 442)), color="#f59e0b", dashed=True),
        Arrow(((pos["QueryState"].x + 300, 560), (pos["LLMConfig"].x, 580)), color="#f59e0b", dashed=True),
        Arrow(((pos["ViewModel"].x + 300, 384), (pos["MapConfig"].x, 714)), color="#f59e0b", dashed=True),
    ]
    return size, panels, boxes, arrows, "WeatherWear 数据流转过程图", "输入对象 -> 请求载荷 -> 领域结果 -> 结果模型 -> 持久化 / 观测"


def render_module_or_data(
    size: tuple[int, int],
    title: str,
    subtitle: str,
    panels: list[Panel],
    boxes: list[Box],
    arrows: list[Arrow],
    base_name: str,
) -> None:
    image, draw = render_base_png(size, title, subtitle)
    for panel in panels:
        draw_panel_png(draw, panel)
    for arrow in arrows:
        draw_arrow_png(draw, arrow)
    for box in boxes:
        draw_box_png(draw, box)
    image.save(ASSET_DIR / f"{base_name}.png")

    content = "".join(draw_panel_svg(panel) for panel in panels)
    content += "".join(draw_arrow_svg(arrow) for arrow in arrows)
    content += "".join(draw_box_svg(box) for box in boxes)
    (ASSET_DIR / f"{base_name}.svg").write_text(render_base_svg(size, title, subtitle, content), encoding="utf-8")


def render_sequence(base_name: str) -> None:
    size = (2400, 1480)
    title = "WeatherWear 请求时序图"
    subtitle = "一次 /api/query 的主成功链路 + Clarification / 规则兜底 / Degraded 分支"
    width, _ = size
    image, draw = render_base_png(size, title, subtitle)
    participants = [
        "用户",
        "QueryPanel / Session",
        "shared/api.ts",
        "FastAPI /api/query",
        "MultiAgentCoordinator",
        "workflow",
        "CityResolver",
        "WeatherService",
        "FashionKnowledge",
        "FashionAgent",
        "Presentation",
        "Session / UI",
    ]
    x_positions = [90 + i * 190 for i in range(len(participants))]
    top_y = 160
    bottom_y = 1360
    for x, label in zip(x_positions, participants):
        rounded_rectangle(draw, (x - 70, top_y, x + 70, top_y + 60), "#ffffff", "#94a3b8", width=2, radius=16)
        draw_multiline_center(draw, x - 70, top_y, 140, 60, label, size=18)
        draw_dashed_line(draw, (x, top_y + 60), (x, bottom_y), "#cbd5e1", dash=10, gap=8)

    def msg(index_from: int, index_to: int, y: int, text: str, color: str = "#475569", dashed: bool = False) -> Arrow:
        return Arrow(((x_positions[index_from], y), (x_positions[index_to], y)), color=color, dashed=dashed)

    blocks = [
        (280, 378, "alt 复杂查询且 LLM 可用 / else fast path"),
        (468, 600, "alt strict / needs_clarification"),
        (648, 774, "alt OpenWeather live / demo-degraded"),
        (822, 946, "alt LLM 可用 / 规则兜底"),
        (1130, 1260, "par 后端观测链 / 前端本地状态链"),
    ]
    for top, bottom, label in blocks:
        rounded_rectangle(draw, (60, top, width - 60, bottom), "#f8fafc", "#cbd5e1", width=2, radius=18)
        draw.text((78, top + 14), label, font=font(20), fill=hex_to_rgb("#334155"))

    messages = [
        (0, 1, 220, "提交文本地点或地图点位", "#2563eb", False),
        (1, 1, 252, "组装 QueryRequest", "#475569", False),
        (1, 2, 410, "postQuery(payload)", "#2563eb", False),
        (2, 3, 442, "POST /api/query", "#2563eb", False),
        (3, 3, 506, "生成 request_id / 记录 query.started", "#475569", False),
        (3, 4, 538, "process_query(payload)", "#2563eb", False),
        (4, 5, 570, "run_query_workflow(QueryState)", "#2563eb", False),
        (5, 4, 330, "调用 planner 节点", "#7c3aed", False),
        (5, 4, 360, "走 fast path", "#0f766e", False),
        (5, 6, 626, "resolve_city(...)", "#2563eb", False),
        (6, 5, 658, "CityResolutionResult", "#2563eb", True),
        (5, 7, 714, "fetch weather by city / coords", "#2563eb", False),
        (7, 5, 746, "WeatherResult(live / demo)", "#2563eb", True),
        (5, 9, 806, "get_fashion_advice(weather, locale, query_context)", "#2563eb", False),
        (9, 8, 838, "retrieve_knowledge_hits(...)", "#0f766e", False),
        (8, 9, 870, "KnowledgeHit[]", "#0f766e", True),
        (9, 5, 916, "FashionAdviceResult(LLM / 规则兜底)", "#2563eb", True),
        (5, 4, 982, "CoordinatorResult", "#2563eb", True),
        (4, 10, 1014, "build_result_view_model(result)", "#2563eb", False),
        (10, 3, 1046, "QueryResponse(view_model)", "#2563eb", True),
        (3, 2, 1078, "200 OK", "#2563eb", True),
        (2, 11, 1110, "返回 view_model", "#2563eb", True),
        (11, 11, 1144, "更新结果区 / notice / 历史收藏状态", "#475569", False),
        (3, 3, 1206, "写 step trace / app.events.jsonl / logs", "#16a34a", False),
        (11, 11, 1238, "写 sessionStorage / localStorage", "#f97316", False),
    ]
    svg_parts = []
    for x, label in zip(x_positions, participants):
        svg_parts.append(f'<rect x="{x - 70}" y="{top_y}" rx="16" ry="16" width="140" height="60" fill="#ffffff" stroke="#94a3b8" stroke-width="2" />')
        svg_parts.append(svg_text(wrap_svg_text(label, 120, 18), x - 70, top_y, 140, 60, size=18))
        svg_parts.append(f'<line x1="{x}" y1="{top_y + 60}" x2="{x}" y2="{bottom_y}" stroke="#cbd5e1" stroke-width="3" stroke-dasharray="10 8" />')
    for top, bottom, label in blocks:
        svg_parts.append(f'<rect x="60" y="{top}" rx="18" ry="18" width="{width - 120}" height="{bottom - top}" fill="#f8fafc" stroke="#cbd5e1" stroke-width="2" />')
        svg_parts.append(f'<text x="78" y="{top + 28}" font-size="20" fill="#334155" font-family="Microsoft YaHei, Arial, sans-serif">{html.escape(label)}</text>')
    for index_from, index_to, y, text, color, dashed in messages:
        arrow = msg(index_from, index_to, y, text, color, dashed)
        draw_arrow_png(draw, arrow)
        draw.text((min(x_positions[index_from], x_positions[index_to]) + 6, y - 26), text, font=font(15), fill=hex_to_rgb("#334155"))
        svg_parts.append(draw_arrow_svg(arrow))
        svg_parts.append(
            f'<text x="{min(x_positions[index_from], x_positions[index_to]) + 6}" y="{y - 8}" font-size="15" fill="#334155" font-family="Microsoft YaHei, Arial, sans-serif">{html.escape(text)}</text>'
        )
    rounded_rectangle(draw, (1640, 180, 2290, 320), "#ffffff", "#cbd5e1", width=2, radius=16)
    draw.text((1660, 202), "关键分支说明", font=font(22), fill=hex_to_rgb("#0f172a"))
    draw.text((1660, 238), "1. strict 模式可能提前返回候选确认", font=font(18), fill=hex_to_rgb("#334155"))
    draw.text((1660, 266), "2. LLM 不可用时由 FashionAgent 规则兜底", font=font(18), fill=hex_to_rgb("#334155"))
    draw.text((1660, 294), "3. OpenWeather 未配置时走 demo / degraded", font=font(18), fill=hex_to_rgb("#334155"))
    svg_parts.append('<rect x="1640" y="180" rx="16" ry="16" width="650" height="140" fill="#ffffff" stroke="#cbd5e1" stroke-width="2" />')
    svg_parts.append('<text x="1660" y="212" font-size="22" fill="#0f172a" font-family="Microsoft YaHei, Arial, sans-serif">关键分支说明</text>')
    svg_parts.append('<text x="1660" y="242" font-size="18" fill="#334155" font-family="Microsoft YaHei, Arial, sans-serif">1. strict 模式可能提前返回候选确认</text>')
    svg_parts.append('<text x="1660" y="270" font-size="18" fill="#334155" font-family="Microsoft YaHei, Arial, sans-serif">2. LLM 不可用时由 FashionAgent 规则兜底</text>')
    svg_parts.append('<text x="1660" y="298" font-size="18" fill="#334155" font-family="Microsoft YaHei, Arial, sans-serif">3. OpenWeather 未配置时走 demo / degraded</text>')
    image.save(ASSET_DIR / f"{base_name}.png")
    (ASSET_DIR / f"{base_name}.svg").write_text(render_base_svg(size, title, subtitle, "".join(svg_parts)), encoding="utf-8")


def draw_shadow_box(draw: ImageDraw.ImageDraw, box: Box, *, shadow_offset: int = 10) -> None:
    rounded_rectangle(
        draw,
        (box.x + shadow_offset, box.y + shadow_offset, box.x + box.w + shadow_offset, box.y + box.h + shadow_offset),
        "#e5e7eb",
        "#e5e7eb",
        width=1,
        radius=8,
    )
    rounded_rectangle(draw, (box.x, box.y, box.x + box.w, box.y + box.h), box.fill, box.stroke, width=3, radius=8)
    draw_multiline_center(draw, box.x, box.y, box.w, box.h, box.text, fill=box.text_color, size=18)


def draw_shadow_box_svg(box: Box, *, shadow_offset: int = 10) -> str:
    lines = wrap_svg_text(box.text, box.w - 24, 18)
    return (
        f'<rect x="{box.x + shadow_offset}" y="{box.y + shadow_offset}" rx="8" ry="8" width="{box.w}" height="{box.h}" fill="#e5e7eb" stroke="none" />'
        f'<rect x="{box.x}" y="{box.y}" rx="8" ry="8" width="{box.w}" height="{box.h}" fill="{box.fill}" stroke="{box.stroke}" stroke-width="3" />'
        + svg_text(lines, box.x, box.y, box.w, box.h, size=18, fill=box.text_color)
    )


def draw_arrow_with_label_png(draw: ImageDraw.ImageDraw, arrow: Arrow) -> None:
    draw_arrow_png(draw, arrow)
    if arrow.label:
        start = arrow.points[0]
        end = arrow.points[-1]
        tx = (start[0] + end[0]) / 2
        ty = (start[1] + end[1]) / 2 - 20
        draw.text((tx, ty), arrow.label, font=font(16), fill=hex_to_rgb("#334155"))


def draw_arrow_with_label_svg(arrow: Arrow) -> str:
    text = ""
    if arrow.label:
        start = arrow.points[0]
        end = arrow.points[-1]
        tx = (start[0] + end[0]) / 2
        ty = (start[1] + end[1]) / 2 - 8
        text = f'<text x="{tx}" y="{ty}" font-size="16" fill="#334155" font-family="Microsoft YaHei, Arial, sans-serif">{html.escape(arrow.label)}</text>'
    return draw_arrow_svg(arrow) + text


def render_architecture_layered_v2(base_name: str) -> None:
    size = (2200, 1700)
    title = "WeatherWear 技术架构图"
    subtitle = "参考教材式分层大框结构，突出前端、后端、编排、服务与外部资源的关系"
    image, draw = render_base_png(size, title, subtitle)

    layers = [
        Panel("前端层（React + TypeScript）", 50, 150, 2100, 240, fill="#f5f5f4", stroke="#312e49"),
        Panel("后端接口层（FastAPI）", 120, 430, 1960, 220, fill="#f5f5f4", stroke="#312e49"),
        Panel("智能体 / 工作流层（Coordinator + Workflow）", 30, 760, 2140, 560, fill="#f5f5f4", stroke="#312e49"),
        Panel("外部服务与持久化层", 80, 1440, 2040, 190, fill="#f5f5f4", stroke="#312e49"),
    ]
    for panel in layers:
        rounded_rectangle(draw, (panel.x, panel.y, panel.x + panel.w, panel.y + panel.h), panel.fill, panel.stroke, width=4, radius=2)
        draw.text((panel.x + panel.w / 2 - 180, panel.y + 8), panel.title, font=font(24), fill=hex_to_rgb("#111827"))

    boxes = [
        Box("UI1", "主查询工作台 UI\nQueryWorkspace / QueryPanel", 180, 230, 440, 130, fill="#dbeafe", stroke="#312e49"),
        Box("UI2", "结果可视化与调试视图\nResult / Trace / Timeline", 1180, 200, 560, 160, fill="#dbeafe", stroke="#312e49"),
        Box("API", "API 路由\n/api/query\n/api/history\n/api/favorites", 880, 500, 420, 130, fill="#fef3c7", stroke="#312e49"),
        Box("Planner", "查询规划器\nQuery Planner", 140, 860, 340, 150, fill="#f3e8ff", stroke="#312e49"),
        Box("Coordinator", "总协调器\nMultiAgentCoordinator", 560, 860, 420, 150, fill="#f3e8ff", stroke="#312e49"),
        Box("Presenter", "结果组装器\npresentation.py", 1080, 860, 340, 150, fill="#f3e8ff", stroke="#312e49"),
        Box("City", "地点解析\ncity_resolver.py", 120, 1120, 300, 150, fill="#ecfccb", stroke="#312e49"),
        Box("Weather", "天气查询\nweather_service.py", 520, 1120, 300, 150, fill="#ecfccb", stroke="#312e49"),
        Box("Knowledge", "知识检索\nfashion_knowledge.py", 920, 1120, 300, 150, fill="#ecfccb", stroke="#312e49"),
        Box("Fashion", "穿搭生成\nfashion_agent.py", 1320, 1120, 300, 150, fill="#ecfccb", stroke="#312e49"),
        Box("Support", "运行时支撑\nllm_support / health_check /\nobservability / runtime_storage", 1680, 1080, 360, 210, fill="#dcfce7", stroke="#312e49"),
        Box("OpenWeather", "OpenWeather", 180, 1505, 260, 90, fill="#fce7f3", stroke="#312e49"),
        Box("JSONL", "知识库 JSONL", 760, 1505, 260, 90, fill="#fce7f3", stroke="#312e49"),
        Box("Runtime", ".runtime 日志 / 状态", 1360, 1505, 340, 90, fill="#fce7f3", stroke="#312e49"),
        Box("LLM", "LLM / Embedding 提供方", 1760, 1505, 280, 90, fill="#fce7f3", stroke="#312e49"),
    ]
    for box in boxes:
        draw_shadow_box(draw, box)

    pos = {box.key: box for box in boxes}
    arrows = [
        Arrow(((400, 360), (400, 470), (880, 560)), color="#111111"),
        Arrow(((1460, 360), (1460, 470), (1300, 560)), color="#111111"),
        Arrow(((1090, 630), (1090, 860)), color="#111111"),
        Arrow(((900, 630), (320, 860)), color="#111111"),
        Arrow(((1280, 630), (1500, 860)), color="#111111"),
        Arrow(((300, 1010), (270, 1120)), color="#111111"),
        Arrow(((750, 1010), (670, 1120)), color="#111111"),
        Arrow(((770, 1010), (1070, 1120)), color="#111111"),
        Arrow(((1240, 1010), (1470, 1120)), color="#111111"),
        Arrow(((270, 1270), (270, 1505)), color="#111111"),
        Arrow(((1070, 1270), (900, 1505)), color="#111111"),
        Arrow(((1470, 1270), (1470, 1505)), color="#111111"),
        Arrow(((1860, 1290), (1900, 1505)), color="#111111"),
        Arrow(((1830, 1080), (1830, 1505)), color="#111111"),
        Arrow(((400, 360), (400, 1120), (520, 1195)), color="#111111", dashed=True),
    ]
    for arrow in arrows:
        draw_arrow_png(draw, arrow)

    svg_parts = []
    for panel in layers:
        svg_parts.append(f'<rect x="{panel.x}" y="{panel.y}" width="{panel.w}" height="{panel.h}" fill="{panel.fill}" stroke="{panel.stroke}" stroke-width="4" />')
        svg_parts.append(f'<text x="{panel.x + panel.w / 2}" y="{panel.y + 34}" text-anchor="middle" font-size="24" fill="#111827" font-family="Microsoft YaHei, Arial, sans-serif">{html.escape(panel.title)}</text>')
    for box in boxes:
        svg_parts.append(draw_shadow_box_svg(box))
    for arrow in arrows:
        svg_parts.append(draw_arrow_svg(arrow))

    image.save(ASSET_DIR / f"{base_name}.png")
    (ASSET_DIR / f"{base_name}.svg").write_text(render_base_svg(size, title, subtitle, "".join(svg_parts)), encoding="utf-8")


def render_request_sequence_v2(base_name: str) -> None:
    size = (2600, 1800)
    title = "WeatherWear 请求时序图（V2）"
    subtitle = "参考教材式泳道 + loop 结构，展示一次查询从规划到结果输出的完整过程"
    image, draw = render_base_png(size, title, subtitle)
    participants = ["用户", "前端", "后端 API", "Planner", "City Resolver", "Weather Service", "Fashion Agent", "Presentation", "存储/日志"]
    xs = [120 + i * 290 for i in range(len(participants))]
    top = 160
    bottom = 1670
    for x, label in zip(xs, participants):
        rounded_rectangle(draw, (x - 90, top, x + 90, top + 56), "#ffffff", "#312e49", width=2, radius=10)
        draw_multiline_center(draw, x - 90, top, 180, 56, label, size=18)
        rounded_rectangle(draw, (x - 90, bottom, x + 90, bottom + 56), "#ffffff", "#312e49", width=2, radius=10)
        draw_multiline_center(draw, x - 90, bottom, 180, 56, label, size=18)
        draw_dashed_line(draw, (x, top + 56), (x, bottom), "#312e49", dash=9, gap=7)

    loop_box = (350, 760, 2320, 1400)
    rounded_rectangle(draw, loop_box, "#fafafa", "#6b7280", width=2, radius=2)
    rounded_rectangle(draw, (350, 760, 420, 805), "#ffffff", "#6b7280", width=2, radius=6)
    draw.text((367, 772), "loop", font=font(18), fill=hex_to_rgb("#111827"))
    draw.text((1260, 785), "[候选地点已确认]", font=font(20), fill=hex_to_rgb("#111827"))

    messages = [
        Arrow(((xs[0], 260), (xs[1], 260)), label="输入查询主题 / 地点 / 场景", color="#312e49"),
        Arrow(((xs[1], 330), (xs[2], 330)), label="POST /api/query", color="#312e49"),
        Arrow(((xs[2], 410), (xs[3], 410)), label="规划查询任务", color="#312e49"),
        Arrow(((xs[3], 480), (xs[2], 480)), label="返回 QueryPlan", color="#312e49", dashed=True),
        Arrow(((xs[2], 560), (xs[4], 560)), label="解析地点 / 候选确认", color="#312e49"),
        Arrow(((xs[4], 630), (xs[2], 630)), label="返回地点结果", color="#312e49", dashed=True),
        Arrow(((xs[2], 705), (xs[1], 705)), label="SSE 推送规划与地点状态", color="#312e49", dashed=True),
        Arrow(((xs[2], 870), (xs[5], 870)), label="查询天气", color="#312e49"),
        Arrow(((xs[5], 940), (xs[2], 940)), label="返回天气结果", color="#312e49", dashed=True),
        Arrow(((xs[2], 1030), (xs[6], 1030)), label="生成穿搭建议（含知识检索）", color="#312e49"),
        Arrow(((xs[6], 1110), (xs[2], 1110)), label="返回穿搭建议", color="#312e49", dashed=True),
        Arrow(((xs[2], 1180), (xs[7], 1180)), label="组装 view_model", color="#312e49"),
        Arrow(((xs[7], 1250), (xs[2], 1250)), label="返回结果模型", color="#312e49", dashed=True),
        Arrow(((xs[2], 1320), (xs[8], 1320)), label="写日志 / trace / history", color="#312e49"),
        Arrow(((xs[2], 1470), (xs[1], 1470)), label="SSE / HTTP 返回结果", color="#312e49", dashed=True),
        Arrow(((xs[1], 1550), (xs[0], 1550)), label="展示天气与穿搭结果", color="#312e49", dashed=True),
    ]
    for arrow in messages:
        draw_arrow_with_label_png(draw, arrow)

    svg_parts = []
    for x, label in zip(xs, participants):
        svg_parts.append(f'<rect x="{x - 90}" y="{top}" rx="10" ry="10" width="180" height="56" fill="#ffffff" stroke="#312e49" stroke-width="2" />')
        svg_parts.append(svg_text(wrap_svg_text(label, 160, 18), x - 90, top, 180, 56, size=18))
        svg_parts.append(f'<rect x="{x - 90}" y="{bottom}" rx="10" ry="10" width="180" height="56" fill="#ffffff" stroke="#312e49" stroke-width="2" />')
        svg_parts.append(svg_text(wrap_svg_text(label, 160, 18), x - 90, bottom, 180, 56, size=18))
        svg_parts.append(f'<line x1="{x}" y1="{top + 56}" x2="{x}" y2="{bottom}" stroke="#312e49" stroke-width="2" stroke-dasharray="9 7" />')
    svg_parts.append(f'<rect x="{loop_box[0]}" y="{loop_box[1]}" width="{loop_box[2]-loop_box[0]}" height="{loop_box[3]-loop_box[1]}" fill="#fafafa" stroke="#6b7280" stroke-width="2" />')
    svg_parts.append('<rect x="350" y="760" width="70" height="45" rx="6" ry="6" fill="#ffffff" stroke="#6b7280" stroke-width="2" />')
    svg_parts.append('<text x="385" y="790" text-anchor="middle" font-size="18" fill="#111827" font-family="Microsoft YaHei, Arial, sans-serif">loop</text>')
    svg_parts.append('<text x="1260" y="790" text-anchor="middle" font-size="20" fill="#111827" font-family="Microsoft YaHei, Arial, sans-serif">[候选地点已确认]</text>')
    for arrow in messages:
        svg_parts.append(draw_arrow_with_label_svg(arrow))

    image.save(ASSET_DIR / f"{base_name}.png")
    (ASSET_DIR / f"{base_name}.svg").write_text(render_base_svg(size, title, subtitle, "".join(svg_parts)), encoding="utf-8")


def render_data_flow_v2(base_name: str) -> None:
    size = (2200, 1300)
    title = "WeatherWear 数据流转过程图（V2）"
    subtitle = "按输入、编排、领域服务、结果模型、持久化五段展示 QueryRequest 到 view_model 的变换过程"
    image, draw = render_base_png(size, title, subtitle)

    steps = [
        Box("S1", "用户输入\nquery_text / selected_coords /\nlocale / confirmation_mode", 70, 420, 340, 140, fill="#dbeafe", stroke="#312e49"),
        Box("S2", "QueryRequest\n前后端请求契约", 490, 420, 280, 140, fill="#fef3c7", stroke="#312e49"),
        Box("S3", "QueryState / QueryPlan\ncoordinator + workflow", 850, 420, 330, 140, fill="#f3e8ff", stroke="#312e49"),
        Box("S4", "领域服务阶段\nCityResolutionResult\nWeatherResult\nKnowledgeHit[]\nFashionAdviceResult", 1260, 360, 380, 260, fill="#dcfce7", stroke="#312e49"),
        Box("S5", "CoordinatorResult\npresentation -> view_model", 1730, 420, 320, 140, fill="#dbeafe", stroke="#312e49"),
    ]
    storage = [
        Box("D1", "OpenWeather", 230, 900, 220, 90, fill="#fce7f3", stroke="#312e49"),
        Box("D2", "知识库 JSONL", 760, 900, 220, 90, fill="#fce7f3", stroke="#312e49"),
        Box("D3", "LLM / Embedding", 1240, 900, 240, 90, fill="#fce7f3", stroke="#312e49"),
        Box("D4", "history.json /\nfavorites.json /\napp.events.jsonl", 1750, 880, 300, 120, fill="#fce7f3", stroke="#312e49"),
    ]
    for box in steps + storage:
        draw_shadow_box(draw, box)

    arrows = [
        Arrow(((410, 490), (490, 490)), label="构造请求", color="#111111"),
        Arrow(((770, 490), (850, 490)), label="进入编排", color="#111111"),
        Arrow(((1180, 490), (1260, 490)), label="驱动服务执行", color="#111111"),
        Arrow(((1640, 490), (1730, 490)), label="汇总结果", color="#111111"),
        Arrow(((1450, 620), (1450, 900)), label="调用模型 / 检索", color="#111111"),
        Arrow(((980, 560), (870, 900)), label="读取知识条件", color="#111111"),
        Arrow(((1380, 620), (340, 900)), label="天气数据查询", color="#111111"),
        Arrow(((1890, 560), (1890, 880)), label="持久化 / 观测", color="#111111"),
    ]
    for arrow in arrows:
        draw_arrow_with_label_png(draw, arrow)

    svg_parts = []
    for box in steps + storage:
        svg_parts.append(draw_shadow_box_svg(box))
    for arrow in arrows:
        svg_parts.append(draw_arrow_with_label_svg(arrow))

    image.save(ASSET_DIR / f"{base_name}.png")
    (ASSET_DIR / f"{base_name}.svg").write_text(render_base_svg(size, title, subtitle, "".join(svg_parts)), encoding="utf-8")


def write_v2_mermaid_sources() -> None:
    sources = {
        "architecture-layered-v2.mmd": """flowchart TB
    subgraph FE["前端层（React + TypeScript）"]
        UI1["主查询工作台 UI"]
        UI2["结果可视化与调试视图"]
    end
    subgraph API["后端接口层（FastAPI）"]
        Route["API 路由<br/>/api/query /api/history /api/favorites"]
    end
    subgraph WF["智能体 / 工作流层"]
        Planner["Query Planner"]
        Coord["MultiAgentCoordinator"]
        Presenter["presentation.py"]
        City["city_resolver.py"]
        Weather["weather_service.py"]
        Knowledge["fashion_knowledge.py"]
        Fashion["fashion_agent.py"]
        Support["llm_support / health_check / observability / runtime_storage"]
    end
    subgraph EXT["外部服务与持久化层"]
        OpenWeather["OpenWeather"]
        Jsonl["知识库 JSONL"]
        Runtime[".runtime 日志 / 状态"]
        LLM["LLM / Embedding"]
    end
""",
        "request-sequence-v2.mmd": """sequenceDiagram
    actor User as 用户
    participant FE as 前端
    participant API as 后端 API
    participant Planner as Planner
    participant City as City Resolver
    participant Weather as Weather Service
    participant Fashion as Fashion Agent
    participant Presenter as Presentation
    participant Store as 存储/日志
""",
        "data-flow-v2.mmd": """flowchart LR
    Input["用户输入"] --> Req["QueryRequest"]
    Req --> State["QueryState / QueryPlan"]
    State --> Domain["地点 / 天气 / 知识 / 穿搭"]
    Domain --> Result["CoordinatorResult / view_model"]
    Result --> Persist["history / favorites / logs"]
""",
    }
    for filename, content in sources.items():
        target = MERMAID_DIR / filename
        if target.exists():
            continue
        target.write_text(content + "\n", encoding="utf-8")


def write_v3_mermaid_sources() -> None:
    sources = {
        "architecture-layered-v3.mmd": """flowchart TB
    User["用户查询入口\\nQueryWorkspace / QueryPanel"]
    Session["会话状态层\\nWeatherWearSession / AppRouter"]
    FrontAPI["前端 API 封装\\nshared/api.ts"]
    Server["后端入口\\nserver.py"]
    Coordinator["应用编排\\nMultiAgentCoordinator"]
    Workflow["工作流执行\\nworkflow.py"]
    CityWeather["城市与天气服务\\ncity_resolver.py + weather_service.py"]
    FashionStack["知识与穿搭服务\\nfashion_knowledge.py + fashion_agent.py"]
    Presentation["结果表示层\\npresentation.py"]
    Runtime["运行时支撑\\nhealth_check / llm_support / map_support / observability"]
    Storage["状态持久化\\nuser_state_store.py + runtime_storage.py"]
    Sources["资源层\\nOpenWeather / fashion_knowledge JSONL / .runtime"]

    User --> Session --> FrontAPI --> Server --> Coordinator --> Workflow
    Workflow --> CityWeather
    Workflow --> FashionStack
    Coordinator --> Presentation --> Session
    CityWeather --> Sources
    FashionStack --> Sources
    Server -. trace / health .-> Runtime
    Runtime -. logs / diagnostics .-> Sources
    Server --> Storage --> Sources
    Session -. developer tools .-> Runtime
""",
        "module-relationship-v2.mmd": """flowchart LR
    AppRouter["AppRouter"]
    QueryPanel["QueryWorkspace / QueryPanel"]
    Session["WeatherWearSession"]
    FrontAPI["shared/api.ts"]
    Server["server.py"]
    Coordinator["MultiAgentCoordinator"]
    Workflow["workflow.py"]
    Presentation["presentation.py"]
    City["city_resolver.py"]
    Weather["weather_service.py"]
    Knowledge["fashion_knowledge.py"]
    Fashion["fashion_agent.py"]
    UserStore["user_state_store.py"]
    RuntimeStore["runtime_storage.py\\n.runtime/state + .runtime/logs"]
    Jsonl["resources/fashion_knowledge/*.jsonl"]

    AppRouter --> QueryPanel --> Session --> FrontAPI --> Server
    Server --> Coordinator --> Workflow
    Coordinator --> Presentation --> Session
    Workflow --> City
    Workflow --> Weather
    Workflow --> Fashion
    Fashion --> Knowledge --> Jsonl
    Server --> UserStore --> RuntimeStore
    Server -. trace / logs .-> RuntimeStore
    AppRouter -. Trace / Logs / ModelConfig / MapConfig .-> Session
""",
        "request-sequence-v3.mmd": """sequenceDiagram
    autonumber
    actor User as 用户
    participant Front as QueryPanel / Session / shared/api.ts
    participant API as FastAPI /api/query
    participant Coord as MultiAgentCoordinator / workflow
    participant CityWeather as CityResolver + WeatherService
    participant Fashion as FashionKnowledge + FashionAgent
    participant Present as Presentation / Session UI

    User->>Front: 提交文本地点或地图点位
    Front->>Front: 组装 QueryRequest
    Front->>API: POST /api/query
    API->>API: 生成 request_id + 记录 query.started
    API->>Coord: process_query(payload)
    Coord->>Coord: planner 或 fast path
    Coord->>CityWeather: resolve_city(...)
    CityWeather-->>Coord: CityResolutionResult

    alt strict / needs_clarification
        Coord->>Present: 返回 clarification view_model
        Present-->>Front: 展示候选确认
    else 地点已确认
        Coord->>CityWeather: fetch_weather(...)
        alt OpenWeather 未配置
            CityWeather-->>Coord: WeatherResult(demo / degraded)
        else OpenWeather 可用
            CityWeather-->>Coord: WeatherResult(live)
        end
        Coord->>Fashion: retrieve_knowledge + get_fashion_advice
        alt LLM 不可用
            Fashion-->>Coord: FashionAdviceResult(规则兜底)
        else LLM 可用
            Fashion-->>Coord: KnowledgeHit[] + FashionAdviceResult
        end
        Coord->>Present: build_result_view_model
        Present-->>Front: QueryResponse(view_model)
        Front->>Front: 更新结果 / 历史 / 收藏 / notice
    end

    par 后端观测
        API->>API: 写 trace / logs / app.events.jsonl
    and 前端本地状态
        Front->>Front: 写 sessionStorage / localStorage
    end
""",
        "data-flow-v3.mmd": """flowchart LR
    Input["输入采集\\nquery_text / selected_coords / confirmation_mode / locale"]
    Request["QueryRequest"]
    State["QueryState / QueryPlan"]
    Domain["领域结果\\nCityResolutionResult / WeatherResult / KnowledgeHit[] / FashionAdviceResult"]
    Result["CoordinatorResult -> view_model"]
    UI["UI 渲染 / 调试面板"]
    History["history.json"]
    Favorites["favorites.json"]
    Events["app.events.jsonl"]
    Sources["数据源池\\nOpenWeather / fashion_knowledge JSONL / LLM config / map config"]

    Input --> Request --> State --> Domain --> Result
    Sources -. 解析 / 检索 / 配置 .-> State
    Sources -. 天气 / 知识 / 模型 .-> Domain
    Result --> UI
    Result --> History
    Result --> Favorites
    State -. 观测 .-> Events
    Result -. 观测 .-> Events
""",
    }
    for filename, content in sources.items():
        (MERMAID_DIR / filename).write_text(content + "\n", encoding="utf-8")


def render_architecture_layered_v3(base_name: str) -> None:
    size = (2400, 1680)
    title = "WeatherWear 技术架构图（V3）"
    subtitle = "汇报优先：一条主链展示前端、API、编排、服务组、资源与运行时支撑的协作关系"
    image, draw = render_base_png(size, title, subtitle)

    layers = [
        Panel("前端体验层", 70, 150, 2260, 150),
        Panel("API 与契约层", 70, 330, 2260, 150),
        Panel("应用编排层", 70, 510, 2260, 200),
        Panel("服务执行层", 70, 740, 2260, 250),
        Panel("资源 / 运行时层", 70, 1020, 2260, 520),
    ]
    for panel in layers:
        draw_panel_png(draw, panel)

    boxes = [
        Box("FEEntry", "主查询入口\nQueryWorkspace / QueryPanel", 160, 192, 430, 88, fill="#dbeafe", stroke="#2563eb"),
        Box("FERouter", "会话与路由\nWeatherWearSession / AppRouter", 720, 192, 430, 88, fill="#dbeafe", stroke="#2563eb"),
        Box("FEDev", "开发者入口\nTrace / Logs / ModelConfig / MapConfig", 1560, 182, 560, 108, fill="#ede9fe", stroke="#7c3aed"),
        Box("FrontAPI", "前端 API 封装\nshared/api.ts", 930, 372, 300, 88, fill="#fef3c7", stroke="#d97706"),
        Box("Server", "后端入口\nserver.py", 930, 560, 300, 100, fill="#fef3c7", stroke="#d97706"),
        Box("Coordinator", "查询总编排\nMultiAgentCoordinator", 570, 815, 360, 100, fill="#e0e7ff", stroke="#4f46e5"),
        Box("Workflow", "工作流执行\nworkflow.py", 1020, 815, 260, 100, fill="#e0e7ff", stroke="#4f46e5"),
        Box("Presentation", "结果表示层\npresentation.py", 1380, 815, 300, 100, fill="#e0e7ff", stroke="#4f46e5"),
        Box("CityWeather", "解析与天气服务\ncity_resolver.py + weather_service.py", 350, 1110, 500, 118, fill="#dcfce7", stroke="#16a34a"),
        Box("FashionStack", "知识与穿搭服务\nfashion_knowledge.py + fashion_agent.py", 980, 1110, 500, 118, fill="#dcfce7", stroke="#16a34a"),
        Box("RuntimeSupport", "运行时支撑\nhealth_check / llm_support /\nmap_support / observability", 1660, 1088, 470, 162, fill="#dcfce7", stroke="#16a34a"),
        Box("OpenWeather", "OpenWeather", 230, 1368, 270, 88, fill="#fff7ed", stroke="#ea580c"),
        Box("KnowledgeJsonl", "resources/fashion_knowledge/*.jsonl", 590, 1368, 420, 88, fill="#fff7ed", stroke="#ea580c"),
        Box("StateStore", "状态持久化\nuser_state_store.py + runtime_storage.py", 1120, 1358, 440, 108, fill="#fff7ed", stroke="#ea580c"),
        Box("RuntimeFiles", ".runtime/state / .runtime/logs\nhistory.json / favorites.json / app.events.jsonl", 1680, 1348, 520, 128, fill="#fff7ed", stroke="#ea580c"),
    ]
    pos = {box.key: box for box in boxes}
    for box in boxes:
        draw_shadow_box(draw, box)

    arrows = [
        Arrow(((pos["FEEntry"].x + pos["FEEntry"].w, 236), (pos["FERouter"].x, 236)), color="#2563eb"),
        Arrow(((pos["FERouter"].x + pos["FERouter"].w / 2, 280), (pos["FrontAPI"].x + pos["FrontAPI"].w / 2, 372)), color="#2563eb"),
        Arrow(((pos["FrontAPI"].x + pos["FrontAPI"].w / 2, 460), (pos["Server"].x + pos["Server"].w / 2, 560)), color="#d97706"),
        Arrow(((pos["Server"].x + pos["Server"].w / 2, 660), (pos["Workflow"].x + pos["Workflow"].w / 2, 815)), color="#4f46e5"),
        Arrow(((pos["Server"].x + 20, 610), (pos["Coordinator"].x + pos["Coordinator"].w / 2, 815)), color="#4f46e5"),
        Arrow(((pos["Coordinator"].x + pos["Coordinator"].w, 865), (pos["Presentation"].x, 865)), color="#4f46e5"),
        Arrow(((pos["Workflow"].x + 40, 915), (pos["CityWeather"].x + 250, 1110)), color="#16a34a"),
        Arrow(((pos["Workflow"].x + pos["Workflow"].w - 40, 915), (pos["FashionStack"].x + 250, 1110)), color="#16a34a"),
        Arrow(((pos["Presentation"].x + 60, 915), (pos["FERouter"].x + 215, 280)), color="#4f46e5"),
        Arrow(((pos["CityWeather"].x + 80, 1228), (pos["OpenWeather"].x + 130, 1368)), color="#ea580c"),
        Arrow(((pos["FashionStack"].x + 160, 1228), (pos["KnowledgeJsonl"].x + 210, 1368)), color="#ea580c"),
        Arrow(((pos["FashionStack"].x + pos["FashionStack"].w - 80, 1228), (pos["RuntimeSupport"].x + 120, 1168)), color="#16a34a", dashed=True),
        Arrow(((pos["FEDev"].x + 180, 290), (pos["RuntimeSupport"].x + 340, 1088)), color="#7c3aed", dashed=True),
        Arrow(((pos["Server"].x + pos["Server"].w, 610), (pos["StateStore"].x + 120, 1358)), color="#ea580c"),
        Arrow(((pos["RuntimeSupport"].x + 200, 1250), (pos["RuntimeFiles"].x + 200, 1348)), color="#ea580c"),
        Arrow(((pos["StateStore"].x + 320, 1412), (pos["RuntimeFiles"].x, 1412)), color="#ea580c"),
    ]
    for arrow in arrows:
        draw_arrow_png(draw, arrow)

    draw.text((170, 1530), "主调用链：实线", font=font(18), fill=hex_to_rgb("#0f172a"))
    draw.line((300, 1542, 390, 1542), fill=hex_to_rgb("#111827"), width=4)
    draw.text((460, 1530), "支撑依赖：虚线", font=font(18), fill=hex_to_rgb("#0f172a"))
    draw_dashed_line(draw, (610, 1542), (700, 1542), "#16a34a", dash=10, gap=6)
    draw.text((770, 1530), "资源/落盘：橙色", font=font(18), fill=hex_to_rgb("#0f172a"))
    draw.line((955, 1542, 1045, 1542), fill=hex_to_rgb("#ea580c"), width=4)

    svg_parts = []
    for panel in layers:
        svg_parts.append(draw_panel_svg(panel))
    for box in boxes:
        svg_parts.append(draw_shadow_box_svg(box))
    for arrow in arrows:
        svg_parts.append(draw_arrow_svg(arrow))
    svg_parts.append('<text x="170" y="1550" font-size="18" fill="#0f172a" font-family="Microsoft YaHei, Arial, sans-serif">主调用链：实线</text>')
    svg_parts.append('<line x1="300" y1="1542" x2="390" y2="1542" stroke="#111827" stroke-width="4" />')
    svg_parts.append('<text x="460" y="1550" font-size="18" fill="#0f172a" font-family="Microsoft YaHei, Arial, sans-serif">支撑依赖：虚线</text>')
    svg_parts.append('<line x1="610" y1="1542" x2="700" y2="1542" stroke="#16a34a" stroke-width="4" stroke-dasharray="10 6" />')
    svg_parts.append('<text x="770" y="1550" font-size="18" fill="#0f172a" font-family="Microsoft YaHei, Arial, sans-serif">资源/落盘：橙色</text>')
    svg_parts.append('<line x1="955" y1="1542" x2="1045" y2="1542" stroke="#ea580c" stroke-width="4" />')

    image.save(ASSET_DIR / f"{base_name}.png")
    (ASSET_DIR / f"{base_name}.svg").write_text(render_base_svg(size, title, subtitle, "".join(svg_parts)), encoding="utf-8")


def render_module_relationship_v2(base_name: str) -> None:
    size = (2380, 1520)
    title = "WeatherWear 模块关系图（V2）"
    subtitle = "工程接手优先：保留关键代码模块，压缩箭头类型为主调用、落盘链、开发者侧链"
    image, draw = render_base_png(size, title, subtitle)

    panels = [
        Panel("前端入口", 50, 150, 340, 1180),
        Panel("会话与请求", 420, 150, 340, 1180),
        Panel("API 与编排", 790, 150, 420, 1180),
        Panel("领域服务", 1240, 150, 520, 1180),
        Panel("资源与持久化", 1790, 150, 540, 1180),
    ]
    for panel in panels:
        draw_panel_png(draw, panel)

    boxes = [
        Box("AppRouter", "AppRouter", 90, 240, 260, 88, fill="#e0e7ff", stroke="#4f46e5"),
        Box("QueryPanel", "QueryWorkspace / QueryPanel", 90, 392, 260, 104, fill="#dbeafe", stroke="#2563eb"),
        Box("Session", "WeatherWearSession", 460, 320, 260, 88, fill="#dbeafe", stroke="#2563eb"),
        Box("FrontAPI", "shared/api.ts", 460, 500, 260, 88, fill="#fef3c7", stroke="#d97706"),
        Box("Server", "server.py", 865, 240, 270, 88, fill="#fef3c7", stroke="#d97706"),
        Box("Coordinator", "MultiAgentCoordinator", 865, 408, 270, 88, fill="#e0e7ff", stroke="#4f46e5"),
        Box("Workflow", "workflow.py", 865, 576, 270, 88, fill="#e0e7ff", stroke="#4f46e5"),
        Box("Presentation", "presentation.py", 865, 744, 270, 88, fill="#e0e7ff", stroke="#4f46e5"),
        Box("City", "city_resolver.py", 1320, 220, 360, 88, fill="#dcfce7", stroke="#16a34a"),
        Box("Weather", "weather_service.py\nOpenWeather / demo 降级", 1320, 376, 360, 108, fill="#dcfce7", stroke="#16a34a"),
        Box("Knowledge", "fashion_knowledge.py", 1320, 564, 360, 88, fill="#dcfce7", stroke="#16a34a"),
        Box("Fashion", "fashion_agent.py", 1320, 720, 360, 88, fill="#dcfce7", stroke="#16a34a"),
        Box("Jsonl", "resources/fashion_knowledge/*.jsonl", 1860, 240, 400, 88, fill="#fff7ed", stroke="#ea580c"),
        Box("UserStore", "user_state_store.py", 1860, 436, 400, 88, fill="#fff7ed", stroke="#ea580c"),
        Box("RuntimeStore", "runtime_storage.py\n.runtime/state + .runtime/logs", 1860, 612, 400, 104, fill="#fff7ed", stroke="#ea580c"),
        Box("DevChain", "开发者功能链\nTrace / Logs / ModelConfig / MapConfig", 110, 980, 220, 120, fill="#ede9fe", stroke="#7c3aed"),
        Box("RuntimeChain", "运行时支撑链\nhistory / favorites / trace / logs", 1860, 980, 400, 120, fill="#ecfccb", stroke="#65a30d"),
    ]
    pos = {box.key: box for box in boxes}
    for box in boxes:
        draw_shadow_box(draw, box)

    arrows = [
        Arrow(((pos["AppRouter"].x + pos["AppRouter"].w, 284), (pos["QueryPanel"].x + 30, 444)), color="#2563eb"),
        Arrow(((pos["QueryPanel"].x + pos["QueryPanel"].w, 444), (pos["Session"].x, 364)), color="#2563eb"),
        Arrow(((pos["Session"].x + pos["Session"].w / 2, 408), (pos["FrontAPI"].x + pos["FrontAPI"].w / 2, 500)), color="#2563eb"),
        Arrow(((pos["FrontAPI"].x + pos["FrontAPI"].w, 544), (pos["Server"].x, 284)), color="#d97706"),
        Arrow(((pos["Server"].x + pos["Server"].w / 2, 328), (pos["Coordinator"].x + pos["Coordinator"].w / 2, 408)), color="#4f46e5"),
        Arrow(((pos["Coordinator"].x + pos["Coordinator"].w / 2, 496), (pos["Workflow"].x + pos["Workflow"].w / 2, 576)), color="#4f46e5"),
        Arrow(((pos["Coordinator"].x + pos["Coordinator"].w / 2, 496), (pos["Presentation"].x + pos["Presentation"].w / 2, 744)), color="#4f46e5"),
        Arrow(((pos["Presentation"].x, 788), (pos["Session"].x + pos["Session"].w, 364)), color="#4f46e5"),
        Arrow(((pos["Workflow"].x + pos["Workflow"].w, 620), (pos["City"].x, 264)), color="#16a34a"),
        Arrow(((pos["Workflow"].x + pos["Workflow"].w, 620), (pos["Weather"].x, 430)), color="#16a34a"),
        Arrow(((pos["Workflow"].x + pos["Workflow"].w, 620), (pos["Fashion"].x, 764)), color="#16a34a"),
        Arrow(((pos["Fashion"].x, 764), (pos["Knowledge"].x + pos["Knowledge"].w, 608)), color="#16a34a"),
        Arrow(((pos["Knowledge"].x + pos["Knowledge"].w, 608), (pos["Jsonl"].x, 284)), color="#ea580c"),
        Arrow(((pos["Server"].x + pos["Server"].w, 284), (pos["UserStore"].x, 480)), color="#ea580c"),
        Arrow(((pos["UserStore"].x + pos["UserStore"].w / 2, 524), (pos["RuntimeStore"].x + pos["RuntimeStore"].w / 2, 612)), color="#ea580c"),
        Arrow(((pos["Server"].x + pos["Server"].w, 306), (pos["RuntimeStore"].x, 664)), color="#ea580c", dashed=True),
        Arrow(((pos["DevChain"].x + pos["DevChain"].w, 1040), (pos["Session"].x + 20, 380)), color="#7c3aed", dashed=True),
        Arrow(((pos["RuntimeStore"].x + 200, 716), (pos["RuntimeChain"].x + 200, 980)), color="#65a30d"),
        Arrow(((pos["UserStore"].x + 40, 524), (pos["RuntimeChain"].x + 80, 980)), color="#65a30d"),
    ]
    for arrow in arrows:
        draw_arrow_png(draw, arrow)

    draw.text((90, 1360), "图例：蓝/黑=主调用，橙色=资源与落盘，紫虚线=开发者侧链，绿色=运行时结果落盘", font=font(18), fill=hex_to_rgb("#334155"))

    svg_parts = []
    for panel in panels:
        svg_parts.append(draw_panel_svg(panel))
    for box in boxes:
        svg_parts.append(draw_shadow_box_svg(box))
    for arrow in arrows:
        svg_parts.append(draw_arrow_svg(arrow))
    svg_parts.append('<text x="90" y="1385" font-size="18" fill="#334155" font-family="Microsoft YaHei, Arial, sans-serif">图例：蓝/黑=主调用，橙色=资源与落盘，紫虚线=开发者侧链，绿色=运行时结果落盘</text>')

    image.save(ASSET_DIR / f"{base_name}.png")
    (ASSET_DIR / f"{base_name}.svg").write_text(render_base_svg(size, title, subtitle, "".join(svg_parts)), encoding="utf-8")


def render_request_sequence_v3(base_name: str) -> None:
    size = (2320, 1560)
    title = "WeatherWear 请求时序图（V3）"
    subtitle = "主成功链路优先：压缩泳道数量，把 needs_clarification、规则兜底、degraded 收拢为紧凑分支"
    image, draw = render_base_png(size, title, subtitle)

    participants = [
        "用户",
        "QueryPanel / Session",
        "FastAPI / shared/api.ts",
        "Coordinator / workflow",
        "CityResolver + WeatherService",
        "FashionKnowledge + FashionAgent",
        "Presentation / Session UI",
    ]
    xs = [120 + index * 340 for index in range(len(participants))]
    top = 170
    bottom = 1420
    for x, label in zip(xs, participants):
        rounded_rectangle(draw, (x - 110, top, x + 110, top + 64), "#ffffff", "#94a3b8", width=2, radius=14)
        draw_multiline_center(draw, x - 110, top, 220, 64, label, size=18)
        draw_dashed_line(draw, (x, top + 64), (x, bottom), "#cbd5e1", dash=10, gap=8)

    frames = [
        (240, 340, "planner / fast path"),
        (560, 676, "alt strict / needs_clarification"),
        (720, 836, "alt OpenWeather live / demo-degraded"),
        (930, 1048, "alt LLM 可用 / 规则兜底"),
        (1170, 1290, "par 观测写入 / 本地状态写入"),
    ]
    for y1, y2, label in frames:
        rounded_rectangle(draw, (70, y1, 2250, y2), "#f8fafc", "#cbd5e1", width=2, radius=18)
        draw.text((92, y1 + 18), label, font=font(20), fill=hex_to_rgb("#334155"))

    messages = [
        (0, 1, 250, "提交文本或地图点位", "#2563eb", False),
        (1, 1, 292, "组装 QueryRequest", "#475569", False),
        (1, 2, 380, "POST /api/query", "#2563eb", False),
        (2, 2, 422, "生成 request_id / 记录 query.started", "#475569", False),
        (2, 3, 464, "process_query + run_query_workflow", "#2563eb", False),
        (3, 3, 506, "选择 planner 或 fast path", "#7c3aed", False),
        (3, 4, 606, "resolve_city(...)", "#2563eb", False),
        (4, 3, 648, "CityResolutionResult", "#2563eb", True),
        (3, 6, 692, "若需澄清：返回 clarification view_model", "#7c3aed", False),
        (6, 1, 732, "展示候选确认与提示", "#7c3aed", True),
        (3, 4, 782, "fetch_weather(city / coords)", "#2563eb", False),
        (4, 3, 824, "WeatherResult(live / demo)", "#2563eb", True),
        (3, 5, 972, "retrieve_knowledge + get_fashion_advice", "#2563eb", False),
        (5, 3, 1014, "KnowledgeHit[] + FashionAdviceResult", "#2563eb", True),
        (3, 6, 1088, "build_result_view_model", "#2563eb", False),
        (6, 2, 1130, "返回 QueryResponse(view_model)", "#2563eb", True),
        (1, 1, 1168, "更新结果 / 历史 / 收藏 / notice", "#475569", False),
        (2, 2, 1224, "写 trace / logs / app.events.jsonl", "#16a34a", False),
        (1, 1, 1264, "写 sessionStorage / localStorage", "#f97316", False),
    ]

    def lane_arrow(index_from: int, index_to: int, y: int, color: str, dashed: bool) -> Arrow:
        return Arrow(((xs[index_from], y), (xs[index_to], y)), color=color, dashed=dashed)

    svg_parts = []
    for x, label in zip(xs, participants):
        svg_parts.append(f'<rect x="{x - 110}" y="{top}" rx="14" ry="14" width="220" height="64" fill="#ffffff" stroke="#94a3b8" stroke-width="2" />')
        svg_parts.append(svg_text(wrap_svg_text(label, 190, 18), x - 110, top, 220, 64, size=18))
        svg_parts.append(f'<line x1="{x}" y1="{top + 64}" x2="{x}" y2="{bottom}" stroke="#cbd5e1" stroke-width="3" stroke-dasharray="10 8" />')
    for y1, y2, label in frames:
        svg_parts.append(f'<rect x="70" y="{y1}" rx="18" ry="18" width="2180" height="{y2 - y1}" fill="#f8fafc" stroke="#cbd5e1" stroke-width="2" />')
        svg_parts.append(f'<text x="92" y="{y1 + 38}" font-size="20" fill="#334155" font-family="Microsoft YaHei, Arial, sans-serif">{html.escape(label)}</text>')
    for index_from, index_to, y, text, color, dashed in messages:
        arrow = lane_arrow(index_from, index_to, y, color, dashed)
        draw_arrow_png(draw, arrow)
        label_x = min(xs[index_from], xs[index_to]) + 10
        draw.text((label_x, y - 24), text, font=font(16), fill=hex_to_rgb("#334155"))
        svg_parts.append(draw_arrow_svg(arrow))
        svg_parts.append(f'<text x="{label_x}" y="{y - 8}" font-size="16" fill="#334155" font-family="Microsoft YaHei, Arial, sans-serif">{html.escape(text)}</text>')

    image.save(ASSET_DIR / f"{base_name}.png")
    (ASSET_DIR / f"{base_name}.svg").write_text(render_base_svg(size, title, subtitle, "".join(svg_parts)), encoding="utf-8")


def render_data_flow_v3(base_name: str) -> None:
    size = (2320, 1460)
    title = "WeatherWear 数据流转过程图（V3）"
    subtitle = "对象变形优先：保持一条主链，把外部依赖统一放入数据源池，把消费端收拢到结果下游"
    image, draw = render_base_png(size, title, subtitle)

    steps = [
        Box("Input", "输入采集\nquery_text / selected_coords /\nconfirmation_mode / locale", 90, 310, 320, 140, fill="#dbeafe", stroke="#2563eb"),
        Box("Request", "请求载荷\nQueryRequest", 490, 326, 260, 108, fill="#fef3c7", stroke="#d97706"),
        Box("State", "编排状态\nQueryState / QueryPlan", 830, 316, 300, 128, fill="#e0e7ff", stroke="#4f46e5"),
        Box("Domain", "领域结果\nCityResolutionResult\nWeatherResult\nKnowledgeHit[]\nFashionAdviceResult", 1210, 266, 360, 228, fill="#dcfce7", stroke="#16a34a"),
        Box("Result", "结果模型\nCoordinatorResult -> view_model", 1650, 326, 360, 108, fill="#dbeafe", stroke="#2563eb"),
    ]
    sources = [
        Box("WeatherSource", "OpenWeather API", 220, 760, 250, 88, fill="#fff7ed", stroke="#ea580c"),
        Box("Jsonl", "resources/fashion_knowledge/*.jsonl", 640, 760, 340, 88, fill="#fff7ed", stroke="#ea580c"),
        Box("ModelConfig", "LLM config / Embedding", 1120, 760, 300, 88, fill="#fff7ed", stroke="#ea580c"),
        Box("MapConfig", "Map config", 1490, 760, 220, 88, fill="#fff7ed", stroke="#ea580c"),
    ]
    consumers = [
        Box("UI", "UI 渲染\n结果页 / 候选确认 / 提示", 1500, 1040, 260, 110, fill="#ecfccb", stroke="#65a30d"),
        Box("Debug", "调试面板\nTrace / Logs / ModelConfig / MapConfig", 1810, 1026, 380, 138, fill="#ecfccb", stroke="#65a30d"),
        Box("History", "history.json", 1490, 1240, 220, 88, fill="#fff7ed", stroke="#ea580c"),
        Box("Favorites", "favorites.json", 1760, 1240, 220, 88, fill="#fff7ed", stroke="#ea580c"),
        Box("Events", "app.events.jsonl", 2030, 1240, 220, 88, fill="#fff7ed", stroke="#ea580c"),
    ]
    for box in steps + sources + consumers:
        draw_shadow_box(draw, box)
    pos = {box.key: box for box in steps + sources + consumers}

    arrows = [
        Arrow(((410, 380), (490, 380)), color="#111827"),
        Arrow(((750, 380), (830, 380)), color="#111827"),
        Arrow(((1130, 380), (1210, 380)), color="#111827"),
        Arrow(((1570, 380), (1650, 380)), color="#111827"),
        Arrow(((pos["State"].x + 150, 444), (pos["WeatherSource"].x + 125, 760)), color="#ea580c", dashed=True),
        Arrow(((pos["Domain"].x - 20, 420), (pos["Jsonl"].x + 170, 760)), color="#ea580c", dashed=True),
        Arrow(((pos["Domain"].x + 180, 494), (pos["ModelConfig"].x + 150, 760)), color="#ea580c", dashed=True),
        Arrow(((pos["Result"].x + 280, 434), (pos["MapConfig"].x + 110, 760)), color="#ea580c", dashed=True),
        Arrow(((pos["Result"].x + 180, 434), (pos["UI"].x + 130, 1040)), color="#65a30d"),
        Arrow(((pos["Result"].x + 250, 434), (pos["Debug"].x + 150, 1026)), color="#65a30d"),
        Arrow(((pos["Result"].x + 70, 434), (pos["History"].x + 110, 1240)), color="#ea580c"),
        Arrow(((pos["Result"].x + 170, 434), (pos["Favorites"].x + 110, 1240)), color="#ea580c"),
        Arrow(((pos["State"].x + 250, 444), (pos["Events"].x + 110, 1240)), color="#ea580c", dashed=True),
        Arrow(((pos["Result"].x + 320, 410), (pos["Events"].x + 110, 1240)), color="#ea580c"),
    ]
    labels = [
        (520, 352, "构造 QueryRequest"),
        (870, 352, "进入编排"),
        (1245, 352, "计算领域结果"),
        (1710, 352, "聚合为 view_model"),
        (370, 732, "天气数据"),
        (770, 732, "知识库命中"),
        (1180, 732, "模型/检索配置"),
        (1545, 732, "地图配置"),
        (1600, 994, "页面消费"),
        (1860, 994, "调试消费"),
    ]
    for arrow in arrows:
        draw_arrow_png(draw, arrow)
    for x, y, text in labels:
        draw.text((x, y), text, font=font(16), fill=hex_to_rgb("#334155"))
    draw.text((120, 640), "数据源池", font=font(22), fill=hex_to_rgb("#0f172a"))
    draw.text((1460, 950), "结果消费与持久化", font=font(22), fill=hex_to_rgb("#0f172a"))

    svg_parts = []
    for box in steps + sources + consumers:
        svg_parts.append(draw_shadow_box_svg(box))
    for arrow in arrows:
        svg_parts.append(draw_arrow_svg(arrow))
    for x, y, text in labels:
        svg_parts.append(f'<text x="{x}" y="{y}" font-size="16" fill="#334155" font-family="Microsoft YaHei, Arial, sans-serif">{html.escape(text)}</text>')
    svg_parts.append('<text x="120" y="640" font-size="22" fill="#0f172a" font-family="Microsoft YaHei, Arial, sans-serif">数据源池</text>')
    svg_parts.append('<text x="1460" y="950" font-size="22" fill="#0f172a" font-family="Microsoft YaHei, Arial, sans-serif">结果消费与持久化</text>')

    image.save(ASSET_DIR / f"{base_name}.png")
    (ASSET_DIR / f"{base_name}.svg").write_text(render_base_svg(size, title, subtitle, "".join(svg_parts)), encoding="utf-8")


def render_if_missing(base_name: str, renderer) -> None:
    png_path = ASSET_DIR / f"{base_name}.png"
    svg_path = ASSET_DIR / f"{base_name}.svg"
    if png_path.exists() and svg_path.exists():
        return
    renderer(base_name)


def main() -> None:
    ensure_dirs()
    write_mermaid_sources()
    write_v2_mermaid_sources()
    write_v3_mermaid_sources()

    module_size, module_panels, module_boxes, module_arrows, module_title, module_subtitle = build_module_diagram()
    render_if_missing(
        "module-relationship",
        lambda base_name: render_module_or_data(module_size, module_title, module_subtitle, module_panels, module_boxes, module_arrows, base_name),
    )

    data_size, data_panels, data_boxes, data_arrows, data_title, data_subtitle = build_data_flow_diagram()
    render_if_missing(
        "data-flow",
        lambda base_name: render_module_or_data(data_size, data_title, data_subtitle, data_panels, data_boxes, data_arrows, base_name),
    )

    render_if_missing("request-sequence", render_sequence)
    render_if_missing("architecture-layered-v2", render_architecture_layered_v2)
    render_if_missing("request-sequence-v2", render_request_sequence_v2)
    render_if_missing("data-flow-v2", render_data_flow_v2)
    render_architecture_layered_v3("architecture-layered-v3")
    render_module_relationship_v2("module-relationship-v2")
    render_request_sequence_v3("request-sequence-v3")
    render_data_flow_v3("data-flow-v3")
    print(f"Generated Mermaid sources in: {MERMAID_DIR}")
    print(f"Generated images in: {ASSET_DIR}")


if __name__ == "__main__":
    main()
