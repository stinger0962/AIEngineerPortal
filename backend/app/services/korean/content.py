"""Authored Korean course content (regions 0-2) + per-kind content_json validation."""
from __future__ import annotations

from typing import Any

_REQUIRED_FIELDS: dict[str, set[str]] = {
    "reading": {"letters", "blocks", "words"},
    "scene": {"setting", "character", "lines", "your_turns", "new_vocab"},
    "drill": {"items"},
    "boss": {"goal_en", "persona", "level", "allowed_vocab", "success_criteria", "max_turns"},
}

VALID_KINDS = set(_REQUIRED_FIELDS)


def validate_node_content(kind: str, content: dict[str, Any]) -> None:
    if kind not in _REQUIRED_FIELDS:
        raise ValueError(f"unknown node kind: {kind!r}")
    missing = _REQUIRED_FIELDS[kind] - set(content or {})
    if missing:
        raise ValueError(f"{kind} node missing fields: {sorted(missing)}")
    if kind == "drill":
        for item in content["items"]:
            if item.get("type") not in {"match", "listen"}:
                raise ValueError(f"drill item has invalid type: {item.get('type')!r}")


REGIONS: list[dict[str, Any]] = [
    # ------------------------------------------------------------------ #
    # Region 0 — 한글 Reading Island                                       #
    # ------------------------------------------------------------------ #
    {
        "slug": "hangul-island",
        "title": "한글 Reading Island",
        "theme": "reading",
        "order_index": 0,
        "nodes": [
            {
                "slug": "hangul-vowels",
                "kind": "reading",
                "title": "Basic Vowels",
                "order_index": 0,
                "content_json": {
                    "letters": [
                        {"jamo": "ㅏ", "sound": "a", "audio_key": "vowel_a"},
                        {"jamo": "ㅓ", "sound": "eo", "audio_key": "vowel_eo"},
                        {"jamo": "ㅗ", "sound": "o", "audio_key": "vowel_o"},
                        {"jamo": "ㅜ", "sound": "u", "audio_key": "vowel_u"},
                        {"jamo": "ㅡ", "sound": "eu", "audio_key": "vowel_eu"},
                        {"jamo": "ㅣ", "sound": "i", "audio_key": "vowel_i"},
                        {"jamo": "ㅑ", "sound": "ya", "audio_key": "vowel_ya"},
                        {"jamo": "ㅕ", "sound": "yeo", "audio_key": "vowel_yeo"},
                        {"jamo": "ㅛ", "sound": "yo", "audio_key": "vowel_yo"},
                        {"jamo": "ㅠ", "sound": "yu", "audio_key": "vowel_yu"},
                    ],
                    "blocks": [
                        {"ko": "아", "romaji": "a"},
                        {"ko": "어", "romaji": "eo"},
                        {"ko": "요", "romaji": "yo"},
                    ],
                    "words": [
                        {"ko": "오이", "en": "cucumber"},
                        {"ko": "우유", "en": "milk"},
                    ],
                },
            },
            {
                "slug": "hangul-consonants-1",
                "kind": "reading",
                "title": "Consonants 1",
                "order_index": 1,
                "content_json": {
                    "letters": [
                        {"jamo": "ㄱ", "sound": "g/k", "audio_key": "cons_g"},
                        {"jamo": "ㄴ", "sound": "n", "audio_key": "cons_n"},
                        {"jamo": "ㄷ", "sound": "d/t", "audio_key": "cons_d"},
                        {"jamo": "ㄹ", "sound": "r/l", "audio_key": "cons_r"},
                        {"jamo": "ㅁ", "sound": "m", "audio_key": "cons_m"},
                        {"jamo": "ㅂ", "sound": "b/p", "audio_key": "cons_b"},
                        {"jamo": "ㅅ", "sound": "s", "audio_key": "cons_s"},
                    ],
                    "blocks": [
                        {"ko": "가", "romaji": "ga"},
                        {"ko": "나", "romaji": "na"},
                        {"ko": "다", "romaji": "da"},
                        {"ko": "라", "romaji": "ra"},
                        {"ko": "마", "romaji": "ma"},
                    ],
                    "words": [
                        {"ko": "나무", "en": "tree"},
                        {"ko": "가구", "en": "furniture"},
                    ],
                },
            },
            {
                "slug": "hangul-consonants-2",
                "kind": "reading",
                "title": "Consonants 2",
                "order_index": 2,
                "content_json": {
                    "letters": [
                        {"jamo": "ㅇ", "sound": "ng/silent", "audio_key": "cons_ng"},
                        {"jamo": "ㅈ", "sound": "j", "audio_key": "cons_j"},
                        {"jamo": "ㅊ", "sound": "ch", "audio_key": "cons_ch"},
                        {"jamo": "ㅋ", "sound": "k", "audio_key": "cons_k"},
                        {"jamo": "ㅌ", "sound": "t", "audio_key": "cons_t"},
                        {"jamo": "ㅍ", "sound": "p", "audio_key": "cons_p"},
                        {"jamo": "ㅎ", "sound": "h", "audio_key": "cons_h"},
                        {"jamo": "ㄲ", "sound": "kk", "audio_key": "cons_kk"},
                        {"jamo": "ㄸ", "sound": "tt", "audio_key": "cons_tt"},
                        {"jamo": "ㅃ", "sound": "pp", "audio_key": "cons_pp"},
                        {"jamo": "ㅆ", "sound": "ss", "audio_key": "cons_ss"},
                        {"jamo": "ㅉ", "sound": "jj", "audio_key": "cons_jj"},
                    ],
                    "blocks": [
                        {"ko": "자", "romaji": "ja"},
                        {"ko": "차", "romaji": "cha"},
                        {"ko": "카", "romaji": "ka"},
                        {"ko": "타", "romaji": "ta"},
                        {"ko": "파", "romaji": "pa"},
                        {"ko": "하", "romaji": "ha"},
                    ],
                    "words": [
                        {"ko": "아기", "en": "baby"},
                        {"ko": "코", "en": "nose"},
                    ],
                },
            },
            {
                "slug": "hangul-blocks-batchim",
                "kind": "reading",
                "title": "Syllable Blocks & 받침 (final consonant)",
                "order_index": 3,
                "content_json": {
                    "letters": [
                        {"jamo": "ㄴ", "sound": "-n (final)", "audio_key": "batchim_n"},
                        {"jamo": "ㄹ", "sound": "-l (final)", "audio_key": "batchim_l"},
                        {"jamo": "ㅂ", "sound": "-p (final)", "audio_key": "batchim_p"},
                        {"jamo": "ㄱ", "sound": "-k (final)", "audio_key": "batchim_k"},
                    ],
                    "blocks": [
                        {"ko": "한", "romaji": "han"},
                        {"ko": "글", "romaji": "geul"},
                        {"ko": "밥", "romaji": "bap"},
                        {"ko": "물", "romaji": "mul"},
                        {"ko": "국", "romaji": "guk"},
                    ],
                    "words": [
                        {"ko": "한국", "en": "Korea"},
                        {"ko": "사람", "en": "person"},
                    ],
                },
            },
            {
                "slug": "hangul-read-signs",
                "kind": "reading",
                "title": "Read Real Signs",
                "order_index": 4,
                "content_json": {
                    "letters": [
                        {"jamo": "ㅊ", "sound": "ch", "audio_key": "review_ch"},
                        {"jamo": "ㅎ", "sound": "h", "audio_key": "review_h"},
                    ],
                    "blocks": [
                        {"ko": "출", "romaji": "chul"},
                        {"ko": "구", "romaji": "gu"},
                    ],
                    "words": [
                        {"ko": "출구", "en": "exit"},
                        {"ko": "화장실", "en": "restroom"},
                        {"ko": "카페", "en": "cafe"},
                        {"ko": "지하철", "en": "subway"},
                        {"ko": "입구", "en": "entrance"},
                    ],
                },
            },
        ],
    },
    # ------------------------------------------------------------------ #
    # Region 1 — Arrival                                                  #
    # ------------------------------------------------------------------ #
    {
        "slug": "arrival",
        "title": "Arrival",
        "theme": "arrival",
        "order_index": 1,
        "nodes": [
            {
                "slug": "arrival-greetings",
                "kind": "scene",
                "title": "First Greetings",
                "order_index": 0,
                "content_json": {
                    "setting": "airport",
                    "character": "staff",
                    "lines": [
                        {
                            "speaker": "staff",
                            "ko": "안녕하세요!",
                            "romaji": "annyeonghaseyo!",
                            "en": "Hello!",
                            "audio_key": "greet_1",
                        },
                        {
                            "speaker": "you",
                            "ko": "안녕하세요.",
                            "romaji": "annyeonghaseyo.",
                            "en": "Hello.",
                            "audio_key": "greet_2",
                        },
                        {
                            "speaker": "staff",
                            "ko": "감사합니다. 좋은 하루 되세요!",
                            "romaji": "gamsahamnida. joeun haru doeseyo!",
                            "en": "Thank you. Have a nice day!",
                            "audio_key": "greet_3",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "The staff greets you. Greet them back.",
                            "options": ["안녕하세요", "감사합니다", "아니요"],
                            "accepted": [
                                {"ko": "안녕하세요", "intents": ["hello", "greeting", "hi"]}
                            ],
                        },
                        {
                            "prompt_en": "They handed you your boarding pass. Thank them.",
                            "options": ["감사합니다", "죄송합니다", "네"],
                            "accepted": [
                                {"ko": "감사합니다", "intents": ["thank you", "thanks", "gratitude"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "안녕하세요", "en": "hello", "romaji": "annyeonghaseyo"},
                        {"ko": "감사합니다", "en": "thank you", "romaji": "gamsahamnida"},
                        {"ko": "네", "en": "yes", "romaji": "ne"},
                        {"ko": "아니요", "en": "no", "romaji": "aniyo"},
                        {"ko": "죄송합니다", "en": "sorry", "romaji": "joesonghamnida"},
                    ],
                },
            },
            {
                "slug": "arrival-greetings-drill",
                "kind": "drill",
                "title": "Greetings Drill",
                "order_index": 1,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "안녕하세요",
                            "answer": "hello",
                            "choices": ["hello", "thank you", "sorry"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "greet_3",
                            "answer": "감사합니다",
                            "choices": ["감사합니다", "안녕하세요", "아니요"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "d_no",
                            "answer": "아니요",
                            "choices": ["아니요", "안녕하세요", "감사합니다"],
                        },
                        {
                            "type": "match",
                            "ko": "감사합니다",
                            "answer": "thank you",
                            "choices": ["thank you", "hello", "sorry"],
                        },
                    ]
                },
            },
            {
                "slug": "arrival-immigration",
                "kind": "scene",
                "title": "At Immigration",
                "order_index": 2,
                "content_json": {
                    "setting": "immigration",
                    "character": "officer",
                    "lines": [
                        {
                            "speaker": "officer",
                            "ko": "여권이요.",
                            "romaji": "yeogwon-iyo.",
                            "en": "Passport, please.",
                            "audio_key": "immig_1",
                        },
                        {
                            "speaker": "officer",
                            "ko": "무슨 일로 오셨어요?",
                            "romaji": "museun illo osyeosseoyo?",
                            "en": "What is the purpose of your visit?",
                            "audio_key": "immig_2",
                        },
                        {
                            "speaker": "you",
                            "ko": "여행이요.",
                            "romaji": "yeohaeng-iyo.",
                            "en": "For travel.",
                            "audio_key": "immig_3",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "The officer asks for your passport. Hand it over and say the word.",
                            "options": ["여권이요", "여행이요", "관광이요"],
                            "accepted": [
                                {"ko": "여권이요", "intents": ["passport", "here is my passport"]}
                            ],
                        },
                        {
                            "prompt_en": "They ask why you're visiting. You're here as a tourist.",
                            "options": ["여행이요", "여권이요", "네"],
                            "accepted": [
                                {"ko": "여행이요", "intents": ["travel", "tourism", "for travel", "sightseeing"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "여권", "en": "passport", "romaji": "yeogwon"},
                        {"ko": "여행", "en": "travel", "romaji": "yeohaeng"},
                        {"ko": "관광", "en": "sightseeing", "romaji": "gwangwang"},
                    ],
                },
            },
            {
                "slug": "arrival-immigration-drill",
                "kind": "drill",
                "title": "Immigration Drill",
                "order_index": 3,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "여권",
                            "answer": "passport",
                            "choices": ["passport", "travel", "sightseeing"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "immig_3",
                            "answer": "여행이요",
                            "choices": ["여행이요", "여권이요", "관광이요"],
                        },
                        {
                            "type": "match",
                            "ko": "여행",
                            "answer": "travel",
                            "choices": ["travel", "passport", "sightseeing"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "d_passport",
                            "answer": "여권",
                            "choices": ["여권", "여행", "관광"],
                        },
                    ]
                },
            },
            {
                "slug": "arrival-taxi",
                "kind": "scene",
                "title": "Taking a Taxi",
                "order_index": 4,
                "content_json": {
                    "setting": "taxi",
                    "character": "driver",
                    "lines": [
                        {
                            "speaker": "driver",
                            "ko": "어디 가세요?",
                            "romaji": "eodi gaseyo?",
                            "en": "Where are you going?",
                            "audio_key": "taxi_1",
                        },
                        {
                            "speaker": "you",
                            "ko": "호텔이요.",
                            "romaji": "hotel-iyo.",
                            "en": "To the hotel.",
                            "audio_key": "taxi_2",
                        },
                        {
                            "speaker": "driver",
                            "ko": "네, 알겠습니다.",
                            "romaji": "ne, algetseumnida.",
                            "en": "Okay, got it.",
                            "audio_key": "taxi_3",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "The driver asks where to. Tell them: to the hotel.",
                            "options": ["호텔이요", "시내요", "얼마예요?"],
                            "accepted": [
                                {"ko": "호텔이요", "intents": ["to the hotel", "hotel"]},
                                {"ko": "시내요", "intents": ["downtown", "to downtown"]},
                            ],
                        },
                        {
                            "prompt_en": "You've arrived. Ask how much the fare is.",
                            "options": ["얼마예요?", "어디 가세요?", "감사합니다"],
                            "accepted": [
                                {"ko": "얼마예요?", "intents": ["how much", "what's the price", "fare"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "시내", "en": "downtown", "romaji": "sinae"},
                        {"ko": "호텔", "en": "hotel", "romaji": "hotel"},
                        {"ko": "얼마예요", "en": "how much", "romaji": "eolmayeyo"},
                    ],
                },
            },
            {
                "slug": "arrival-taxi-drill",
                "kind": "drill",
                "title": "Taxi Drill",
                "order_index": 5,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "얼마예요?",
                            "answer": "how much?",
                            "choices": ["how much?", "where to?", "thank you"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "taxi_1",
                            "answer": "어디 가세요?",
                            "choices": ["어디 가세요?", "얼마예요?", "여권이요"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "d_hotel",
                            "answer": "호텔이요",
                            "choices": ["호텔이요", "시내요", "얼마예요?"],
                        },
                        {
                            "type": "match",
                            "ko": "시내",
                            "answer": "downtown",
                            "choices": ["downtown", "hotel", "how much?"],
                        },
                    ]
                },
            },
            {
                "slug": "arrival-boss",
                "kind": "boss",
                "title": "Boss: Airport to Hotel",
                "order_index": 6,
                "content_json": {
                    "goal_en": "Take a taxi from the airport to your hotel",
                    "persona": "taxi_driver",
                    "level": "beginner",
                    "allowed_vocab": [
                        "안녕하세요",
                        "감사합니다",
                        "네",
                        "아니요",
                        "호텔",
                        "호텔이요",
                        "시내",
                        "시내요",
                        "어디 가세요?",
                        "얼마예요?",
                    ],
                    "success_criteria": "Learner tells the driver the destination and responds to the fare",
                    "max_turns": 8,
                },
            },
        ],
    },
    # ------------------------------------------------------------------ #
    # Region 2 — Café & Food                                              #
    # ------------------------------------------------------------------ #
    {
        "slug": "cafe-food",
        "title": "Café & Food",
        "theme": "cafe",
        "order_index": 2,
        "nodes": [
            {
                "slug": "cafe-ordering",
                "kind": "scene",
                "title": "Ordering a Drink",
                "order_index": 0,
                "content_json": {
                    "setting": "cafe",
                    "character": "barista",
                    "lines": [
                        {
                            "speaker": "barista",
                            "ko": "어서 오세요!",
                            "romaji": "eoseo oseyo!",
                            "en": "Welcome!",
                            "audio_key": "cafe_order_1",
                        },
                        {
                            "speaker": "barista",
                            "ko": "뭐 드릴까요?",
                            "romaji": "mwo deurilkkayo?",
                            "en": "What would you like?",
                            "audio_key": "cafe_order_2",
                        },
                        {
                            "speaker": "you",
                            "ko": "아메리카노 주세요.",
                            "romaji": "amerikano juseyo.",
                            "en": "An americano, please.",
                            "audio_key": "cafe_order_3",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "The barista asks what you'd like. Order an americano.",
                            "options": ["아메리카노 주세요", "얼마예요?", "감사합니다"],
                            "accepted": [
                                {"ko": "아메리카노 주세요", "intents": ["americano please", "order americano", "i want an americano"]}
                            ],
                        },
                        {
                            "prompt_en": "Say 'please give me' politely to end your order.",
                            "options": ["주세요", "뭐", "네"],
                            "accepted": [
                                {"ko": "주세요", "intents": ["please give", "please", "i'll have"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "아메리카노", "en": "americano", "romaji": "amerikano"},
                        {"ko": "주세요", "en": "please give", "romaji": "juseyo"},
                        {"ko": "뭐", "en": "what", "romaji": "mwo"},
                    ],
                },
            },
            {
                "slug": "cafe-ordering-drill",
                "kind": "drill",
                "title": "Ordering Drill",
                "order_index": 1,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "주세요",
                            "answer": "please give",
                            "choices": ["please give", "what", "welcome"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "cafe_order_2",
                            "answer": "뭐 드릴까요?",
                            "choices": ["뭐 드릴까요?", "어서 오세요!", "얼마예요?"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "d_juseyo",
                            "answer": "주세요",
                            "choices": ["주세요", "뭐 드릴까요?", "얼마예요?"],
                        },
                        {
                            "type": "match",
                            "ko": "아메리카노",
                            "answer": "americano",
                            "choices": ["americano", "please give", "what"],
                        },
                    ]
                },
            },
            {
                "slug": "cafe-numbers",
                "kind": "scene",
                "title": "Counting Cups",
                "order_index": 2,
                "content_json": {
                    "setting": "cafe",
                    "character": "barista",
                    "lines": [
                        {
                            "speaker": "barista",
                            "ko": "몇 잔 드릴까요?",
                            "romaji": "myeot jan deurilkkayo?",
                            "en": "How many cups would you like?",
                            "audio_key": "cafe_num_1",
                        },
                        {
                            "speaker": "you",
                            "ko": "두 잔 주세요.",
                            "romaji": "du jan juseyo.",
                            "en": "Two cups, please.",
                            "audio_key": "cafe_num_2",
                        },
                        {
                            "speaker": "barista",
                            "ko": "네, 두 잔이요.",
                            "romaji": "ne, du jan-iyo.",
                            "en": "Okay, two cups.",
                            "audio_key": "cafe_num_3",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "The barista asks how many cups. Order one cup.",
                            "options": ["한 잔 주세요", "두 잔 주세요", "얼마예요?"],
                            "accepted": [
                                {"ko": "한 잔 주세요", "intents": ["one cup", "one cup please", "just one"]},
                                {"ko": "두 잔 주세요", "intents": ["two cups", "two cups please"]},
                            ],
                        },
                        {
                            "prompt_en": "Say the native Korean number for 'one'.",
                            "options": ["하나", "둘", "셋"],
                            "accepted": [
                                {"ko": "하나", "intents": ["one", "number one"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "하나", "en": "one", "romaji": "hana"},
                        {"ko": "둘", "en": "two", "romaji": "dul"},
                        {"ko": "잔", "en": "cup (counter)", "romaji": "jan"},
                        {"ko": "한 잔", "en": "one cup", "romaji": "han jan"},
                    ],
                },
            },
            {
                "slug": "cafe-numbers-drill",
                "kind": "drill",
                "title": "Numbers Drill",
                "order_index": 3,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "하나",
                            "answer": "one",
                            "choices": ["one", "two", "three"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "cafe_num_2",
                            "answer": "두 잔 주세요",
                            "choices": ["두 잔 주세요", "한 잔 주세요", "얼마예요?"],
                        },
                        {
                            "type": "match",
                            "ko": "한 잔",
                            "answer": "one cup",
                            "choices": ["one cup", "two cups", "cup (counter)"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "d_dul",
                            "answer": "둘",
                            "choices": ["둘", "하나", "잔"],
                        },
                    ]
                },
            },
            {
                "slug": "cafe-paying",
                "kind": "scene",
                "title": "Paying the Bill",
                "order_index": 4,
                "content_json": {
                    "setting": "cafe",
                    "character": "barista",
                    "lines": [
                        {
                            "speaker": "you",
                            "ko": "얼마예요?",
                            "romaji": "eolmayeyo?",
                            "en": "How much is it?",
                            "audio_key": "cafe_pay_1",
                        },
                        {
                            "speaker": "barista",
                            "ko": "4,500원이에요.",
                            "romaji": "sacheonobaek-won-ieyo.",
                            "en": "It's 4,500 won.",
                            "audio_key": "cafe_pay_2",
                        },
                        {
                            "speaker": "you",
                            "ko": "카드요.",
                            "romaji": "kadeu-yo.",
                            "en": "By card.",
                            "audio_key": "cafe_pay_3",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "Ask the barista how much it costs.",
                            "options": ["얼마예요?", "주세요", "감사합니다"],
                            "accepted": [
                                {"ko": "얼마예요?", "intents": ["how much", "what's the price", "the bill"]}
                            ],
                        },
                        {
                            "prompt_en": "They ask how you'll pay. Say you'll pay by card.",
                            "options": ["카드요", "현금이요", "네"],
                            "accepted": [
                                {"ko": "카드요", "intents": ["by card", "card", "pay by card"]},
                                {"ko": "현금이요", "intents": ["cash", "by cash", "pay cash"]},
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "얼마예요", "en": "how much", "romaji": "eolmayeyo"},
                        {"ko": "원", "en": "won (currency)", "romaji": "won"},
                        {"ko": "카드", "en": "card", "romaji": "kadeu"},
                        {"ko": "현금", "en": "cash", "romaji": "hyeon-geum"},
                    ],
                },
            },
            {
                "slug": "cafe-paying-drill",
                "kind": "drill",
                "title": "Paying Drill",
                "order_index": 5,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "현금",
                            "answer": "cash",
                            "choices": ["cash", "card", "won"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "cafe_pay_3",
                            "answer": "카드요",
                            "choices": ["카드요", "현금이요", "얼마예요?"],
                        },
                        {
                            "type": "match",
                            "ko": "얼마예요?",
                            "answer": "how much?",
                            "choices": ["how much?", "by card", "by cash"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "d_card",
                            "answer": "카드",
                            "choices": ["카드", "현금", "원"],
                        },
                    ]
                },
            },
            {
                "slug": "cafe-boss",
                "kind": "boss",
                "title": "Boss: Order & Pay",
                "order_index": 6,
                "content_json": {
                    "goal_en": "Order a drink and pay for it",
                    "persona": "barista",
                    "level": "beginner",
                    "allowed_vocab": [
                        "안녕하세요",
                        "감사합니다",
                        "아메리카노",
                        "주세요",
                        "한 잔",
                        "두 잔",
                        "얼마예요?",
                        "카드",
                        "카드요",
                        "현금",
                        "현금이요",
                    ],
                    "success_criteria": "Learner orders a drink and responds to the price",
                    "max_turns": 8,
                },
            },
        ],
    },
    # ------------------------------------------------------------------ #
    # Region 3 — Getting Around                                          #
    # ------------------------------------------------------------------ #
    {
        "slug": "getting-around",
        "title": "Getting Around",
        "theme": "transit",
        "order_index": 3,
        "nodes": [
            {
                "slug": "getting-around-tmoney",
                "kind": "scene",
                "title": "Buying a T-money Card",
                "order_index": 0,
                "content_json": {
                    "setting": "convenience store",
                    "character": "clerk",
                    "lines": [
                        {
                            "speaker": "you",
                            "ko": "티머니 카드 주세요.",
                            "romaji": "timeoni kadeu juseyo.",
                            "en": "A T-money card, please.",
                            "audio_key": "ga_tmoney_1",
                        },
                        {
                            "speaker": "clerk",
                            "ko": "네, 충전도 해 드릴까요?",
                            "romaji": "ne, chungjeon-do hae deurilkkayo?",
                            "en": "Sure, shall I recharge it too?",
                            "audio_key": "ga_tmoney_2",
                        },
                        {
                            "speaker": "you",
                            "ko": "네, 만 원 충전해 주세요.",
                            "romaji": "ne, man won chungjeonhae juseyo.",
                            "en": "Yes, please recharge 10,000 won.",
                            "audio_key": "ga_tmoney_3",
                        },
                        {
                            "speaker": "clerk",
                            "ko": "네, 다 됐어요.",
                            "romaji": "ne, da dwaesseoyo.",
                            "en": "Okay, all done.",
                            "audio_key": "ga_tmoney_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "Ask the clerk for a T-money card.",
                            "options": ["티머니 카드 주세요", "얼마예요?", "감사합니다"],
                            "accepted": [
                                {"ko": "티머니 카드 주세요", "intents": ["t-money card please", "a t-money card", "buy t-money"]}
                            ],
                        },
                        {
                            "prompt_en": "They ask if you want to recharge it. Say yes, recharge it.",
                            "options": ["네, 충전해 주세요", "아니요", "어디예요?"],
                            "accepted": [
                                {"ko": "네, 충전해 주세요", "intents": ["yes recharge it", "please recharge", "top it up"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "티머니", "en": "T-money card", "romaji": "timeoni"},
                        {"ko": "충전", "en": "recharge", "romaji": "chungjeon"},
                        {"ko": "충전해 주세요", "en": "please recharge", "romaji": "chungjeonhae juseyo"},
                    ],
                },
            },
            {
                "slug": "getting-around-tmoney-drill",
                "kind": "drill",
                "title": "T-money Drill",
                "order_index": 1,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "티머니",
                            "answer": "T-money card",
                            "choices": ["T-money card", "subway", "recharge"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "ga_tmoney_1",
                            "answer": "티머니 카드 주세요",
                            "choices": ["티머니 카드 주세요", "충전해 주세요", "얼마예요?"],
                        },
                        {
                            "type": "match",
                            "ko": "충전",
                            "answer": "recharge",
                            "choices": ["recharge", "card", "station"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "ga_d_chungjeon",
                            "answer": "충전",
                            "choices": ["충전", "티머니", "지하철"],
                        },
                    ]
                },
            },
            {
                "slug": "getting-around-subway",
                "kind": "scene",
                "title": "Which Subway Line?",
                "order_index": 2,
                "content_json": {
                    "setting": "subway station",
                    "character": "passerby",
                    "lines": [
                        {
                            "speaker": "you",
                            "ko": "저기요, 강남역 가요?",
                            "romaji": "jeogiyo, gangnamyeok gayo?",
                            "en": "Excuse me, does this go to Gangnam Station?",
                            "audio_key": "ga_subway_1",
                        },
                        {
                            "speaker": "passerby",
                            "ko": "네, 2호선 타세요.",
                            "romaji": "ne, i-hoseon taseyo.",
                            "en": "Yes, take Line 2.",
                            "audio_key": "ga_subway_2",
                        },
                        {
                            "speaker": "you",
                            "ko": "지하철 어디에서 타요?",
                            "romaji": "jihacheol eodieseo tayo?",
                            "en": "Where do I catch the subway?",
                            "audio_key": "ga_subway_3",
                        },
                        {
                            "speaker": "passerby",
                            "ko": "저기 2번 출구요.",
                            "romaji": "jeogi i-beon chulguyo.",
                            "en": "Over there, Exit 2.",
                            "audio_key": "ga_subway_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "Ask whether this goes to Gangnam Station.",
                            "options": ["강남역 가요?", "얼마예요?", "감사합니다"],
                            "accepted": [
                                {"ko": "강남역 가요?", "intents": ["does it go to gangnam station", "to gangnam", "gangnam station"]}
                            ],
                        },
                        {
                            "prompt_en": "Ask which line to take.",
                            "options": ["몇 호선이에요?", "어디예요?", "네"],
                            "accepted": [
                                {"ko": "몇 호선이에요?", "intents": ["which line", "what line is it", "which subway line"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "지하철", "en": "subway", "romaji": "jihacheol"},
                        {"ko": "역", "en": "station", "romaji": "yeok"},
                        {"ko": "호선", "en": "(subway) line", "romaji": "hoseon"},
                        {"ko": "어디", "en": "where", "romaji": "eodi"},
                    ],
                },
            },
            {
                "slug": "getting-around-subway-drill",
                "kind": "drill",
                "title": "Subway Drill",
                "order_index": 3,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "지하철",
                            "answer": "subway",
                            "choices": ["subway", "bus", "station"],
                        },
                        {
                            "type": "match",
                            "ko": "역",
                            "answer": "station",
                            "choices": ["station", "line", "where"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "ga_subway_2",
                            "answer": "2호선 타세요",
                            "choices": ["2호선 타세요", "강남역 가요?", "어디에서 타요?"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "ga_d_eodi",
                            "answer": "어디",
                            "choices": ["어디", "호선", "역"],
                        },
                    ]
                },
            },
            {
                "slug": "getting-around-bus",
                "kind": "scene",
                "title": "Where to Get Off the Bus",
                "order_index": 4,
                "content_json": {
                    "setting": "bus",
                    "character": "driver",
                    "lines": [
                        {
                            "speaker": "you",
                            "ko": "이 버스 서울역까지 가요?",
                            "romaji": "i beoseu seoulyeok-kkaji gayo?",
                            "en": "Does this bus go to Seoul Station?",
                            "audio_key": "ga_bus_1",
                        },
                        {
                            "speaker": "driver",
                            "ko": "네, 가요. 타세요.",
                            "romaji": "ne, gayo. taseyo.",
                            "en": "Yes, it does. Hop on.",
                            "audio_key": "ga_bus_2",
                        },
                        {
                            "speaker": "you",
                            "ko": "어디에서 내려요?",
                            "romaji": "eodieseo naeryeoyo?",
                            "en": "Where do I get off?",
                            "audio_key": "ga_bus_3",
                        },
                        {
                            "speaker": "driver",
                            "ko": "다음 역에서 내려요.",
                            "romaji": "daeum yeok-eseo naeryeoyo.",
                            "en": "Get off at the next stop.",
                            "audio_key": "ga_bus_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "Ask if this bus goes all the way to Seoul Station.",
                            "options": ["서울역까지 가요?", "얼마예요?", "감사합니다"],
                            "accepted": [
                                {"ko": "서울역까지 가요?", "intents": ["does it go to seoul station", "to seoul station", "all the way to seoul station"]}
                            ],
                        },
                        {
                            "prompt_en": "Ask where you should get off.",
                            "options": ["어디에서 내려요?", "어디 가세요?", "네"],
                            "accepted": [
                                {"ko": "어디에서 내려요?", "intents": ["where do i get off", "where to get off", "which stop"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "버스", "en": "bus", "romaji": "beoseu"},
                        {"ko": "까지", "en": "to/until", "romaji": "kkaji"},
                        {"ko": "내려요", "en": "get off", "romaji": "naeryeoyo"},
                    ],
                },
            },
            {
                "slug": "getting-around-bus-drill",
                "kind": "drill",
                "title": "Bus Drill",
                "order_index": 5,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "버스",
                            "answer": "bus",
                            "choices": ["bus", "subway", "station"],
                        },
                        {
                            "type": "match",
                            "ko": "내려요",
                            "answer": "get off",
                            "choices": ["get off", "get on", "to/until"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "ga_bus_3",
                            "answer": "어디에서 내려요?",
                            "choices": ["어디에서 내려요?", "서울역까지 가요?", "2호선 타세요"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "ga_d_kkaji",
                            "answer": "까지",
                            "choices": ["까지", "내려요", "버스"],
                        },
                    ]
                },
            },
            {
                "slug": "getting-around-boss",
                "kind": "boss",
                "title": "Boss: Find Your Line & Stop",
                "order_index": 6,
                "content_json": {
                    "goal_en": "Ask for directions to the right subway line and confirm your stop",
                    "persona": "transit_staff",
                    "level": "beginner",
                    "allowed_vocab": [
                        "안녕하세요",
                        "감사합니다",
                        "네",
                        "아니요",
                        "지하철",
                        "버스",
                        "역",
                        "호선",
                        "어디",
                        "어디에서 내려요?",
                        "내려요",
                        "까지",
                        "티머니",
                    ],
                    "success_criteria": "Learner asks which line to take and confirms where to get off",
                    "max_turns": 8,
                },
            },
        ],
    },
]
