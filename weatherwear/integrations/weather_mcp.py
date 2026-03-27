from __future__ import annotations

from dataclasses import asdict

from weatherwear.services.weather_service import Weather

IMPORT_ERROR = None

try:
    from fastmcp import FastMCP
except Exception as exc:  # pragma: no cover - 仅在缺少可选依赖时提示
    FastMCP = None
    IMPORT_ERROR = exc


if FastMCP is not None:
    mcp = FastMCP("WeatherWearWeatherServer")

    @mcp.tool()
    def query_weather(city_name: str):
        """查询城市天气，返回结构化结果。"""
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
        return """WeatherWear MCP 可选扩展能力：

- query_weather(city_name): 查询城市天气
- get_weather_details(city_name): 获取天气详情
- get_weather_by_coords(lat, lon, lang): 通过坐标查询天气
"""

    @mcp.prompt()
    def weather_helper() -> str:
        return "你是天气工具助手。请优先使用结构化天气工具，不要编造天气结果。"


if __name__ == "__main__":
    if FastMCP is None or IMPORT_ERROR is not None:
        raise SystemExit(
            f"无法启动 weather_mcp.py：未安装或无法导入 fastmcp。错误：{IMPORT_ERROR}"
        )
    mcp.run()
