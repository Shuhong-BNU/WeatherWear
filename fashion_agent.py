from __future__ import annotations

import re

from app_types import FashionAdviceResult, WeatherResult
from common_utils import compact_text
from llm_support import run_agent


FASHION_SYSTEM_PROMPT = """你是一位专业时尚顾问，专门根据结构化天气数据提供实用、清晰的中文穿衣建议。
要求：
1. 必须同时参考当前温度、体感温度、今日最高温、今日最低温、全天温差、天气现象、湿度和风速。
2. 输出必须包含两个核心部分：`分时段建议` 和 `分层建议`。
3. `分时段建议` 至少覆盖：早晨、白天、晚上。
4. `分层建议` 至少覆盖：内层、中层、外层、可随身携带的增减层。
5. 还要补充鞋子/配饰与特别提醒。
6. 语言自然、具体，不要解释你的推理过程。"""


SECTION_HEADERS = {
    "time_of_day_advice": "分时段建议",
    "layering_advice": "分层建议",
}


class FashionAgent:
    """穿衣建议智能体，优先调用 LangChain LLM，失败时使用规则兜底。"""

    def __init__(self, name: str = "FashionAgent"):
        self.name = name

    def _build_prompt(self, weather_result: WeatherResult) -> str:
        return f"""请根据以下结构化天气信息生成穿衣建议：
- 城市: {weather_result.city}
- 国家/地区: {weather_result.country}
- 当前温度: {weather_result.temperature}{weather_result.temperature_unit}
- 体感温度: {weather_result.feels_like}{weather_result.temperature_unit}
- 今日最低温: {weather_result.temp_min}{weather_result.temperature_unit}
- 今日最高温: {weather_result.temp_max}{weather_result.temperature_unit}
- 今日温度范围: {weather_result.daily_range_text or "未知"}
- 天气状况: {weather_result.description}
- 湿度: {weather_result.humidity}%
- 风速: {weather_result.wind_speed} {weather_result.wind_unit}
- 天气数据时间: {weather_result.observed_at_local or weather_result.observed_at}
- 城市当地时间: {weather_result.city_local_time}

请严格按下面结构回答：
### 分时段建议
- 早晨：
- 白天：
- 晚上：

### 分层建议
- 内层：
- 中层：
- 外层：
- 携带建议：

### 鞋子与配饰

### 特别提醒
"""

    def _temp_band(self, temperature: float) -> tuple[str, str, str]:
        if temperature >= 30:
            return ("速干或透气短袖", "可不加中层，空调环境备薄衫", "防晒外套或超薄衬衫")
        if temperature >= 24:
            return ("轻薄短袖或薄衬衫", "轻薄针织开衫或薄卫衣", "防晒衫或薄外套")
        if temperature >= 18:
            return ("长袖 T 恤或衬衫", "薄针织或卫衣", "轻夹克或薄风衣")
        if temperature >= 10:
            return ("保暖打底或长袖内搭", "毛衣、抓绒或厚卫衣", "风衣、夹克或薄羽绒")
        return ("保暖内衣或高领打底", "厚毛衣、抓绒或羊毛中层", "羽绒服、厚棉服或呢大衣")

    def _choose_shoes_and_accessories(self, weather_result: WeatherResult) -> tuple[str, str]:
        condition = weather_result.description or ""
        temp_floor = weather_result.temp_min if weather_result.temp_min is not None else weather_result.temperature
        temp_floor = temp_floor if temp_floor is not None else 15

        if temp_floor <= 5:
            shoes = "加绒短靴、保暖运动鞋或防滑靴，搭配厚袜子。"
            accessories = "建议围巾、保暖帽和手套一起准备，早晚更实用。"
        elif temp_floor <= 15:
            shoes = "包裹性较好的运动鞋、乐福鞋或短靴，必要时配中厚袜。"
            accessories = "可带轻围巾或薄披肩，方便应对温差。"
        else:
            shoes = "透气运动鞋、休闲鞋或乐福鞋，兼顾舒适和活动性。"
            accessories = "以轻便为主，晴天可带帽子或太阳镜。"

        if "雨" in condition:
            shoes += " 有雨时优先选防水鞋面。"
            accessories += " 记得带伞。"
        if "雪" in condition:
            shoes += " 雪天优先防滑鞋底。"
            accessories += " 增加围巾和手套，注意防滑。"
        if "风" in condition:
            accessories += " 风大时建议增加防风层。"
        return shoes, accessories

    def _special_notes(self, weather_result: WeatherResult, range_delta: float) -> str:
        notes: list[str] = []
        condition = weather_result.description or ""

        if range_delta >= 8:
            notes.append("今天昼夜温差明显，建议采用洋葱式穿法，并随身带一层可脱卸外套。")
        if weather_result.feels_like is not None and weather_result.temperature is not None:
            if weather_result.feels_like <= weather_result.temperature - 2:
                notes.append("体感温度明显低于实际温度，保暖要按体感来。")
        if weather_result.humidity is not None and weather_result.humidity >= 80:
            notes.append("湿度较高，体感会更阴冷，鞋袜和外层尽量选择干爽材质。")
        if weather_result.wind_speed is not None and weather_result.wind_speed >= 6:
            notes.append("风速偏大，外层优先考虑防风款式。")
        if "晴" in condition and weather_result.temp_max is not None and weather_result.temp_max >= 24:
            notes.append("白天晴朗偏暖，中午前后可以适当减一层，避免闷热。")
        if not notes:
            notes.append("整体以舒适、可增减、方便通勤和活动为主。")
        return " ".join(notes)

    def _build_rule_based_advice(self, weather_result: WeatherResult) -> tuple[str, str, str]:
        current_temp = weather_result.temperature if weather_result.temperature is not None else 20.0
        temp_min = weather_result.temp_min if weather_result.temp_min is not None else current_temp
        temp_max = weather_result.temp_max if weather_result.temp_max is not None else current_temp
        range_delta = round(temp_max - temp_min, 1)

        morning_inner, morning_mid, morning_outer = self._temp_band(temp_min)
        day_inner, _, day_outer = self._temp_band(max(current_temp, temp_max))
        evening_inner, evening_mid, evening_outer = self._temp_band(temp_min + min(range_delta, 2))

        time_of_day_advice = (
            f"- 早晨：建议以 {morning_inner} + {morning_mid} + {morning_outer} 为主，先保暖再出门。\n"
            f"- 白天：以 {day_inner} 为主，保留 {day_outer} 作为可脱卸层，偏热时可以减一层。\n"
            f"- 晚上：回落到 {temp_min}{weather_result.temperature_unit} 左右时，建议重新加回 {evening_mid} 或 {evening_outer}。"
        )

        carry_note = "建议随身带一件可脱卸外层。" if range_delta >= 6 else "全天温差不算大，可按当前温度为主来穿。"
        layering_advice = (
            f"- 内层：{morning_inner}。\n"
            f"- 中层：{morning_mid}。\n"
            f"- 外层：{morning_outer}。\n"
            f"- 携带建议：{carry_note}"
        )

        shoes, accessories = self._choose_shoes_and_accessories(weather_result)
        notes = self._special_notes(weather_result, range_delta)
        advice_text = (
            "### 分时段建议\n"
            f"{time_of_day_advice}\n\n"
            "### 分层建议\n"
            f"{layering_advice}\n\n"
            "### 鞋子与配饰\n"
            f"- 鞋子：{shoes}\n"
            f"- 配饰：{accessories}\n\n"
            "### 特别提醒\n"
            f"- 当前温度为 {current_temp}{weather_result.temperature_unit}，今日范围约 {temp_min}{weather_result.temperature_unit} ~ {temp_max}{weather_result.temperature_unit}。\n"
            f"- {notes}"
        )
        return advice_text, time_of_day_advice, layering_advice

    def _extract_section(self, text: str, header: str) -> str:
        pattern = re.compile(
            rf"(?:^|\n)#+\s*{re.escape(header)}\s*\n(.*?)(?=\n#+\s*[\u4e00-\u9fffA-Za-z].*|\Z)",
            flags=re.DOTALL,
        )
        match = pattern.search(text)
        return match.group(1).strip() if match else ""

    def get_rule_based_fashion_advice(self, weather_result: WeatherResult) -> FashionAdviceResult:
        advice_text, time_of_day_advice, layering_advice = self._build_rule_based_advice(weather_result)
        return FashionAdviceResult(
            advice_text=advice_text,
            time_of_day_advice=time_of_day_advice,
            layering_advice=layering_advice,
            used_llm=False,
            fallback_used=True,
            source="rule_based_fashion",
        )

    def get_fashion_advice(self, weather_result: WeatherResult) -> FashionAdviceResult:
        prompt = self._build_prompt(weather_result)
        output, record = run_agent(
            role="穿衣建议智能体",
            name=self.name,
            system_prompt=FASHION_SYSTEM_PROMPT,
            prompt=prompt,
        )
        record.node_name = "generate_outfit"
        record.decision_reason = "weather_to_outfit_generation"
        if record.success and output:
            return FashionAdviceResult(
                advice_text=output,
                time_of_day_advice=self._extract_section(output, SECTION_HEADERS["time_of_day_advice"]),
                layering_advice=self._extract_section(output, SECTION_HEADERS["layering_advice"]),
                used_llm=True,
                fallback_used=False,
                source="langchain_llm",
                execution_records=[record],
            )

        fallback = self.get_rule_based_fashion_advice(weather_result)
        fallback.error = record.error
        fallback.execution_records.append(record)
        return fallback

    def summarize_for_trace(self, advice_result: FashionAdviceResult) -> str:
        return compact_text(advice_result.advice_text)


def main():
    test_weather = WeatherResult(
        ok=True,
        city="Shanghai",
        country="China",
        temperature=25,
        feels_like=26,
        temp_min=20,
        temp_max=29,
        description="晴天",
        humidity=60,
        wind_speed=3,
        daily_range_text="20°C ~ 29°C",
    )
    fashion_agent = FashionAgent()
    result = fashion_agent.get_fashion_advice(test_weather)
    print(result.advice_text)


if __name__ == "__main__":
    main()
