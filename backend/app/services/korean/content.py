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
    # ------------------------------------------------------------------ #
    # Region 4 — Shopping                                                #
    # ------------------------------------------------------------------ #
    {
        "slug": "shopping",
        "title": "Shopping",
        "theme": "shopping",
        "order_index": 4,
        "nodes": [
            {
                "slug": "shopping-price",
                "kind": "scene",
                "title": "How Much Is This?",
                "order_index": 0,
                "content_json": {
                    "setting": "clothing shop",
                    "character": "clerk",
                    "lines": [
                        {
                            "speaker": "clerk",
                            "ko": "어서 오세요!",
                            "romaji": "eoseo oseyo!",
                            "en": "Welcome!",
                            "audio_key": "sh_price_1",
                        },
                        {
                            "speaker": "you",
                            "ko": "이거 얼마예요?",
                            "romaji": "igeo eolmayeyo?",
                            "en": "How much is this?",
                            "audio_key": "sh_price_2",
                        },
                        {
                            "speaker": "clerk",
                            "ko": "이만 원이에요.",
                            "romaji": "iman won-ieyo.",
                            "en": "It's 20,000 won.",
                            "audio_key": "sh_price_3",
                        },
                        {
                            "speaker": "you",
                            "ko": "저거는요?",
                            "romaji": "jeogeoneunyo?",
                            "en": "And that one?",
                            "audio_key": "sh_price_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "Point at an item and ask how much this one is.",
                            "options": ["이거 얼마예요?", "감사합니다", "네"],
                            "accepted": [
                                {"ko": "이거 얼마예요?", "intents": ["how much is this", "this price", "what's the price of this"]}
                            ],
                        },
                        {
                            "prompt_en": "Now ask about that one over there.",
                            "options": ["저거 얼마예요?", "이거 얼마예요?", "주세요"],
                            "accepted": [
                                {"ko": "저거 얼마예요?", "intents": ["how much is that", "that price", "what's the price of that"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "얼마예요", "en": "how much", "romaji": "eolmayeyo"},
                        {"ko": "이거", "en": "this (one)", "romaji": "igeo"},
                        {"ko": "저거", "en": "that (one)", "romaji": "jeogeo"},
                    ],
                },
            },
            {
                "slug": "shopping-price-drill",
                "kind": "drill",
                "title": "Price Drill",
                "order_index": 1,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "이거",
                            "answer": "this (one)",
                            "choices": ["this (one)", "that (one)", "how much"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "sh_price_2",
                            "answer": "이거 얼마예요?",
                            "choices": ["이거 얼마예요?", "저거 얼마예요?", "감사합니다"],
                        },
                        {
                            "type": "match",
                            "ko": "저거",
                            "answer": "that (one)",
                            "choices": ["that (one)", "this (one)", "card"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "sh_d_eolma",
                            "answer": "얼마예요",
                            "choices": ["얼마예요", "이거", "저거"],
                        },
                    ]
                },
            },
            {
                "slug": "shopping-size",
                "kind": "scene",
                "title": "A Different Size",
                "order_index": 2,
                "content_json": {
                    "setting": "clothing shop",
                    "character": "clerk",
                    "lines": [
                        {
                            "speaker": "you",
                            "ko": "이거 작아요. 큰 사이즈 있어요?",
                            "romaji": "igeo jagayo. keun saijeu isseoyo?",
                            "en": "This is small. Do you have a bigger size?",
                            "audio_key": "sh_size_1",
                        },
                        {
                            "speaker": "clerk",
                            "ko": "네, 여기 있어요.",
                            "romaji": "ne, yeogi isseoyo.",
                            "en": "Yes, here you go.",
                            "audio_key": "sh_size_2",
                        },
                        {
                            "speaker": "you",
                            "ko": "다른 색깔도 있어요?",
                            "romaji": "dareun saekkkal-do isseoyo?",
                            "en": "Do you have other colors too?",
                            "audio_key": "sh_size_3",
                        },
                        {
                            "speaker": "clerk",
                            "ko": "네, 검은색도 있어요.",
                            "romaji": "ne, geomeunsaek-do isseoyo.",
                            "en": "Yes, we have black too.",
                            "audio_key": "sh_size_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "This one is too small. Ask for a bigger size.",
                            "options": ["큰 사이즈 있어요?", "작은 사이즈 있어요?", "얼마예요?"],
                            "accepted": [
                                {"ko": "큰 사이즈 있어요?", "intents": ["bigger size", "do you have a bigger size", "a larger size"]},
                                {"ko": "작은 사이즈 있어요?", "intents": ["smaller size", "do you have a smaller size"]},
                            ],
                        },
                        {
                            "prompt_en": "Ask if they have another color.",
                            "options": ["다른 색깔 있어요?", "큰 사이즈 있어요?", "네"],
                            "accepted": [
                                {"ko": "다른 색깔 있어요?", "intents": ["another color", "other colors", "different color"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "사이즈", "en": "size", "romaji": "saijeu"},
                        {"ko": "색깔", "en": "color", "romaji": "saekkkal"},
                        {"ko": "작아요", "en": "(it's) small", "romaji": "jagayo"},
                        {"ko": "커요", "en": "(it's) big", "romaji": "keoyo"},
                    ],
                },
            },
            {
                "slug": "shopping-size-drill",
                "kind": "drill",
                "title": "Size Drill",
                "order_index": 3,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "사이즈",
                            "answer": "size",
                            "choices": ["size", "color", "card"],
                        },
                        {
                            "type": "match",
                            "ko": "작아요",
                            "answer": "(it's) small",
                            "choices": ["(it's) small", "(it's) big", "color"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "sh_d_saekkkal",
                            "answer": "색깔",
                            "choices": ["색깔", "사이즈", "커요"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "sh_d_keoyo",
                            "answer": "커요",
                            "choices": ["커요", "작아요", "사이즈"],
                        },
                    ]
                },
            },
            {
                "slug": "shopping-pay",
                "kind": "scene",
                "title": "Paying & a Bag",
                "order_index": 4,
                "content_json": {
                    "setting": "clothing shop",
                    "character": "clerk",
                    "lines": [
                        {
                            "speaker": "clerk",
                            "ko": "이거 주세요? 현금이요, 카드요?",
                            "romaji": "igeo juseyo? hyeon-geum-iyo, kadeu-yo?",
                            "en": "You'll take this? Cash or card?",
                            "audio_key": "sh_pay_1",
                        },
                        {
                            "speaker": "you",
                            "ko": "카드로 할게요.",
                            "romaji": "kadeu-ro halgeyo.",
                            "en": "I'll pay by card.",
                            "audio_key": "sh_pay_2",
                        },
                        {
                            "speaker": "you",
                            "ko": "봉투 주세요.",
                            "romaji": "bongtu juseyo.",
                            "en": "A bag, please.",
                            "audio_key": "sh_pay_3",
                        },
                        {
                            "speaker": "clerk",
                            "ko": "네, 감사합니다!",
                            "romaji": "ne, gamsahamnida!",
                            "en": "Sure, thank you!",
                            "audio_key": "sh_pay_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "They ask how you'll pay. Say you'll pay by card.",
                            "options": ["카드요", "현금이요", "네"],
                            "accepted": [
                                {"ko": "카드요", "intents": ["by card", "card", "pay by card"]},
                                {"ko": "현금이요", "intents": ["cash", "by cash", "pay cash"]},
                            ],
                        },
                        {
                            "prompt_en": "Ask for a bag.",
                            "options": ["봉투 주세요", "카드요", "감사합니다"],
                            "accepted": [
                                {"ko": "봉투 주세요", "intents": ["a bag please", "can i get a bag", "bag please"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "카드", "en": "card", "romaji": "kadeu"},
                        {"ko": "봉투", "en": "bag", "romaji": "bongtu"},
                        {"ko": "깎아 주세요", "en": "please give a discount", "romaji": "kkakka juseyo"},
                    ],
                },
            },
            {
                "slug": "shopping-pay-drill",
                "kind": "drill",
                "title": "Paying Drill",
                "order_index": 5,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "봉투",
                            "answer": "bag",
                            "choices": ["bag", "card", "size"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "sh_pay_3",
                            "answer": "봉투 주세요",
                            "choices": ["봉투 주세요", "카드로 할게요", "이거 얼마예요?"],
                        },
                        {
                            "type": "match",
                            "ko": "깎아 주세요",
                            "answer": "please give a discount",
                            "choices": ["please give a discount", "a bag please", "by card"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "sh_d_kadeu",
                            "answer": "카드",
                            "choices": ["카드", "봉투", "색깔"],
                        },
                    ]
                },
            },
            {
                "slug": "shopping-boss",
                "kind": "boss",
                "title": "Boss: Ask & Buy",
                "order_index": 6,
                "content_json": {
                    "goal_en": "Ask the price of an item and buy it",
                    "persona": "shopkeeper",
                    "level": "beginner",
                    "allowed_vocab": [
                        "안녕하세요",
                        "감사합니다",
                        "네",
                        "아니요",
                        "이거",
                        "저거",
                        "얼마예요?",
                        "사이즈",
                        "색깔",
                        "카드",
                        "카드요",
                        "봉투",
                        "봉투 주세요",
                        "깎아 주세요",
                    ],
                    "success_criteria": "Learner asks the price of an item and completes the purchase",
                    "max_turns": 8,
                },
            },
        ],
    },
    # ------------------------------------------------------------------ #
    # Region 5 — Stay                                                    #
    # ------------------------------------------------------------------ #
    {
        "slug": "stay",
        "title": "Stay",
        "theme": "stay",
        "order_index": 5,
        "nodes": [
            {
                "slug": "stay-checkin",
                "kind": "scene",
                "title": "Checking In",
                "order_index": 0,
                "content_json": {
                    "setting": "hotel front desk",
                    "character": "receptionist",
                    "lines": [
                        {
                            "speaker": "receptionist",
                            "ko": "안녕하세요, 예약하셨어요?",
                            "romaji": "annyeonghaseyo, yeyakhasyeosseoyo?",
                            "en": "Hello, do you have a reservation?",
                            "audio_key": "st_checkin_1",
                        },
                        {
                            "speaker": "you",
                            "ko": "네, 체크인이요.",
                            "romaji": "ne, chekeu-in-iyo.",
                            "en": "Yes, check-in, please.",
                            "audio_key": "st_checkin_2",
                        },
                        {
                            "speaker": "receptionist",
                            "ko": "성함이 어떻게 되세요?",
                            "romaji": "seonghami eotteoke doeseyo?",
                            "en": "What's your name?",
                            "audio_key": "st_checkin_3",
                        },
                        {
                            "speaker": "you",
                            "ko": "김민수예요. 예약 있어요.",
                            "romaji": "kim minsu-yeyo. yeyak isseoyo.",
                            "en": "It's Kim Minsu. I have a reservation.",
                            "audio_key": "st_checkin_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "The receptionist greets you. Tell them you'd like to check in.",
                            "options": ["체크인이요", "체크아웃이요", "감사합니다"],
                            "accepted": [
                                {"ko": "체크인이요", "intents": ["check in", "i want to check in", "check-in please"]}
                            ],
                        },
                        {
                            "prompt_en": "They ask for your name. Say you have a reservation.",
                            "options": ["예약 있어요", "예약 없어요", "얼마예요?"],
                            "accepted": [
                                {"ko": "예약 있어요", "intents": ["i have a reservation", "yes i have a booking", "there's a reservation"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "체크인", "en": "check-in", "romaji": "chekeu-in"},
                        {"ko": "예약", "en": "reservation", "romaji": "yeyak"},
                        {"ko": "있어요", "en": "have / there is", "romaji": "isseoyo"},
                    ],
                },
            },
            {
                "slug": "stay-checkin-drill",
                "kind": "drill",
                "title": "Check-in Drill",
                "order_index": 1,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "예약",
                            "answer": "reservation",
                            "choices": ["reservation", "check-in", "room"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "st_checkin_2",
                            "answer": "체크인이요",
                            "choices": ["체크인이요", "체크아웃이요", "예약 있어요"],
                        },
                        {
                            "type": "match",
                            "ko": "있어요",
                            "answer": "have / there is",
                            "choices": ["have / there is", "don't have", "reservation"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "st_d_yeyak",
                            "answer": "예약",
                            "choices": ["예약", "체크인", "방"],
                        },
                    ]
                },
            },
            {
                "slug": "stay-wifi",
                "kind": "scene",
                "title": "Asking for Wifi",
                "order_index": 2,
                "content_json": {
                    "setting": "hotel front desk",
                    "character": "receptionist",
                    "lines": [
                        {
                            "speaker": "you",
                            "ko": "와이파이 있어요?",
                            "romaji": "waipai isseoyo?",
                            "en": "Is there wifi?",
                            "audio_key": "st_wifi_1",
                        },
                        {
                            "speaker": "receptionist",
                            "ko": "네, 있어요.",
                            "romaji": "ne, isseoyo.",
                            "en": "Yes, there is.",
                            "audio_key": "st_wifi_2",
                        },
                        {
                            "speaker": "you",
                            "ko": "비밀번호 뭐예요?",
                            "romaji": "bimilbeonho mwoyeyo?",
                            "en": "What's the password?",
                            "audio_key": "st_wifi_3",
                        },
                        {
                            "speaker": "receptionist",
                            "ko": "방 번호예요.",
                            "romaji": "bang beonho-yeyo.",
                            "en": "It's your room number.",
                            "audio_key": "st_wifi_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "Ask the receptionist if there is wifi.",
                            "options": ["와이파이 있어요?", "방 있어요?", "얼마예요?"],
                            "accepted": [
                                {"ko": "와이파이 있어요?", "intents": ["is there wifi", "do you have wifi", "wifi"]}
                            ],
                        },
                        {
                            "prompt_en": "Now ask for the wifi password.",
                            "options": ["비밀번호 뭐예요?", "방 번호 뭐예요?", "감사합니다"],
                            "accepted": [
                                {"ko": "비밀번호 뭐예요?", "intents": ["what's the password", "the wifi password", "password please"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "와이파이", "en": "wifi", "romaji": "waipai"},
                        {"ko": "비밀번호", "en": "password", "romaji": "bimilbeonho"},
                        {"ko": "방", "en": "room", "romaji": "bang"},
                    ],
                },
            },
            {
                "slug": "stay-wifi-drill",
                "kind": "drill",
                "title": "Wifi Drill",
                "order_index": 3,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "비밀번호",
                            "answer": "password",
                            "choices": ["password", "wifi", "room"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "st_wifi_1",
                            "answer": "와이파이 있어요?",
                            "choices": ["와이파이 있어요?", "비밀번호 뭐예요?", "방 번호예요"],
                        },
                        {
                            "type": "match",
                            "ko": "방",
                            "answer": "room",
                            "choices": ["room", "password", "reservation"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "st_d_waipai",
                            "answer": "와이파이",
                            "choices": ["와이파이", "비밀번호", "수건"],
                        },
                    ]
                },
            },
            {
                "slug": "stay-checkout",
                "kind": "scene",
                "title": "Checkout & a Towel",
                "order_index": 4,
                "content_json": {
                    "setting": "hotel front desk",
                    "character": "receptionist",
                    "lines": [
                        {
                            "speaker": "you",
                            "ko": "체크아웃 몇 시예요?",
                            "romaji": "chekeu-aut myeot si-yeyo?",
                            "en": "What time is checkout?",
                            "audio_key": "st_checkout_1",
                        },
                        {
                            "speaker": "receptionist",
                            "ko": "열한 시예요.",
                            "romaji": "yeolhan si-yeyo.",
                            "en": "It's eleven o'clock.",
                            "audio_key": "st_checkout_2",
                        },
                        {
                            "speaker": "you",
                            "ko": "수건 있어요? 수건 더 주세요.",
                            "romaji": "sugeon isseoyo? sugeon deo juseyo.",
                            "en": "Are there towels? Please give me more towels.",
                            "audio_key": "st_checkout_3",
                        },
                        {
                            "speaker": "receptionist",
                            "ko": "네, 카드키 주세요.",
                            "romaji": "ne, kadeuki juseyo.",
                            "en": "Sure, please give me the key card.",
                            "audio_key": "st_checkout_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "Ask what time checkout is.",
                            "options": ["체크아웃 몇 시예요?", "체크인 몇 시예요?", "얼마예요?"],
                            "accepted": [
                                {"ko": "체크아웃 몇 시예요?", "intents": ["what time is checkout", "checkout time", "when is checkout"]}
                            ],
                        },
                        {
                            "prompt_en": "Ask for an extra towel.",
                            "options": ["수건 더 주세요", "카드키 주세요", "네"],
                            "accepted": [
                                {"ko": "수건 더 주세요", "intents": ["more towels please", "an extra towel", "another towel"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "몇 시", "en": "what time", "romaji": "myeot si"},
                        {"ko": "체크아웃", "en": "checkout", "romaji": "chekeu-aut"},
                        {"ko": "수건", "en": "towel", "romaji": "sugeon"},
                        {"ko": "카드키", "en": "key card", "romaji": "kadeuki"},
                    ],
                },
            },
            {
                "slug": "stay-checkout-drill",
                "kind": "drill",
                "title": "Checkout Drill",
                "order_index": 5,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "수건",
                            "answer": "towel",
                            "choices": ["towel", "key card", "room"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "st_checkout_1",
                            "answer": "체크아웃 몇 시예요?",
                            "choices": ["체크아웃 몇 시예요?", "와이파이 있어요?", "수건 더 주세요"],
                        },
                        {
                            "type": "match",
                            "ko": "몇 시",
                            "answer": "what time",
                            "choices": ["what time", "checkout", "towel"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "st_d_kadeuki",
                            "answer": "카드키",
                            "choices": ["카드키", "수건", "체크아웃"],
                        },
                    ]
                },
            },
            {
                "slug": "stay-boss",
                "kind": "boss",
                "title": "Boss: Check In & Wifi",
                "order_index": 6,
                "content_json": {
                    "goal_en": "Check in and ask for the wifi password",
                    "persona": "receptionist",
                    "level": "beginner",
                    "allowed_vocab": [
                        "안녕하세요",
                        "감사합니다",
                        "네",
                        "아니요",
                        "체크인",
                        "체크인이요",
                        "예약",
                        "있어요",
                        "방",
                        "와이파이",
                        "비밀번호",
                        "몇 시",
                        "체크아웃",
                        "수건",
                        "카드키",
                    ],
                    "success_criteria": "Learner checks in with their reservation and asks for the wifi password",
                    "max_turns": 8,
                },
            },
        ],
    },
    # ------------------------------------------------------------------ #
    # Region 6 — Restaurant                                              #
    # ------------------------------------------------------------------ #
    {
        "slug": "restaurant",
        "title": "Restaurant",
        "theme": "restaurant",
        "order_index": 6,
        "nodes": [
            {
                "slug": "restaurant-seat",
                "kind": "scene",
                "title": "Getting a Table",
                "order_index": 0,
                "content_json": {
                    "setting": "restaurant entrance",
                    "character": "server",
                    "lines": [
                        {
                            "speaker": "server",
                            "ko": "어서 오세요! 몇 명이세요?",
                            "romaji": "eoseo oseyo! myeot myeong-iseyo?",
                            "en": "Welcome! How many people?",
                            "audio_key": "re_seat_1",
                        },
                        {
                            "speaker": "you",
                            "ko": "두 명이요.",
                            "romaji": "du myeong-iyo.",
                            "en": "Two people.",
                            "audio_key": "re_seat_2",
                        },
                        {
                            "speaker": "server",
                            "ko": "이쪽으로 오세요.",
                            "romaji": "ijjok-euro oseyo.",
                            "en": "This way, please.",
                            "audio_key": "re_seat_3",
                        },
                        {
                            "speaker": "you",
                            "ko": "메뉴 주세요.",
                            "romaji": "menyu juseyo.",
                            "en": "The menu, please.",
                            "audio_key": "re_seat_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "The server asks how many people. You're a party of two.",
                            "options": ["두 명이요", "한 명이요", "감사합니다"],
                            "accepted": [
                                {"ko": "두 명이요", "intents": ["two people", "for two", "table for two"]},
                                {"ko": "한 명이요", "intents": ["one person", "just me", "table for one"]},
                            ],
                        },
                        {
                            "prompt_en": "You've sat down. Ask for the menu.",
                            "options": ["메뉴 주세요", "계산서 주세요", "여기요"],
                            "accepted": [
                                {"ko": "메뉴 주세요", "intents": ["the menu please", "can i see the menu", "menu please"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "메뉴", "en": "menu", "romaji": "menyu"},
                        {"ko": "몇 명", "en": "how many people", "romaji": "myeot myeong"},
                        {"ko": "여기요", "en": "excuse me (calling the server)", "romaji": "yeogiyo"},
                    ],
                },
            },
            {
                "slug": "restaurant-seat-drill",
                "kind": "drill",
                "title": "Seating Drill",
                "order_index": 1,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "메뉴",
                            "answer": "menu",
                            "choices": ["menu", "the bill", "water"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "re_seat_1",
                            "answer": "몇 명이세요?",
                            "choices": ["몇 명이세요?", "메뉴 주세요", "여기요"],
                        },
                        {
                            "type": "match",
                            "ko": "몇 명",
                            "answer": "how many people",
                            "choices": ["how many people", "the menu", "delicious"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "re_d_yeogiyo",
                            "answer": "여기요",
                            "choices": ["여기요", "메뉴", "몇 명"],
                        },
                    ]
                },
            },
            {
                "slug": "restaurant-order",
                "kind": "scene",
                "title": "Ordering Food",
                "order_index": 2,
                "content_json": {
                    "setting": "restaurant table",
                    "character": "server",
                    "lines": [
                        {
                            "speaker": "you",
                            "ko": "여기요, 추천 좀 해 주세요.",
                            "romaji": "yeogiyo, chucheon jom hae juseyo.",
                            "en": "Excuse me, please recommend something.",
                            "audio_key": "re_order_1",
                        },
                        {
                            "speaker": "server",
                            "ko": "이게 맛있어요. 근데 좀 매워요.",
                            "romaji": "ige masisseoyo. geunde jom maewoyo.",
                            "en": "This is delicious. But it's a bit spicy.",
                            "audio_key": "re_order_2",
                        },
                        {
                            "speaker": "you",
                            "ko": "안 매운 거 주세요.",
                            "romaji": "an maeun geo juseyo.",
                            "en": "Give me the not-spicy one, please.",
                            "audio_key": "re_order_3",
                        },
                        {
                            "speaker": "server",
                            "ko": "네, 물도 드릴게요.",
                            "romaji": "ne, mul-do deurilgeyo.",
                            "en": "Okay, I'll bring water too.",
                            "audio_key": "re_order_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "Ask the server for a recommendation.",
                            "options": ["추천 좀 해 주세요", "계산서 주세요", "감사합니다"],
                            "accepted": [
                                {"ko": "추천 좀 해 주세요", "intents": ["please recommend something", "what do you recommend", "a recommendation please"]}
                            ],
                        },
                        {
                            "prompt_en": "It's too spicy for you. Order the not-spicy one.",
                            "options": ["안 매운 거 주세요", "물 주세요", "메뉴 주세요"],
                            "accepted": [
                                {"ko": "안 매운 거 주세요", "intents": ["the not-spicy one please", "something not spicy", "not spicy please"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "추천", "en": "recommendation", "romaji": "chucheon"},
                        {"ko": "매워요", "en": "(it's) spicy", "romaji": "maewoyo"},
                        {"ko": "안 매운 거", "en": "the not-spicy one", "romaji": "an maeun geo"},
                        {"ko": "물", "en": "water", "romaji": "mul"},
                    ],
                },
            },
            {
                "slug": "restaurant-order-drill",
                "kind": "drill",
                "title": "Ordering Drill",
                "order_index": 3,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "추천",
                            "answer": "recommendation",
                            "choices": ["recommendation", "the bill", "water"],
                        },
                        {
                            "type": "match",
                            "ko": "매워요",
                            "answer": "(it's) spicy",
                            "choices": ["(it's) spicy", "(it's) delicious", "water"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "re_order_3",
                            "answer": "안 매운 거 주세요",
                            "choices": ["안 매운 거 주세요", "추천 좀 해 주세요", "물 주세요"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "re_d_mul",
                            "answer": "물",
                            "choices": ["물", "추천", "메뉴"],
                        },
                    ]
                },
            },
            {
                "slug": "restaurant-bill",
                "kind": "scene",
                "title": "It Was Delicious",
                "order_index": 4,
                "content_json": {
                    "setting": "restaurant table",
                    "character": "server",
                    "lines": [
                        {
                            "speaker": "server",
                            "ko": "맛있게 드셨어요?",
                            "romaji": "masitge deusyeosseoyo?",
                            "en": "Did you enjoy your meal?",
                            "audio_key": "re_bill_1",
                        },
                        {
                            "speaker": "you",
                            "ko": "네, 정말 맛있어요!",
                            "romaji": "ne, jeongmal masisseoyo!",
                            "en": "Yes, it's really delicious!",
                            "audio_key": "re_bill_2",
                        },
                        {
                            "speaker": "you",
                            "ko": "계산서 주세요.",
                            "romaji": "gyesanseo juseyo.",
                            "en": "The bill, please.",
                            "audio_key": "re_bill_3",
                        },
                        {
                            "speaker": "server",
                            "ko": "네, 여기요. 감사합니다!",
                            "romaji": "ne, yeogiyo. gamsahamnida!",
                            "en": "Sure, here it is. Thank you!",
                            "audio_key": "re_bill_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "The server asks if you enjoyed it. Say it was delicious.",
                            "options": ["맛있어요", "매워요", "감사합니다"],
                            "accepted": [
                                {"ko": "맛있어요", "intents": ["it's delicious", "it was delicious", "very good"]}
                            ],
                        },
                        {
                            "prompt_en": "You're done eating. Ask for the bill.",
                            "options": ["계산서 주세요", "메뉴 주세요", "물 주세요"],
                            "accepted": [
                                {"ko": "계산서 주세요", "intents": ["the bill please", "can i get the check", "check please"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "맛있어요", "en": "(it's) delicious", "romaji": "masisseoyo"},
                        {"ko": "계산서", "en": "the bill", "romaji": "gyesanseo"},
                        {"ko": "주문", "en": "order", "romaji": "jumun"},
                    ],
                },
            },
            {
                "slug": "restaurant-bill-drill",
                "kind": "drill",
                "title": "Bill Drill",
                "order_index": 5,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "계산서",
                            "answer": "the bill",
                            "choices": ["the bill", "the menu", "recommendation"],
                        },
                        {
                            "type": "match",
                            "ko": "맛있어요",
                            "answer": "(it's) delicious",
                            "choices": ["(it's) delicious", "(it's) spicy", "order"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "re_bill_3",
                            "answer": "계산서 주세요",
                            "choices": ["계산서 주세요", "메뉴 주세요", "안 매운 거 주세요"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "re_d_jumun",
                            "answer": "주문",
                            "choices": ["주문", "계산서", "물"],
                        },
                    ]
                },
            },
            {
                "slug": "restaurant-boss",
                "kind": "boss",
                "title": "Boss: Order & Pay",
                "order_index": 6,
                "content_json": {
                    "goal_en": "Order a dish and ask for the bill",
                    "persona": "server",
                    "level": "beginner",
                    "allowed_vocab": [
                        "안녕하세요",
                        "감사합니다",
                        "네",
                        "아니요",
                        "여기요",
                        "메뉴",
                        "주문",
                        "추천",
                        "매워요",
                        "안 매운 거",
                        "물",
                        "몇 명",
                        "맛있어요",
                        "계산서",
                        "주세요",
                    ],
                    "success_criteria": "Learner orders a dish and asks for the bill",
                    "max_turns": 8,
                },
            },
        ],
    },
    # ------------------------------------------------------------------ #
    # Region 7 — Making Friends                                         #
    # ------------------------------------------------------------------ #
    {
        "slug": "making-friends",
        "title": "Making Friends",
        "theme": "friends",
        "order_index": 7,
        "nodes": [
            {
                "slug": "making-friends-intro",
                "kind": "scene",
                "title": "Nice to Meet You",
                "order_index": 0,
                "content_json": {
                    "setting": "language exchange meetup",
                    "character": "friend",
                    "lines": [
                        {
                            "speaker": "friend",
                            "ko": "안녕하세요! 이름이 뭐예요?",
                            "romaji": "annyeonghaseyo! ireum-i mwoyeyo?",
                            "en": "Hi! What's your name?",
                            "audio_key": "fr_intro_1",
                        },
                        {
                            "speaker": "you",
                            "ko": "저는 마이클이에요. 만나서 반가워요.",
                            "romaji": "jeoneun maikeul-ieyo. mannaseo bangawoyo.",
                            "en": "I'm Michael. Nice to meet you.",
                            "audio_key": "fr_intro_2",
                        },
                        {
                            "speaker": "friend",
                            "ko": "반가워요! 어느 나라 사람이에요?",
                            "romaji": "bangawoyo! eoneu nara saram-ieyo?",
                            "en": "Nice to meet you! Which country are you from?",
                            "audio_key": "fr_intro_3",
                        },
                        {
                            "speaker": "you",
                            "ko": "저는 미국 사람이에요.",
                            "romaji": "jeoneun miguk saram-ieyo.",
                            "en": "I'm American.",
                            "audio_key": "fr_intro_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "Your new friend asks your name. Say nice to meet you.",
                            "options": ["만나서 반가워요", "감사합니다", "얼마예요?"],
                            "accepted": [
                                {"ko": "만나서 반가워요", "intents": ["nice to meet you", "pleased to meet you", "good to meet you"]}
                            ],
                        },
                        {
                            "prompt_en": "They ask which country you're from. Say where you're from (e.g. 저는 미국 사람이에요).",
                            "options": ["저는 미국 사람이에요", "저는 학생이에요", "네"],
                            "accepted": [
                                {"ko": "저는 미국 사람이에요", "intents": ["i'm american", "i'm from the usa", "i am from america"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "이름", "en": "name", "romaji": "ireum"},
                        {"ko": "저는", "en": "I / as for me", "romaji": "jeoneun"},
                        {"ko": "만나서 반가워요", "en": "nice to meet you", "romaji": "mannaseo bangawoyo"},
                    ],
                },
            },
            {
                "slug": "making-friends-intro-drill",
                "kind": "drill",
                "title": "Intro Drill",
                "order_index": 1,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "이름",
                            "answer": "name",
                            "choices": ["name", "hobby", "age"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "fr_intro_1",
                            "answer": "이름이 뭐예요?",
                            "choices": ["이름이 뭐예요?", "어느 나라 사람이에요?", "취미가 뭐예요?"],
                        },
                        {
                            "type": "match",
                            "ko": "만나서 반가워요",
                            "answer": "nice to meet you",
                            "choices": ["nice to meet you", "thank you", "which country"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "fr_d_jeoneun",
                            "answer": "저는",
                            "choices": ["저는", "이름", "친구"],
                        },
                    ]
                },
            },
            {
                "slug": "making-friends-hobby",
                "kind": "scene",
                "title": "What's Your Hobby?",
                "order_index": 2,
                "content_json": {
                    "setting": "café table",
                    "character": "friend",
                    "lines": [
                        {
                            "speaker": "friend",
                            "ko": "취미가 뭐예요?",
                            "romaji": "chwimi-ga mwoyeyo?",
                            "en": "What's your hobby?",
                            "audio_key": "fr_hobby_1",
                        },
                        {
                            "speaker": "you",
                            "ko": "저는 영화를 좋아해요.",
                            "romaji": "jeoneun yeonghwa-reul joahaeyo.",
                            "en": "I like movies.",
                            "audio_key": "fr_hobby_2",
                        },
                        {
                            "speaker": "friend",
                            "ko": "저도요! 저는 음악을 좋아해요.",
                            "romaji": "jeodoyo! jeoneun eumak-eul joahaeyo.",
                            "en": "Me too! I like music.",
                            "audio_key": "fr_hobby_3",
                        },
                        {
                            "speaker": "you",
                            "ko": "와, 우리 친구해요!",
                            "romaji": "wa, uri chinguhaeyo!",
                            "en": "Wow, let's be friends!",
                            "audio_key": "fr_hobby_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "They ask your hobby. Say you like movies.",
                            "options": ["저는 영화를 좋아해요", "저는 미국 사람이에요", "얼마예요?"],
                            "accepted": [
                                {"ko": "저는 영화를 좋아해요", "intents": ["i like movies", "my hobby is movies", "i love films"]}
                            ],
                        },
                        {
                            "prompt_en": "Say you like music too.",
                            "options": ["저는 음악을 좋아해요", "저는 친구예요", "네"],
                            "accepted": [
                                {"ko": "저는 음악을 좋아해요", "intents": ["i like music", "i love music", "music too"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "취미", "en": "hobby", "romaji": "chwimi"},
                        {"ko": "좋아해요", "en": "(I) like", "romaji": "joahaeyo"},
                        {"ko": "친구", "en": "friend", "romaji": "chingu"},
                    ],
                },
            },
            {
                "slug": "making-friends-hobby-drill",
                "kind": "drill",
                "title": "Hobby Drill",
                "order_index": 3,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "취미",
                            "answer": "hobby",
                            "choices": ["hobby", "name", "friend"],
                        },
                        {
                            "type": "match",
                            "ko": "좋아해요",
                            "answer": "(I) like",
                            "choices": ["(I) like", "nice to meet you", "name"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "fr_hobby_2",
                            "answer": "저는 영화를 좋아해요",
                            "choices": ["저는 영화를 좋아해요", "취미가 뭐예요?", "이름이 뭐예요?"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "fr_d_chingu",
                            "answer": "친구",
                            "choices": ["친구", "취미", "이름"],
                        },
                    ]
                },
            },
            {
                "slug": "making-friends-kakao",
                "kind": "scene",
                "title": "Let's Exchange KakaoTalk",
                "order_index": 4,
                "content_json": {
                    "setting": "café table",
                    "character": "friend",
                    "lines": [
                        {
                            "speaker": "friend",
                            "ko": "나이가 어떻게 돼요?",
                            "romaji": "nai-ga eotteoke dwaeyo?",
                            "en": "How old are you?",
                            "audio_key": "fr_kakao_1",
                        },
                        {
                            "speaker": "you",
                            "ko": "저는 스물다섯 살이에요.",
                            "romaji": "jeoneun seumuldaseot sal-ieyo.",
                            "en": "I'm twenty-five years old.",
                            "audio_key": "fr_kakao_2",
                        },
                        {
                            "speaker": "you",
                            "ko": "우리 카톡 해요!",
                            "romaji": "uri katok haeyo!",
                            "en": "Let's exchange KakaoTalk!",
                            "audio_key": "fr_kakao_3",
                        },
                        {
                            "speaker": "friend",
                            "ko": "좋아요! 카톡 아이디 뭐예요?",
                            "romaji": "joayo! katok aidi mwoyeyo?",
                            "en": "Great! What's your KakaoTalk ID?",
                            "audio_key": "fr_kakao_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "They ask your age. Say how old you are (e.g. 저는 스물다섯 살이에요).",
                            "options": ["저는 스물다섯 살이에요", "저는 미국 사람이에요", "얼마예요?"],
                            "accepted": [
                                {"ko": "저는 스물다섯 살이에요", "intents": ["i'm twenty-five", "i am 25 years old", "my age is twenty-five"]}
                            ],
                        },
                        {
                            "prompt_en": "Ask to exchange KakaoTalk.",
                            "options": ["우리 카톡 해요", "메뉴 주세요", "감사합니다"],
                            "accepted": [
                                {"ko": "우리 카톡 해요", "intents": ["let's exchange kakaotalk", "let's add kakao", "let's do kakaotalk"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "나이", "en": "age", "romaji": "nai"},
                        {"ko": "살", "en": "years (of age)", "romaji": "sal"},
                        {"ko": "카톡", "en": "KakaoTalk", "romaji": "katok"},
                    ],
                },
            },
            {
                "slug": "making-friends-kakao-drill",
                "kind": "drill",
                "title": "KakaoTalk Drill",
                "order_index": 5,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "카톡",
                            "answer": "KakaoTalk",
                            "choices": ["KakaoTalk", "hobby", "friend"],
                        },
                        {
                            "type": "match",
                            "ko": "나이",
                            "answer": "age",
                            "choices": ["age", "name", "years (of age)"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "fr_kakao_3",
                            "answer": "우리 카톡 해요!",
                            "choices": ["우리 카톡 해요!", "나이가 어떻게 돼요?", "취미가 뭐예요?"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "fr_d_sal",
                            "answer": "살",
                            "choices": ["살", "나이", "카톡"],
                        },
                    ]
                },
            },
            {
                "slug": "making-friends-boss",
                "kind": "boss",
                "title": "Boss: Introduce Yourself",
                "order_index": 6,
                "content_json": {
                    "goal_en": "Introduce yourself and exchange KakaoTalk",
                    "persona": "friend",
                    "level": "beginner",
                    "allowed_vocab": [
                        "안녕하세요",
                        "감사합니다",
                        "네",
                        "아니요",
                        "이름",
                        "저는",
                        "어느 나라",
                        "취미",
                        "좋아해요",
                        "카톡",
                        "만나서 반가워요",
                        "친구",
                        "나이",
                        "살",
                    ],
                    "success_criteria": "Learner introduces themselves and asks to exchange KakaoTalk",
                    "max_turns": 8,
                },
            },
        ],
    },
    # ------------------------------------------------------------------ #
    # Region 8 — Living Here                                            #
    # ------------------------------------------------------------------ #
    {
        "slug": "living-here",
        "title": "Living Here",
        "theme": "living",
        "order_index": 8,
        "nodes": [
            {
                "slug": "living-here-pharmacy",
                "kind": "scene",
                "title": "At the Pharmacy",
                "order_index": 0,
                "content_json": {
                    "setting": "pharmacy",
                    "character": "pharmacist",
                    "lines": [
                        {
                            "speaker": "pharmacist",
                            "ko": "어서 오세요. 어디가 아파요?",
                            "romaji": "eoseo oseyo. eodiga apayo?",
                            "en": "Welcome. Where does it hurt?",
                            "audio_key": "lv_pharmacy_1",
                        },
                        {
                            "speaker": "you",
                            "ko": "감기예요. 머리가 아파요.",
                            "romaji": "gamgi-yeyo. meori-ga apayo.",
                            "en": "I have a cold. My head hurts.",
                            "audio_key": "lv_pharmacy_2",
                        },
                        {
                            "speaker": "you",
                            "ko": "감기약 주세요.",
                            "romaji": "gamgiyak juseyo.",
                            "en": "Please give me cold medicine.",
                            "audio_key": "lv_pharmacy_3",
                        },
                        {
                            "speaker": "pharmacist",
                            "ko": "네, 여기 있어요.",
                            "romaji": "ne, yeogi isseoyo.",
                            "en": "Sure, here you go.",
                            "audio_key": "lv_pharmacy_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "The pharmacist asks where it hurts. Say you have a cold.",
                            "options": ["감기예요", "택배예요", "감사합니다"],
                            "accepted": [
                                {"ko": "감기예요", "intents": ["i have a cold", "it's a cold", "a cold"]}
                            ],
                        },
                        {
                            "prompt_en": "Ask the pharmacist for medicine.",
                            "options": ["약 주세요", "병원 어디예요?", "네"],
                            "accepted": [
                                {"ko": "약 주세요", "intents": ["please give me medicine", "medicine please", "i need medicine"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "약", "en": "medicine", "romaji": "yak"},
                        {"ko": "감기", "en": "cold", "romaji": "gamgi"},
                        {"ko": "머리", "en": "head", "romaji": "meori"},
                    ],
                },
            },
            {
                "slug": "living-here-pharmacy-drill",
                "kind": "drill",
                "title": "Pharmacy Drill",
                "order_index": 1,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "약",
                            "answer": "medicine",
                            "choices": ["medicine", "cold", "head"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "lv_pharmacy_3",
                            "answer": "감기약 주세요",
                            "choices": ["감기약 주세요", "머리가 아파요", "병원 어디예요?"],
                        },
                        {
                            "type": "match",
                            "ko": "감기",
                            "answer": "cold",
                            "choices": ["cold", "medicine", "fever"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "lv_d_meori",
                            "answer": "머리",
                            "choices": ["머리", "약", "감기"],
                        },
                    ]
                },
            },
            {
                "slug": "living-here-clinic",
                "kind": "scene",
                "title": "At the Clinic",
                "order_index": 2,
                "content_json": {
                    "setting": "clinic",
                    "character": "nurse",
                    "lines": [
                        {
                            "speaker": "nurse",
                            "ko": "어디가 아파요?",
                            "romaji": "eodiga apayo?",
                            "en": "Where does it hurt?",
                            "audio_key": "lv_clinic_1",
                        },
                        {
                            "speaker": "you",
                            "ko": "배가 아파요. 열도 있어요.",
                            "romaji": "bae-ga apayo. yeol-do isseoyo.",
                            "en": "My stomach hurts. I also have a fever.",
                            "audio_key": "lv_clinic_2",
                        },
                        {
                            "speaker": "nurse",
                            "ko": "처방전 드릴게요.",
                            "romaji": "cheobangjeon deurilgeyo.",
                            "en": "I'll give you a prescription.",
                            "audio_key": "lv_clinic_3",
                        },
                        {
                            "speaker": "you",
                            "ko": "감사합니다.",
                            "romaji": "gamsahamnida.",
                            "en": "Thank you.",
                            "audio_key": "lv_clinic_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "The nurse asks where it hurts. Say your stomach hurts.",
                            "options": ["배가 아파요", "머리가 아파요", "감사합니다"],
                            "accepted": [
                                {"ko": "배가 아파요", "intents": ["my stomach hurts", "stomachache", "my belly hurts"]},
                                {"ko": "머리가 아파요", "intents": ["my head hurts", "headache"]},
                            ],
                        },
                        {
                            "prompt_en": "Tell the nurse you have a fever.",
                            "options": ["열이 있어요", "처방전 있어요", "네"],
                            "accepted": [
                                {"ko": "열이 있어요", "intents": ["i have a fever", "i'm running a fever", "fever"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "아파요", "en": "(it) hurts", "romaji": "apayo"},
                        {"ko": "배", "en": "stomach / belly", "romaji": "bae"},
                        {"ko": "병원", "en": "hospital / clinic", "romaji": "byeongwon"},
                        {"ko": "열", "en": "fever", "romaji": "yeol"},
                    ],
                },
            },
            {
                "slug": "living-here-clinic-drill",
                "kind": "drill",
                "title": "Clinic Drill",
                "order_index": 3,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "병원",
                            "answer": "hospital / clinic",
                            "choices": ["hospital / clinic", "pharmacy", "fever"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "lv_clinic_2",
                            "answer": "배가 아파요",
                            "choices": ["배가 아파요", "머리가 아파요", "열도 있어요"],
                        },
                        {
                            "type": "match",
                            "ko": "열",
                            "answer": "fever",
                            "choices": ["fever", "stomach / belly", "head"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "lv_d_bae",
                            "answer": "배",
                            "choices": ["배", "열", "병원"],
                        },
                    ]
                },
            },
            {
                "slug": "living-here-delivery",
                "kind": "scene",
                "title": "A Delivery Arrives",
                "order_index": 4,
                "content_json": {
                    "setting": "apartment door",
                    "character": "courier",
                    "lines": [
                        {
                            "speaker": "courier",
                            "ko": "택배 왔어요!",
                            "romaji": "taekbae wasseoyo!",
                            "en": "A delivery is here!",
                            "audio_key": "lv_delivery_1",
                        },
                        {
                            "speaker": "courier",
                            "ko": "김민수 씨 맞아요?",
                            "romaji": "kim minsu ssi majayo?",
                            "en": "Is this Kim Minsu?",
                            "audio_key": "lv_delivery_2",
                        },
                        {
                            "speaker": "you",
                            "ko": "네, 제 거예요.",
                            "romaji": "ne, je geo-yeyo.",
                            "en": "Yes, it's mine.",
                            "audio_key": "lv_delivery_3",
                        },
                        {
                            "speaker": "you",
                            "ko": "감사합니다!",
                            "romaji": "gamsahamnida!",
                            "en": "Thank you!",
                            "audio_key": "lv_delivery_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "The courier asks if the package is yours. Confirm it's yours.",
                            "options": ["네, 제 거예요", "아니요", "얼마예요?"],
                            "accepted": [
                                {"ko": "네, 제 거예요", "intents": ["yes it's mine", "that's mine", "yes that's me"]}
                            ],
                        },
                        {
                            "prompt_en": "Thank the courier for the delivery.",
                            "options": ["감사합니다", "택배예요", "아파요"],
                            "accepted": [
                                {"ko": "감사합니다", "intents": ["thank you", "thanks", "thank you for the delivery"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "처방전", "en": "prescription", "romaji": "cheobangjeon"},
                        {"ko": "택배", "en": "delivery package", "romaji": "taekbae"},
                    ],
                },
            },
            {
                "slug": "living-here-delivery-drill",
                "kind": "drill",
                "title": "Delivery Drill",
                "order_index": 5,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "택배",
                            "answer": "delivery package",
                            "choices": ["delivery package", "prescription", "medicine"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "lv_delivery_1",
                            "answer": "택배 왔어요!",
                            "choices": ["택배 왔어요!", "어디가 아파요?", "처방전 드릴게요"],
                        },
                        {
                            "type": "match",
                            "ko": "처방전",
                            "answer": "prescription",
                            "choices": ["prescription", "delivery package", "fever"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "lv_d_taekbae",
                            "answer": "택배",
                            "choices": ["택배", "처방전", "약"],
                        },
                    ]
                },
            },
            {
                "slug": "living-here-boss",
                "kind": "boss",
                "title": "Boss: Buy Cold Medicine",
                "order_index": 6,
                "content_json": {
                    "goal_en": "Buy cold medicine at the pharmacy",
                    "persona": "pharmacist",
                    "level": "beginner",
                    "allowed_vocab": [
                        "안녕하세요",
                        "감사합니다",
                        "네",
                        "아니요",
                        "약",
                        "감기",
                        "아파요",
                        "머리",
                        "배",
                        "병원",
                        "열",
                        "처방전",
                        "택배",
                        "주세요",
                    ],
                    "success_criteria": "Learner says they have a cold and asks for cold medicine",
                    "max_turns": 8,
                },
            },
        ],
    },
    # ------------------------------------------------------------------ #
    # Region 9 — Intermediate (capstone: past & future tense)           #
    # ------------------------------------------------------------------ #
    {
        "slug": "intermediate",
        "title": "Intermediate",
        "theme": "intermediate",
        "order_index": 9,
        "nodes": [
            {
                "slug": "intermediate-yesterday",
                "kind": "scene",
                "title": "What Did You Do Yesterday?",
                "order_index": 0,
                "content_json": {
                    "setting": "café table",
                    "character": "friend",
                    "lines": [
                        {
                            "speaker": "friend",
                            "ko": "어제 뭐 했어요?",
                            "romaji": "eoje mwo haesseoyo?",
                            "en": "What did you do yesterday?",
                            "audio_key": "im_yesterday_1",
                        },
                        {
                            "speaker": "you",
                            "ko": "친구를 만났어요. 영화도 봤어요.",
                            "romaji": "chingu-reul mannasseoyo. yeonghwa-do bwasseoyo.",
                            "en": "I met a friend. I watched a movie too.",
                            "audio_key": "im_yesterday_2",
                        },
                        {
                            "speaker": "friend",
                            "ko": "와, 재미있었어요?",
                            "romaji": "wa, jaemiisseosseoyo?",
                            "en": "Wow, was it fun?",
                            "audio_key": "im_yesterday_3",
                        },
                        {
                            "speaker": "you",
                            "ko": "네, 정말 재미있었어요!",
                            "romaji": "ne, jeongmal jaemiisseosseoyo!",
                            "en": "Yes, it was really fun!",
                            "audio_key": "im_yesterday_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "Your friend asks what you did yesterday. Say you went home (past tense).",
                            "options": ["집에 갔어요", "집에 가요", "감사합니다"],
                            "accepted": [
                                {"ko": "집에 갔어요", "intents": ["i went home", "i went back home", "went home"]}
                            ],
                        },
                        {
                            "prompt_en": "Tell your friend it was fun.",
                            "options": ["재미있었어요", "맛있어요", "얼마예요?"],
                            "accepted": [
                                {"ko": "재미있었어요", "intents": ["it was fun", "it was enjoyable", "i had fun"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "어제", "en": "yesterday", "romaji": "eoje"},
                        {"ko": "갔어요", "en": "went", "romaji": "gasseoyo"},
                        {"ko": "재미있었어요", "en": "it was fun", "romaji": "jaemiisseosseoyo"},
                    ],
                },
            },
            {
                "slug": "intermediate-yesterday-drill",
                "kind": "drill",
                "title": "Yesterday Drill",
                "order_index": 1,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "어제",
                            "answer": "yesterday",
                            "choices": ["yesterday", "today", "tomorrow"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "im_yesterday_1",
                            "answer": "어제 뭐 했어요?",
                            "choices": ["어제 뭐 했어요?", "내일 뭐 해요?", "얼마예요?"],
                        },
                        {
                            "type": "match",
                            "ko": "갔어요",
                            "answer": "went",
                            "choices": ["went", "did", "will do"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "im_d_jaemi",
                            "answer": "재미있었어요",
                            "choices": ["재미있었어요", "어제", "갔어요"],
                        },
                    ]
                },
            },
            {
                "slug": "intermediate-opinion",
                "kind": "scene",
                "title": "How Was It?",
                "order_index": 2,
                "content_json": {
                    "setting": "café table",
                    "character": "friend",
                    "lines": [
                        {
                            "speaker": "friend",
                            "ko": "어제 콘서트 어땠어요?",
                            "romaji": "eoje konseoteu eottaesseoyo?",
                            "en": "How was the concert yesterday?",
                            "audio_key": "im_opinion_1",
                        },
                        {
                            "speaker": "you",
                            "ko": "정말 좋았어요. 노래가 좋아요.",
                            "romaji": "jeongmal joasseoyo. norae-ga joayo.",
                            "en": "It was really good. The songs are nice.",
                            "audio_key": "im_opinion_2",
                        },
                        {
                            "speaker": "friend",
                            "ko": "음식은 어땠어요?",
                            "romaji": "eumsig-eun eottaesseoyo?",
                            "en": "How was the food?",
                            "audio_key": "im_opinion_3",
                        },
                        {
                            "speaker": "you",
                            "ko": "음식도 맛있었어요!",
                            "romaji": "eumsik-do masisseosseoyo!",
                            "en": "The food was delicious too!",
                            "audio_key": "im_opinion_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "Your friend asks how it was. Say it was good.",
                            "options": ["좋았어요", "갔어요", "감사합니다"],
                            "accepted": [
                                {"ko": "좋았어요", "intents": ["it was good", "it was nice", "it was great"]}
                            ],
                        },
                        {
                            "prompt_en": "Ask your friend how their weekend was.",
                            "options": ["주말 어땠어요?", "어제 갔어요?", "얼마예요?"],
                            "accepted": [
                                {"ko": "주말 어땠어요?", "intents": ["how was your weekend", "how was the weekend", "was the weekend good"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "어땠어요", "en": "how was it", "romaji": "eottaesseoyo"},
                        {"ko": "좋아요", "en": "good / nice", "romaji": "joayo"},
                        {"ko": "오늘", "en": "today", "romaji": "oneul"},
                    ],
                },
            },
            {
                "slug": "intermediate-opinion-drill",
                "kind": "drill",
                "title": "Opinion Drill",
                "order_index": 3,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "어땠어요",
                            "answer": "how was it",
                            "choices": ["how was it", "how much", "what time"],
                        },
                        {
                            "type": "match",
                            "ko": "좋아요",
                            "answer": "good / nice",
                            "choices": ["good / nice", "it was fun", "spicy"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "im_opinion_1",
                            "answer": "어땠어요?",
                            "choices": ["어땠어요?", "뭐 했어요?", "얼마예요?"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "im_d_oneul",
                            "answer": "오늘",
                            "choices": ["오늘", "어제", "주말"],
                        },
                    ]
                },
            },
            {
                "slug": "intermediate-plans",
                "kind": "scene",
                "title": "Weekend Plans",
                "order_index": 4,
                "content_json": {
                    "setting": "café table",
                    "character": "friend",
                    "lines": [
                        {
                            "speaker": "friend",
                            "ko": "주말에 뭐 할 거예요?",
                            "romaji": "jumar-e mwo hal geoyeyo?",
                            "en": "What will you do this weekend?",
                            "audio_key": "im_plans_1",
                        },
                        {
                            "speaker": "you",
                            "ko": "내일 친구를 만날 거예요.",
                            "romaji": "naeil chingu-reul mannal geoyeyo.",
                            "en": "Tomorrow I will meet a friend.",
                            "audio_key": "im_plans_2",
                        },
                        {
                            "speaker": "friend",
                            "ko": "좋아요! 같이 영화 볼 거예요?",
                            "romaji": "joayo! gachi yeonghwa bol geoyeyo?",
                            "en": "Nice! Will you watch a movie together?",
                            "audio_key": "im_plans_3",
                        },
                        {
                            "speaker": "you",
                            "ko": "네, 같이 갈 거예요.",
                            "romaji": "ne, gachi gal geoyeyo.",
                            "en": "Yes, we will go together.",
                            "audio_key": "im_plans_4",
                        },
                    ],
                    "your_turns": [
                        {
                            "prompt_en": "Your friend asks about your weekend. Say what you will do (future tense).",
                            "options": ["공부할 거예요", "공부했어요", "감사합니다"],
                            "accepted": [
                                {"ko": "공부할 거예요", "intents": ["i will study", "i'm going to study", "study"]}
                            ],
                        },
                        {
                            "prompt_en": "Say you will meet a friend tomorrow.",
                            "options": ["내일 친구를 만날 거예요", "어제 친구를 만났어요", "얼마예요?"],
                            "accepted": [
                                {"ko": "내일 친구를 만날 거예요", "intents": ["i will meet a friend tomorrow", "meeting a friend tomorrow", "i'm seeing a friend tomorrow"]}
                            ],
                        },
                    ],
                    "new_vocab": [
                        {"ko": "내일", "en": "tomorrow", "romaji": "naeil"},
                        {"ko": "주말", "en": "weekend", "romaji": "jumal"},
                        {"ko": "할 거예요", "en": "will do", "romaji": "hal geoyeyo"},
                    ],
                },
            },
            {
                "slug": "intermediate-plans-drill",
                "kind": "drill",
                "title": "Plans Drill",
                "order_index": 5,
                "content_json": {
                    "items": [
                        {
                            "type": "match",
                            "ko": "내일",
                            "answer": "tomorrow",
                            "choices": ["tomorrow", "yesterday", "today"],
                        },
                        {
                            "type": "match",
                            "ko": "주말",
                            "answer": "weekend",
                            "choices": ["weekend", "tomorrow", "weekday"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "im_plans_1",
                            "answer": "주말에 뭐 할 거예요?",
                            "choices": ["주말에 뭐 할 거예요?", "어제 뭐 했어요?", "어땠어요?"],
                        },
                        {
                            "type": "listen",
                            "audio_key": "im_d_halgeoyeyo",
                            "answer": "할 거예요",
                            "choices": ["할 거예요", "했어요", "갔어요"],
                        },
                    ]
                },
            },
            {
                "slug": "intermediate-boss",
                "kind": "boss",
                "title": "Boss: Yesterday & Weekend Plans",
                "order_index": 6,
                "content_json": {
                    "goal_en": "Talk about what you did yesterday and your weekend plans",
                    "persona": "friend",
                    "level": "intermediate",
                    "allowed_vocab": [
                        "안녕하세요",
                        "감사합니다",
                        "네",
                        "아니요",
                        "어제",
                        "오늘",
                        "내일",
                        "주말",
                        "갔어요",
                        "했어요",
                        "할 거예요",
                        "어땠어요",
                        "재미있었어요",
                        "좋아요",
                    ],
                    "success_criteria": "Learner says what they did yesterday and what they will do on the weekend",
                    "max_turns": 8,
                },
            },
        ],
    },
]
