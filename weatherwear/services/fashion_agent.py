from __future__ import annotations

import re
from typing import Any

from weatherwear.domain.types import ExecutionRecord, FashionAdviceResult, KnowledgeHit, WeatherResult
from weatherwear.services.fashion_knowledge import retrieve_knowledge_hits
from weatherwear.support.common_utils import compact_text
from weatherwear.support.llm_support import run_agent


def _is_english(locale: str) -> bool:
    return str(locale).lower().startswith("en")


def _msg(locale: str, zh_text: str, en_text: str) -> str:
    return en_text if _is_english(locale) else zh_text


def _headers(locale: str) -> dict[str, str]:
    if _is_english(locale):
        return {
            "headline": "Today's advice",
            "factors": "Why this advice",
            "time": "Time-of-day plan",
            "layering": "Upper-body layering",
            "bottoms": "Bottoms",
            "shoes": "Shoes and accessories",
            "notes": "Extra notes",
        }
    return {
        "headline": "今日建议",
        "factors": "主导因素",
        "time": "分时段建议",
        "layering": "上装分层",
        "bottoms": "下装建议",
        "shoes": "鞋子与配饰",
        "notes": "结果补充",
    }


FASHION_SYSTEM_PROMPT_ZH = """你是一位实用型穿搭顾问。请基于天气事实、场合和检索到的穿搭知识，输出自然、简洁、可执行的中文建议。
要求：
1. 全文只能使用中文。
2. 建议必须体现主导因素，而不是复述全部天气指标。
3. 必须覆盖：今日建议、主导因素、分时段建议、上装分层、下装建议、鞋子与配饰、结果补充。
4. 下装建议必须明确回答裤装/裙装/打底/材质/厚薄中至少两个点。
5. 性别只影响示例单品，不要产生刻板限制。
6. 文风保持平衡型：有信息量，但不要像天气播报。"""


FASHION_SYSTEM_PROMPT_EN = """You are a practical outfit advisor. Use weather facts, occasion context, and retrieved outfit knowledge to produce concise, useful English guidance.
Requirements:
1. English only.
2. Emphasize the few dominant decision factors instead of repeating every metric.
3. Must cover: Today's advice, Why this advice, Time-of-day plan, Upper-body layering, Bottoms, Shoes and accessories, Extra notes.
4. The Bottoms section must clearly address at least two of these: pants/skirt choice, base layer, fabric, thickness, weather limitations.
5. Gender affects example items only, not weather logic.
6. Keep the tone balanced and product-ready, not like a weather bulletin."""


class FashionAgent:
    def __init__(self, name: str = "FashionAgent"):
        self.name = name

    def _guidance_items(self, knowledge_hits: list[KnowledgeHit], key: str) -> list[str]:
        items: list[str] = []
        for hit in knowledge_hits:
            guidance = hit.guidance if isinstance(hit.guidance, dict) else {}
            raw_value = guidance.get(key)
            if isinstance(raw_value, list):
                for value in raw_value:
                    text = str(value).strip()
                    if text and text not in items:
                        items.append(text)
            elif isinstance(raw_value, str):
                text = raw_value.strip()
                if text and text not in items:
                    items.append(text)
        return items

    def _language_mismatch(self, text: str, locale: str) -> bool:
        if not text:
            return False
        has_cjk = bool(re.search(r"[\u4e00-\u9fff]", text))
        english_word_count = len(re.findall(r"[A-Za-z]{3,}", text))
        if _is_english(locale):
            return has_cjk
        return not has_cjk and english_word_count >= 10

    def _normalize_query_context(self, query_context: str | dict[str, Any] | None) -> dict[str, Any]:
        if isinstance(query_context, dict):
            return {
                "query_text": str(query_context.get("query_text", "") or ""),
                "gender": str(query_context.get("gender", "neutral") or "neutral"),
                "occasion_text": str(query_context.get("occasion_text", "") or ""),
                "occasion_tags": list(query_context.get("occasion_tags", []) or []),
                "primary_scene": str(query_context.get("primary_scene", "") or ""),
                "context_tags": list(query_context.get("context_tags", []) or []),
                "target_date": str(query_context.get("target_date", "") or ""),
            }
        return {
            "query_text": str(query_context or ""),
            "gender": "neutral",
            "occasion_text": "",
            "occasion_tags": [],
            "primary_scene": "",
            "context_tags": [],
            "target_date": "",
        }

    def _format_condition(self, weather_result: WeatherResult, locale: str) -> str:
        condition = weather_result.description or ""
        return condition or (_msg(locale, "待查询", "Waiting for weather"))

    def _build_decision_factors(
        self,
        weather_result: WeatherResult,
        locale: str,
        knowledge_hits: list[KnowledgeHit],
    ) -> list[str]:
        factors: list[str] = self._guidance_items(knowledge_hits, "dominant_factors")
        unit = weather_result.temperature_unit or "°C"
        if weather_result.feels_like is not None:
            factors.append(
                _msg(
                    locale,
                    f"体感温度约 {round(weather_result.feels_like, 1)}{unit}，优先按体感而不是名义温度穿衣。",
                    f"Feels-like temperature is around {round(weather_result.feels_like, 1)}{unit}, so dress for feel rather than the raw reading.",
                )
            )
        if weather_result.wind_speed is not None and weather_result.wind_speed >= 5:
            factors.append(
                _msg(
                    locale,
                    f"风速约 {round(weather_result.wind_speed, 1)} {weather_result.wind_unit}，外层需要更防风。",
                    f"Wind is about {round(weather_result.wind_speed, 1)} {weather_result.wind_unit}, so the outer layer should block wind better.",
                )
            )
        if weather_result.humidity is not None and weather_result.humidity >= 80:
            factors.append(
                _msg(
                    locale,
                    f"湿度约 {weather_result.humidity}%，潮湿感会放大凉意，材质应偏干爽。",
                    f"Humidity is about {weather_result.humidity}%, so dry-feeling fabrics will usually be more comfortable.",
                )
            )
        condition = (weather_result.description or "").lower()
        if "rain" in condition or "雨" in condition:
            factors.append(
                _msg(
                    locale,
                    "有降雨信号，鞋面和外层要兼顾防水。",
                    "Rain is in play, so the outer layer and shoes should handle light moisture.",
                )
            )
        if weather_result.temp_max is not None and weather_result.temp_min is not None and weather_result.temp_max - weather_result.temp_min >= 8:
            factors.append(
                _msg(
                    locale,
                    f"日内温差约 {round(weather_result.temp_max - weather_result.temp_min, 1)}{unit}，适合可增减的分层穿法。",
                    f"The day swings by about {round(weather_result.temp_max - weather_result.temp_min, 1)}{unit}, so adjustable layers work best.",
                )
            )
        for hit in knowledge_hits[:2]:
            if hit.short_reason and hit.short_reason not in factors:
                factors.append(hit.short_reason)
        return factors[:3]

    def _bottomwear_options(
        self,
        weather_result: WeatherResult,
        locale: str,
        gender: str,
        knowledge_hits: list[KnowledgeHit],
    ) -> list[str]:
        low = weather_result.temp_min if weather_result.temp_min is not None else weather_result.temperature or 18.0
        condition = (weather_result.description or "").lower()
        options: list[str] = self._guidance_items(knowledge_hits, "bottomwear")
        if low <= 8:
            options.append(_msg(locale, "优先长裤，必要时加薄打底或保暖袜。", "Go with full-length pants, and add a thin base layer or warmer socks if needed."))
        elif low <= 18:
            options.append(_msg(locale, "长裤最稳妥；若想穿裙装，建议配打底或长靴。", "Full-length pants are safest; if you prefer a skirt, pair it with tights or taller boots."))
        else:
            options.append(_msg(locale, "轻薄长裤、休闲裤或顺滑面料裙装都可行。", "Light trousers, casual pants, or lighter skirts can all work here."))

        if "rain" in condition or "雨" in condition:
            options.append(_msg(locale, "雨天尽量避免拖地裤脚和易吸水裙摆。", "For rain, avoid hems that drag and fabrics that soak up water easily."))
        if weather_result.wind_speed is not None and weather_result.wind_speed >= 6:
            options.append(_msg(locale, "风大时裤装更省心；裙装建议选更有垂感或搭配打底。", "With stronger wind, pants are easier; if you wear a skirt, choose one with weight or add tights."))
        if gender == "female":
            options.append(_msg(locale, "如果追求更精致的搭配，可在不冷不湿的前提下考虑中长裙。", "If you want a dressier option, a midi skirt works when it is not too cold or wet."))
        elif gender == "male":
            options.append(_msg(locale, "裤型可在直筒、休闲西裤和轻薄工装裤之间选更合场景的一种。", "Choose between straight trousers, casual slacks, or light utility pants depending on the setting."))
        else:
            options.append(_msg(locale, "如果不限定风格，可在裤装和裙装之间按活动量与风雨情况二选一。", "If style is open, decide between pants and skirts based on activity level and wind or rain." ))
        return list(dict.fromkeys(options))[:3]

    def _occasion_adjustments(
        self,
        locale: str,
        occasion_text: str,
        occasion_tags: list[str],
        knowledge_hits: list[KnowledgeHit],
    ) -> list[str]:
        tags = set(occasion_tags)
        text = occasion_text.strip()
        notes: list[str] = self._guidance_items(knowledge_hits, "occasion_adjustments")
        if "work" in tags:
            notes.append(_msg(locale, "优先整洁、通勤友好的单品，室内空调场景可备一层可脱外搭。", "Prioritize neat commuting pieces, and keep one removable layer for office AC."))
        if "date" in tags:
            notes.append(_msg(locale, "在舒适基础上保留一点精致感，避免为了造型牺牲体感。", "Keep a polished touch, but do not trade comfort away just for styling."))
        if "friends" in tags:
            notes.append(_msg(locale, "以轻松好活动为主，留给走动和久坐都舒服的搭配。", "Keep it relaxed and easy to move in, comfortable for both walking and sitting."))
        if "home" in tags:
            notes.append(_msg(locale, "居家场景可把结构感降一点，优先柔软和温感稳定。", "At home, reduce structure and favor soft, temperature-stable pieces."))
        if "exercise" in tags:
            notes.append(_msg(locale, "运动场景优先透气、排汗、弹性和鞋底支撑。", "For exercise, prioritize breathability, sweat handling, stretch, and shoe support."))
        if "walking" in tags:
            notes.append(_msg(locale, "需要走很多路时，鞋子和下装的活动自由度要优先于装饰性。", "If you will walk a lot, prioritize footwear support and freedom of movement over decorative styling."))
        if not notes and text:
            notes.append(_msg(locale, f"结合场合“{text}”，建议保持舒适与体面之间的平衡。", f"For “{text}”, keep the outfit balanced between comfort and looking put together."))
        return list(dict.fromkeys(notes))[:2]

    def _knowledge_application_mode(self, knowledge_hits: list[KnowledgeHit]) -> str:
        return "matched" if knowledge_hits else "no_match"

    def _apply_knowledge_record(self, locale: str, knowledge_hits: list[KnowledgeHit], factors: list[str], bottomwear: list[str], occasion_notes: list[str]) -> ExecutionRecord:
        return ExecutionRecord(
            role=_msg(locale, "知识应用", "Knowledge application"),
            name="FashionKnowledgeApplier",
            node_name="apply_knowledge",
            step_kind="apply_knowledge",
            provider="hybrid_retrieval",
            success=True,
            used_llm=False,
            fallback_used=False,
            input_summary=compact_text(", ".join(hit.label for hit in knowledge_hits), max_len=160),
            output_summary=compact_text(" | ".join(factors[:2] + bottomwear[:1] + occasion_notes[:1]), max_len=180),
            metadata={
                "knowledge_hit_count": len(knowledge_hits),
                "dominant_factors": factors,
                "bottomwear_guidance": bottomwear,
                "occasion_adjustments": occasion_notes,
            },
        )

    def _build_llm_prompt(
        self,
        weather_result: WeatherResult,
        locale: str,
        query_context: dict[str, Any],
        knowledge_hits: list[KnowledgeHit],
        dominant_factors: list[str],
        bottomwear_guidance: list[str],
        occasion_adjustments: list[str],
    ) -> str:
        headers = _headers(locale)
        knowledge_lines = "\n".join(
            f"- [{hit.category or 'general'}] {hit.label}: {hit.body}"
            for hit in knowledge_hits[:4]
        ) or "- none"
        dayparts = "\n".join(
            f"- {item.get('label')}: {item.get('temperature')} / {item.get('condition')}"
            for item in weather_result.daypart_summaries
        ) or "- none"
        factors = "\n".join(f"- {item}" for item in dominant_factors)
        bottoms = "\n".join(f"- {item}" for item in bottomwear_guidance)
        occasion = "\n".join(f"- {item}" for item in occasion_adjustments) or "- none"
        gender_hint = {"male": _msg(locale, "男性化示例", "male examples"), "female": _msg(locale, "女性化示例", "female examples"), "neutral": _msg(locale, "中性表达", "neutral examples")}.get(query_context["gender"], "neutral")
        return f"""
Weather facts:
- Location: {weather_result.city}, {weather_result.country}
- Target date: {query_context.get('target_date') or weather_result.forecast_date or weather_result.city_local_time[:10]}
- Forecast mode: {weather_result.forecast_mode or 'current'}
- Condition: {self._format_condition(weather_result, locale)}
- Current/representative temp: {weather_result.temperature}{weather_result.temperature_unit}
- Feels like: {weather_result.feels_like}{weather_result.temperature_unit}
- Daily low/high: {weather_result.temp_min}{weather_result.temperature_unit} / {weather_result.temp_max}{weather_result.temperature_unit}
- Humidity: {weather_result.humidity}%
- Wind: {weather_result.wind_speed} {weather_result.wind_unit}

Daypart hints:
{dayparts}

User context:
- Gender mode: {query_context['gender']} ({gender_hint})
- Occasion text: {query_context['occasion_text'] or 'none'}
- Occasion tags: {', '.join(query_context['occasion_tags']) or 'none'}

Dominant factors:
{factors}

Bottomwear guidance:
{bottoms}

Occasion adjustments:
{occasion}

Retrieved outfit knowledge:
{knowledge_lines}

Use exactly these sections:
### {headers['headline']}
### {headers['factors']}
### {headers['time']}
### {headers['layering']}
### {headers['bottoms']}
### {headers['shoes']}
### {headers['notes']}
"""

    def _extract_section(self, text: str, title: str) -> str:
        pattern = re.compile(rf"(?:^|\n)###\s*{re.escape(title)}\s*\n(.*?)(?=\n###\s+|\Z)", flags=re.DOTALL)
        match = pattern.search(text or "")
        return match.group(1).strip() if match else ""

    def _collapse_lines(self, text: str) -> str:
        lines = [line.strip().lstrip("- ").strip() for line in (text or "").splitlines() if line.strip()]
        return " ".join(lines).strip()

    def _rule_sections(
        self,
        weather_result: WeatherResult,
        locale: str,
        query_context: dict[str, Any],
        knowledge_hits: list[KnowledgeHit],
    ) -> dict[str, Any]:
        headers = _headers(locale)
        dominant_factors = self._build_decision_factors(weather_result, locale, knowledge_hits)
        occasion_adjustments = self._occasion_adjustments(
            locale,
            query_context["occasion_text"],
            query_context["occasion_tags"],
            knowledge_hits,
        )
        bottomwear_guidance = self._bottomwear_options(
            weather_result,
            locale,
            query_context["gender"],
            knowledge_hits,
        )
        shoes_guidance = self._guidance_items(knowledge_hits, "shoes")
        notes_guidance = self._guidance_items(knowledge_hits, "notes")
        temp_unit = weather_result.temperature_unit or "°C"
        low = weather_result.temp_min if weather_result.temp_min is not None else weather_result.temperature or 18.0
        high = weather_result.temp_max if weather_result.temp_max is not None else weather_result.temperature or low

        if _is_english(locale):
            headline = (
                f"Start with easy layers and keep the outfit adjustable through the day. "
                f"The main drivers are {self._collapse_lines(dominant_factors[0]) if dominant_factors else 'the temperature and wind'}."
            )
            time_plan = "\n".join(
                [
                    f"- Morning: Around {round(low, 1)}{temp_unit}, so keep the outer layer on.",
                    f"- Daytime: Closer to {round(high, 1)}{temp_unit}, you can relax one layer if you warm up.",
                    f"- Evening: Temperatures fall again, so put the carry layer back on.",
                ]
            )
            layering = "\n".join(
                [
                    "- Base layer: breathable long-sleeve tee, shirt, or moisture-wicking top.",
                    "- Mid layer: thin knit, light sweatshirt, or compact cardigan.",
                    "- Outer layer: jacket, trench, windbreaker, or light weather shell depending on wind and rain.",
                    "- Carry layer: one removable piece that covers the colder part of the day.",
                ]
            )
            bottoms = "\n".join(f"- {item}" for item in bottomwear_guidance)
            shoes_items = shoes_guidance or [
                "Shoes: closed-toe sneakers, loafers, or weather-aware ankle boots depending on the surface and rain risk.",
                "Accessories: keep one practical item such as an umbrella, scarf, cap, or sunglasses based on wind, rain, and sun.",
            ]
            shoes = "\n".join(f"- {item}" for item in shoes_items[:3])
            notes = "\n".join(f"- {item}" for item in (occasion_adjustments[:2] + notes_guidance[:1]) or [
                "Keep the outfit easy to adjust rather than over-styling a single fixed look."
            ])
        else:
            headline = (
                f"今天更适合可增减的分层穿法，先把舒适和场合适配做好。"
                f"{dominant_factors[0] if dominant_factors else '核心判断主要来自体感与风感。'}"
            )
            time_plan = "\n".join(
                [
                    f"- 早晨：大约 {round(low, 1)}{temp_unit}，先把外层穿上再出门。",
                    f"- 白天：接近 {round(high, 1)}{temp_unit} 时可适当减一层，但保留可随时加回的外搭。",
                    f"- 晚上：气温再回落，建议把携带层重新加回来。",
                ]
            )
            layering = "\n".join(
                [
                    "- 内层：透气长袖、衬衫或吸湿打底，先保证体感稳定。",
                    "- 中层：薄针织、轻卫衣或开衫，负责弹性调温。",
                    "- 外层：夹克、风衣、轻薄冲锋衣或更防风的外搭，根据风雨强度决定。",
                    "- 携带层：准备一件可随时增减的外搭，覆盖更凉的时段。",
                ]
            )
            bottoms = "\n".join(f"- {item}" for item in bottomwear_guidance)
            shoes_items = shoes_guidance or [
                "鞋子：以包裹性和步行舒适度为主，雨天或风大时优先更稳的闭口鞋。",
                "配饰：按风、雨、日晒从围巾、雨伞、帽子、墨镜里选一到两样真正有用的。",
            ]
            shoes = "\n".join(f"- {item}" for item in shoes_items[:3])
            notes = "\n".join(f"- {item}" for item in (occasion_adjustments[:2] + notes_guidance[:1]) or [
                "把重点放在舒适、可活动和场合得体之间的平衡，不必堆太多装饰层。"
            ])

        advice_text = "\n\n".join(
            [
                f"### {headers['headline']}\n{headline}",
                f"### {headers['factors']}\n" + "\n".join(f"- {item}" for item in dominant_factors),
                f"### {headers['time']}\n{time_plan}",
                f"### {headers['layering']}\n{layering}",
                f"### {headers['bottoms']}\n{bottoms}",
                f"### {headers['shoes']}\n{shoes}",
                f"### {headers['notes']}\n{notes}",
            ]
        )
        return {
            "advice_text": advice_text,
            "headline_advice": headline,
            "time_of_day_advice": time_plan,
            "layering_advice": layering,
            "bottomwear_advice": bottoms,
            "shoes_accessories_advice": shoes,
            "notes_advice": notes,
            "dominant_factors": dominant_factors,
            "hard_requirements": dominant_factors[:2],
            "optional_refinements": occasion_adjustments[:2],
            "bottomwear_guidance": bottomwear_guidance,
            "occasion_adjustments": occasion_adjustments,
            "knowledge_application_mode": "matched" if knowledge_hits else "no_match",
        }

    def get_rule_based_fashion_advice(
        self,
        weather_result: WeatherResult,
        locale: str = "zh-CN",
        query_context: str | dict[str, Any] | None = None,
        knowledge_hits: list[KnowledgeHit] | None = None,
    ) -> FashionAdviceResult:
        normalized_query_context = self._normalize_query_context(query_context)
        knowledge_hits = knowledge_hits or []
        sections = self._rule_sections(weather_result, locale, normalized_query_context, knowledge_hits)
        return FashionAdviceResult(
            advice_text=sections["advice_text"],
            headline_advice=sections["headline_advice"],
            time_of_day_advice=sections["time_of_day_advice"],
            layering_advice=sections["layering_advice"],
            bottomwear_advice=sections["bottomwear_advice"],
            shoes_accessories_advice=sections["shoes_accessories_advice"],
            notes_advice=sections["notes_advice"],
            dominant_factors=sections["dominant_factors"],
            hard_requirements=sections["hard_requirements"],
            optional_refinements=sections["optional_refinements"],
            bottomwear_guidance=sections["bottomwear_guidance"],
            occasion_adjustments=sections["occasion_adjustments"],
            knowledge_application_mode=sections["knowledge_application_mode"],
            used_llm=False,
            fallback_used=True,
            source="rule_based_fashion",
            knowledge_hits=knowledge_hits,
        )

    def get_fashion_advice(
        self,
        weather_result: WeatherResult,
        locale: str = "zh-CN",
        query_context: str | dict[str, Any] | None = None,
        cancel_token: object | None = None,
    ) -> FashionAdviceResult:
        normalized_query_context = self._normalize_query_context(query_context)
        if cancel_token and hasattr(cancel_token, "raise_if_cancelled"):
            cancel_token.raise_if_cancelled("generate_outfit:before_retrieve_knowledge")
        knowledge_hits, knowledge_records = retrieve_knowledge_hits(
            weather_result,
            locale=locale,
            query_context=normalized_query_context,
            cancel_token=cancel_token,
        )
        sections = self._rule_sections(weather_result, locale, normalized_query_context, knowledge_hits)
        apply_record = self._apply_knowledge_record(
            locale,
            knowledge_hits,
            sections["dominant_factors"],
            sections["bottomwear_guidance"],
            sections["occasion_adjustments"],
        )
        rerank_record = next((item for item in reversed(knowledge_records) if item.node_name == "rerank_knowledge"), None)
        if rerank_record is not None:
            apply_record.metadata = {
                **(apply_record.metadata or {}),
                "retrieval_mode": rerank_record.metadata.get("retrieval_mode", "rules_only"),
                "vector_leg_status": rerank_record.metadata.get("vector_leg_status", "unknown"),
                "vector_leg_skipped_reason": rerank_record.metadata.get("vector_leg_skipped_reason", ""),
            }
        prompt = self._build_llm_prompt(
            weather_result,
            locale,
            normalized_query_context,
            knowledge_hits,
            sections["dominant_factors"],
            sections["bottomwear_guidance"],
            sections["occasion_adjustments"],
        )
        output, record = run_agent(
            role=_msg(locale, "穿搭建议智能体", "Outfit advisor"),
            name=self.name,
            system_prompt=FASHION_SYSTEM_PROMPT_EN if _is_english(locale) else FASHION_SYSTEM_PROMPT_ZH,
            prompt=prompt,
            cancel_token=cancel_token,
        )
        record.node_name = "generate_outfit"
        record.step_kind = "fashion_agent_llm"
        record.decision_reason = "weather_to_outfit_generation"
        if record.success and output and not self._language_mismatch(output, locale):
            headers = _headers(locale)
            headline = self._collapse_lines(self._extract_section(output, headers["headline"])) or sections["headline_advice"]
            time_of_day = self._extract_section(output, headers["time"]) or sections["time_of_day_advice"]
            layering = self._extract_section(output, headers["layering"]) or sections["layering_advice"]
            bottoms = self._extract_section(output, headers["bottoms"]) or sections["bottomwear_advice"]
            shoes = self._extract_section(output, headers["shoes"]) or sections["shoes_accessories_advice"]
            notes = self._extract_section(output, headers["notes"]) or sections["notes_advice"]
            factors_text = self._extract_section(output, headers["factors"])
            dominant_factors = [line.strip().lstrip("- ").strip() for line in factors_text.splitlines() if line.strip()] or sections["dominant_factors"]
            return FashionAdviceResult(
                advice_text=output,
                headline_advice=headline,
                time_of_day_advice=time_of_day,
                layering_advice=layering,
                bottomwear_advice=bottoms,
                shoes_accessories_advice=shoes,
                notes_advice=notes,
                dominant_factors=dominant_factors[:3],
                hard_requirements=sections["hard_requirements"],
                optional_refinements=sections["optional_refinements"],
                bottomwear_guidance=sections["bottomwear_guidance"],
                occasion_adjustments=sections["occasion_adjustments"],
                knowledge_application_mode="merged" if knowledge_hits else "no_match",
                used_llm=True,
                fallback_used=False,
                source="langchain_llm",
                knowledge_hits=knowledge_hits,
                execution_records=[*knowledge_records, apply_record, record],
            )

        fallback = self.get_rule_based_fashion_advice(
            weather_result,
            locale=locale,
            query_context=normalized_query_context,
            knowledge_hits=knowledge_hits,
        )
        fallback.error = record.error or ("llm_output_language_mismatch" if output else "")
        fallback.execution_records = [*knowledge_records, apply_record, record]
        return fallback

    def summarize_for_trace(self, advice_result: FashionAdviceResult) -> str:
        return compact_text(advice_result.advice_text)
