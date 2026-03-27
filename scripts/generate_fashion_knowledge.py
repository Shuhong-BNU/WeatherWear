from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "weatherwear" / "resources" / "fashion_knowledge"

TEMP_BANDS = [
    {
        "id": "cold",
        "zh": "低温",
        "en": "cold",
        "min": None,
        "max": 7,
        "upper_zh": "保暖内层、中层保温和防风外层",
        "upper_en": "a warm base, an insulating mid layer, and a wind-blocking outer layer",
        "bottom_zh": "长裤优先，必要时加打底或厚袜",
        "bottom_en": "full-length pants first, with a thin base layer or warmer socks if needed",
        "shoes_zh": "闭口鞋或短靴更稳妥",
        "shoes_en": "closed shoes or ankle boots are the safer pick",
        "fabric_zh": "温感稳定、不过分厚重的贴身面料",
        "fabric_en": "temperature-stable fabrics that do not become bulky",
        "factor_zh": "温度偏低，保暖优先级高",
        "factor_en": "Low temperatures make insulation the first priority",
    },
    {
        "id": "cool",
        "zh": "偏凉",
        "en": "cool",
        "min": 8,
        "max": 15,
        "upper_zh": "长袖内搭加一层可脱外搭",
        "upper_en": "a long-sleeve base with one removable outer layer",
        "bottom_zh": "长裤最稳妥，裙装建议配打底",
        "bottom_en": "full-length pants work best, while skirts usually need tights",
        "shoes_zh": "闭口休闲鞋、乐福鞋或短靴更合适",
        "shoes_en": "closed sneakers, loafers, or ankle boots fit best",
        "fabric_zh": "轻薄但不发凉的面料",
        "fabric_en": "light fabrics that do not feel chilly on the skin",
        "factor_zh": "早晚会更凉，可调节分层更重要",
        "factor_en": "The day gets cooler at the edges, so adjustable layers matter more",
    },
    {
        "id": "mild",
        "zh": "温和",
        "en": "mild",
        "min": 16,
        "max": 22,
        "upper_zh": "轻薄长袖或薄针织，必要时带一件轻外套",
        "upper_en": "a light long-sleeve or thin knit, with a light jacket only if needed",
        "bottom_zh": "长裤和轻薄裙装都可行，按活动量选择",
        "bottom_en": "both trousers and lighter skirts can work, depending on activity level",
        "shoes_zh": "舒适步行鞋通常就够了",
        "shoes_en": "comfortable walking shoes are usually enough",
        "fabric_zh": "透气、顺滑、方便久穿的面料",
        "fabric_en": "breathable easy-wearing fabrics that do not drag through the day",
        "factor_zh": "重点转向风、场合和活动量",
        "factor_en": "Wind, setting, and activity level matter more than pure warmth",
    },
    {
        "id": "warm",
        "zh": "偏暖",
        "en": "warm",
        "min": 23,
        "max": 29,
        "upper_zh": "以透气、轻薄和快干为主",
        "upper_en": "focus on breathable, light, quick-drying pieces",
        "bottom_zh": "轻薄长裤、阔腿裤、裙装或更轻的裤装更舒服",
        "bottom_en": "lighter trousers, wider-leg options, skirts, or other easy bottoms feel better",
        "shoes_zh": "鞋面透气比厚度更重要",
        "shoes_en": "breathable uppers matter more than insulation",
        "fabric_zh": "干爽、透气、快干面料",
        "fabric_en": "dry-feeling, breathable, quick-drying fabrics",
        "factor_zh": "散热和活动舒适度更关键",
        "factor_en": "Breathability and movement comfort matter more than extra coverage",
    },
    {
        "id": "hot",
        "zh": "炎热",
        "en": "hot",
        "min": 30,
        "max": None,
        "upper_zh": "尽量轻薄、排汗并控制贴身厚度",
        "upper_en": "keep it very light, sweat-friendly, and low in bulk",
        "bottom_zh": "下装越轻越好，但仍要兼顾防晒和场合体面",
        "bottom_en": "the lower half should stay as light as possible while still matching the setting",
        "shoes_zh": "轻便透气鞋和最少但有效的配饰更舒服",
        "shoes_en": "light breathable shoes and only the most useful accessories feel best",
        "fabric_zh": "轻薄、快干、不过分贴肤的面料",
        "fabric_en": "light, quick-dry fabrics that do not cling too much",
        "factor_zh": "散热、防晒和出汗后的舒适度是主因",
        "factor_en": "Heat release, sun exposure, and post-sweat comfort become the main drivers",
    },
]

OCCASIONS = [
    {"id": "work", "zh": "上班通勤", "en": "work commute", "adjust_zh": "优先整洁、通勤友好和办公室内外都能成立的组合。", "adjust_en": "Keep the look neat, commute-friendly, and workable both outdoors and in the office.", "tags_zh": ["工作", "通勤", "办公室", "空调"], "tags_en": ["work", "commute", "office", "ac"]},
    {"id": "date", "zh": "约会外出", "en": "date", "adjust_zh": "在舒适基础上保留一点精致感，不要为造型牺牲体感。", "adjust_en": "Keep a polished touch, but do not sacrifice comfort for styling.", "tags_zh": ["约会", "精致", "外出"], "tags_en": ["date", "polished", "out"]},
    {"id": "friends", "zh": "见朋友", "en": "meeting friends", "adjust_zh": "风格可以轻松一些，但要给走动和室内外切换留余量。", "adjust_en": "The look can stay relaxed, but leave room for walking and indoor-outdoor shifts.", "tags_zh": ["朋友", "周末", "聚会"], "tags_en": ["friends", "weekend", "casual"]},
    {"id": "home", "zh": "在家", "en": "at home", "adjust_zh": "减少结构感，优先柔软、亲肤和低束缚。", "adjust_en": "Reduce structure and favor softness, skin comfort, and low restriction.", "tags_zh": ["在家", "居家", "室内"], "tags_en": ["home", "indoor", "lounging"]},
    {"id": "exercise", "zh": "运动", "en": "exercise", "adjust_zh": "优先透气、排汗、弹性和鞋底支撑。", "adjust_en": "Prioritize breathability, sweat handling, stretch, and shoe support.", "tags_zh": ["运动", "跑步", "训练"], "tags_en": ["exercise", "running", "training"]},
    {"id": "travel", "zh": "出行旅行", "en": "travel", "adjust_zh": "兼顾久坐、步行、背包和室内外切换的舒适度。", "adjust_en": "Balance sitting, walking, carrying a bag, and indoor-outdoor transitions.", "tags_zh": ["旅行", "走很多路", "室内外切换"], "tags_en": ["travel", "walking", "indoor", "outdoor"]},
]

SPECIALS = [
    ("light-rain-hems", "bottoms", {"condition_any": ["rain", "drizzle", "小雨", "阵雨"]}, ["work", "friends", "travel"], ["小雨", "裤脚", "裙摆"], ["drizzle", "hems"], {"bottomwear": ["雨天尽量避免拖地裤脚和易吸水裙摆。"], "shoes": ["优先不容易进水的闭口鞋，并随身带伞。"]}, {"bottomwear": ["For rain, avoid hems that drag and fabrics that soak up water easily."], "shoes": ["Favor closed shoes that do not take on water easily, and keep an umbrella nearby."]}, "小雨天要特别注意裤脚、裙摆和鞋面是否容易沾水", "Light rain still makes hems and shoe uppers worth managing"),
    ("steady-rain-shell", "upper_body", {"condition_any": ["rain", "shower", "中雨", "阵雨"]}, ["work", "travel"], ["中雨", "防泼水", "外层"], ["steady rain", "shell"], {"dominant_factors": ["有持续降雨信号，外层和鞋面要兼顾防泼水。"]}, {"dominant_factors": ["Steady rain makes a weather-aware outer layer and practical shoes much more important."]}, "持续降雨时，外层的实用性要高于造型感", "In steady rain, outer-layer usefulness matters more than styling"),
    ("snow-traction-first", "shoes_accessories", {"condition_any": ["snow", "sleet", "雪", "冻雨"]}, ["work", "travel", "friends"], ["雪", "防滑", "鞋底"], ["snow", "traction"], {"shoes": ["雪天优先防滑鞋底、包裹性更好的鞋型和更稳的袜子厚度。"]}, {"shoes": ["In snow, prioritize traction, foot coverage, and socks that hold warmth without bulk."]}, "雪天不能只顾保暖，抓地力同样重要", "Snowy conditions demand traction, not just warmth"),
    ("wind-shell-priority", "upper_body", {"wind_speed_min": 6}, ["work", "date", "friends", "travel"], ["大风", "防风", "领口"], ["wind", "shell"], {"dominant_factors": ["风感明显，外层需要更防风而不是单纯更厚。"]}, {"dominant_factors": ["Wind is a dominant factor here, so outerwear should block movement of air, not just add bulk."]}, "风大的日子，外层结构和领口收束比单纯加厚更重要", "On windy days, shell structure and closure matter more than pure thickness"),
    ("high-humidity-fabric", "materials", {"humidity_min": 80}, ["work", "friends", "exercise", "travel"], ["高湿", "面料", "快干"], ["humidity", "quick-dry"], {"notes": ["湿度高时优先干爽、透气或快干材质。"]}, {"notes": ["High humidity favors dry-feeling, breathable, or quick-drying fabrics."]}, "高湿环境里，材质选择会直接影响舒服程度", "In very humid weather, fabric choice changes comfort directly"),
    ("dry-air-accessories", "shoes_accessories", {"humidity_max": 30}, ["work", "travel", "friends"], ["干燥", "围巾", "唇膏"], ["dry air", "scarf"], {"shoes": ["配饰可优先围巾、口罩或保湿补位，而不是单纯叠厚衣服。"]}, {"shoes": ["Accessories can focus on scarf, mask, or comfort items instead of simply adding heavier clothing."]}, "空气偏干时，小配件和护肤补位会更有价值", "Dry air makes small accessories and comfort items more useful"),
    ("large-range-carry-layer", "upper_body", {"temp_range_min": 8}, ["work", "date", "friends", "travel"], ["温差", "可脱外层", "分层"], ["range", "layering"], {"dominant_factors": ["日内温差明显，建议准备一层可随时增减的外搭。"]}, {"dominant_factors": ["The day swings enough to justify one removable carry layer."]}, "昼夜温差一大，就要给自己留一层可增减的余地", "Large day-night swings call for one removable layer"),
    ("office-ac-delta", "occasion", {"temperature_min": 20}, ["work", "indoor", "air_conditioning"], ["空调", "办公室", "室内外切换"], ["office ac", "indoor"], {"occasion_adjustments": ["若要进空调环境，最好保留一层轻薄外搭。"]}, {"occasion_adjustments": ["If office AC is likely, keep one light removable layer in the outfit."]}, "办公室空调会把本来偏暖的天气拉回分层逻辑", "Office AC can push a warm day back into layering territory"),
    ("walking-support", "shoes_accessories", {"temperature_min": 8, "temperature_max": 28}, ["walking", "travel", "friends", "date"], ["走很多路", "支撑", "鞋底"], ["walking", "support"], {"occasion_adjustments": ["如果当天步行量大，鞋子支撑和下装灵活度要优先于装饰性。"]}, {"occasion_adjustments": ["If the day involves a lot of walking, prioritize shoe support and easier movement over decorative styling."]}, "需要走很多路时，鞋底支撑和下装活动量优先级会抬高", "If you will walk a lot, support and movement room deserve more priority"),
    ("exercise-sweat-management", "materials", {"temperature_min": 10}, ["exercise"], ["运动", "排汗", "透气"], ["exercise", "sweat"], {"occasion_adjustments": ["运动场景优先快干、弹性和鞋底支撑。"]}, {"occasion_adjustments": ["For exercise, prioritize quick-dry fabrics, stretch, and shoe support."]}, "运动场景里，排汗和摩擦舒适度比静态保暖更重要", "For exercise, sweat handling and low-friction comfort beat static warmth"),
    ("sun-uv-priority", "shoes_accessories", {"condition_any": ["clear", "sun", "晴"], "temperature_min": 18}, ["work", "friends", "date", "travel"], ["晴天", "紫外线", "帽子", "墨镜"], ["sun", "uv", "hat"], {"shoes": ["晴天时可优先帽子、墨镜或基础防晒，而不是继续加厚。"]}, {"shoes": ["On sunny days, think hat, sunglasses, and UV basics before adding more clothing."]}, "晴天且不冷时，防晒配件会从可有可无变成真正有用", "On sunny mild-to-warm days, UV accessories become genuinely useful"),
    ("tights-cool-skirt", "bottoms", {"temperature_min": 8, "temperature_max": 16}, ["date", "friends", "work"], ["裙装", "打底", "偏凉"], ["skirt", "tights"], {"bottomwear": ["偏凉天若想穿裙装，建议配打底或更稳的靴型。"]}, {"bottomwear": ["If you want a skirt on a cool day, pair it with tights or a steadier boot option."]}, "偏凉天气想穿裙装时，打底层能明显提高稳定性", "On cool days, tights make skirts much more stable to wear"),
]


def add_range(target: dict[str, object], minimum: int | None, maximum: int | None) -> None:
    if minimum is not None:
        target["temperature_min"] = minimum
    if maximum is not None:
        target["temperature_max"] = maximum


def make_entry(locale: str, entry_id: str, category: str, tags: list[str], occasion_hints: list[str], weather_conditions: dict[str, object], summary: str, body: str, guidance: dict[str, object]) -> dict[str, object]:
    return {
        "id": entry_id,
        "locale": locale,
        "category": category,
        "tags": tags,
        "occasion_hints": occasion_hints,
        "gender_compatibility": ["neutral", "male", "female"],
        "weather_conditions": weather_conditions,
        "summary": summary,
        "body": body,
        "structured_guidance": guidance,
    }


def locale_text(locale: str, zh: str, en: str) -> str:
    return zh if locale == "zh-CN" else en


def band_entries(locale: str) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for band in TEMP_BANDS:
        for occasion in OCCASIONS:
            wc: dict[str, object] = {}
            add_range(wc, band["min"], band["max"])
            if occasion["id"] == "exercise":
                wc["wind_speed_max"] = 8
            occ_tags = occasion["tags_zh"] if locale == "zh-CN" else occasion["tags_en"]
            band_label = band["zh"] if locale == "zh-CN" else band["en"]

            entries.append(make_entry(
                locale,
                f"{occasion['id']}-{band['id']}-upper",
                "upper_body",
                occ_tags + [band_label, locale_text(locale, "上装", "upper")],
                [occasion["id"]],
                wc,
                locale_text(locale, f"{occasion['zh']}遇到{band['zh']}天气时，上装优先{band['upper_zh']}", f"For {occasion['en']} in {band['en']} weather, keep the upper body focused on {band['upper_en']}"),
                locale_text(locale, f"如果场合是{occasion['zh']}，而且当天偏向{band['zh']}，上装建议以{band['upper_zh']}为主；{occasion['adjust_zh']}", f"If the plan is {occasion['en']} and the day feels {band['en']}, the upper body should lean toward {band['upper_en']}. {occasion['adjust_en']}"),
                {
                    "dominant_factors": [locale_text(locale, band["factor_zh"], band["factor_en"])],
                    "occasion_adjustments": [locale_text(locale, occasion["adjust_zh"], occasion["adjust_en"])],
                },
            ))

            entries.append(make_entry(
                locale,
                f"{occasion['id']}-{band['id']}-bottoms",
                "bottoms",
                occ_tags + [band_label, locale_text(locale, "下装", "bottoms")],
                [occasion["id"]],
                wc,
                locale_text(locale, f"{occasion['zh']}在{band['zh']}天气里，下装更适合{band['bottom_zh']}", f"For {occasion['en']} in {band['en']} weather, bottoms work better when they follow {band['bottom_en']}"),
                locale_text(locale, f"{occasion['zh']}场景下，下装不只要看温度，还要看活动量。{band['bottom_zh']}，同时别忽略场合体面度。", f"In {occasion['en']}, the lower half should answer both the temperature and the amount of movement involved. {band['bottom_en']}, while still fitting the setting."),
                {
                    "bottomwear": [
                        locale_text(locale, band["bottom_zh"], band["bottom_en"]),
                        locale_text(locale, f"{occasion['zh']}时，下装要兼顾活动量和场合得体。", f"For {occasion['en']}, the lower half should balance movement needs with the setting."),
                    ],
                },
            ))

            entries.append(make_entry(
                locale,
                f"{occasion['id']}-{band['id']}-shoes",
                "shoes_accessories",
                occ_tags + [band_label, locale_text(locale, "鞋子", "shoes"), locale_text(locale, "配饰", "accessories")],
                [occasion["id"]],
                wc,
                locale_text(locale, f"{occasion['zh']}在{band['zh']}天气里，鞋子与配饰应围绕“{band['shoes_zh']}”来配", f"For {occasion['en']} in {band['en']} weather, shoes and accessories should revolve around {band['shoes_en']}"),
                locale_text(locale, f"{band['shoes_zh']}；鞋履和配件往往比再多一件衣服更能决定当天的实际舒服程度。", f"{band['shoes_en']}. Shoes and accessories often decide daily comfort faster than adding another garment."),
                {
                    "shoes": [
                        locale_text(locale, band["shoes_zh"], band["shoes_en"]),
                        locale_text(locale, occasion["adjust_zh"], occasion["adjust_en"]),
                    ],
                },
            ))

            entries.append(make_entry(
                locale,
                f"{occasion['id']}-{band['id']}-material",
                "materials",
                occ_tags + [band_label, locale_text(locale, "材质", "materials")],
                [occasion["id"]],
                wc,
                locale_text(locale, f"{occasion['zh']}在{band['zh']}天气里更适合{band['fabric_zh']}", f"For {occasion['en']} in {band['en']} weather, materials should lean toward {band['fabric_en']}"),
                locale_text(locale, f"{band['fabric_zh']}通常更适合{occasion['zh']}这种场景，因为它更容易兼顾体感稳定、久穿和场合完成度。", f"{band['fabric_en']} usually fit {occasion['en']} better because they balance thermal comfort, durability through the day, and a more finished look."),
                {
                    "notes": [locale_text(locale, f"材质可优先{band['fabric_zh']}。", f"Favor {band['fabric_en']} in the fabric choice.")],
                },
            ))
    return entries


def special_entries(locale: str) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for entry_id, category, wc, occasion_hints, tags_zh, tags_en, guidance_zh, guidance_en, summary_zh, summary_en in SPECIALS:
        items.append(make_entry(
            locale,
            entry_id,
            category,
            tags_zh if locale == "zh-CN" else tags_en,
            occasion_hints,
            dict(wc),
            summary_zh if locale == "zh-CN" else summary_en,
            summary_zh if locale == "zh-CN" else summary_en,
            guidance_zh if locale == "zh-CN" else guidance_en,
        ))
    return items


def build_locale(locale: str) -> list[dict[str, object]]:
    return [*band_entries(locale), *special_entries(locale)]


def write_locale(locale: str) -> int:
    entries = build_locale(locale)
    path = OUT_DIR / f"{locale}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return len(entries)


if __name__ == "__main__":
    counts = {locale: write_locale(locale) for locale in ("zh-CN", "en-US")}
    print(json.dumps(counts, ensure_ascii=False))
