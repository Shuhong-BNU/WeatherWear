from __future__ import annotations

from dataclasses import asdict

from weather import Weather

IMPORT_ERROR = None

try:
    from fastmcp import FastMCP
except Exception as exc:  # pragma: no cover - 依赖缺失时仅在运行时提示
    FastMCP = None
    IMPORT_ERROR = exc


if FastMCP is not None:
    mcp = FastMCP("WeatherServer")

    @mcp.tool()
    def query_weather(city_name: str):
        """查询城市天气（结构化结果）。"""
        weather = Weather()
        return asdict(weather.get_weather_by_query(city_name))

    @mcp.tool()
    def get_weather_details(city_name: str):
        """获取城市天气详情。"""
        weather = Weather()
        return asdict(weather.get_weather_by_query(city_name))

    @mcp.tool()
    def get_weather_by_coords(lat: float, lon: float, lang: str = "zh_cn"):
        """通过经纬度查询天气。"""
        weather = Weather()
        return asdict(weather.get_weather_by_coords(lat, lon, lang=lang))

    @mcp.resource("info://capabilities")
    def get_capabilities() -> str:
        return """服务器能力列表：

天气查询能力：
- query_weather(city_name): 查询城市天气（结构化结果）
- get_weather_details(city_name): 获取详细天气结果
- get_weather_by_coords(lat, lon, lang): 通过经纬度查询天气
"""

    @mcp.prompt()
    def weather_helper() -> str:
        return """你是一个天气查询助手。请优先使用结构化天气工具，不要编造天气结果。"""


if __name__ == "__main__":
    if FastMCP is None or IMPORT_ERROR is not None:
        raise SystemExit(f"❌ 无法启动 weather_mcp.py：未安装或无法导入 fastmcp。错误: {IMPORT_ERROR}")
    mcp.run()
