#!/usr/bin/env python3
"""Round 109: posting-api dict brute batch BQ (200 words) + gh10 R105 remote-SWE replay (10) + rotate@109 replay slices (R105 remote SWE, R106 staff engineer, R107 AI engineer)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_RUNTIME = Path(__file__).resolve().parents[2]
if str(_RUNTIME) not in sys.path:
    sys.path.insert(0, str(_RUNTIME))
from paths import (  # noqa: E402
    ADAPTERS_DIR,
    DATA_DIR,
    SCRIPTS_DIR,
    SKILL_ROOT,
    WORK_DIR,
    TRACKER_CSV,
    PDF_DIR,
    resume_pdf,
)

sys.path.insert(0, str(ADAPTERS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

import argparse
import csv
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

TRACKER = TRACKER_CSV
POOL_DIR = HOME / "job-hunt" / "candidate-pools"

SLUG_RX = re.compile(r"jobs\.ashbyhq\.com/([a-zA-Z0-9._%-]+)", re.I)
SLUG_LINE_RX = re.compile(r"^[a-zA-Z0-9._%-]+$")
UUID_RX = re.compile(r"^[0-9a-f-]{36}$", re.I)

INVALID_SLUGS = {
    "api", "ashby", "application", "embed", "meeting", "b", "company",
    "board_name", "ashbyembeddemoorg", "------",
}

# Master dict (batch T+U+); batch U = slice [200:400] after dedupe (starts at space after southern).
_MASTER_DICT = [
    "sealed", "sean", "search", "searched", "searches", "searching", "seas", "season", "seasonal", "seasons",
    "seat", "seating", "seats", "seattle", "sec", "second", "secondary", "seconds", "secret", "secretariat",
    "secretary", "secrets", "section", "sections", "sector", "sectors", "secure", "secured", "securely", "securities",
    "security", "see", "seed", "seeds", "seeing", "seek", "seeker", "seekers", "seeking", "seeks",
    "seem", "seemed", "seems", "seen", "sees", "sega", "segment", "segments", "select", "selected",
    "selecting", "selection", "selections", "selective", "self", "sell", "seller", "sellers", "selling", "sells",
    "semester", "semi", "semiconductor", "seminar", "seminars", "sen", "senate", "senator",
    "send", "senior", "sense", "sensor", "sent", "sentence", "separate", "september", "sequence", "series",
    "serious", "serve", "server", "service", "session", "set", "setting", "settle", "setup", "seven",
    "several", "severe", "shade", "shadow", "shake", "shall", "shape", "share", "sharp", "sheet",
    "shelf", "shell", "shelter", "shift", "shine", "ship", "shirt", "shock", "shoe", "shoot",
    "shop", "shopping", "shore", "short", "shot", "should", "shoulder", "show", "shown", "side",
    "sight", "sign", "signal", "signature", "signed", "significant", "silence", "silent", "silk", "silly",
    "silver", "similar", "simple", "simply", "sin", "since", "sing", "singer", "single", "sink",
    "sir", "sister", "sit", "site", "sitting", "situation", "six", "size", "ski", "skill",
    "skin", "sky", "slave", "sleep", "slice", "slide", "slight", "slightly", "slim", "slip",
    "slow", "slowly", "small", "smart", "smell", "smile", "smoke", "smooth", "snap", "snow",
    "soap", "soccer", "social", "society", "soft", "software", "soil", "solar", "soldier", "solid",
    "solution", "solve", "some", "somebody", "somehow", "someone", "something", "sometimes", "somewhat", "somewhere",
    "son", "song", "soon", "sore", "sorry", "sort", "soul", "sound", "soup", "source",
    "south", "southern", "space", "spare", "speak", "speaker", "special", "species", "specific", "speech",
    "speed", "spell", "spend", "spent", "sphere", "spice", "spider", "spin", "spirit", "spiritual",
    "split", "spoke", "spoken", "sport", "spot", "spread", "spring", "square", "squeeze", "stability",
    "stable", "staff", "stage", "stair", "stake", "stand", "standard", "standing", "star", "stare",
    "start", "state", "statement", "station", "statistics", "status", "stay", "steady", "steal", "steam",
    "steel", "step", "stick", "sticky", "still", "stir", "stock", "stomach", "stone", "stood",
    "stop", "storage", "store", "storm", "story", "straight", "strange", "stranger", "straw", "stream",
    "street", "strength", "stress", "stretch", "strict", "strike", "string", "strip", "stroke", "strong",
    "strongly", "structure", "struggle", "stuck", "student", "studio", "study", "stuff", "stupid", "style",
    "subject", "substance", "success", "successful", "such", "sudden", "suddenly", "suffer", "sugar", "suggest",
    "suit", "suitable", "sum", "summer", "sun", "sunday", "sunny", "super", "superior", "supply",
    "support", "suppose", "sure", "surely", "surface", "surgery", "surprise", "surprised", "surprising", "surround",
    "survey", "survive", "suspect", "sustain", "swallow", "swear", "sweat", "sweep", "sweet", "swim",
    "swing", "switch", "symbol", "sympathy", "system",
]

DICT_LIMIT = 200

_seen_master: set[str] = set()
_MASTER_DEDUP = [s for s in _MASTER_DICT if not (s in _seen_master or _seen_master.add(s))]  # type: ignore[func-returns-value]

# batch-AE: continue after batch-AD terminus "faculty" — 200 real English words.
_MASTER_DICT_BATCH_AE = [
    "fade", "fail", "failure", "fair", "fairly", "faith", "fake", "fall", "false", "fame",
    "familiar", "family", "famous", "fan", "fancy", "fantastic", "far", "farm", "farmer", "fashion",
    "fast", "fat", "father", "fault", "favor", "favorite", "fear", "feather", "feature", "federal",
    "fee", "feed", "feel", "feeling", "fellow", "female", "fence", "festival", "fetch", "fever",
    "few", "fiber", "fiction", "field", "fifteen", "fifth", "fifty", "fight", "fighter", "figure",
    "file", "fill", "film", "filter", "final", "finally", "finance", "find", "finding", "fine",
    "finger", "finish", "fire", "firm", "first", "fiscal", "fish", "fitness", "five", "fix",
    "flag", "flame", "flash", "flat", "flavor", "flee", "flesh", "flight", "flip", "float",
    "flock", "floor", "flow", "flower", "flu", "fluid", "fly", "foam", "focus", "fog",
    "folk", "follow", "following", "food", "foot", "football", "for", "force", "forecast", "foreign",
    "forest", "forever", "forget", "fork", "form", "formal", "format", "formation", "former", "formula",
    "forth", "fortune", "forty", "forum", "forward", "fossil", "foster", "fought", "foul", "found",
    "foundation", "founder", "fountain", "four", "fourth", "fox", "frame", "framework", "frankly", "fraud",
    "freak", "freedom", "freeze", "freight", "french", "frequency", "frequent", "fresh", "friend", "friendly",
    "friendship", "frighten", "frog", "front", "frontier", "frost", "frown", "frozen", "fruit", "frustration",
    "fuel", "full", "fully", "fun", "function", "fund", "fundamental", "funeral", "funny", "fur",
    "furniture", "further", "future", "gain", "galaxy", "gallery", "game", "gap", "garage", "garden",
    "garlic", "gas", "gasoline", "gate", "gather", "gauge", "gaze", "gear", "gender", "gene",
    "general", "generally", "generate", "generation", "generic", "generous", "genius", "genre", "gentle", "gentleman",
    "gently", "genuine", "gesture", "get", "ghost", "giant", "gift", "gifted", "girl", "girlfriend",
    "give", "given", "glad", "glance", "glare", "glass", "glimpse", "global", "globe", "glory",
    "glove", "goal", "goat", "goddess", "gold", "golden", "golf", "gone", "good", "goodbye",
    "goods", "govern", "government", "governor", "grab", "grace", "grade", "gradually", "graduate", "grain",
    "grand", "grandfather", "grandmother", "grant", "grass", "grave", "gravity", "gray", "great", "greatly",
    "green", "grocery", "ground", "group", "grow", "growing", "growth", "guarantee", "guard", "guest",
    "guide", "guideline", "guilt", "gun", "guy", "habit", "habitat", "hail", "hair", "half",
    "hall", "hallway", "hand", "handful", "handle", "happen", "happily", "happy", "harbor", "hard",
    "hardly", "hardship", "hardware", "harm", "harmful", "handsome", "harmony", "harvest", "hat", "hatch",
    "hate", "haul", "have", "haven", "hazard", "head", "headline", "headquarters", "heal", "health",
    "healthy", "heap", "hear", "hearing", "heart", "heat", "heaven", "heavily", "heavy", "hedge",
    "heel", "height", "helicopter", "hell", "hello", "helmet", "help", "helpful", "hence", "herd",
    "here", "heritage", "hero", "herself", "hide", "highlight", "highly", "highway", "hill", "hint",
    "hip", "hire", "historian", "historic", "historical", "history", "hit", "hobby", "hockey", "hold",
    "holder", "hole", "holiday", "hollow", "holy", "home", "homeless", "honest", "honey", "honor",
    "hook", "hope", "horizon", "hormone", "horn", "horrible", "horror", "horse", "hospital", "host",
    "hostage", "hostile", "hot", "hotel", "hour", "house", "household", "housing", "how", "however",
    "huge", "human", "humor", "hundred", "hungry", "hunt", "hunter", "hunting", "hurry", "hurt",
    "husband", "hybrid", "ice", "idea", "ideal", "identification", "identify", "identity", "ideological", "ideology",
    "ignore", "ill", "illegal", "illness", "illustrate", "image", "imagination", "imagine", "immediate", "immediately",
    "immigrant", "immigration", "immune", "impact", "implement", "implication", "imply", "import", "importance", "important",
    "impose", "impossible", "impress", "impression", "impressive", "improve", "improvement", "impulse", "inch", "incident",
    "include", "including", "income", "incorporate", "increase", "increased", "increasing", "increasingly", "incredible", "indeed",
    "independence", "independent", "index", "indicate", "indication", "indicator", "indigenous", "individual", "indoor", "induce",
    "infant", "infection", "inflation", "influence", "influential", "inform", "informal", "information", "infrastructure", "ingredient",
    "initial", "initially", "initiative", "inject", "injury", "inmate", "inner", "innocent", "innovation", "input",
    "inquire", "insect", "inside", "insight", "insist", "inspire", "install", "instance", "instant", "instead",
    "instinct", "institution", "institutional", "instruct", "instruction", "instructor", "instrument", "insurance", "intake", "integer",
    "integrate", "integrated", "integration", "integrity", "intellectual", "intelligence", "intelligent", "intend", "intense", "intensity",
    "intent", "intention", "interact", "interaction", "interest", "interested", "interesting", "internal", "international", "internet",
    "interpret", "interpretation", "interrupt", "interval", "intimate", "into", "introduce", "introduction", "invade", "invasion",
    "invent", "invention", "inventory", "invest", "investigate", "investigation", "investigator", "investment", "investor", "invite",
    "involve", "involved", "involvement", "iron", "island", "isolate", "isolation", "issue", "item", "its",
    "itself", "jacket", "jail", "jam", "jar", "jaw", "jazz", "jealous", "jeans", "jet",
    "jewel", "job", "join", "joint", "joke", "journal", "journalist", "journey", "joy", "judge",
    "judgment", "juice", "jump", "jungle", "junior", "jury", "just", "justice", "justify",
]
_MASTER_DICT_BATCH_AF = [
    "garden", "garlic", "gas", "gasoline", "gate", "gather", "gauge", "gaze", "gear", "gender",
    "gene", "general", "generally", "generate", "generation", "generic", "generous", "genius", "genre", "gentle",
    "gentleman", "gently", "genuine", "gesture", "get", "ghost", "giant", "gift", "gifted", "girl",
    "girlfriend", "give", "given", "glad", "glance", "glare", "glass", "glimpse", "global", "globe",
    "glory", "glove", "goal", "goat", "goddess", "gold", "golden", "golf", "gone", "good",
    "goodbye", "goods", "govern", "government", "governor", "grab", "grace", "grade", "gradually", "graduate",
    "grain", "grand", "grandfather", "grandmother", "grant", "grass", "grave", "gravity", "gray", "great",
    "greatly", "green", "grocery", "ground", "group", "grow", "growing", "growth", "guarantee", "guard",
    "guest", "guide", "guideline", "guilt", "gun", "guy", "habit", "habitat", "hail", "hair",
    "half", "hall", "hallway", "hand", "handful", "handle", "happen", "happily", "happy", "harbor",
    "hard", "hardly", "hardship", "hardware", "harm", "harmful", "handsome", "harmony", "harvest", "hat",
    "hatch", "hate", "haul", "have", "haven", "hazard", "head", "headline", "headquarters", "heal",
    "health", "healthy", "heap", "hear", "hearing", "heart", "heat", "heaven", "heavily", "heavy",
    "hedge", "heel", "height", "helicopter", "hell", "hello", "helmet", "help", "helpful", "hence",
    "herd", "here", "heritage", "hero", "herself", "hide", "highlight", "highly", "highway", "hill",
    "hint", "hip", "hire", "historian", "historic", "historical", "history", "hit", "hobby", "hockey",
    "hold", "holder", "hole", "holiday", "hollow", "holy", "home", "homeless", "honest", "honey",
    "honor", "hook", "hope", "horizon", "hormone", "horn", "horrible", "horror", "horse", "hospital",
    "host", "hostage", "hostile", "hot", "hotel", "hour", "house", "household", "housing", "how",
    "however", "huge", "human", "humor", "hundred", "hungry", "hunt", "hunter", "hunting", "hurry"
]
# batch-AG: anchor at harmony in combined list from garage (batch-AE) through batch-AF tail.
_seen_ae_garage: set[str] = set()
_AE_FROM_GARAGE = [s for s in _MASTER_DICT_BATCH_AE if not (s in _seen_ae_garage or _seen_ae_garage.add(s))]  # type: ignore[func-returns-value]
_gi = _AE_FROM_GARAGE.index("garage")
_combined_from_garage = _AE_FROM_GARAGE[_gi:]
_seen_af_tail: set[str] = set(_combined_from_garage)
_AF_TAIL = [s for s in _MASTER_DICT_BATCH_AF if not (s in _seen_af_tail or _seen_af_tail.add(s))]  # type: ignore[func-returns-value]
_combined_from_garage = _combined_from_garage + _AF_TAIL
_hi = _combined_from_garage.index("harmony")
_MASTER_DICT_BATCH_AG = _combined_from_garage[_hi : _hi + DICT_LIMIT]
_seen_batch_ag: set[str] = set()
_BATCH_AG_DEDUP = [s for s in _MASTER_DICT_BATCH_AG if not (s in _seen_batch_ag or _seen_batch_ag.add(s))]  # type: ignore[func-returns-value]

# batch-AH: continue after batch-AG terminus anchor "impulse" — 200 real English words.
_ii = _combined_from_garage.index("impulse")
_AH_TAIL = _combined_from_garage[_ii + 1 :]
_seen_ah_used: set[str] = set(_combined_from_garage[: _ii + 1])
_AH_SUPPLEMENT = [s for s in _MASTER_DEDUP if not (s in _seen_ah_used or _seen_ah_used.add(s))]  # type: ignore[func-returns-value]
_MASTER_DICT_BATCH_AH = (_AH_TAIL + _AH_SUPPLEMENT)[:DICT_LIMIT]
_seen_batch_ah: set[str] = set()
_BATCH_AH_DEDUP = [s for s in _MASTER_DICT_BATCH_AH if not (s in _seen_batch_ah or _seen_batch_ah.add(s))]  # type: ignore[func-returns-value]

# batch-AI: continue after batch-AH terminus — next 200 real English words.
_all_ah_source = _AH_TAIL + _AH_SUPPLEMENT
_seen_ai_used: set[str] = set(_combined_from_garage[: _ii + 1]) | set(_BATCH_AH_DEDUP)
_AI_TAIL = _all_ah_source[DICT_LIMIT:]
_AI_SUPPLEMENT = [s for s in _MASTER_DEDUP if not (s in _seen_ai_used or _seen_ai_used.add(s))]  # type: ignore[func-returns-value]
_MASTER_DICT_BATCH_AI = (_AI_TAIL + _AI_SUPPLEMENT)[:DICT_LIMIT]
_seen_batch_ai: set[str] = set()
_BATCH_AI_DEDUP = [s for s in _MASTER_DICT_BATCH_AI if not (s in _seen_batch_ai or _seen_batch_ai.add(s))]  # type: ignore[func-returns-value]
_BATCH_AI_DEDUP_FROZEN = list(_BATCH_AI_DEDUP)

# batch-AJ: continue after batch-AI terminus — next 200 real English words.
_all_ai_source = _AI_TAIL + _AI_SUPPLEMENT
_seen_aj_used: set[str] = set(_combined_from_garage[: _ii + 1]) | set(_BATCH_AH_DEDUP) | set(_BATCH_AI_DEDUP_FROZEN)
_AJ_TAIL = _all_ai_source[DICT_LIMIT:]
_AJ_SUPPLEMENT = [s for s in _MASTER_DEDUP if not (s in _seen_aj_used or _seen_aj_used.add(s))]  # type: ignore[func-returns-value]
_MASTER_DICT_BATCH_AJ = (_AJ_TAIL + _AJ_SUPPLEMENT)[:DICT_LIMIT]
_seen_batch_aj: set[str] = set()
_BATCH_AJ_DEDUP = [s for s in _MASTER_DICT_BATCH_AJ if not (s in _seen_batch_aj or _seen_batch_aj.add(s))]  # type: ignore[func-returns-value]
_BATCH_AJ_DEDUP_FROZEN = list(_BATCH_AJ_DEDUP)

# batch-AL: extend vocabulary after combined_from_garage exhaustion — 200 real English words for AK+.
_MASTER_DICT_BATCH_AL = [
    "kill", "kind", "king", "kingdom", "kiss", "kitchen", "knee", "knife", "knock", "know",
    "knowledge", "known", "label", "labor", "laboratory", "lack", "ladder", "lady", "lake", "lamp",
    "land", "landscape", "lane", "language", "lap", "large", "largely", "laser", "last", "late",
    "later", "latin", "latter", "laugh", "launch", "law", "lawn", "lawsuit", "lawyer", "lay",
    "layer", "lead", "leader", "leadership", "leading", "leaf", "league", "lean", "learn", "learning",
    "least", "leather", "leave", "left", "leg", "legacy", "legal", "legend", "legislation", "legitimate",
    "lemon", "length", "lens", "less", "lesson", "let", "letter", "level", "liberal", "library",
    "license", "lid", "lie", "life", "lifestyle", "lifetime", "lift", "light", "lighting", "like",
    "likely", "limit", "limitation", "limited", "line", "link", "lion", "lip", "list", "listen",
    "literally", "literary", "literature", "little", "live", "living", "load", "loan", "local", "locate",
    "location", "lock", "log", "logic", "logical", "lonely", "long", "look", "loop", "loose",
    "lose", "loss", "lost", "lot", "lots", "loud", "love", "lovely", "lover", "low",
    "lower", "luck", "lucky", "lunch", "lung", "machine", "mad", "magazine", "magic", "magnetic",
    "magnificent", "mail", "main", "mainly", "maintain", "maintenance", "major", "majority", "make", "maker",
    "makeup", "male", "mall", "man", "manage", "management", "manager", "manner", "manufacturer", "manufacturing",
    "many", "map", "march", "margin", "mark", "market", "marketing", "marriage", "married", "marry",
    "mask", "mass", "massive", "master", "match", "mate", "material", "math", "matter", "maximum",
    "maybe", "mayor", "meal", "mean", "meaning", "meanwhile", "measure", "measurement", "meat", "mechanic",
    "mechanism", "medal", "media", "medical", "medication", "medicine", "medium", "meet", "meeting", "member",
    "membership", "memory", "mental", "mention", "menu", "mere", "merely", "mess", "message", "metal",
    "meter", "method", "middle", "midnight", "might", "mild", "mile", "military", "milk", "mill",
    "million", "mind", "mine", "mineral", "minimum", "minister", "minor", "minority", "minute", "miracle",
    "mirror", "miss", "missile", "missing", "mission", "mistake", "mix", "mixture", "mobile", "mode",
    "model", "moderate", "modern", "modest", "modify", "mom", "moment", "money", "monitor", "monkey",
    "month", "mood", "moon", "moral", "more", "moreover", "morning", "mortgage", "most", "mostly",
    "mother", "motion", "motivation", "motor", "mount", "mountain", "mouse", "mouth", "move", "movement",
    "movie", "much", "multiple", "murder", "muscle", "museum", "music", "musical", "musician", "must",
    "mutual", "myself", "mystery", "myth", "nail", "naked", "name", "narrow", "nation", "national",
    "native", "natural", "naturally", "nature", "near", "nearby", "nearly", "necessarily", "necessary", "neck",
    "need", "negative", "negotiate", "negotiation", "neighbor", "neighborhood", "neither", "nerve", "nervous", "nest",
    "network", "never", "nevertheless", "new", "news", "newspaper", "next", "nice", "night", "nine",
    "no", "nobody", "nod", "noise", "nomination", "none", "nonetheless", "nonsense", "noon", "nor",
    "normal", "normally", "north", "northern", "nose", "not", "note", "nothing", "notice", "notion",
    "novel", "now", "nowhere", "nuclear", "number", "numerous", "nurse", "nut", "object", "objective",
    "obligation", "observation", "observe", "observer", "obtain", "obvious", "obviously", "occasion", "occasionally", "occupation",
    "occupy", "occur", "ocean", "odd", "odds", "off", "offense", "offensive", "offer", "office",
    "officer", "official", "often", "oil", "okay", "old", "olympic", "once", "one", "ongoing",
    "onion", "online", "only", "onto", "open", "opening", "operate", "operating", "operation", "operator",
    "opinion", "opponent", "opportunity", "oppose", "opposite", "opposition", "option", "orange", "order", "ordinary",
    "organic", "organization", "organize", "orientation", "origin", "original", "originally", "other", "others", "otherwise",
    "ought", "ounce", "out", "outcome", "outside", "oven", "over", "overall", "overcome", "overlook",
    "owe", "own", "owner", "pace", "pack", "package", "page", "pain", "painful", "paint",
    "painter", "painting", "pair", "palace", "pale", "palm", "pan", "panel", "panic", "paper",
    "parent", "park", "parking", "part", "participant", "participate", "participation", "particular", "particularly", "partly",
    "partner", "partnership", "party", "pass", "passage", "passenger", "passion", "past", "patch", "path",
    "patient", "pattern", "pause", "pay", "payment", "peace", "peak", "peer", "pen", "penalty",
    "people", "pepper", "per", "perceive", "percentage", "perception", "perfect", "perfectly", "perform", "performance",
    "perhaps", "period", "permanent", "permission", "permit", "person", "personal", "personality", "personally", "personnel",
    "perspective", "persuade", "pet", "phase", "phenomenon", "philosophy", "phone", "photo", "photograph", "photographer",
    "phrase", "physical", "physically", "physician", "piano", "pick", "picture", "pie", "piece", "pile",
    "pilot", "pin", "pine", "pink", "pipe", "pitch", "place", "plain", "plan", "plane",
    "planet", "planning", "plant", "plastic", "plate", "platform", "play", "player", "please", "pleasure",
    "plenty", "plot", "plus", "pocket", "poem", "poet", "poetry", "point", "pole", "police",
    "policy", "political", "politically", "politician", "politics", "poll", "pollution", "pool", "poor", "pop",
    "popular", "population", "porch", "port", "portion", "portrait", "portray", "pose", "position", "positive",
    "possess", "possession", "possibility", "possible", "possibly", "post", "pot", "potato", "potential", "potentially",
    "pound", "pour", "poverty", "powder", "power", "powerful", "practical", "practice", "pray", "prayer",
    "precisely", "predict", "prefer", "preference", "pregnancy", "pregnant", "preparation", "prepare", "prescription", "presence",
    "present", "presentation", "preserve", "president", "presidential", "press", "pressure", "pretend", "pretty", "prevent",
    "previous", "previously", "price", "pride", "priest", "primarily", "primary", "prime", "principal", "principle",
    "print", "prior", "priority", "prison", "prisoner", "privacy", "private", "probably", "problem", "procedure",
    "proceed", "process", "produce", "producer", "product", "production", "profession", "professional", "professor", "profile",
    "profit", "program", "progress", "project", "prominent", "promise", "promote", "prompt", "proof", "proper",
    "properly", "property", "proportion", "proposal", "propose", "proposed", "prosecutor", "prospect", "protect", "protection",
    "protein", "protest", "proud", "prove", "provide", "provider", "province", "provision", "psychological", "psychologist",
    "psychology", "public", "publication", "publicly", "publish", "publisher", "pull", "punishment", "purchase", "pure",
    "purpose", "pursue", "push", "put", "qualify", "quality", "quarter", "question", "quick", "quickly",
    "quiet", "quietly", "quit", "quite", "quote", "race", "racial", "radical", "radio", "rail",
    "rain", "raise", "range", "rank", "rapid", "rapidly", "rare", "rarely", "rate", "rather",
    "rating", "ratio", "raw", "reach", "react", "reaction", "read", "reader", "reading", "ready",
    "real", "reality", "realize", "really", "reason", "reasonable", "reasonably", "recall", "receive", "recent",
    "recently", "recipe", "recognition", "recognize", "recommend", "recommendation", "record", "recording", "recover", "recovery",
    "recruit", "red", "reduce", "reduction", "refer", "reference", "reflect", "reflection", "reform", "refugee",
    "refuse", "regard", "regarding", "regardless", "regime", "region", "regional", "register", "regular", "regularly",
    "regulate", "regulation", "reinforce", "reject", "relate", "relation", "relationship", "relative", "relatively", "relax",
    "release", "relevant", "relief", "religion", "religious", "rely", "remain", "remaining", "remarkable", "remember",
    "remind", "remote", "remove", "repeat", "repeatedly", "replace", "reply", "report", "reporter", "represent",
    "representation", "representative", "republican", "reputation", "request", "require", "requirement", "research", "researcher", "resemble",
    "reservation", "resident", "resist", "resistance", "resolution", "resolve", "resort", "resource", "respect", "respond",
    "respondent", "response", "responsibility", "responsible", "rest", "restaurant", "restore", "restriction", "result", "retain",
    "retire", "retirement", "return", "reveal", "revenue", "review", "revolution", "rhythm", "rice", "rich",
    "rid", "ride", "rifle", "right", "ring", "rip", "rise", "risk", "river", "road",
    "robot", "rock", "role", "roll", "romantic", "roof", "room", "root", "rope", "rose",
    "rough", "roughly", "round", "route", "routine", "row", "rub", "rubber", "rule", "run",
    "running", "rural", "rush", "sacred", "sad", "safe", "safety", "sail", "sake", "salad",
    "salary", "sale", "sales", "salt", "same", "sample", "sanction", "sand", "satellite", "satisfaction",
    "satisfy", "sauce", "save", "saving", "saw", "say", "scale", "scandal", "scared", "scenario",
    "scene", "schedule", "scheme", "scholar", "scholarship", "school", "science", "scientific", "scientist", "scope",
    "score", "scream", "screen", "script", "sea", "search", "season", "seat", "second", "secret",
    "secretary", "section", "sector", "secure", "security", "see", "seed", "seek", "seem", "segment",
    "seize", "select", "selection", "self", "sell", "senate", "senator", "send", "senior", "sense",
    "sensitive", "sentence", "separate", "sequence", "series", "serious", "seriously", "serve", "service", "session",
    "set", "setting", "settle", "settlement", "seven", "several", "severe", "sex", "sexual", "shade",
    "shadow", "shake", "shall", "shape", "share", "sharp", "she", "sheet", "shelf", "shell",
    "shelter", "shift", "shine", "ship", "shirt", "shock", "shoe", "shoot", "shop", "shopping",
    "shore", "short", "shortly", "shot", "should", "shoulder", "shout", "show", "shower", "shrug",
    "shut", "sick", "side", "sigh", "sight", "sign", "signal", "significance", "significant", "significantly",
    "silence", "silent", "silk", "silly", "silver", "similar", "similarly", "simple", "simply", "sin",
    "since", "sing", "singer", "single", "sink", "sir", "sister", "sit", "site", "situation",
    "six", "size", "ski", "skill", "skin", "sky", "slave", "sleep", "slice", "slide",
    "slight", "slightly", "slip", "slow", "slowly", "small", "smart", "smell", "smile", "smoke",
    "smooth", "snap", "snow", "soap", "soccer", "social", "society", "sock", "soft", "software",
    "soil", "solar", "soldier", "solid", "solution", "solve", "some", "somebody", "somehow", "someone",
    "something", "sometimes", "somewhat", "somewhere", "son", "song", "soon", "sophisticated", "sore", "sorry",
    "sort", "soul", "sound", "soup", "source", "south", "southern", "space", "spare", "speak",
    "speaker", "special", "specialist", "species", "specific", "specifically", "speech", "speed", "spell", "spend",
    "spending", "spin", "spirit", "spiritual", "split", "spokesman", "sport", "spot", "spread", "spring",
    "square", "squeeze", "stability", "stable", "staff", "stage", "stain", "stair", "stake", "stand",
    "standard", "standing", "star", "stare", "start", "state", "statement", "station", "statistics", "status",
    "stay", "steady", "steal", "steam", "steel", "step", "stick", "still", "stir", "stock",
    "stomach", "stone", "stop", "storage", "store", "storm", "story", "straight", "strange", "stranger",
    "strategic", "strategy", "stream", "street", "strength", "stress", "stretch", "strike", "string", "strip",
    "stroke", "strong", "strongly", "structure", "struggle", "student", "studio", "study", "stuff", "stupid",
    "style", "subject", "submit", "subsequent", "substance", "substantial", "succeed", "success", "successful", "such",
    "sudden", "suddenly", "suffer", "sugar", "suggest", "suggestion", "suicide", "suit", "summer", "summit",
    "sun", "super", "supply", "support", "supporter", "suppose", "supposed", "supreme", "sure", "surely",
    "surface", "surgery", "surprise", "surprised", "surprising", "surround", "survey", "survival", "survive", "survivor",
    "suspect", "sustain", "swear", "sweep", "sweet", "swim", "swing", "switch", "symbol", "symptom",
    "syndrome", "system", "table", "tackle", "tactic", "tail", "take", "tale", "talent", "talk",
    "tall", "tank", "tap", "tape", "target", "task", "taste", "tax", "taxpayer", "tea",
    "teach", "teacher", "teaching", "team", "tear", "teaspoon", "technical", "technique", "technology", "teen",
    "teenager", "telephone", "telescope", "television", "tell", "temperature", "temporary", "ten", "tend", "tendency",
    "tennis", "tension", "tent", "term", "terms", "terrible", "territory", "terror", "terrorism", "terrorist",
    "test", "testify", "testimony", "testing", "text", "than", "thank", "thanks", "that", "the",
    "theater", "their", "them", "theme", "themselves", "then", "theory", "therapy", "there", "therefore",
    "these", "they", "thick", "thin", "thing", "think", "thinking", "third", "thirty", "this",
    "those", "though", "thought", "thousand", "threat", "threaten", "three", "throat", "through", "throughout",
    "throw", "thumb", "thus", "ticket", "tie", "tight", "time", "tiny", "tip", "tire",
    "tired", "tissue", "title", "to", "tobacco", "today", "toe", "together", "tomato", "tomorrow",
    "tone", "tongue", "tonight", "too", "tool", "tooth", "top", "topic", "toss", "total",
    "totally", "touch", "tough", "tour", "tourist", "tournament", "toward", "towards", "tower", "town",
    "toy", "trace", "track", "trade", "tradition", "traditional", "traffic", "tragedy", "trail", "train",
    "training", "transfer", "transform", "transformation", "transition", "translate", "transportation", "trap", "trash", "travel",
    "treat", "treatment", "treaty", "tree", "tremendous", "trend", "trial", "tribe", "trick", "trip",
    "troop", "trouble", "truck", "true", "truly", "trust", "truth", "try", "tube", "tunnel",
    "turn", "tv", "twelve", "twenty", "twice", "twin", "two", "type", "typical", "typically",
    "ugly", "ultimate", "ultimately", "unable", "uncle", "under", "undergo", "understand", "understanding", "unfortunately",
    "uniform", "union", "unique", "unit", "united", "unity", "universal", "universe", "university", "unknown",
    "unless", "unlike", "unlikely", "until", "unusual", "up", "upon", "upper", "urban", "urge",
    "use", "used", "useful", "user", "usual", "usually", "utility", "vacation", "valley", "valuable",
    "value", "variable", "variation", "variety", "various", "vast", "vegetable", "vehicle", "venture", "version",
    "versus", "very", "vessel", "veteran", "via", "victim", "victory", "video", "view", "viewer",
    "village", "violate", "violation", "violence", "violent", "virtually", "virtue", "virus", "visible", "vision",
    "visit", "visitor", "visual", "vital", "voice", "volume", "volunteer", "vote", "voter", "vs",
    "vulnerable", "wage", "wait", "wake", "walk", "wall", "wander", "want", "war", "warm",
    "warn", "warning", "wash", "waste", "watch", "water", "wave", "way", "we", "weak",
    "wealth", "wealthy", "weapon", "wear", "weather", "wedding", "week", "weekend", "weekly", "weigh",
    "weight", "welcome", "welfare", "well", "west", "western", "wet", "what", "whatever", "wheel",
    "when", "whenever", "where", "whereas", "whether", "which", "while", "whisper", "white", "who",
    "whole", "whom", "whose", "why", "wide", "widely", "widespread", "wife", "wild", "will",
    "willing", "win", "wind", "window", "wine", "wing", "winner", "winter", "wipe", "wire",
    "wisdom", "wise", "wish", "with", "withdraw", "within", "without", "witness", "woman", "wonder",
    "wonderful", "wood", "wooden", "word", "work", "worker", "working", "workshop", "world", "worried",
    "worry", "worth", "would", "wound", "wrap", "write", "writer", "writing", "wrong", "yard",
    "yeah", "year", "yell", "yellow", "yes", "yesterday", "yet", "yield", "you", "young",
    "your", "yours", "yourself", "youth", "zone",
]

# batch-AK: continue after batch-AK terminus — next 200 real English words.
_all_aj_source = _AJ_TAIL + _AJ_SUPPLEMENT
_seen_ak_used: set[str] = set(_combined_from_garage[: _ii + 1]) | set(_BATCH_AH_DEDUP) | set(_BATCH_AI_DEDUP_FROZEN) | set(_BATCH_AJ_DEDUP_FROZEN)
_AK_TAIL = _all_aj_source[DICT_LIMIT:]
_AK_SUPPLEMENT = [s for s in _MASTER_DICT_BATCH_AL if s not in _seen_ak_used]
_seen_batch_ak: set[str] = set()
_BATCH_AK_DEDUP: list[str] = []
for s in _AK_TAIL:
    if s in _seen_batch_ak:
        continue
    _seen_batch_ak.add(s)
    _BATCH_AK_DEDUP.append(s)
for s in _AK_SUPPLEMENT:
    if s in _seen_batch_ak:
        continue
    _seen_batch_ak.add(s)
    _BATCH_AK_DEDUP.append(s)
    if len(_BATCH_AK_DEDUP) >= DICT_LIMIT:
        break
_BATCH_AL_DEDUP_FROUP = _BATCH_AK_DEDUP[:DICT_LIMIT]
_BATCH_AL_DEDUP_FROZEN = list(_BATCH_AL_DEDUP_FROUP)

# batch-AM: extend vocabulary after round78 batch-AL exhaustion — 200 real English words.
_MASTER_DICT_BATCH_AM = [
    "abandon", "ability", "able", "abortion", "about", "above", "abroad", "absence", "absent", "absolute",
    "absolutely", "absorb", "abuse", "academic", "accept", "access", "accident", "accompany", "accomplish", "according",
    "account", "accurate", "accuse", "achieve", "achievement", "acid", "acknowledge", "acquire", "across", "act",
    "action", "active", "activist", "activity", "actor", "actress", "actual", "actually", "adapt", "add",
    "addition", "additional", "address", "adequate", "adjust", "adjustment", "administration", "administrator", "admire", "admission",
    "admit", "adolescent", "adopt", "adult", "advance", "advanced", "advantage", "adventure", "advertising", "advice",
    "advise", "adviser", "advocate", "affair", "affect", "afford", "afraid", "african", "after", "afternoon",
    "again", "against", "age", "agency", "agenda", "agent", "aggressive", "ago", "agree", "agreement",
    "agricultural", "ahead", "aid", "aide", "aids", "air", "aircraft", "airline", "airport", "album",
    "alcohol", "alive", "all", "alliance", "allow", "ally", "almost", "alone", "along", "already",
    "also", "alter", "alternative", "although", "always", "amazing", "american", "among", "amount", "analysis",
    "analyst", "analyze", "ancient", "and", "anger", "angle", "angry", "animal", "anniversary", "announce",
    "annual", "another", "answer", "anxiety", "any", "anybody", "anymore", "anyone", "anything", "anyway",
    "anywhere", "apart", "apartment", "apparent", "apparently", "appeal", "appear", "appearance", "apple", "application",
    "apply", "appoint", "appointment", "appreciate", "approach", "appropriate", "approval", "approve", "approximately", "architect",
    "area", "argue", "argument", "arise", "arm", "armed", "army", "around", "arrange", "arrangement",
    "arrest", "arrival", "arrive", "art", "article", "artist", "artistic", "as", "asian", "aside",
    "ask", "asleep", "aspect", "assault", "assert", "assess", "assessment", "asset", "assign", "assignment",
    "assist", "assistance", "assistant", "associate", "association", "assume", "assumption", "assure", "at", "athlete",
    "atmosphere", "attach", "attack", "attempt", "attend", "attention", "attitude", "attorney", "attract", "attractive",
    "attribute", "audience", "author", "authority", "auto", "available", "average", "avoid", "award", "aware",
    "awareness", "away", "awful", "baby", "back", "background", "bad", "badly", "bag", "bake",
    "balance", "ball", "ban", "band", "bank", "bar", "barely", "barrel", "barrier", "base",
    "baseball", "basic", "basically", "basis", "basket", "basketball", "bathroom", "battery", "battle", "be",
    "beach", "bean", "bear", "beat", "beautiful", "beauty", "because", "become", "bed", "bedroom",
    "beer", "before", "begin", "beginning", "behavior", "behind", "being", "belief", "believe", "bell",
    "belong", "below", "belt", "bench", "bend", "beneath", "benefit", "beside", "besides", "best",
    "bet", "better", "between", "beyond", "bible", "big", "bike", "bill", "billion", "bind",
    "biological", "bird", "birth", "birthday", "bit", "black", "blade", "blame", "blanket", "blind",
    "block", "blood", "blow", "blue", "board", "boat", "body", "bomb", "bond", "bone",
    "book", "boom", "boot", "border", "born", "borrow", "boss", "both", "bother", "bottle",
    "bottom", "boundary", "bowl", "box", "boy", "boyfriend", "brain", "branch", "brand", "bread",
    "break", "breakfast", "breast", "breath", "breathe", "brick", "bridge", "brief", "briefly", "bright",
    "brilliant", "bring", "british", "broad", "broken", "brother", "brown", "brush", "buck", "budget",
    "build", "building", "bullet", "bunch", "burden", "burn", "bury", "bus", "business", "busy",
    "but", "butter", "button", "buy", "buyer", "by", "cabin", "cabinet", "cable", "cake",
    "calculate", "call", "camera", "camp", "campaign", "campus", "can", "canadian", "cancer", "candidate",
    "cap", "capability", "capable", "capacity", "capital", "captain", "capture", "car", "carbon", "card",
    "care", "career", "careful", "carefully", "carrier", "carry", "case", "cash", "cast", "cat",
    "catch", "category", "catholic", "cause", "ceiling", "celebrate", "celebration", "celebrity", "cell", "center",
    "central", "century", "ceo", "ceremony", "certain", "certainly", "chain", "chair", "chairman", "challenge",
    "chamber", "champion", "championship", "chance", "change", "changing", "channel", "chapter", "character", "characteristic",
    "characterize", "charge", "charity", "chart", "chase", "cheap", "check", "cheek", "cheese", "chef",
    "chemical", "chest", "chicken", "chief", "child", "childhood", "chinese", "chip", "chocolate", "choice",
    "choose", "christian", "christmas", "church", "cigarette", "circle", "circumstance", "cite", "citizen", "city",
    "civil", "civilian", "claim", "class", "classic", "classroom", "clean", "clear", "clearly", "client",
    "climate", "climb", "clinic", "clinical", "clock", "close", "closely", "closer", "clothes", "clothing",
    "cloud", "club", "clue", "cluster", "coach", "coal", "coalition", "coast", "coat", "code",
    "coffee", "cognitive", "cold", "collapse", "colleague", "collect", "collection", "collective", "college", "colonial",
    "color", "column", "combination", "combine", "come", "comedy", "comfort", "comfortable", "command", "commander",
    "comment", "commercial", "commission", "commit", "commitment", "committee", "common", "communicate", "communication", "community",
    "company", "compare", "comparison", "compete", "competition", "competitive", "competitor", "complain", "complaint", "complete",
    "completely", "complex", "complicated", "component", "compose", "composition", "comprehensive", "computer", "concentrate", "concentration",
    "concept", "concern", "concerned", "concert", "conclude", "conclusion", "concrete", "condition", "conduct", "conference",
    "confidence", "confident", "confirm", "conflict", "confront", "confusion", "congress", "congressional", "connect", "connection",
    "consciousness", "consensus", "consequence", "conservative", "consider", "considerable", "consideration", "consist", "consistent", "constant",
    "constantly", "constitute", "constitutional", "construct", "construction", "consultant", "consume", "consumer", "consumption", "contact",
    "contain", "container", "contemporary", "content", "contest", "context", "continue", "continued", "contract", "contrast",
    "contribute", "contribution", "control", "controversial", "controversy", "convention", "conventional", "conversation", "convert", "conviction",
    "convince", "cook", "cookie", "cooking", "cool", "cooperation", "cop", "cope", "copy", "core",
    "corn", "corner", "corporate", "corporation", "correct", "correspondent", "cost", "cotton", "couch", "could",
    "council", "counsel", "count", "counter", "country", "county", "couple", "courage", "course", "court",
    "cousin", "cover", "coverage", "cow", "crack", "craft", "crash", "crazy", "cream", "create",
    "creation", "creative", "creature", "credit", "crew", "crime", "criminal", "crisis", "critic", "critical",
    "criticism", "criticize", "crop", "cross", "crowd", "crucial", "cry", "cultural", "culture", "cup",
    "curious", "current", "currently", "curriculum", "custom", "customer", "cut", "cycle", "dad", "daily",
    "damage", "dance", "danger", "dangerous", "dare", "dark", "darkness", "data", "date", "daughter",
    "day", "dead", "deal", "dealer", "dear", "death", "debate", "debt", "decade", "decide",
    "decision", "deck", "declare", "decline", "decrease", "deep", "deeply", "deer", "defeat", "defend",
    "defendant", "defense", "deficit", "define", "definitely", "definition", "degree", "delay", "deliver", "delivery",
    "demand", "democracy", "democrat", "democratic", "demonstrate", "demonstration", "deny", "department", "depend", "dependent",
    "depending", "depict", "depression", "depth", "deputy", "derive", "describe", "description", "desert", "deserve",
    "design", "designer", "desire", "desk", "desperate", "despite", "destroy", "destruction", "detail", "detailed",
    "detect", "determine", "develop", "developing", "development", "device", "devote", "dialogue", "die", "diet",
    "differ", "difference", "different", "differently", "difficult", "difficulty", "dig", "digital", "dimension", "dining",
    "dinner", "direct", "direction", "directly", "director", "dirt", "dirty", "disability", "disagree", "disappear",
    "disaster", "discipline", "discourse", "discover", "discovery", "discrimination", "discuss", "discussion", "disease", "dish",
    "dismiss", "disorder", "display", "dispute", "distance", "distant", "distinct", "distinction", "distinguish", "distribute",
    "distribution", "district", "disturb", "diverse", "diversity", "divide", "division", "divorce", "dna", "do",
    "doctor", "document", "dog", "domestic", "dominant", "dominate", "door", "double", "doubt", "down",
    "downtown", "dozen", "draft", "drag", "drama", "dramatic", "dramatically", "draw", "drawing", "dream",
    "dress", "drink", "drive", "driver", "drop", "drug", "dry", "due", "during", "dust",
    "duty", "each", "eager", "ear", "early", "earn", "earnings", "earth", "ease", "easily",
    "east", "eastern", "easy", "eat", "economic", "economics", "economist", "economy", "edge", "edition",
    "editor", "educate", "education", "educational", "educator", "effect", "effective", "effectively", "efficiency", "efficient",
    "effort", "egg", "eight", "either", "elderly", "elect", "election", "electric", "electricity", "electronic",
    "element", "elementary", "eliminate", "elite", "else", "elsewhere", "emerge", "emergency", "emission", "emotion",
    "emotional", "emphasis", "emphasize", "employ", "employee", "employer", "employment", "empty", "enable", "encounter",
    "encourage", "end", "enemy", "energy", "enforcement", "engage", "engine", "engineer", "engineering", "english",
    "enhance", "enjoy", "enormous", "enough", "ensure", "enter", "enterprise", "entertainment", "entire", "entirely",
    "entrance", "entry", "environment", "environmental", "episode", "equal", "equally", "equipment", "era", "error",
    "escape", "especially", "essay", "essential", "essentially", "establish", "establishment", "estate", "estimate", "etc",
    "ethics", "ethnic", "european", "evaluate", "evaluation", "even", "evening", "event", "eventually", "ever",
    "every", "everybody", "everyday", "everyone", "everything", "everywhere", "evidence", "evolution", "evolve", "exact",
    "exactly", "examination", "examine", "example", "exceed", "excellent", "except", "exception", "exchange", "exciting",
    "executive", "exercise", "exhibit", "exhibition", "exist", "existence", "existing", "expand", "expansion", "expect",
    "expectation", "expense", "expensive", "experience", "experiment", "expert", "explain", "explanation", "explode", "explore",
    "explosion", "expose", "exposure", "express", "expression", "extend", "extension", "extensive", "extent", "external",
    "extra", "extraordinary", "extreme", "extremely", "eye", "fabric", "face", "facility", "fact", "factor",
    "factory", "faculty", "fail", "failure", "fair", "fairly", "faith", "fall", "false", "fame",
    "familiar", "family", "famous", "fan", "fantasy", "far", "farm", "farmer", "fashion", "fast",
    "fat", "father", "fault", "favor", "favorite", "fear", "feature", "federal", "fee", "feed",
    "feedback", "feel", "feeling", "fellow", "female", "fence", "few", "fiber", "fiction", "field",
    "fifteen", "fifth", "fifty", "fight", "fighter", "figure", "file", "fill", "film", "final",
    "finally", "finance", "financial", "find", "finding", "fine", "finger", "finish", "fire", "firm",
    "first", "fish", "fishing", "fit", "fitness", "five", "fix", "flag", "flame", "flat",
    "flavor", "flee", "flesh", "flight", "floor", "flow", "flower", "fly", "focus", "folk",
    "follow", "following", "food", "foot", "football", "for", "force", "foreign", "forest", "forever",
    "forget", "form", "formal", "formation", "former", "formula", "forth", "fortune", "forward", "found",
    "foundation", "founder", "four", "fourth", "frame", "framework", "free", "freedom", "freeze", "french",
    "frequency", "frequent", "fresh", "friend", "friendly", "friendship", "from", "front", "fruit", "frustration",
    "fuel", "full", "fully", "fun", "function", "fund", "fundamental", "funny", "furniture", "furthermore",
    "future", "gain", "gallery", "game", "gap", "garage", "garden", "gas", "gate", "gather",
    "gay", "gaze", "gear", "gender", "gene", "general", "generally", "generate", "generation", "genetic",
    "gentleman", "gently", "german", "gesture", "get", "ghost", "giant", "gift", "girl", "girlfriend",
    "give", "given", "glad", "glance", "glass", "global", "glove", "goal", "god", "gold",
    "golden", "golf", "good", "government", "governor", "grab", "grade", "gradually", "graduate", "grain",
    "grand", "grant", "grass", "grave", "great", "greatest", "green", "grocery", "ground", "group",
    "grow", "growth", "guarantee", "guard", "guess", "guest", "guide", "guideline", "guilty", "gun",
    "guy", "habit", "hair", "half", "hall", "hand", "handle", "hang", "happen", "happy",
    "hard", "hardly", "harm", "hat", "hate", "have", "head", "headline", "health", "healthy",
    "hear", "hearing", "heart", "heat", "heavy", "height", "helicopter", "hell", "hello", "help",
    "helpful", "hence", "her", "here", "heritage", "hero", "herself", "hey", "hi", "hide",
    "high", "highlight", "highly", "highway", "hill", "him", "himself", "hip", "hire", "his",
    "historian", "historic", "historical", "history", "hit", "hold", "hole", "holiday", "holy", "home",
    "homeless", "honest", "honey", "honor", "hope", "horizon", "horror", "horse", "hospital", "host",
    "hot", "hotel", "hour", "house", "household", "housing", "how", "however", "huge", "human",
    "humor", "hundred", "hungry", "hunter", "hunting", "hurt", "husband", "hypothesis", "i", "ice",
    "idea", "ideal", "identification", "identify", "identity", "ie", "if", "ignore", "ill", "illegal",
    "illness", "illustrate", "image", "imagination", "imagine", "immediate", "immediately", "immigrant", "immigration", "impact",
    "implement", "implication", "imply", "importance", "important", "impose", "impossible", "impress", "impression", "impressive",
    "improve", "improvement", "in", "incentive", "incident", "include", "including", "income", "incorporate", "increase",
    "increased", "increasing", "increasingly", "incredible", "indeed", "independence", "independent", "index", "indicate", "indication",
    "individual", "industrial", "industry", "infant", "infection", "inflation", "influence", "inform", "information", "ingredient",
    "initial", "initially", "initiative", "injury", "inner", "innocent", "inquiry", "inside", "insight", "insist",
    "inspire", "install", "instance", "instead", "institution", "institutional", "instruction", "instructor", "instrument", "insurance",
    "intelligence", "intend", "intense", "intensity", "intention", "interaction", "interest", "interested", "interesting", "internal",
    "international", "internet", "interpret", "interpretation", "intervention", "interview", "into", "introduce", "introduction", "invasion",
    "invest", "investigate", "investigation", "investigator", "investment", "investor", "invite", "involve", "involved", "involvement",
    "iron", "is", "islamic", "island", "isolate", "issue", "it", "italian", "item", "its",
    "itself", "jacket", "jail", "jar", "jaw", "jazz", "jeans", "jet", "jew", "jewish",
    "job", "join", "joint", "joke", "journal", "journalist", "journey", "joy", "judge", "judgment",
    "juice", "jump", "jungle", "junior", "jury", "just", "justice", "justify", "keep", "key",
    "kick", "kid", "kill", "kind", "king", "kiss", "kitchen", "knee", "knife", "knock",
    "know", "knowledge", "lab", "label", "labor", "laboratory", "lack", "lady", "lake", "land",
    "landscape", "language", "large", "largely", "last", "late", "later", "latin", "latter", "laugh",
    "launch", "law", "lawn", "lawsuit", "lawyer", "lay", "layer", "lead", "leader", "leadership",
    "leading", "leaf", "league", "lean", "learn", "learning", "least", "leather", "leave", "left",
    "leg", "legacy", "legal", "legend", "legislation", "lemon", "length", "less", "lesson", "let",
    "letter", "level", "liberal", "library", "license", "lie", "life", "lifestyle", "lifetime", "lift",
    "light", "like", "likely", "limit", "line", "link", "lip", "list", "listen", "literally",
    "literary", "literature", "little", "live", "living", "load", "loan", "local", "locate", "location",
    "lock", "long", "look", "loose", "lose", "loss", "lost", "lot", "lots", "loud",
    "love", "lovely", "lover", "low", "lower", "luck", "lucky", "lunch", "lung", "machine",
    "mad", "magazine", "mail", "main", "mainly", "maintain", "major", "majority", "make", "maker",
    "male", "mall", "man", "manage", "management", "manager", "manner", "manufacturer", "many", "map",
    "margin", "mark", "market", "marketing", "marriage", "married", "marry", "mask", "mass", "massive",
    "master", "match", "material", "math", "matter", "maximum", "maybe", "mayor", "meal", "mean",
    "meaning", "meanwhile", "measure", "measurement", "meat", "mechanism", "media", "medical", "medication", "medicine",
    "medium", "meet", "meeting", "member", "membership", "memory", "mental", "mention", "menu", "mere",
    "merely", "mess", "message", "metal", "meter", "method", "middle", "might", "military", "milk",
    "million", "mind", "mineral", "minimum", "minister", "minor", "minority", "minute", "mirror", "miss",
    "mission", "mistake", "mix", "mixture", "mm", "mode", "model", "moderate", "modern", "modest",
    "mom", "moment", "money", "monitor", "month", "mood", "moon", "moral", "more", "moreover",
    "morning", "mortgage", "most", "mostly", "mother", "motion", "motivation", "motor", "mount", "mountain",
    "mouse", "mouth", "move", "movement", "movie", "mr", "mrs", "ms", "much", "multiple",
    "murder", "muscle", "museum", "music", "musical", "musician", "must", "mutual", "my", "myself",
    "mystery", "myth", "naked", "name", "narrative", "narrow", "nation", "national", "native", "natural",
    "naturally", "nature", "near", "nearby", "nearly", "necessarily", "necessary", "neck", "need", "negative",
    "negotiate", "negotiation", "neighbor", "neighborhood", "neither", "nerve", "nervous", "net", "network", "never",
    "nevertheless", "new", "news", "newspaper", "next", "nice", "night", "nine", "no", "nobody",
    "nod", "noise", "nomination", "none", "nonetheless", "nor", "normal", "normally", "north", "northern",
    "nose", "not", "note", "nothing", "notice", "notion", "novel", "now", "nowhere", "nt",
    "nuclear", "number", "numerous", "nurse", "nut", "object", "objective", "obligation", "observation", "observe",
    "observer", "obtain", "obvious", "obviously", "occasion", "occasionally", "occupation", "occupy", "occur", "ocean",
    "odd", "odds", "of", "off", "offense", "offensive", "offer", "office", "officer", "official",
    "often", "oh", "oil", "ok", "okay", "old", "olympic", "on", "once", "one",
    "ongoing", "onion", "online", "only", "onto", "open", "opening", "operate", "operating", "operation",
    "operator", "opinion", "opponent", "opportunity", "oppose", "opposite", "opposition", "option", "or", "orange",
    "order", "ordinary", "organic", "organization", "organize", "orientation", "origin", "original", "originally", "other",
    "others", "otherwise", "ought", "our", "ourselves", "out", "outcome", "outside", "oven", "over",
    "overall", "overcome", "overlook", "owe", "own", "owner", "pace", "pack", "package", "page",
    "pain", "painful", "paint", "painter", "painting", "pair", "pale", "palm", "pan", "panel",
    "panic", "paper", "parent", "park", "parking", "part", "participant", "participate", "participation", "particular",
    "particularly", "partly", "partner", "partnership", "party", "pass", "passage", "passenger", "passion", "past",
    "patch", "path", "patient", "pattern", "pay", "payment", "peace", "peak", "peer", "penalty",
    "people", "pepper", "per", "perceive", "percentage", "perception", "perfect", "perform", "performance", "perhaps",
    "period", "permanent", "permission", "permit", "person", "personal", "personality", "personally", "personnel", "perspective",
    "persuade", "pet", "phase", "phenomenon", "philosophy", "phone", "photo", "photograph", "photographer", "phrase",
    "physical", "physically", "physician", "piano", "pick", "picture", "pie", "piece", "pile", "pilot",
    "pin", "pink", "pipe", "pitch", "place", "plain", "plan", "plane", "planet", "planning",
    "plant", "plastic", "plate", "platform", "play", "player", "please", "pleasure", "plenty", "plus",
    "pm", "pocket", "poem", "poet", "poetry", "point", "pole", "police", "policy", "political",
    "politically", "politician", "politics", "poll", "pollution", "pool", "poor", "pop", "popular", "population",
    "porch", "port", "portion", "portrait", "portray", "pose", "position", "positive", "possess", "possibility",
    "possible", "possibly", "post", "pot", "potato", "potential", "potentially", "pound", "pour", "poverty",
    "powder", "power", "powerful", "practical", "practice", "pray", "precisely", "predict", "prefer", "pregnancy",
    "pregnant", "preparation", "prepare", "prescription", "presence", "present", "presentation", "preserve", "president", "presidential",
    "press", "pressure", "pretend", "pretty", "prevent", "previous", "previously", "price", "pride", "priest",
    "primarily", "primary", "prime", "principal", "principle", "print", "prior", "priority", "prison", "prisoner",
    "privacy", "private", "probably", "problem", "procedure", "proceed", "process", "produce", "producer", "product",
    "production", "profession", "professional", "professor", "profile", "profit", "program", "progress", "project", "prominent",
    "promise", "promote", "prompt", "proof", "proper", "properly", "property", "proportion", "proposal", "propose",
    "proposed", "prosecutor", "prospect", "protect", "protection", "protein", "protest", "proud", "prove", "provide",
    "provider", "province", "provision", "psychological", "psychologist", "psychology", "public", "publication", "publicly", "publish",
    "publisher", "pull", "punishment", "purchase", "pure", "purpose", "pursue", "push", "put", "qualify",
    "quality", "quarter", "question", "quick", "quickly", "quiet", "quietly", "quit", "quite", "quote",
    "race", "racial", "radical", "radio", "rail", "rain", "raise", "range", "rank", "rapid",
    "rapidly", "rare", "rarely", "rate", "rather", "rating", "ratio", "raw", "reach", "react",
    "reaction", "read", "reader", "reading", "ready", "real", "reality", "realize", "really", "reason",
    "reasonable", "recall", "receive", "recent", "recently", "recipe", "recognition", "recognize", "recommend", "recommendation",
    "record", "recording", "recover", "recovery", "recruit", "red", "reduce", "reduction", "refer", "reference",
    "reflect", "reflection", "reform", "refugee", "refuse", "regard", "regarding", "regardless", "regime", "region",
    "regional", "register", "regular", "regularly", "regulate", "regulation", "reinforce", "reject", "relate", "relation",
    "relationship", "relative", "relatively", "relax", "release", "relevant", "relief", "religion", "religious", "rely",
    "remain", "remaining", "remarkable", "remember", "remind", "remote", "remove", "repeat", "replace", "reply",
    "report", "reporter", "represent", "representation", "representative", "republican", "reputation", "request", "require", "requirement",
    "research", "researcher", "resemble", "reservation", "resident", "resist", "resistance", "resolution", "resolve", "resort",
    "resource", "respect", "respond", "respondent", "response", "responsibility", "responsible", "rest", "restaurant", "restore",
    "restriction", "result", "retain", "retire", "retirement", "return", "reveal", "revenue", "review", "revolution",
    "rhythm", "rice", "rich", "rid", "ride", "rifle", "right", "ring", "rise", "risk",
    "river", "road", "rock", "role", "roll", "romantic", "roof", "room", "root", "rope",
    "rose", "rough", "roughly", "round", "route", "routine", "row", "rub", "rule", "run",
    "running", "rural", "rush", "russian", "sacred", "sad", "safe", "safety", "sake", "salad",
    "salary", "sale", "sales", "salt", "same", "sample", "sanction", "sand", "satellite", "satisfaction",
    "satisfy", "sauce", "save", "saving", "say", "scale", "scandal", "scared", "scenario", "scene",
    "schedule", "scheme", "scholar", "scholarship", "school", "science", "scientific", "scientist", "scope", "score",
    "scream", "screen", "script", "sea", "search", "season", "seat", "second", "secret", "secretary",
    "section", "sector", "secure", "security", "see", "seed", "seek", "seem", "segment", "seize",
    "select", "selection", "self", "sell", "senate", "senator", "send", "senior", "sense", "sensitive",
    "sentence", "separate", "sequence", "series", "serious", "seriously", "serve", "service", "session", "set",
    "setting", "settle", "settlement", "seven", "several", "severe", "sex", "sexual", "shade", "shadow",
    "shake", "shall", "shape", "share", "sharp", "she", "sheet", "shelf", "shell", "shelter",
    "shift", "shine", "ship", "shirt", "shock", "shoe", "shoot", "shop", "shopping", "shore",
    "short", "shortly", "shot", "should", "shoulder", "shout", "show", "shower", "shut", "sick",
    "side", "sigh", "sight", "sign", "signal", "significance", "significant", "significantly", "silence", "silent",
    "silk", "silly", "silver", "similar", "similarly", "simple", "simply", "sin", "since", "sing",
    "singer", "single", "sink", "sir", "sister", "sit", "site", "situation", "six", "size",
    "ski", "skill", "skin", "sky", "slave", "sleep", "slice", "slide", "slight", "slightly",
    "slip", "slow", "slowly", "small", "smart", "smell", "smile", "smoke", "smooth", "snap",
    "snow", "so", "so-called", "soccer", "social", "society", "sock", "soft", "software", "soil",
    "solar", "soldier", "solid", "solution", "solve", "some", "somebody", "somehow", "someone", "something",
    "sometimes", "somewhat", "somewhere", "son", "song", "soon", "sophisticated", "sore", "sorry", "sort",
    "soul", "sound", "soup", "source", "south", "southern", "soviet", "space", "spare", "speak",
    "speaker", "special", "specialist", "species", "specific", "specifically", "speech", "speed", "spell", "spend",
    "spending", "spin", "spirit", "spiritual", "split", "spokesman", "sport", "spot", "spread", "spring",
    "square", "squeeze", "stability", "stable", "staff", "stage", "stain", "stair", "stake", "stand",
    "standard", "standing", "star", "stare", "start", "state", "statement", "station", "statistics", "status",
    "stay", "steady", "steal", "steam", "steel", "step", "stick", "still", "stir", "stock",
    "stomach", "stone", "stop", "storage", "store", "storm", "story", "straight", "strange", "stranger",
    "strategic", "strategy", "stream", "street", "strength", "stress", "stretch", "strike", "string", "strip",
    "stroke", "strong", "strongly", "structure", "struggle", "student", "studio", "study", "stuff", "stupid",
    "style", "subject", "submit", "subsequent", "substance", "substantial", "succeed", "success", "successful", "such",
    "sudden", "suddenly", "suffer", "sugar", "suggest", "suggestion", "suicide", "suit", "summer", "summit",
    "sun", "super", "supply", "support", "supporter", "suppose", "supposed", "supreme", "sure", "surely",
    "surface", "surgery", "surprise", "surprised", "surprising", "surround", "survey", "survival", "survive", "survivor",
    "suspect", "sustain", "swear", "sweep", "sweet", "swim", "swing", "switch", "symbol", "symptom",
    "syndrome", "system", "table", "tackle", "tactic", "tail", "take", "tale", "talent", "talk",
    "tall", "tank", "tap", "tape", "target", "task", "taste", "tax", "taxpayer", "tea",
    "teach", "teacher", "teaching", "team", "tear", "technical", "technique", "technology", "teen", "teenager",
    "telephone", "telescope", "television", "tell", "temperature", "temporary", "ten", "tend", "tendency", "tennis",
    "tension", "tent", "term", "terms", "terrible", "territory", "terror", "terrorism", "terrorist", "test",
    "testify", "testimony", "testing", "text", "than", "thank", "thanks", "that", "the", "theater",
    "their", "them", "theme", "themselves", "then", "theory", "therapy", "there", "therefore", "these",
    "they", "thick", "thin", "thing", "think", "thinking", "third", "thirty", "this", "those",
    "though", "thought", "thousand", "threat", "threaten", "three", "throat", "through", "throughout", "throw",
    "thumb", "thus", "ticket", "tie", "tight", "time", "tiny", "tip", "tire", "tired",
    "tissue", "title", "to", "tobacco", "today", "toe", "together", "tomato", "tomorrow", "tone",
    "tongue", "tonight", "too", "tool", "tooth", "top", "topic", "toss", "total", "totally",
    "touch", "tough", "tour", "tourist", "tournament", "toward", "towards", "tower", "town", "toy",
    "trace", "track", "trade", "tradition", "traditional", "traffic", "tragedy", "trail", "train", "training",
    "transfer", "transform", "transformation", "transition", "translate", "transportation", "trap", "trash", "travel", "treat",
    "treatment", "treaty", "tree", "tremendous", "trend", "trial", "tribe", "trick", "trip", "troop",
    "trouble", "truck", "true", "truly", "trust", "truth", "try", "tube", "tunnel", "turn",
    "tv", "twelve", "twenty", "twice", "twin", "two", "type", "typical", "typically", "ugly",
    "ultimate", "ultimately", "unable", "uncle", "under", "undergo", "understand", "understanding", "unfortunately", "uniform",
    "union", "unique", "unit", "united", "unity", "universal", "universe", "university", "unknown", "unless",
    "unlike", "unlikely", "until", "unusual", "up", "upon", "upper", "urban", "urge", "us",
    "use", "used", "useful", "user", "usual", "usually", "utility", "vacation", "valley", "valuable",
    "value", "variable", "variation", "variety", "various", "vast", "vegetable", "vehicle", "venture", "version",
    "versus", "very", "vessel", "veteran", "via", "victim", "victory", "video", "view", "viewer",
    "village", "violate", "violation", "violence", "violent", "virtually", "virtue", "virus", "visible", "vision",
    "visit", "visitor", "visual", "vital", "voice", "volume", "volunteer", "vote", "voter", "vs",
    "vulnerable", "wage", "wait", "wake", "walk", "wall", "wander", "want", "war", "warm",
    "warn", "warning", "wash", "waste", "watch", "water", "wave", "way", "we", "weak",
    "wealth", "wealthy", "weapon", "wear", "weather", "wedding", "week", "weekend", "weekly", "weigh",
    "weight", "welcome", "welfare", "well", "west", "western", "wet", "what", "whatever", "wheel",
    "when", "whenever", "where", "whereas", "whether", "which", "while", "whisper", "white", "who",
    "whole", "whom", "whose", "why", "wide", "widely", "widespread", "wife", "wild", "will",
    "willing", "win", "wind", "window", "wine", "wing", "winner", "winter", "wipe", "wire",
    "wisdom", "wise", "wish", "with", "withdraw", "within", "without", "witness", "woman", "wonder",
    "wonderful", "wood", "wooden", "word", "work", "worker", "working", "workshop", "world", "worried",
    "worry", "worth", "would", "wound", "wrap", "write", "writer", "writing", "wrong", "yard",
    "yeah", "year", "yell", "yellow", "yes", "yesterday", "yet", "yield", "you", "young",
    "your", "yours", "yourself", "youth", "zero", "zoo",
]

# batch-AU: fresh vocabulary after batch-AM exhaustion (early-alphabet words absent from garage path).
_MASTER_DICT_BATCH_AU = [
    "abandon", "ability", "able", "abortion", "about", "above", "abroad", "absence", "absent", "absolute",
    "absolutely", "absorb", "abstract", "abuse", "academic", "accept", "access", "accident", "accompany", "accomplish",
    "accord", "account", "accurate", "accuse", "achieve", "achievement", "acid", "acknowledge", "acquire", "across",
    "act", "action", "active", "activist", "activity", "actor", "actress", "actual", "actually", "adapt",
    "add", "addition", "additional", "address", "adequate", "adjust", "adjustment", "administration", "administrator", "admire",
    "admission", "admit", "adolescent", "adopt", "adult", "advance", "advanced", "advantage", "adventure", "advertising",
    "advice", "advise", "adviser", "advocate", "affair", "affect", "afford", "afraid", "african", "after",
    "afternoon", "again", "against", "age", "agency", "agenda", "agent", "aggressive", "ago", "agree",
    "agreement", "agricultural", "ahead", "aid", "aide", "aim", "air", "aircraft", "airline", "airport",
    "album", "alcohol", "alive", "all", "alliance", "allow", "ally", "almost", "alone", "along",
    "already", "also", "alter", "alternative", "although", "always", "amazing", "american", "among", "amount",
    "analysis", "analyst", "analyze", "ancient", "and", "anger", "angle", "angry", "animal", "anniversary",
    "announce", "annual", "another", "answer", "anxiety", "any", "anybody", "anymore", "anyone", "anything",
    "anyway", "anywhere", "apart", "apartment", "apparent", "apparently", "appeal", "appear", "appearance", "apple",
    "application", "apply", "appoint", "appointment", "appreciate", "approach", "appropriate", "approval", "approve", "approximately",
    "architect", "area", "argue", "argument", "arise", "arm", "armed", "army", "around", "arrange",
    "arrangement", "arrest", "arrival", "arrive", "art", "article", "artist", "artistic", "as", "asian",
    "aside", "ask", "asleep", "aspect", "assault", "assert", "assess", "assessment", "asset", "assign",
    "assignment", "assist", "assistance", "assistant", "associate", "association", "assume", "assumption", "assure", "at",
    "athlete", "athletic", "atmosphere", "attach", "attack", "attempt", "attend", "attention", "attitude", "attorney",
    "attract", "attractive", "attribute", "auction", "audience", "author", "authority", "auto", "available", "average",
    "avoid", "award", "aware", "awareness", "away", "awful", "baby", "back", "background", "bad",
    "badly", "bag", "bake", "balance", "ball", "ban", "band", "bank", "bar", "barely",
    "barrel", "barrier", "base", "baseball", "basic", "basically", "basis", "basket", "basketball", "bathroom",
    "battery", "battle", "be", "beach", "bean", "bear", "beat", "beautiful", "beauty", "because",
    "become", "bed", "bedroom", "beer", "before", "begin", "beginning", "behavior", "behind", "being",
    "belief", "believe", "bell", "belong", "below", "belt", "bench", "bend", "beneath", "benefit",
    "beside", "besides", "best", "bet", "better", "between", "beyond", "bible", "big", "bike",
    "bill", "billion", "bind", "biological", "bird", "birth", "birthday", "bit", "black", "blade",
    "blame", "blanket", "blind", "block", "blood", "blow", "blue", "board", "boat", "body",
    "bomb", "bond", "bone", "book", "boom", "boot", "border", "born", "borrow", "boss",
    "both", "bother", "bottle", "bottom", "boundary", "bowl", "box", "boy", "boyfriend", "brain",
    "branch", "brand", "bread", "break", "breakfast", "breast", "breath", "breathe", "brick", "bridge",
    "brief", "bright", "brilliant", "bring", "british", "broad", "broken", "brother", "brown", "brush",
    "buck", "budget", "build", "building", "bullet", "bunch", "burden", "burn", "bury", "bus",
    "business", "busy", "but", "butter", "buy", "buyer", "by", "cabin", "cabinet", "cable",
    "cake", "calculate", "call", "camera", "camp", "campaign", "campus", "can", "canadian", "cancer",
    "candidate", "candle", "candy", "cap", "capability", "capable", "capacity", "capital", "captain", "capture",
    "car", "carbon", "card", "care", "career", "careful", "carefully", "carrier", "carry", "case",
    "cash", "cast", "cat", "catch", "category", "catholic", "cause", "ceiling", "celebrate", "celebration",
    "celebrity", "cell", "center", "central", "century", "ceo", "ceremony", "certain", "certainly", "chain",
    "chair", "chairman", "challenge", "chamber", "champion", "championship", "chance", "change", "changing", "channel",
    "chapter", "character", "characteristic", "characterize", "charge", "charity", "chart", "chase", "cheap", "check",
    "cheek", "cheese", "chef", "chemical", "chest", "chicken", "chief", "child", "childhood", "chinese",
    "chip", "chocolate", "choice", "cholesterol", "choose", "christian", "christmas", "church", "cigarette", "circle",
    "circumstance", "cite", "citizen", "city", "civil", "civilian", "claim", "class", "classic", "classroom",
    "clean", "clear", "clearly", "client", "climate", "climb", "clinic", "clinical", "clock", "close",
    "closely", "closer", "clothes", "clothing", "cloud", "club", "clue", "cluster", "coach", "coal",
    "coalition", "coast", "coat", "code", "coffee", "cognitive", "cold", "collapse", "colleague", "collect",
    "collection", "collective", "college", "colonial", "color", "column", "combination", "combine", "come", "comedy",
    "comfort", "comfortable", "command", "commander", "comment", "commercial", "commission", "commit", "commitment", "committee",
    "common", "communicate", "communication", "community", "company", "compare", "comparison", "compete", "competition", "competitive",
    "competitor", "complain", "complaint", "complete", "completely", "complex", "complicated", "component", "compose", "composition",
    "comprehensive", "computer", "concentrate", "concentration", "concept", "concern", "concerned", "concert", "conclude", "conclusion",
    "concrete", "condition", "conduct", "conference", "confidence", "confident", "confirm", "conflict", "confront", "confusion",
    "congress", "congressional", "connect", "connection", "consciousness", "consensus", "consequence", "conservative", "consider", "considerable",
    "consideration", "consist", "consistent", "constant", "constantly", "constitute", "constitutional", "construct", "construction", "consultant",
    "consume", "consumer", "consumption", "contact", "contain", "container", "contemporary", "content", "contest", "context",
    "continue", "continued", "contract", "contrast", "contribute", "contribution", "control", "controversial", "controversy", "convention",
    "conventional", "conversation", "convert", "conviction", "convince", "cook", "cookie", "cooking", "cool", "cooperation",
    "cop", "cope", "copy", "core", "corn", "corner", "corporate", "corporation", "correct", "correspondent",
    "cost", "cotton", "couch", "could", "council", "counselor", "count", "counter", "country", "county",
    "couple", "courage", "course", "court", "cousin", "cover", "coverage", "cow", "crack", "craft",
    "crash", "crazy", "cream", "create", "creation", "creative", "creature", "credit", "crew", "crime",
    "criminal", "crisis", "criteria", "critic", "critical", "criticism", "criticize", "crop", "cross", "crowd",
    "crucial", "cry", "cultural", "culture", "cup", "curious", "current", "currently", "curriculum", "custom",
    "customer", "cut", "cycle", "dad", "daily", "damage", "dance", "danger", "dangerous", "dare",
    "dark", "darkness", "data", "database", "date", "daughter", "day", "dead", "deal", "dealer",
    "dear", "death", "debate", "debt", "decade", "decide", "decision", "deck", "declare", "decline",
    "decrease", "deep", "deeply", "deer", "defeat", "defend", "defendant", "defense", "defensive", "deficit",
    "define", "definitely", "definition", "degree", "delay", "deliver", "delivery", "demand", "democracy", "democrat",
    "democratic", "demonstrate", "demonstration", "deny", "department", "depend", "dependent", "depending", "depict", "depression",
    "depth", "deputy", "derive", "describe", "description", "desert", "deserve", "design", "designer", "desire",
    "desk", "desperate", "despite", "destroy", "destruction", "detail", "detailed", "detect", "determine", "develop",
    "developing", "development", "device", "devote", "dialogue", "die", "diet", "differ", "difference", "different",
    "differently", "difficult", "difficulty", "dig", "digital", "dimension", "dining", "dinner", "direct", "direction",
    "directly", "director", "dirt", "dirty", "disability", "disagree", "disappear", "disaster", "discipline", "discourse",
    "discover", "discovery", "discrimination", "discuss", "discussion", "disease", "dish", "dismiss", "disorder", "display",
    "dispute", "distance", "distant", "distinct", "distinction", "distinguish", "distribute", "distribution", "district", "disturb",
    "diverse", "diversity", "divide", "division", "divorce", "dna", "do", "doctor", "document", "dog",
    "domestic", "dominant", "dominate", "door", "double", "doubt", "down", "downtown", "dozen", "draft",
    "drag", "drama", "dramatic", "dramatically", "draw", "drawing", "dream", "dress", "drink", "drive",
    "driver", "drop", "drug", "dry", "due", "during", "dust", "duty", "each", "eager",
    "ear", "early", "earn", "earnings", "earth", "ease", "easily", "east", "eastern", "easy",
    "eat", "economic", "economics", "economist", "economy", "edge", "edition", "editor", "educate", "education",
    "educational", "educator", "effect", "effective", "effectively", "efficiency", "efficient", "effort", "egg", "eight",
    "either", "elderly", "elect", "election", "electric", "electricity", "electronic", "element", "elementary", "eliminate",
    "elite", "else", "elsewhere", "email", "embrace", "emerge", "emergency", "emission", "emotion", "emotional",
    "emphasis", "emphasize", "employ", "employee", "employer", "employment", "empty", "enable", "encounter", "encourage",
    "end", "enemy", "energy", "enforcement", "engage", "engine", "engineer", "engineering", "english", "enhance",
    "enjoy", "enormous", "enough", "ensure", "enter", "enterprise", "entertainment", "entire", "entirely", "entrance",
    "entry", "environment", "environmental", "episode", "equal", "equally", "equipment", "era", "error", "escape",
    "especially", "essay", "essential", "essentially", "establish", "establishment", "estate", "estimate", "etc", "ethics",
    "ethnic", "european", "evaluate", "evaluation", "even", "evening", "event", "eventually", "ever", "every",
    "everybody", "everyday", "everyone", "everything", "everywhere", "evidence", "evolution", "evolve", "exact", "exactly",
    "examination", "examine", "example", "exceed", "excellent", "except", "exception", "exchange", "exciting", "executive",
    "exercise", "exhibit", "exhibition", "exist", "existence", "existing", "expand", "expansion", "expect", "expectation",
    "expense", "expensive", "experience", "experiment", "expert", "explain", "explanation", "explode", "explore", "explosion",
    "expose", "express", "expression", "extend", "extension", "extensive", "extent", "external", "extra", "extraordinary",
    "extreme", "extremely", "eye", "fabric", "face", "facility", "fact", "factor", "factory", "faculty",
]

# batch-AV: fresh vocabulary for batch-AT after AE/AU exhaustion.
_MASTER_DICT_BATCH_AV = [
    "gadfly", "gadget", "gaffe", "gait", "galley", "gallant", "galvanize", "gambit", "gamut", "gander",
    "gape", "garble", "gargle", "garish", "garland", "garment", "garner", "garrison", "gasket", "gasp",
    "gaudy", "gaunt", "gavel", "gawk", "gazette", "geek", "giggle", "gild", "gimmick", "ginger",
    "gingham", "giraffe", "gird", "gist", "glade", "glider", "glimmer", "glisten", "glitch", "glitter",
    "gloom", "glossary", "glow", "glue", "glum", "gnaw", "gnome", "gnostic", "goad", "gobble",
    "goggle", "gondola", "gong", "goodwill", "goofy", "gorge", "gorilla", "gory", "gospel", "gossip",
    "gothic", "gouge", "gourd", "gourmet", "graceful", "gracious", "gradient", "graft", "grammar", "granite",
    "grantee", "granular", "grape", "graph", "graphite", "grapple", "grasp", "greased", "greet", "grid",
    "grief", "grill", "grimace", "grime", "grin", "grind", "gripe", "grit", "groan", "grocer",
    "groom", "groove", "gross", "grotto", "grouchy", "groundhog", "grove", "growl", "grudge", "gruff",
    "grumble", "grunt", "guacamole", "guardrail", "guesswork", "guesthouse", "guidance", "guile", "gulf", "gull",
    "gulp", "gumption", "gurgle", "guru", "gush", "gusto", "gusty", "gutter", "guzzle", "gypsy",
    "hackney", "haggard", "hairpin", "halcyon", "halter", "halve", "hamlet", "hammock", "hamper", "handcuff",
    "handshake", "hangar", "hanker", "haphazard", "hapless", "harass", "harbinger", "harden", "hardy", "hawk",
    "haystack", "hazel", "headband", "headlong", "headstrong", "headway", "hearken", "heartache", "heartbeat", "hearth",
    "heartland", "heckle", "hedgehog", "heed", "heft", "heighten", "heirloom", "helix", "helpline", "hemisphere",
    "henchman", "herald", "herb", "hermit", "herring", "hexagon", "hiatus", "hibernate", "hiccup", "hideaway",
    "hideous", "hijack", "hilarious", "hillside", "hinder", "hinge", "hobbyist", "hoard", "hoarse", "holistic",
    "homage", "homebound", "homely", "homestead", "hone", "honeycomb", "hoodwink", "hoof", "hooray", "hopscotch",
    "horticulture", "hospitable", "hotline", "hourglass", "houseboat", "hover", "howl", "huddle", "hue", "huff",
    "hull", "humble", "humdrum", "humid", "humiliate", "hunch", "hurdle", "hurl", "hurricane", "hurried",
    "husky", "hustle", "hydrant", "hygiene", "hymn", "hyperlink", "hyphen", "ibex", "icicle", "icon",
    "idle", "idol", "ignite", "illusion", "imitate", "immense", "imminent", "impale", "impart", "impede",
    "impel", "implant", "impound", "impromptu", "improvise", "impure", "inactive", "incantation", "incense", "incite",
    "incline", "incognito", "incoherent", "incubate", "incur", "indict", "indigo", "indulge", "inept", "inertia",
]

# batch-AW: round89 dict200 — fresh vocabulary after batch-AV exhaustion.
_MASTER_DICT_BATCH_AW = [
    "inertial", "inertion", "inertly", "inertness", "inerubescent", "inerudite", "ineruditely", "inerudition", "inescapable", "inescapably",
    "inesculent", "inescutcheon", "inesite", "inessential", "inestimable", "inestimably", "inestivation", "inethical", "ineunt", "ineuphonious",
    "inevadible", "inevadibly", "inevaporable", "inevasible", "inevidence", "inevident", "inevitable", "inevitably", "inexact", "inexacting",
    "inexactitude", "inexactly", "inexactness", "inexcellence", "inexcitable", "inexclusive", "inexcusable", "inexcusably", "inexecutable", "inexecution",
    "inexertion", "inexhausted", "inexhaustive", "inexigible", "inexist", "inexistence", "inexistency", "inexistent", "inexorable", "inexorably",
    "inexpansible", "inexpansive", "inexpectancy", "inexpectant", "inexpected", "inexpectedly", "inexpedience", "inexpediency", "inexpedient", "inexpensive",
    "inexperience", "inexpert", "inexpertly", "inexpertness", "inexpiable", "inexpiably", "inexpiate", "inexplicable", "inexplicably", "inexplicit",
    "inexplicitly", "inexplorable", "inexplosive", "inexportable", "inexposable", "inexposure", "inexpress", "inexpressive", "inexpugnable", "inexpugnably",
    "inexpungible", "inextant", "inextended", "inextensible", "inextensile", "inextension", "inextensive", "inextinct", "inextirpable", "inextricable",
    "inextricably", "inez", "inface", "infall", "infallible", "infallibly", "infalling", "infame", "infamiliar", "infamize",
    "infamonize", "infamous", "infamously", "infamousness", "infamy", "infancy", "infand", "infandous", "infang", "infanglement",
    "infangthief", "infant", "infanta", "infantado", "infante", "infanthood", "infanticidal", "infanticide", "infantile", "infantilism",
    "infantility", "infantine", "infantlike", "infantry", "infantryman", "infarct", "infarctate", "infarcted", "infarction", "infare",
    "infatuate", "infatuatedly", "infatuation", "infatuator", "infaust", "infeasible", "infect", "infectant", "infected", "infectedness",
    "infecter", "infectible", "infection", "infectionist", "infectious", "infectiously", "infective", "infectivity", "infector", "infectress",
    "infectuous", "infecund", "infecundity", "infeed", "infeft", "infeftment", "infelicific", "infelicitous", "infelicity", "infelonious",
    "infelt", "infeminine", "infer", "inferable", "inference", "inferent", "inferential", "inferior", "inferiorism", "inferiority",
    "inferiorize", "inferiorly", "infern", "infernal", "infernalism", "infernality", "infernalize", "infernally", "infernalry", "infernalship",
    "inferno", "inferomedian", "inferrer", "inferrible", "inferringly", "infertile", "infertilely", "infertility", "infest", "infestant",
    "infestation", "infester", "infestive", "infestivity", "infestment", "infeudation", "infibulate", "infibulation", "inficete", "infidel",
]

# batch-AX: round90 dict200 — fresh vocabulary after batch-AW exhaustion.
_MASTER_DICT_BATCH_AX = [
    "infidelic", "infidelical", "infidelism", "infidelistic", "infidelity", "infidelize", "infidelly", "infield", "infielder", "infieldsman",
    "infighter", "infighting", "infill", "infilling", "infilm", "infilter", "infiltrate", "infiltration", "infiltrative", "infinitant",
    "infinitarily", "infinitary", "infinitate", "infinitation", "infinite", "infinitely", "infiniteness", "infinitesimal", "infinitesimalism", "infinitesimality",
    "infinitesimally", "infinitesimalness", "infiniteth", "infinitieth", "infinitival", "infinitivally", "infinitive", "infinitively", "infinitize", "infinitude",
    "infinituple", "infinity", "infirm", "infirmarer", "infirmaress", "infirmarian", "infirmary", "infirmate", "infirmation", "infirmative",
    "infirmity", "infirmly", "infirmness", "infissile", "infit", "infitter", "infix", "infixion", "inflame", "inflamed",
    "inflamedly", "inflamedness", "inflamer", "inflaming", "inflamingly", "inflammability", "inflammable", "inflammableness", "inflammably", "inflammation",
    "inflammative", "inflammatorily", "inflammatory", "inflatable", "inflate", "inflated", "inflatedly", "inflatedness", "inflater", "inflatile",
    "inflatingly", "inflation", "inflationary", "inflationism", "inflationist", "inflative", "inflatus", "inflect", "inflected", "inflectedness",
    "inflection", "inflectional", "inflectionally", "inflectionless", "inflective", "inflector", "inflex", "inflexed", "inflexibility", "inflexible",
    "inflexibleness", "inflexibly", "inflexive", "inflict", "inflictable", "inflicter", "infliction", "inflictive", "inflood", "inflorescence",
    "inflorescent", "inflow", "inflowering", "influence", "influenceable", "influencer", "influencive", "influent", "influential", "influentiality",
    "influentially", "influenza", "influenzal", "influenzic", "influx", "influxable", "influxible", "influxibly", "influxion", "influxionism",
    "infold", "infolder", "infolding", "infoldment", "infoliate", "inform", "informable", "informal", "informality", "informalize",
    "informally", "informant", "information", "informational", "informative", "informatively", "informatory", "informed", "informedly", "informer",
    "informidable", "informingly", "informity", "infortiate", "infortitude", "infortunate", "infortunately", "infortunateness", "infortune", "infra",
    "infrabasal", "infrabestial", "infrabranchial", "infrabuccal", "infracanthal", "infracaudal", "infracelestial", "infracentral", "infracephalic", "infraclavicle",
    "infraclavicular", "infraclusion", "infraconscious", "infracortical", "infracostal", "infracostalis", "infracotyloid", "infract", "infractible", "infraction",
    "infractor", "infradentary", "infradiaphragmatic", "infragenual", "infraglacial", "infraglenoid", "infraglottic", "infragrant", "infragular", "infrahuman",
    "infrahyoid", "infralabial", "infralapsarian", "infralapsarianism", "infralinear", "infralittoral", "inframammary", "inframammillary", "inframandibular", "inframarginal",
]

# batch-AY: round91 dict200 — fresh vocabulary after batch-AX exhaustion.
_MASTER_DICT_BATCH_AY = [
    "inframedian", "inframontane", "inframundane", "infranatural", "infrangible", "infrangibly", "infranodal", "infranuclear", "infraocular", "infraoral",
    "infraorbital", "infrapose", "infraprotein", "infrapubian", "infraradular", "infrared", "infrarenal", "infrarenally", "infrarimal", "infraspinal",
    "infraspinate", "infraspinous", "infrasternal", "infrasutral", "infraterrene", "infratubal", "infravaginal", "infraventral", "infrequency", "infrequent",
    "infrequently", "infrigidate", "infringe", "infringement", "infringer", "infringible", "infructuose", "infructuous", "infrugal", "infrustrable",
    "infrustrably", "infula", "infumate", "infumated", "infumation", "infundibular", "infundibulum", "infuriate", "infuriately", "infuriation",
    "infuscate", "infuscation", "infuse", "infusedly", "infuser", "infusibility", "infusible", "infusile", "infusion", "infusionism",
    "infusionist", "infusive", "infusoria", "infusorial", "infusorian", "infusoriform", "infusorioid", "infusorium", "infusory", "ing",
    "inga", "ingaevones", "ingaevonic", "ingallantry", "ingate", "ingather", "ingatherer", "ingathering", "ingeldable", "ingeminate",
    "ingemination", "ingenerable", "ingenerably", "ingenerate", "ingenerately", "ingeneration", "ingenerative", "ingeniosity", "ingenious", "ingeniously",
    "ingenit", "ingenue", "ingenuity", "ingenuous", "ingenuously", "inger", "ingerminate", "ingest", "ingesta", "ingestible",
    "ingestion", "ingestive", "inghamite", "inghilois", "ingiver", "ingiving", "ingle", "inglenook", "ingleside", "inglobate",
    "inglobe", "inglorious", "ingloriously", "inglutition", "ingluvial", "ingluvies", "ingluviitis", "ingoing", "ingomar", "ingot",
    "ingotman", "ingraft", "ingrain", "ingrained", "ingrainedly", "ingram", "ingrandize", "ingrate", "ingrateful", "ingratefully",
    "ingrately", "ingratiate", "ingratiating", "ingratiation", "ingratiatory", "ingratitude", "ingravescent", "ingravidate", "ingredient", "ingress",
    "ingression", "ingressive", "ingross", "ingrow", "ingrown", "ingrownness", "ingrowth", "inguen", "inguinal", "inguinodynia",
    "inguklimiut", "ingulf", "ingulfment", "ingurgitate", "ingush", "inhabit", "inhabitable", "inhabitancy", "inhabitant", "inhabitation",
    "inhabitative", "inhabited", "inhabiter", "inhabitress", "inhalant", "inhalation", "inhalator", "inhale", "inhalement", "inhalent",
    "inhaler", "inharmonic", "inharmonical", "inharmonious", "inharmony", "inhaul", "inhauler", "inhaust", "inhaustion", "inhearse",
    "inheaven", "inhere", "inherence", "inherency", "inherent", "inherently", "inherit", "inheritable", "inheritably", "inheritage",
    "inheritance", "inheritor", "inheritress", "inheritrice", "inheritrix", "inhesion", "inhiate", "inhibit", "inhibitable", "inhibiter",
]

_seen_am_used: set[str] = (
    set(_combined_from_garage[: _ii + 1])
    | set(_BATCH_AH_DEDUP)
    | set(_BATCH_AI_DEDUP_FROZEN)
    | set(_BATCH_AJ_DEDUP_FROZEN)
    | set(_BATCH_AL_DEDUP_FROZEN)
)
_AM_TAIL = [s for s in _MASTER_DICT_BATCH_AL if s not in _seen_am_used]
_AM_SUPPLEMENT = [s for s in _MASTER_DICT_BATCH_AM if s not in _seen_am_used]
_seen_batch_am: set[str] = set()
_BATCH_AM_DEDUP: list[str] = []
for s in _AM_TAIL:
    if s in _seen_batch_am:
        continue
    _seen_batch_am.add(s)
    _BATCH_AM_DEDUP.append(s)
for s in _AM_SUPPLEMENT:
    if s in _seen_batch_am:
        continue
    _seen_batch_am.add(s)
    _BATCH_AM_DEDUP.append(s)
    if len(_BATCH_AM_DEDUP) >= DICT_LIMIT:
        break

_BATCH_AM_DEDUP_FROZEN = list(_BATCH_AM_DEDUP)

# batch-AN: continue after batch-AM terminus — next 200 real English words.
_seen_an_used: set[str] = (
    set(_combined_from_garage[: _ii + 1])
    | set(_BATCH_AH_DEDUP)
    | set(_BATCH_AI_DEDUP_FROZEN)
    | set(_BATCH_AJ_DEDUP_FROZEN)
    | set(_BATCH_AL_DEDUP_FROZEN)
    | set(_BATCH_AM_DEDUP_FROZEN)
)
_AN_TAIL = [s for s in _MASTER_DICT_BATCH_AM if s not in _seen_an_used]
_seen_batch_an: set[str] = set()
_BATCH_AN_DEDUP: list[str] = []
for s in _AN_TAIL:
    if s in _seen_batch_an:
        continue
    _seen_batch_an.add(s)
    _BATCH_AN_DEDUP.append(s)
    if len(_BATCH_AN_DEDUP) >= DICT_LIMIT:
        break
_BATCH_AN_DEDUP_FROZEN = list(_BATCH_AN_DEDUP)

# batch-AO: continue after batch-AN terminus (attention→attribute) — next 200 real English words.
_seen_ao_used: set[str] = (
    set(_combined_from_garage[: _ii + 1])
    | set(_BATCH_AH_DEDUP)
    | set(_BATCH_AI_DEDUP_FROZEN)
    | set(_BATCH_AJ_DEDUP_FROZEN)
    | set(_BATCH_AL_DEDUP_FROZEN)
    | set(_BATCH_AM_DEDUP_FROZEN)
    | set(_BATCH_AN_DEDUP_FROZEN)
)
_AO_TAIL = [s for s in _MASTER_DICT_BATCH_AM if s not in _seen_ao_used]
_seen_batch_ao: set[str] = set()
_BATCH_AO_DEDUP: list[str] = []
for s in _AO_TAIL:
    if s in _seen_batch_ao:
        continue
    _seen_batch_ao.add(s)
    _BATCH_AO_DEDUP.append(s)
    if len(_BATCH_AO_DEDUP) >= DICT_LIMIT:
        break
_BATCH_AO_DEDUP_FROZEN = list(_BATCH_AO_DEDUP)

# batch-AP: continue after batch-AO terminus (central) — next 200 real English words.
_seen_ap_used: set[str] = (
    set(_combined_from_garage[: _ii + 1])
    | set(_BATCH_AH_DEDUP)
    | set(_BATCH_AI_DEDUP_FROZEN)
    | set(_BATCH_AJ_DEDUP_FROZEN)
    | set(_BATCH_AL_DEDUP_FROZEN)
    | set(_BATCH_AM_DEDUP_FROZEN)
    | set(_BATCH_AN_DEDUP_FROZEN)
    | set(_BATCH_AO_DEDUP_FROZEN)
)
_AP_TAIL = [s for s in _MASTER_DICT_BATCH_AM if s not in _seen_ap_used]
_seen_batch_ap: set[str] = set()
_BATCH_AP_DEDUP: list[str] = []
for s in _AP_TAIL:
    if s in _seen_batch_ap:
        continue
    _seen_batch_ap.add(s)
    _BATCH_AP_DEDUP.append(s)
    if len(_BATCH_AP_DEDUP) >= DICT_LIMIT:
        break
_BATCH_AP_DEDUP_FROZEN = list(_BATCH_AP_DEDUP)

# batch-AQ: continue after batch-AP terminus (central) — next 200 real English words.
_seen_aq_used: set[str] = (
    set(_combined_from_garage[: _ii + 1])
    | set(_BATCH_AH_DEDUP)
    | set(_BATCH_AI_DEDUP_FROZEN)
    | set(_BATCH_AJ_DEDUP_FROZEN)
    | set(_BATCH_AL_DEDUP_FROZEN)
    | set(_BATCH_AM_DEDUP_FROZEN)
    | set(_BATCH_AN_DEDUP_FROZEN)
    | set(_BATCH_AO_DEDUP_FROZEN)
    | set(_BATCH_AP_DEDUP_FROZEN)
)
_AQ_TAIL = [s for s in _MASTER_DICT_BATCH_AM if s not in _seen_aq_used]
_seen_batch_aq: set[str] = set()
_BATCH_AQ_DEDUP: list[str] = []
for s in _AQ_TAIL:
    if s in _seen_batch_aq:
        continue
    _seen_batch_aq.add(s)
    _BATCH_AQ_DEDUP.append(s)
    if len(_BATCH_AQ_DEDUP) >= DICT_LIMIT:
        break
_BATCH_AQ_DEDUP_FROZEN = list(_BATCH_AQ_DEDUP)

# batch-AR: continue after batch-AQ terminus (central) — next 200 real English words.
_seen_ar_used: set[str] = (
    set(_combined_from_garage[: _ii + 1])
    | set(_BATCH_AH_DEDUP)
    | set(_BATCH_AI_DEDUP_FROZEN)
    | set(_BATCH_AJ_DEDUP_FROZEN)
    | set(_BATCH_AL_DEDUP_FROZEN)
    | set(_BATCH_AM_DEDUP_FROZEN)
    | set(_BATCH_AN_DEDUP_FROZEN)
    | set(_BATCH_AO_DEDUP_FROZEN)
    | set(_BATCH_AP_DEDUP_FROZEN)
    | set(_BATCH_AQ_DEDUP_FROZEN)
)
_AR_TAIL = [s for s in _MASTER_DICT_BATCH_AM if s not in _seen_ar_used]
_seen_batch_ar: set[str] = set()
_BATCH_AR_DEDUP: list[str] = []
for s in _AR_TAIL:
    if s in _seen_batch_ar:
        continue
    _seen_batch_ar.add(s)
    _BATCH_AR_DEDUP.append(s)
    if len(_BATCH_AR_DEDUP) >= DICT_LIMIT:
        break
_BATCH_AR_DEDUP_FROZEN = list(_BATCH_AR_DEDUP)

# batch-AS: continue after batch-AR terminus (central) — next 200 real English words.
_seen_as_used: set[str] = (
    set(_combined_from_garage[: _ii + 1])
    | set(_BATCH_AH_DEDUP)
    | set(_BATCH_AI_DEDUP_FROZEN)
    | set(_BATCH_AJ_DEDUP_FROZEN)
    | set(_BATCH_AL_DEDUP_FROZEN)
    | set(_BATCH_AM_DEDUP_FROZEN)
    | set(_BATCH_AN_DEDUP_FROZEN)
    | set(_BATCH_AO_DEDUP_FROZEN)
    | set(_BATCH_AP_DEDUP_FROZEN)
    | set(_BATCH_AQ_DEDUP_FROZEN)
    | set(_BATCH_AR_DEDUP_FROZEN)
)
_AS_TAIL = [s for s in _MASTER_DICT_BATCH_AM if s not in _seen_as_used]
_seen_as_supp: set[str] = set(_seen_as_used) | set(_AS_TAIL)
_AS_SUPPLEMENT = [s for s in _MASTER_DICT_BATCH_AE if s not in _seen_as_supp]
_seen_batch_as: set[str] = set()
_BATCH_AS_DEDUP: list[str] = []
for s in _AS_TAIL + _AS_SUPPLEMENT:
    if s in _seen_batch_as:
        continue
    _seen_batch_as.add(s)
    _BATCH_AS_DEDUP.append(s)
    if len(_BATCH_AS_DEDUP) >= DICT_LIMIT:
        break
_BATCH_AS_DEDUP_FROZEN = list(_BATCH_AS_DEDUP)

# batch-AU: round87 dict200 — early-alphabet vocabulary + /usr/share/dict/words fallback.
_seen_batch_au: set[str] = set()
_BATCH_AU_DEDUP: list[str] = []
for s in _MASTER_DICT_BATCH_AU:
    if s in _seen_batch_au:
        continue
    _seen_batch_au.add(s)
    _BATCH_AU_DEDUP.append(s)
    if len(_BATCH_AU_DEDUP) >= DICT_LIMIT:
        break
if len(_BATCH_AU_DEDUP) < DICT_LIMIT:
    _dict_path = Path("/usr/share/dict/words")
    _seen_au_supp: set[str] = set(_BATCH_AU_DEDUP)
    if _dict_path.is_file():
        for w in _dict_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = w.strip().lower()
            if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_au_supp:
                continue
            _BATCH_AU_DEDUP.append(s)
            _seen_au_supp.add(s)
            if len(_BATCH_AU_DEDUP) >= DICT_LIMIT:
                break
_BATCH_AU_DEDUP_FROZEN = list(_BATCH_AU_DEDUP)

# batch-AW: round89 dict200 — fresh vocabulary after batch-AV exhaustion.
_seen_batch_aw: set[str] = set()
_BATCH_AW_DEDUP: list[str] = []
for s in _MASTER_DICT_BATCH_AW:
    if s in _seen_batch_aw:
        continue
    _seen_batch_aw.add(s)
    _BATCH_AW_DEDUP.append(s)
    if len(_BATCH_AW_DEDUP) >= DICT_LIMIT:
        break
if len(_BATCH_AW_DEDUP) < DICT_LIMIT:
    _dict_path = Path("/usr/share/dict/words")
    _seen_aw_supp: set[str] = set(_BATCH_AW_DEDUP)
    _seen_aw_supp.update(_BATCH_AV_DEDUP_FROZEN)
    if _dict_path.is_file():
        for w in _dict_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = w.strip().lower()
            if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_aw_supp:
                continue
            _BATCH_AW_DEDUP.append(s)
            _seen_aw_supp.add(s)
            if len(_BATCH_AW_DEDUP) >= DICT_LIMIT:
                break
_BATCH_AW_DEDUP_FROZEN = list(_BATCH_AW_DEDUP)
# DICT_GUESSES = _BATCH_AW_DEDUP[:DICT_LIMIT]  # round90: superseded by batch-AX

# batch-AX: round90 dict200 — frozen after batch-AW exhaustion.
_seen_batch_ax: set[str] = set()
_BATCH_AX_DEDUP: list[str] = []
for s in _MASTER_DICT_BATCH_AX:
    if s in _seen_batch_ax:
        continue
    _seen_batch_ax.add(s)
    _BATCH_AX_DEDUP.append(s)
    if len(_BATCH_AX_DEDUP) >= DICT_LIMIT:
        break
if len(_BATCH_AX_DEDUP) < DICT_LIMIT:
    _dict_path = Path("/usr/share/dict/words")
    _seen_ax_supp: set[str] = set(_BATCH_AX_DEDUP)
    _seen_ax_supp.update(_BATCH_AW_DEDUP_FROZEN)
    if _dict_path.is_file():
        for w in _dict_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = w.strip().lower()
            if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_ax_supp:
                continue
            _BATCH_AX_DEDUP.append(s)
            _seen_ax_supp.add(s)
            if len(_BATCH_AX_DEDUP) >= DICT_LIMIT:
                break
_BATCH_AX_DEDUP_FROZEN = list(_BATCH_AX_DEDUP)
# DICT_GUESSES = _BATCH_AX_DEDUP[:DICT_LIMIT]  # round91: superseded by batch-AY

# batch-AY: round91 dict200 — fresh vocabulary after batch-AX exhaustion.
_seen_batch_ay: set[str] = set()
_BATCH_AY_DEDUP: list[str] = []
for s in _MASTER_DICT_BATCH_AY:
    if s in _seen_batch_ay:
        continue
    _seen_batch_ay.add(s)
    _BATCH_AY_DEDUP.append(s)
    if len(_BATCH_AY_DEDUP) >= DICT_LIMIT:
        break
if len(_BATCH_AY_DEDUP) < DICT_LIMIT:
    _dict_path = Path("/usr/share/dict/words")
    _seen_ay_supp: set[str] = set(_BATCH_AY_DEDUP)
    _seen_ay_supp.update(_BATCH_AX_DEDUP_FROZEN)
    if _dict_path.is_file():
        for w in _dict_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = w.strip().lower()
            if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_ay_supp:
                continue
            _BATCH_AY_DEDUP.append(s)
            _seen_ay_supp.add(s)
            if len(_BATCH_AY_DEDUP) >= DICT_LIMIT:
                break
_BATCH_AY_DEDUP_FROZEN = list(_BATCH_AY_DEDUP)
# DICT_GUESSES = _BATCH_AY_DEDUP[:DICT_LIMIT]  # round93: superseded by batch-BA

# batch-AZ: round92 dict200 — frozen for batch-BA chain.
_MASTER_DICT_BATCH_AZ = [
    "inhibition", "inhibitive", "inhibitor", "inhibitory", "inhospitable", "inhospitably", "inhuman", "inhumane", "inhumanely", "inhumanism",
    "inhumanity", "inhumanize", "inhumanly", "inhumanness", "inhumate", "inhumation", "inhume", "inhumer", "inhumorous", "inhumorously",
    "inia", "inial", "inidoneity", "inidoneous", "inigo", "inimicable", "inimical", "inimicality", "inimically", "inimicalness",
    "inimitable", "inimitably", "iniome", "iniomi", "iniomous", "inion", "iniquitable", "iniquitably", "iniquitous", "iniquitously",
    "iniquity", "inirritable", "inirritant", "inirritative", "inissuable", "initialer", "initialist", "initialize", "initiant", "initiary",
    "initiate", "initiation", "initiatively", "initiator", "initiatorily", "initiatory", "initiatress", "initiatrix", "initis", "initive",
    "injectable", "injection", "injector", "injelly", "injudicial", "injudicially", "injudicious", "injun", "injunct", "injunction",
    "injunctive", "injunctively", "injurable", "injure", "injured", "injuredly", "injuredness", "injurer", "injurious", "injuriously",
    "injustice", "ink", "inkberry", "inkbush", "inken", "inker", "inkerman", "inket", "inkfish", "inkholder",
    "inkhorn", "inkhornism", "inkhornist", "inkhornize", "inkhornizer", "inkindle", "inkiness", "inkish", "inkle", "inkless",
    "inklike", "inkling", "inkmaker", "inkmaking", "inknot", "inkosi", "inkpot", "inkra", "inkroot", "inks",
    "inkshed", "inkslinger", "inkslinging", "inkstain", "inkstand", "inkstandish", "inkstone", "inkweed", "inkwell", "inkwood",
    "inkwriter", "inky", "inlagation", "inlaid", "inlaik", "inlake", "inland", "inlander", "inlandish", "inlaut",
    "inlaw", "inlawry", "inlay", "inlayer", "inlaying", "inleague", "inleak", "inleakage", "inlet", "inlier",
    "inlook", "inlooker", "inly", "inlying", "inmeats", "inmixture", "inmost", "inn", "innascible", "innate",
    "innately", "innateness", "innatism", "innative", "innatural", "innaturality", "innaturally", "inneity", "innerly", "innermore",
    "innermost", "innermostly", "innerness", "innervate", "innervation", "innerve", "inness", "innest", "innet", "innholder",
    "inning", "inninmorite", "innisfail", "innkeeper", "innless", "innocence", "innocency", "innocently", "innocentness", "innocuity",
    "innocuous", "innocuously", "innominable", "innominables", "innominata", "innominate", "innominatum", "innovant", "innovate", "innovational",
    "innovative", "innovator", "innovatory", "innoxious", "innoxiously", "innuendo", "innuit", "innumerable", "innumerably", "innumerous",
]
_seen_batch_az: set[str] = set()
_BATCH_AZ_DEDUP: list[str] = []
for s in _MASTER_DICT_BATCH_AZ:
    if s in _seen_batch_az:
        continue
    _seen_batch_az.add(s)
    _BATCH_AZ_DEDUP.append(s)
    if len(_BATCH_AZ_DEDUP) >= DICT_LIMIT:
        break
if len(_BATCH_AZ_DEDUP) < DICT_LIMIT:
    _dict_path = Path("/usr/share/dict/words")
    _seen_az_supp: set[str] = set(_BATCH_AZ_DEDUP)
    _seen_az_supp.update(_BATCH_AY_DEDUP_FROZEN)
    if _dict_path.is_file():
        for w in _dict_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = w.strip().lower()
            if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_az_supp:
                continue
            _BATCH_AZ_DEDUP.append(s)
            _seen_az_supp.add(s)
            if len(_BATCH_AZ_DEDUP) >= DICT_LIMIT:
                break
_BATCH_AZ_DEDUP_FROZEN = list(_BATCH_AZ_DEDUP)
# DICT_GUESSES = _BATCH_AZ_DEDUP[:DICT_LIMIT]  # round93: superseded by batch-BA

# batch-BA: round93 dict200 — fresh vocabulary after batch-AZ exhaustion.
_MASTER_DICT_BATCH_BA = [
    "innutrient", "innutrition", "innutritious", "innutritive", "innyard", "ino", "inobedience", "inobedient", "inobediently", "inoblast",
    "inobnoxious", "inobscurable", "inobservable", "inobservance", "inobservancy", "inobservant", "inobtainable", "inobtrusive", "inobvious", "inocarpus",
    "inoccupation", "inoceramus", "inochondroma", "inoculable", "inoculant", "inocular", "inoculate", "inoculation", "inoculative", "inoculator",
    "inoculum", "inocystoma", "inocyte", "inodes", "inodorous", "inodorously", "inoffending", "inoffensive", "inofficial", "inofficially",
    "inofficious", "inogen", "inogenesis", "inogenic", "inogenous", "inoglia", "inohymenitic", "inolith", "inoma", "inominous",
    "inomyoma", "inomyositis", "inomyxoma", "inone", "inoneuroma", "inoperable", "inoperative", "inopercular", "inoperculata", "inoperculate",
    "inopinable", "inopinate", "inopinately", "inopine", "inopportune", "inoppressive", "inoppugnable", "inopulent", "inorb", "inorderly",
    "inordinacy", "inordinary", "inordinate", "inordinately", "inorganic", "inorganical", "inorganized", "inoriginate", "inornate", "inosclerosis",
    "inoscopy", "inosculate", "inosculation", "inosic", "inosin", "inosinic", "inosite", "inositol", "inostensible", "inostensibly",
    "inotropic", "inower", "inoxidable", "inoxidizable", "inoxidize", "inparabola", "inpardonable", "inpatient", "inpayment", "inpensioner",
    "inphase", "inpolygon", "inpolyhedron", "inport", "inpour", "inpush", "input", "inquaintance", "inquartation", "inquest",
    "inquestual", "inquiet", "inquietation", "inquietly", "inquietness", "inquietude", "inquilinae", "inquiline", "inquilinism", "inquilinity",
    "inquilinous", "inquinate", "inquination", "inquirable", "inquirant", "inquiration", "inquire", "inquirendo", "inquirent", "inquirer",
    "inquiring", "inquiringly", "inquiry", "inquisite", "inquisition", "inquisitive", "inquisitor", "inquisitory", "inquisitress", "inquisitrix",
    "inradius", "inreality", "inrigged", "inrigger", "inrighted", "inring", "inro", "inroad", "inroader", "inroll",
    "inrooted", "inrub", "inrun", "inrunning", "inruption", "inrush", "insack", "insagacity", "insalivate", "insalivation",
    "insalubrious", "insalubrity", "insalutary", "insalvable", "insane", "insanely", "insaneness", "insanify", "insanitary", "insanitation",
    "insanity", "insapiency", "insapient", "insatiable", "insatiably", "insatiate", "insatiated", "insatiately", "insatiety",
    "insaturable", "inscenation", "inscibile", "inscience", "inscient", "inscribable", "inscribe", "inscriber", "inscript", "inscriptible",
    "inscription", "inscriptive", "inscriptured", "inscroll", "inscrutable", "inscrutables", "inscrutably", "insculp", "insculpture", "insea",
    "inseam",
]
_seen_batch_ba: set[str] = set()
_BATCH_BA_DEDUP: list[str] = []
for s in _MASTER_DICT_BATCH_BA:
    if s in _seen_batch_ba:
        continue
    _seen_batch_ba.add(s)
    _BATCH_BA_DEDUP.append(s)
    if len(_BATCH_BA_DEDUP) >= DICT_LIMIT:
        break
if len(_BATCH_BA_DEDUP) < DICT_LIMIT:
    _dict_path = Path("/usr/share/dict/words")
    _seen_ba_supp: set[str] = set(_BATCH_BA_DEDUP)
    _seen_ba_supp.update(_BATCH_AZ_DEDUP_FROZEN)
    if _dict_path.is_file():
        for w in _dict_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = w.strip().lower()
            if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_ba_supp:
                continue
            _BATCH_BA_DEDUP.append(s)
            _seen_ba_supp.add(s)
            if len(_BATCH_BA_DEDUP) >= DICT_LIMIT:
                break
_BATCH_BA_DEDUP_FROZEN = list(_BATCH_BA_DEDUP)
# DICT_GUESSES = _BATCH_BA_DEDUP[:DICT_LIMIT]  # round94: superseded by batch-BB

# batch-BB: round94 dict200 — fresh vocabulary after batch-BA exhaustion.
_MASTER_DICT_BATCH_BB = [
    "aal", "aalii", "aam", "aani", "aardvark", "aardwolf", "aaron", "aaronic", "aaronical", "aaronite",
    "aaronitic", "aaru", "aba", "ababdeh", "ababua", "abac", "abaca", "abacate", "abacay", "abacinate",
    "abacination", "abaciscus", "abacist", "aback", "abactinal", "abactinally", "abaction", "abactor", "abaculus", "abacus",
    "abadite", "abaff", "abaft", "abaisance", "abaiser", "abaissed", "abalienate", "abalienation", "abalone", "abama",
    "abampere", "abandon", "abandonable", "abandoned", "abandonedly", "abandonee", "abandoner", "abandonment", "abanic", "abantes",
    "abaptiston", "abarambo", "abaris", "abarthrosis", "abarticular", "abas", "abase", "abased", "abasedly", "abasedness",
    "abasement", "abaser", "abasgi", "abash", "abashed", "abashedly", "abashedness", "abashless", "abashlessly", "abashment",
    "abasia", "abasic", "abask", "abassin", "abastardize", "abatable", "abate", "abatement", "abater", "abatis",
    "abatised", "abaton", "abator", "abattoir", "abatua", "abature", "abave", "abaxial", "abaxile", "abaze",
    "abb", "abba", "abbacomes", "abbacy", "abbadide", "abbas", "abbasi", "abbassi", "abbasside", "abbatial",
    "abbatical", "abbess", "abbey", "abbeystede", "abbie", "abbot", "abbotcy", "abbotnullius", "abbotship", "abbreviate",
    "abbreviately", "abbreviation", "abbreviator", "abbreviatory", "abbreviature", "abby", "abcoulomb", "abdal", "abdat", "abderian",
    "abderite", "abdest", "abdicable", "abdicant", "abdicate", "abdication", "abdicative", "abdicator", "abdiel", "abditive",
    "abditory", "abdomen", "abdominal", "abdominales", "abdominalian", "abdominally", "abdominous", "abduce", "abducens", "abducent",
    "abduct", "abduction", "abductor", "abe", "abeam", "abear", "abearance", "abecedarian", "abecedarium", "abecedary",
    "abed", "abeigh", "abel", "abele", "abelia", "abelian", "abelicea", "abelite", "abelmoschus", "abelmosk",
    "abelonian", "abeltree", "abencerrages", "abenteric", "abepithymia", "aberdeen", "aberdevine", "aberdonian", "aberia", "aberrance",
    "aberrancy", "aberrant", "aberrate", "aberration", "aberrational", "aberrator", "aberrometer", "aberroscope", "aberuncator", "abet",
    "abetment", "abettal", "abettor", "abevacuation", "abey", "abeyance", "abeyancy", "abeyant", "abfarad", "abhenry",
    "abhiseka", "abhominable", "abhor", "abhorrence", "abhorrency", "abhorrent", "abhorrently", "abhorrer", "abhorrible", "abhorring",
]
_seen_batch_bb: set[str] = set()
_BATCH_BB_DEDUP: list[str] = []
for s in _MASTER_DICT_BATCH_BB:
    if s in _seen_batch_bb:
        continue
    _seen_batch_bb.add(s)
    _BATCH_BB_DEDUP.append(s)
    if len(_BATCH_BB_DEDUP) >= DICT_LIMIT:
        break
if len(_BATCH_BB_DEDUP) < DICT_LIMIT:
    _dict_path = Path("/usr/share/dict/words")
    _seen_bb_supp: set[str] = set(_BATCH_BB_DEDUP)
    _seen_bb_supp.update(_BATCH_BA_DEDUP_FROZEN)
    if _dict_path.is_file():
        for w in _dict_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = w.strip().lower()
            if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_bb_supp:
                continue
            _BATCH_BB_DEDUP.append(s)
            _seen_bb_supp.add(s)
            if len(_BATCH_BB_DEDUP) >= DICT_LIMIT:
                break
_BATCH_BB_DEDUP_FROZEN = list(_BATCH_BB_DEDUP)
# DICT_GUESSES = _BATCH_BB_DEDUP[:DICT_LIMIT]  # round95: superseded by batch-BC

# batch-BC: round95 dict200 — fresh vocabulary after batch-BB exhaustion.
_BATCH_BC_DEDUP: list[str] = []
_dict_path_bc = Path("/usr/share/dict/words")
_seen_bc_supp: set[str] = set(_BATCH_BB_DEDUP_FROZEN)
_seen_bc_supp.update(_BATCH_BA_DEDUP_FROZEN)
if _dict_path_bc.is_file():
    for w in _dict_path_bc.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = w.strip().lower()
        if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_bc_supp:
            continue
        _BATCH_BC_DEDUP.append(s)
        _seen_bc_supp.add(s)
        if len(_BATCH_BC_DEDUP) >= DICT_LIMIT:
            break
_BATCH_BC_DEDUP_FROZEN = list(_BATCH_BC_DEDUP)

# batch-BD: round96 dict200 — fresh vocabulary after batch-BC exhaustion.
_BATCH_BD_DEDUP: list[str] = []
_dict_path_bd = Path("/usr/share/dict/words")
_seen_bd_supp: set[str] = set(_BATCH_BC_DEDUP_FROZEN)
_seen_bd_supp.update(_BATCH_BB_DEDUP_FROZEN)
_seen_bd_supp.update(_BATCH_BA_DEDUP_FROZEN)
if _dict_path_bd.is_file():
    for w in _dict_path_bd.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = w.strip().lower()
        if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_bd_supp:
            continue
        _BATCH_BD_DEDUP.append(s)
        _seen_bd_supp.add(s)
        if len(_BATCH_BD_DEDUP) >= DICT_LIMIT:
            break
_BATCH_BD_DEDUP_FROZEN = list(_BATCH_BD_DEDUP)

# batch-BE: round97 dict200 — fresh vocabulary after batch-BD exhaustion.
_BATCH_BE_DEDUP: list[str] = []
_dict_path_be = Path("/usr/share/dict/words")
_seen_be_supp: set[str] = set(_BATCH_BD_DEDUP_FROZEN)
_seen_be_supp.update(_BATCH_BC_DEDUP_FROZEN)
_seen_be_supp.update(_BATCH_BB_DEDUP_FROZEN)
_seen_be_supp.update(_BATCH_BA_DEDUP_FROZEN)
if _dict_path_be.is_file():
    for w in _dict_path_be.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = w.strip().lower()
        if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_be_supp:
            continue
        _BATCH_BE_DEDUP.append(s)
        _seen_be_supp.add(s)
        if len(_BATCH_BE_DEDUP) >= DICT_LIMIT:
            break
_BATCH_BE_DEDUP_FROZEN = list(_BATCH_BE_DEDUP)

# batch-BF: round98 dict200 — fresh vocabulary after batch-BE exhaustion.
_BATCH_BF_DEDUP: list[str] = []
_dict_path_bf = Path("/usr/share/dict/words")
_seen_bf_supp: set[str] = set(_BATCH_BE_DEDUP_FROZEN)
_seen_bf_supp.update(_BATCH_BD_DEDUP_FROZEN)
_seen_bf_supp.update(_BATCH_BC_DEDUP_FROZEN)
_seen_bf_supp.update(_BATCH_BB_DEDUP_FROZEN)
_seen_bf_supp.update(_BATCH_BA_DEDUP_FROZEN)
if _dict_path_bf.is_file():
    for w in _dict_path_bf.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = w.strip().lower()
        if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_bf_supp:
            continue
        _BATCH_BF_DEDUP.append(s)
        _seen_bf_supp.add(s)
        if len(_BATCH_BF_DEDUP) >= DICT_LIMIT:
            break
_BATCH_BF_DEDUP_FROZEN = list(_BATCH_BF_DEDUP)

# batch-BG: round99 dict200 — frozen vocabulary (excluded from batch-BH).
_BATCH_BG_DEDUP: list[str] = []
_dict_path_bg99 = Path("/usr/share/dict/words")
_seen_bg99_supp: set[str] = set(_BATCH_BF_DEDUP_FROZEN)
_seen_bg99_supp.update(_BATCH_BE_DEDUP_FROZEN)
_seen_bg99_supp.update(_BATCH_BD_DEDUP_FROZEN)
_seen_bg99_supp.update(_BATCH_BC_DEDUP_FROZEN)
_seen_bg99_supp.update(_BATCH_BB_DEDUP_FROZEN)
_seen_bg99_supp.update(_BATCH_BA_DEDUP_FROZEN)
if _dict_path_bg99.is_file():
    for w in _dict_path_bg99.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = w.strip().lower()
        if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_bg99_supp:
            continue
        _BATCH_BG_DEDUP.append(s)
        _seen_bg99_supp.add(s)
        if len(_BATCH_BG_DEDUP) >= DICT_LIMIT:
            break
_BATCH_BG_DEDUP_FROZEN = list(_BATCH_BG_DEDUP)

# batch-BH: round100 dict200 — fresh vocabulary after batch-BG exhaustion.
_BATCH_BH_DEDUP: list[str] = []
_dict_path_bh = Path("/usr/share/dict/words")
_seen_bh_supp: set[str] = set(_BATCH_BG_DEDUP_FROZEN)
_seen_bh_supp.update(_BATCH_BF_DEDUP_FROZEN)
_seen_bh_supp.update(_BATCH_BE_DEDUP_FROZEN)
_seen_bh_supp.update(_BATCH_BD_DEDUP_FROZEN)
_seen_bh_supp.update(_BATCH_BC_DEDUP_FROZEN)
_seen_bh_supp.update(_BATCH_BB_DEDUP_FROZEN)
_seen_bh_supp.update(_BATCH_BA_DEDUP_FROZEN)
if _dict_path_bh.is_file():
    for w in _dict_path_bh.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = w.strip().lower()
        if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_bh_supp:
            continue
        _BATCH_BH_DEDUP.append(s)
        _seen_bh_supp.add(s)
        if len(_BATCH_BH_DEDUP) >= DICT_LIMIT:
            break
_BATCH_BH_DEDUP_FROZEN = list(_BATCH_BH_DEDUP)

# batch-BI: round101 dict200 — fresh vocabulary after batch-BH exhaustion.
_BATCH_BI_DEDUP: list[str] = []
_dict_path_bi = Path("/usr/share/dict/words")
_seen_bi_supp: set[str] = set(_BATCH_BH_DEDUP_FROZEN)
_seen_bi_supp.update(_BATCH_BG_DEDUP_FROZEN)
_seen_bi_supp.update(_BATCH_BF_DEDUP_FROZEN)
_seen_bi_supp.update(_BATCH_BE_DEDUP_FROZEN)
_seen_bi_supp.update(_BATCH_BD_DEDUP_FROZEN)
_seen_bi_supp.update(_BATCH_BC_DEDUP_FROZEN)
_seen_bi_supp.update(_BATCH_BB_DEDUP_FROZEN)
_seen_bi_supp.update(_BATCH_BA_DEDUP_FROZEN)
if _dict_path_bi.is_file():
    for w in _dict_path_bi.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = w.strip().lower()
        if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_bi_supp:
            continue
        _BATCH_BI_DEDUP.append(s)
        _seen_bi_supp.add(s)
        if len(_BATCH_BI_DEDUP) >= DICT_LIMIT:
            break
_BATCH_BI_DEDUP_FROZEN = list(_BATCH_BI_DEDUP)

# batch-BJ: round102 dict200 — fresh vocabulary after batch-BI exhaustion.
_BATCH_BJ_DEDUP: list[str] = []
_dict_path_bj = Path("/usr/share/dict/words")
_seen_bj_supp: set[str] = set(_BATCH_BI_DEDUP_FROZEN)
_seen_bj_supp.update(_BATCH_BH_DEDUP_FROZEN)
_seen_bj_supp.update(_BATCH_BG_DEDUP_FROZEN)
_seen_bj_supp.update(_BATCH_BF_DEDUP_FROZEN)
_seen_bj_supp.update(_BATCH_BE_DEDUP_FROZEN)
_seen_bj_supp.update(_BATCH_BD_DEDUP_FROZEN)
_seen_bj_supp.update(_BATCH_BC_DEDUP_FROZEN)
_seen_bj_supp.update(_BATCH_BB_DEDUP_FROZEN)
_seen_bj_supp.update(_BATCH_BA_DEDUP_FROZEN)
if _dict_path_bj.is_file():
    for w in _dict_path_bj.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = w.strip().lower()
        if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_bj_supp:
            continue
        _BATCH_BJ_DEDUP.append(s)
        _seen_bj_supp.add(s)
        if len(_BATCH_BJ_DEDUP) >= DICT_LIMIT:
            break
_BATCH_BJ_DEDUP_FROZEN = list(_BATCH_BJ_DEDUP)

# batch-BK: round103 dict200 — fresh vocabulary after batch-BJ exhaustion.
_BATCH_BK_DEDUP: list[str] = []
_dict_path_bk = Path("/usr/share/dict/words")
_seen_bk_supp: set[str] = set(_BATCH_BJ_DEDUP_FROZEN)
_seen_bk_supp.update(_BATCH_BI_DEDUP_FROZEN)
_seen_bk_supp.update(_BATCH_BH_DEDUP_FROZEN)
_seen_bk_supp.update(_BATCH_BG_DEDUP_FROZEN)
_seen_bk_supp.update(_BATCH_BF_DEDUP_FROZEN)
_seen_bk_supp.update(_BATCH_BE_DEDUP_FROZEN)
_seen_bk_supp.update(_BATCH_BD_DEDUP_FROZEN)
_seen_bk_supp.update(_BATCH_BC_DEDUP_FROZEN)
_seen_bk_supp.update(_BATCH_BB_DEDUP_FROZEN)
_seen_bk_supp.update(_BATCH_BA_DEDUP_FROZEN)
if _dict_path_bk.is_file():
    for w in _dict_path_bk.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = w.strip().lower()
        if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_bk_supp:
            continue
        _BATCH_BK_DEDUP.append(s)
        _seen_bk_supp.add(s)
        if len(_BATCH_BK_DEDUP) >= DICT_LIMIT:
            break
_BATCH_BK_DEDUP_FROZEN = list(_BATCH_BK_DEDUP)

# batch-BL: round104 dict200 — fresh vocabulary after batch-BK exhaustion.
_BATCH_BL_DEDUP: list[str] = []
_dict_path_bl = Path("/usr/share/dict/words")
_seen_bl_supp: set[str] = set(_BATCH_BK_DEDUP_FROZEN)
_seen_bl_supp.update(_BATCH_BJ_DEDUP_FROZEN)
_seen_bl_supp.update(_BATCH_BI_DEDUP_FROZEN)
_seen_bl_supp.update(_BATCH_BH_DEDUP_FROZEN)
_seen_bl_supp.update(_BATCH_BG_DEDUP_FROZEN)
_seen_bl_supp.update(_BATCH_BF_DEDUP_FROZEN)
_seen_bl_supp.update(_BATCH_BE_DEDUP_FROZEN)
_seen_bl_supp.update(_BATCH_BD_DEDUP_FROZEN)
_seen_bl_supp.update(_BATCH_BC_DEDUP_FROZEN)
_seen_bl_supp.update(_BATCH_BB_DEDUP_FROZEN)
_seen_bl_supp.update(_BATCH_BA_DEDUP_FROZEN)
if _dict_path_bl.is_file():
    for w in _dict_path_bl.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = w.strip().lower()
        if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_bl_supp:
            continue
        _BATCH_BL_DEDUP.append(s)
        _seen_bl_supp.add(s)
        if len(_BATCH_BL_DEDUP) >= DICT_LIMIT:
            break
_BATCH_BL_DEDUP_FROZEN = list(_BATCH_BL_DEDUP)

# batch-BM: round105 dict200 — fresh vocabulary after batch-BL exhaustion.
_BATCH_BM_DEDUP: list[str] = []
_dict_path_bm = Path("/usr/share/dict/words")
_seen_bm_supp: set[str] = set(_BATCH_BL_DEDUP_FROZEN)
_seen_bm_supp.update(_BATCH_BK_DEDUP_FROZEN)
_seen_bm_supp.update(_BATCH_BJ_DEDUP_FROZEN)
_seen_bm_supp.update(_BATCH_BI_DEDUP_FROZEN)
_seen_bm_supp.update(_BATCH_BH_DEDUP_FROZEN)
_seen_bm_supp.update(_BATCH_BG_DEDUP_FROZEN)
_seen_bm_supp.update(_BATCH_BF_DEDUP_FROZEN)
_seen_bm_supp.update(_BATCH_BE_DEDUP_FROZEN)
_seen_bm_supp.update(_BATCH_BD_DEDUP_FROZEN)
_seen_bm_supp.update(_BATCH_BC_DEDUP_FROZEN)
_seen_bm_supp.update(_BATCH_BB_DEDUP_FROZEN)
_seen_bm_supp.update(_BATCH_BA_DEDUP_FROZEN)
if _dict_path_bm.is_file():
    for w in _dict_path_bm.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = w.strip().lower()
        if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_bm_supp:
            continue
        _BATCH_BM_DEDUP.append(s)
        _seen_bm_supp.add(s)
        if len(_BATCH_BM_DEDUP) >= DICT_LIMIT:
            break
_BATCH_BM_DEDUP_FROZEN = list(_BATCH_BM_DEDUP)

# batch-BN: round106 dict200 — fresh vocabulary after batch-BM exhaustion.
_BATCH_BN_DEDUP: list[str] = []
_dict_path_bn = Path("/usr/share/dict/words")
_seen_bn_supp: set[str] = set(_BATCH_BM_DEDUP_FROZEN)
_seen_bn_supp.update(_BATCH_BL_DEDUP_FROZEN)
_seen_bn_supp.update(_BATCH_BK_DEDUP_FROZEN)
_seen_bn_supp.update(_BATCH_BJ_DEDUP_FROZEN)
_seen_bn_supp.update(_BATCH_BI_DEDUP_FROZEN)
_seen_bn_supp.update(_BATCH_BH_DEDUP_FROZEN)
_seen_bn_supp.update(_BATCH_BG_DEDUP_FROZEN)
_seen_bn_supp.update(_BATCH_BF_DEDUP_FROZEN)
_seen_bn_supp.update(_BATCH_BE_DEDUP_FROZEN)
_seen_bn_supp.update(_BATCH_BD_DEDUP_FROZEN)
_seen_bn_supp.update(_BATCH_BC_DEDUP_FROZEN)
_seen_bn_supp.update(_BATCH_BB_DEDUP_FROZEN)
_seen_bn_supp.update(_BATCH_BA_DEDUP_FROZEN)
if _dict_path_bn.is_file():
    for w in _dict_path_bn.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = w.strip().lower()
        if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_bn_supp:
            continue
        _BATCH_BN_DEDUP.append(s)
        _seen_bn_supp.add(s)
        if len(_BATCH_BN_DEDUP) >= DICT_LIMIT:
            break
_BATCH_BN_DEDUP_FROZEN = list(_BATCH_BN_DEDUP)

# batch-BO: round107 dict200 — fresh vocabulary after batch-BN exhaustion.
_BATCH_BO_DEDUP: list[str] = []
_dict_path_bo = Path("/usr/share/dict/words")
_seen_bo_supp: set[str] = set(_BATCH_BN_DEDUP_FROZEN)
_seen_bo_supp.update(_BATCH_BM_DEDUP_FROZEN)
_seen_bo_supp.update(_BATCH_BL_DEDUP_FROZEN)
_seen_bo_supp.update(_BATCH_BK_DEDUP_FROZEN)
_seen_bo_supp.update(_BATCH_BJ_DEDUP_FROZEN)
_seen_bo_supp.update(_BATCH_BI_DEDUP_FROZEN)
_seen_bo_supp.update(_BATCH_BH_DEDUP_FROZEN)
_seen_bo_supp.update(_BATCH_BG_DEDUP_FROZEN)
_seen_bo_supp.update(_BATCH_BF_DEDUP_FROZEN)
_seen_bo_supp.update(_BATCH_BE_DEDUP_FROZEN)
_seen_bo_supp.update(_BATCH_BD_DEDUP_FROZEN)
_seen_bo_supp.update(_BATCH_BC_DEDUP_FROZEN)
_seen_bo_supp.update(_BATCH_BB_DEDUP_FROZEN)
_seen_bo_supp.update(_BATCH_BA_DEDUP_FROZEN)
if _dict_path_bo.is_file():
    for w in _dict_path_bo.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = w.strip().lower()
        if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_bo_supp:
            continue
        _BATCH_BO_DEDUP.append(s)
        _seen_bo_supp.add(s)
        if len(_BATCH_BO_DEDUP) >= DICT_LIMIT:
            break
_BATCH_BO_DEDUP_FROZEN = list(_BATCH_BO_DEDUP)

# batch-BP: round108 dict200 — fresh vocabulary after batch-BO exhaustion.
_BATCH_BP_DEDUP: list[str] = []
_dict_path_bp = Path("/usr/share/dict/words")
_seen_bp_supp: set[str] = set(_BATCH_BO_DEDUP_FROZEN)
_seen_bp_supp.update(_BATCH_BN_DEDUP_FROZEN)
_seen_bp_supp.update(_BATCH_BM_DEDUP_FROZEN)
_seen_bp_supp.update(_BATCH_BL_DEDUP_FROZEN)
_seen_bp_supp.update(_BATCH_BK_DEDUP_FROZEN)
_seen_bp_supp.update(_BATCH_BJ_DEDUP_FROZEN)
_seen_bp_supp.update(_BATCH_BI_DEDUP_FROZEN)
_seen_bp_supp.update(_BATCH_BH_DEDUP_FROZEN)
_seen_bp_supp.update(_BATCH_BG_DEDUP_FROZEN)
_seen_bp_supp.update(_BATCH_BF_DEDUP_FROZEN)
_seen_bp_supp.update(_BATCH_BE_DEDUP_FROZEN)
_seen_bp_supp.update(_BATCH_BD_DEDUP_FROZEN)
_seen_bp_supp.update(_BATCH_BC_DEDUP_FROZEN)
_seen_bp_supp.update(_BATCH_BB_DEDUP_FROZEN)
_seen_bp_supp.update(_BATCH_BA_DEDUP_FROZEN)
if _dict_path_bp.is_file():
    for w in _dict_path_bp.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = w.strip().lower()
        if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_bp_supp:
            continue
        _BATCH_BP_DEDUP.append(s)
        _seen_bp_supp.add(s)
        if len(_BATCH_BP_DEDUP) >= DICT_LIMIT:
            break
_BATCH_BP_DEDUP_FROZEN = list(_BATCH_BP_DEDUP)

# batch-BQ: round109 dict200 — fresh vocabulary after batch-BP exhaustion.
_BATCH_BQ_DEDUP: list[str] = []
_dict_path_bq = Path("/usr/share/dict/words")
_seen_bq_supp: set[str] = set(_BATCH_BP_DEDUP_FROZEN)
_seen_bq_supp.update(_BATCH_BN_DEDUP_FROZEN)
_seen_bq_supp.update(_BATCH_BM_DEDUP_FROZEN)
_seen_bq_supp.update(_BATCH_BL_DEDUP_FROZEN)
_seen_bq_supp.update(_BATCH_BK_DEDUP_FROZEN)
_seen_bq_supp.update(_BATCH_BJ_DEDUP_FROZEN)
_seen_bq_supp.update(_BATCH_BI_DEDUP_FROZEN)
_seen_bq_supp.update(_BATCH_BH_DEDUP_FROZEN)
_seen_bq_supp.update(_BATCH_BG_DEDUP_FROZEN)
_seen_bq_supp.update(_BATCH_BF_DEDUP_FROZEN)
_seen_bq_supp.update(_BATCH_BE_DEDUP_FROZEN)
_seen_bq_supp.update(_BATCH_BD_DEDUP_FROZEN)
_seen_bq_supp.update(_BATCH_BC_DEDUP_FROZEN)
_seen_bq_supp.update(_BATCH_BB_DEDUP_FROZEN)
_seen_bq_supp.update(_BATCH_BA_DEDUP_FROZEN)
if _dict_path_bq.is_file():
    for w in _dict_path_bq.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = w.strip().lower()
        if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_bq_supp:
            continue
        _BATCH_BQ_DEDUP.append(s)
        _seen_bq_supp.add(s)
        if len(_BATCH_BQ_DEDUP) >= DICT_LIMIT:
            break
_BATCH_BQ_DEDUP_FROZEN = list(_BATCH_BQ_DEDUP)

# batch-BR: round110 dict200 — fresh vocabulary after batch-BQ exhaustion.
_BATCH_BR_DEDUP: list[str] = []
_dict_path_br = Path("/usr/share/dict/words")
_seen_br_supp: set[str] = set(_BATCH_BQ_DEDUP_FROZEN)
_seen_br_supp.update(_BATCH_BP_DEDUP_FROZEN)
_seen_br_supp.update(_BATCH_BN_DEDUP_FROZEN)
_seen_br_supp.update(_BATCH_BM_DEDUP_FROZEN)
_seen_br_supp.update(_BATCH_BL_DEDUP_FROZEN)
_seen_br_supp.update(_BATCH_BK_DEDUP_FROZEN)
_seen_br_supp.update(_BATCH_BJ_DEDUP_FROZEN)
_seen_br_supp.update(_BATCH_BI_DEDUP_FROZEN)
_seen_br_supp.update(_BATCH_BH_DEDUP_FROZEN)
_seen_br_supp.update(_BATCH_BG_DEDUP_FROZEN)
_seen_br_supp.update(_BATCH_BF_DEDUP_FROZEN)
_seen_br_supp.update(_BATCH_BE_DEDUP_FROZEN)
_seen_br_supp.update(_BATCH_BD_DEDUP_FROZEN)
_seen_br_supp.update(_BATCH_BC_DEDUP_FROZEN)
_seen_br_supp.update(_BATCH_BB_DEDUP_FROZEN)
_seen_br_supp.update(_BATCH_BA_DEDUP_FROZEN)
if _dict_path_br.is_file():
    for w in _dict_path_br.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = w.strip().lower()
        if not s.isalpha() or len(s) < 3 or len(s) > 12 or s in _seen_br_supp:
            continue
        _BATCH_BR_DEDUP.append(s)
        _seen_br_supp.add(s)
        if len(_BATCH_BR_DEDUP) >= DICT_LIMIT:
            break
_BATCH_BR_DEDUP_FROZEN = list(_BATCH_BR_DEDUP)


DICT_GUESSES = _BATCH_BR_DEDUP[:DICT_LIMIT]
if len(DICT_GUESSES) < DICT_LIMIT:
    raise RuntimeError(f"batch-BR requires {DICT_LIMIT} real dict words; got {len(DICT_GUESSES)}")


GH_GLOBAL_QUERIES = [
    "ashbyhq.com extension:rb",
    "ashbyhq.com extension:php",
    "ashbyhq.com extension:java",
    "ashbyhq.com extension:kt",
    "ashbyhq.com extension:scala",
    "ashbyhq.com extension:cs",
    "ashbyhq.com extension:cpp",
    "ashbyhq.com extension:c",
    "ashbyhq.com extension:dockerfile",
    "ashbyhq.com extension:gradle",
    "ashbyhq.com extension:ipynb",
    "ashbyhq.com founder",
    "ashbyhq.com fullstack",
    "ashbyhq.com full-stack",
    "ashbyhq.com senior",
    "ashbyhq.com staff",
    "ashbyhq.com principal",
    "jobs.ashbyhq.com bay-area",
    "jobs.ashbyhq.com seattle",
    "jobs.ashbyhq.com boston",
    "ashbyhq.com org:health",
    "ashbyhq.com org:robot",
    "ashbyhq.com org:defense",
    "ashbyhq.com now-hiring",
    "ashbyhq.com open-positions",
    # round65+ beyond backend_platform global rotation
    "ashbyhq.com extension:tsx",
    "ashbyhq.com extension:swift",
    "jobs.ashbyhq.com remote",
    "jobs.ashbyhq.com nyc",
    "devops ashbyhq.com in:file",
    "frontend engineer ashbyhq.com in:file",
    "security engineer ashbyhq.com in:file",
    "ashbyhq.com org:fintech",
    "ashbyhq.com org:climate",
    "ashbyhq.com hiring extension:md",
    # round65+ rotate@65 extras
    "ashbyhq.com org:biotech",
    "ashbyhq.com org:edtech",
    "jobs.ashbyhq.com london",
    "jobs.ashbyhq.com austin",
    # round66+ rotate@66 extras
    "ashbyhq.com org:nonprofit",
    "ashbyhq.com org:saas",
    "jobs.ashbyhq.com chicago",
    "jobs.ashbyhq.com denver",
]


# round67+ rotate@67 slice (first mine-zero fallback for round68)
GH_ROTATE_67_QUERIES = [
    "ashbyhq.com org:fintech",
    "ashbyhq.com org:climate",
    "ashbyhq.com org:robotics",
    "ashbyhq.com agent in:file",
    "ashbyhq.com LLM in:file",
    "ashbyhq.com org:ai",
    "jobs.ashbyhq.com fintech",
    "jobs.ashbyhq.com climate",
    "robotics ashbyhq.com in:file",
    "llm engineer ashbyhq.com in:file",
    "agent engineer ashbyhq.com in:file",
    "ML platform jobs.ashbyhq.com extension:py",
]

# round68+ rotate@68 fresh slice (NOT r67)
GH_ROTATE_68_QUERIES = [
    "ashbyhq.com org:crypto",
    "ashbyhq.com org:gaming",
    "ashbyhq.com org:security",
    "ashbyhq.com inference in:file",
    "ashbyhq.com GPU in:file",
    "ashbyhq.com org:enterprise",
    "jobs.ashbyhq.com miami",
    "jobs.ashbyhq.com dallas",
    "blockchain ashbyhq.com in:file",
    "inference engineer ashbyhq.com in:file",
    "GPU engineer ashbyhq.com in:file",
    "kernel engineer ashbyhq.com extension:c",
]

# round69+ rotate@69 fresh slice (NOT r68)
GH_ROTATE_69_QUERIES = [
    "ashbyhq.com org:healthtech",
    "ashbyhq.com org:logistics",
    "ashbyhq.com org:legal",
    "ashbyhq.com distributed in:file",
    "ashbyhq.com realtime in:file",
    "ashbyhq.com embedded in:file",
    "jobs.ashbyhq.com portland",
    "jobs.ashbyhq.com atlanta",
    "compiler engineer ashbyhq.com in:file",
    "distributed systems ashbyhq.com in:file",
    "realtime engineer ashbyhq.com in:file",
    "firmware engineer ashbyhq.com extension:c",
]

# round70+ rotate@70 fresh slice (NOT r69)
GH_ROTATE_70_QUERIES = [
    "ashbyhq.com org:proptech",
    "ashbyhq.com org:insurtech",
    "ashbyhq.com org:martech",
    "ashbyhq.com observability in:file",
    "ashbyhq.com streaming in:file",
    "ashbyhq.com warehouse in:file",
    "jobs.ashbyhq.com phoenix",
    "jobs.ashbyhq.com minneapolis",
    "database engineer ashbyhq.com in:file",
    "streaming engineer ashbyhq.com in:file",
    "observability engineer ashbyhq.com in:file",
    "rust engineer ashbyhq.com extension:rs",
]

# round72+ rotate@71 fresh slice (NOT r70)
GH_ROTATE_71_QUERIES = [
    "ashbyhq.com org:edutech",
    "ashbyhq.com org:govtech",
    "ashbyhq.com org:cleantech",
    "ashbyhq.com search in:file",
    "ashbyhq.com indexing in:file",
    "ashbyhq.com analytics in:file",
    "jobs.ashbyhq.com houston",
    "jobs.ashbyhq.com san-diego",
    "network engineer ashbyhq.com in:file",
    "data platform ashbyhq.com in:file",
    "search engineer ashbyhq.com in:file",
    "terraform ashbyhq.com in:file",
]



# round73 rotate@73 (agtech window — NOT used for r74)
GH_ROTATE_73_QUERIES = [
    "ashbyhq.com org:agtech",
    "ashbyhq.com org:retailtech",
    "ashbyhq.com org:autotech",
    "ashbyhq.com redis in:file",
    "ashbyhq.com elasticsearch in:file",
    "ashbyhq.com mongodb in:file",
    "jobs.ashbyhq.com berlin",
    "jobs.ashbyhq.com sydney",
    "typescript ashbyhq.com in:file",
    "react engineer ashbyhq.com in:file",
    "verilog ashbyhq.com in:file",
    "firmware engineer ashbyhq.com in:file",
]

# round74+ rotate@74 — R65 biotech/edtech + R70 fintech/robotics (NOT r73 agtech)
GH_ROTATE_74_QUERIES = [
    "ashbyhq.com org:biotech",
    "ashbyhq.com org:edtech",
    "jobs.ashbyhq.com london",
    "jobs.ashbyhq.com austin",
    "ashbyhq.com org:fintech",
    "ashbyhq.com org:robotics",
    "jobs.ashbyhq.com fintech",
    "robotics ashbyhq.com in:file",
    "fintech engineer ashbyhq.com in:file",
    "biotech engineer ashbyhq.com in:file",
    "edtech engineer ashbyhq.com in:file",
    "ML platform jobs.ashbyhq.com extension:py",
]

# round77+ rotate@77 — martech/adtech/ecommerce/growth/consumer (NOT r74/r75/r76)
GH_ROTATE_77_QUERIES = [
    "ashbyhq.com org:martech",
    "martech engineer ashbyhq.com in:file",
    "ashbyhq.com org:adtech",
    "adtech engineer ashbyhq.com in:file",
    "ashbyhq.com org:ecommerce",
    "ecommerce engineer ashbyhq.com in:file",
    "ashbyhq.com growth in:file",
    "growth engineer ashbyhq.com in:file",
    "ashbyhq.com org:consumer",
    "consumer tech ashbyhq.com in:file",
    "jobs.ashbyhq.com ecommerce",
    "jobs.ashbyhq.com growth",
]


# round80+ rotate@78 — deeptech/aerospace/semiconductor/energy/industrial (NOT r74/r75/r76/r77)
GH_ROTATE_78_QUERIES = [
    "ashbyhq.com org:deeptech",
    "deeptech engineer ashbyhq.com in:file",
    "ashbyhq.com org:aerospace",
    "aerospace engineer ashbyhq.com in:file",
    "ashbyhq.com org:semiconductor",
    "semiconductor engineer ashbyhq.com in:file",
    "ashbyhq.com org:energy",
    "energy engineer ashbyhq.com in:file",
    "ashbyhq.com battery in:file",
    "battery engineer ashbyhq.com in:file",
    "ashbyhq.com org:industrial",
    "industrial iot ashbyhq.com in:file",
    "jobs.ashbyhq.com munich",
    "jobs.ashbyhq.com tel-aviv",
]









# round95+ rotate@95 slice1 — payments/fintech-infra/banking-api/treasury/billing (NOT r94 automotive)
GH_ROTATE_95_SLICE1_QUERIES = [
    "ashbyhq.com org:payments",
    "payments engineer ashbyhq.com in:file",
    "ashbyhq.com fintech-infra in:file",
    "fintech infra engineer ashbyhq.com in:file",
    "ashbyhq.com banking-api in:file",
    "banking api engineer ashbyhq.com in:file",
    "ashbyhq.com treasury in:file",
    "treasury engineer ashbyhq.com in:file",
    "ashbyhq.com billing in:file",
    "billing engineer ashbyhq.com in:file",
    "jobs.ashbyhq.com payments",
    "jobs.ashbyhq.com fintech-infra",
    "jobs.ashbyhq.com banking-api",
    "jobs.ashbyhq.com treasury",
    "jobs.ashbyhq.com billing",
]

# round95+ rotate@95 slice2 — devtools/observability/monitoring/logging/tracing (boost when pool<5)
GH_ROTATE_95_SLICE2_QUERIES = [
    "ashbyhq.com org:devtools",
    "devtools engineer ashbyhq.com in:file",
    "ashbyhq.com observability in:file",
    "observability engineer ashbyhq.com in:file",
    "ashbyhq.com monitoring in:file",
    "monitoring engineer ashbyhq.com in:file",
    "ashbyhq.com logging in:file",
    "logging engineer ashbyhq.com in:file",
    "ashbyhq.com tracing in:file",
    "tracing engineer ashbyhq.com in:file",
    "jobs.ashbyhq.com devtools",
    "jobs.ashbyhq.com observability",
    "jobs.ashbyhq.com monitoring",
    "jobs.ashbyhq.com logging",
    "jobs.ashbyhq.com tracing",
]

# round96+ rotate@96 slice1 — security/identity/IAM/SSO/access-management/zero-trust (NOT r95 payments)
GH_ROTATE_96_SLICE1_QUERIES = [
    "ashbyhq.com org:security",
    "security engineer ashbyhq.com in:file",
    "ashbyhq.com identity in:file",
    "identity engineer ashbyhq.com in:file",
    "ashbyhq.com iam in:file",
    "iam engineer ashbyhq.com in:file",
    "ashbyhq.com sso in:file",
    "sso engineer ashbyhq.com in:file",
    "ashbyhq.com access-management in:file",
    "access management engineer ashbyhq.com in:file",
    "ashbyhq.com zero-trust in:file",
    "zero trust engineer ashbyhq.com in:file",
    "jobs.ashbyhq.com security",
    "jobs.ashbyhq.com identity",
    "jobs.ashbyhq.com iam",
]

# round96+ rotate@96 slice2 — devtools/observability/monitoring/logging/tracing (boost when pool<5)
GH_ROTATE_96_SLICE2_QUERIES = [
    "ashbyhq.com org:devtools",
    "devtools engineer ashbyhq.com in:file",
    "ashbyhq.com observability in:file",
    "observability engineer ashbyhq.com in:file",
    "ashbyhq.com monitoring in:file",
    "monitoring engineer ashbyhq.com in:file",
    "ashbyhq.com logging in:file",
    "logging engineer ashbyhq.com in:file",
    "ashbyhq.com tracing in:file",
    "tracing engineer ashbyhq.com in:file",
    "jobs.ashbyhq.com devtools",
    "jobs.ashbyhq.com observability",
    "jobs.ashbyhq.com monitoring",
    "jobs.ashbyhq.com logging",
    "jobs.ashbyhq.com tracing",
]

# round94+ rotate@94 — automotive/mobility/EV-charging/fleet/autonomous-vehicles/rideshare (NOT r93 insurance)
GH_ROTATE_94_QUERIES = [
    "ashbyhq.com org:automotive",
    "automotive engineer ashbyhq.com in:file",
    "ashbyhq.com mobility in:file",
    "mobility engineer ashbyhq.com in:file",
    "ashbyhq.com ev-charging in:file",
    "ev charging engineer ashbyhq.com in:file",
    "ashbyhq.com fleet in:file",
    "fleet engineer ashbyhq.com in:file",
    "ashbyhq.com autonomous-vehicles in:file",
    "autonomous vehicles engineer ashbyhq.com in:file",
    "ashbyhq.com rideshare in:file",
    "rideshare engineer ashbyhq.com in:file",
    "jobs.ashbyhq.com automotive",
    "jobs.ashbyhq.com mobility",
    "jobs.ashbyhq.com ev-charging",
    "jobs.ashbyhq.com fleet",
]

# round93+ rotate@93 — insurance/insurtech/underwriting/claims/actuarial/reinsurance (NOT r92 media)
GH_ROTATE_93_QUERIES = [
    "ashbyhq.com org:insurance",
    "insurance engineer ashbyhq.com in:file",
    "ashbyhq.com insurtech in:file",
    "insurtech engineer ashbyhq.com in:file",
    "ashbyhq.com underwriting in:file",
    "underwriting engineer ashbyhq.com in:file",
    "ashbyhq.com claims in:file",
    "claims engineer ashbyhq.com in:file",
    "ashbyhq.com actuarial in:file",
    "actuarial engineer ashbyhq.com in:file",
    "ashbyhq.com reinsurance in:file",
    "reinsurance engineer ashbyhq.com in:file",
    "jobs.ashbyhq.com insurance",
    "jobs.ashbyhq.com insurtech",
    "jobs.ashbyhq.com underwriting",
    "jobs.ashbyhq.com claims",
]

# round92+ rotate@92 — media-streaming/podcast/video/audio/creator-tools/broadcast (NOT r91 quantum)
GH_ROTATE_92_QUERIES = [
    "ashbyhq.com org:media-streaming",
    "media streaming engineer ashbyhq.com in:file",
    "ashbyhq.com podcast in:file",
    "podcast engineer ashbyhq.com in:file",
    "ashbyhq.com video in:file",
    "video engineer ashbyhq.com in:file",
    "ashbyhq.com audio in:file",
    "audio engineer ashbyhq.com in:file",
    "ashbyhq.com creator-tools in:file",
    "creator tools engineer ashbyhq.com in:file",
    "ashbyhq.com broadcast in:file",
    "broadcast engineer ashbyhq.com in:file",
    "jobs.ashbyhq.com media-streaming",
    "jobs.ashbyhq.com podcast",
    "jobs.ashbyhq.com video",
    "jobs.ashbyhq.com broadcast",
]

# round91+ rotate@91 — quantum/photonics/laser/optics/semiconductor-equipment/materials-science (NOT r90 government)
GH_ROTATE_91_QUERIES = [
    "ashbyhq.com org:quantum",
    "quantum engineer ashbyhq.com in:file",
    "ashbyhq.com photonics in:file",
    "photonics engineer ashbyhq.com in:file",
    "ashbyhq.com laser in:file",
    "laser engineer ashbyhq.com in:file",
    "ashbyhq.com optics in:file",
    "optics engineer ashbyhq.com in:file",
    "ashbyhq.com semiconductor-equipment in:file",
    "semiconductor equipment engineer ashbyhq.com in:file",
    "ashbyhq.com materials-science in:file",
    "materials science engineer ashbyhq.com in:file",
    "jobs.ashbyhq.com quantum",
    "jobs.ashbyhq.com photonics",
    "jobs.ashbyhq.com laser",
    "jobs.ashbyhq.com optics",
]

# round90+ rotate@90 — government/public-sector/civic-tech/defense-contractor/federal (NOT r89 nonprofit)
GH_ROTATE_90_QUERIES = [
    "ashbyhq.com org:government",
    "government engineer ashbyhq.com in:file",
    "ashbyhq.com public-sector in:file",
    "public sector engineer ashbyhq.com in:file",
    "ashbyhq.com civic-tech in:file",
    "civic tech engineer ashbyhq.com in:file",
    "ashbyhq.com org:defense",
    "defense contractor ashbyhq.com in:file",
    "ashbyhq.com federal in:file",
    "federal engineer ashbyhq.com in:file",
    "ashbyhq.com org:civic",
    "civic engineer ashbyhq.com in:file",
    "jobs.ashbyhq.com government",
    "jobs.ashbyhq.com federal",
    "jobs.ashbyhq.com defense",
    "jobs.ashbyhq.com public-sector",
]

# round89+ rotate@89 — nonprofit/NGO/charity/foundation/social-impact (NOT r88 sports)
GH_ROTATE_89_QUERIES = [
    "ashbyhq.com org:nonprofit",
    "nonprofit engineer ashbyhq.com in:file",
    "ashbyhq.com org:ngo",
    "ngo engineer ashbyhq.com in:file",
    "ashbyhq.com charity in:file",
    "charity engineer ashbyhq.com in:file",
    "ashbyhq.com foundation in:file",
    "foundation engineer ashbyhq.com in:file",
    "ashbyhq.com social-impact in:file",
    "social impact engineer ashbyhq.com in:file",
    "ashbyhq.com org:charity",
    "ashbyhq.com philanthropic in:file",
    "jobs.ashbyhq.com nonprofit",
    "jobs.ashbyhq.com foundation",
    "jobs.ashbyhq.com charity",
    "jobs.ashbyhq.com social-impact",
]

# round88+ rotate@88 — sports/fitness/wellness/mental-health/therapy/coaching (NOT r87 edtech)
GH_ROTATE_88_QUERIES = [
    "ashbyhq.com org:sports",
    "sports engineer ashbyhq.com in:file",
    "ashbyhq.com fitness in:file",
    "fitness engineer ashbyhq.com in:file",
    "ashbyhq.com wellness in:file",
    "wellness engineer ashbyhq.com in:file",
    "ashbyhq.com mental-health in:file",
    "mental health engineer ashbyhq.com in:file",
    "ashbyhq.com therapy in:file",
    "therapy engineer ashbyhq.com in:file",
    "ashbyhq.com coaching in:file",
    "coaching engineer ashbyhq.com in:file",
    "ashbyhq.com org:health",
    "health coach ashbyhq.com in:file",
    "jobs.ashbyhq.com fitness",
    "jobs.ashbyhq.com wellness",
]

# round87+ rotate@87 — education/edtech/tutoring/learning/university/campus (NOT r86 pharma)
GH_ROTATE_87_QUERIES = [
    "ashbyhq.com org:education",
    "education engineer ashbyhq.com in:file",
    "ashbyhq.com org:edtech",
    "edtech engineer ashbyhq.com in:file",
    "ashbyhq.com tutoring in:file",
    "tutoring engineer ashbyhq.com in:file",
    "ashbyhq.com learning in:file",
    "learning engineer ashbyhq.com in:file",
    "ashbyhq.com university in:file",
    "university engineer ashbyhq.com in:file",
    "ashbyhq.com campus in:file",
    "campus engineer ashbyhq.com in:file",
    "ashbyhq.com org:nonprofit education",
    "jobs.ashbyhq.com education",
    "jobs.ashbyhq.com edtech",
    "jobs.ashbyhq.com university",
]

# round86+ rotate@86 — pharma/biopharma/medtech/clinical/diagnostics/life-sciences (NOT r85 agtech)
GH_ROTATE_86_QUERIES = [
    "ashbyhq.com org:pharma",
    "pharma engineer ashbyhq.com in:file",
    "ashbyhq.com biopharma in:file",
    "biopharma engineer ashbyhq.com in:file",
    "ashbyhq.com org:medtech",
    "medtech engineer ashbyhq.com in:file",
    "ashbyhq.com clinical in:file",
    "clinical engineer ashbyhq.com in:file",
    "ashbyhq.com diagnostics in:file",
    "diagnostics engineer ashbyhq.com in:file",
    "ashbyhq.com org:life-sciences",
    "life sciences engineer ashbyhq.com in:file",
    "ashbyhq.com org:healthcare",
    "healthcare engineer ashbyhq.com in:file",
    "jobs.ashbyhq.com pharma",
    "jobs.ashbyhq.com biotech",
]

# round85+ rotate@85 — agriculture/farming/agtech/food-tech/restaurant/grocery (NOT r84 construction)
GH_ROTATE_85_QUERIES = [
    "ashbyhq.com org:agriculture",
    "agriculture engineer ashbyhq.com in:file",
    "ashbyhq.com farming in:file",
    "farming engineer ashbyhq.com in:file",
    "ashbyhq.com org:agtech",
    "agtech engineer ashbyhq.com in:file",
    "ashbyhq.com food-tech in:file",
    "food tech engineer ashbyhq.com in:file",
    "ashbyhq.com restaurant in:file",
    "restaurant engineer ashbyhq.com in:file",
    "ashbyhq.com grocery in:file",
    "grocery engineer ashbyhq.com in:file",
    "ashbyhq.com org:food",
    "food engineer ashbyhq.com in:file",
    "jobs.ashbyhq.com agriculture",
    "jobs.ashbyhq.com food",
]

# round84+ rotate@84 — construction/real-estate/architecture/civil/infrastructure-planning (NOT r83 hospitality)
GH_ROTATE_84_QUERIES = [
    "ashbyhq.com org:construction",
    "construction engineer ashbyhq.com in:file",
    "ashbyhq.com org:real-estate",
    "real estate engineer ashbyhq.com in:file",
    "ashbyhq.com architecture in:file",
    "architecture engineer ashbyhq.com in:file",
    "ashbyhq.com civil in:file",
    "civil engineer ashbyhq.com in:file",
    "ashbyhq.com infrastructure in:file",
    "infrastructure planning ashbyhq.com in:file",
    "ashbyhq.com org:proptech",
    "proptech engineer ashbyhq.com in:file",
    "ashbyhq.com org:built-environment",
    "built environment ashbyhq.com in:file",
    "jobs.ashbyhq.com construction",
    "jobs.ashbyhq.com real-estate",
]

# round83+ rotate@83 — hospitality/travel/hotel/airline/tourism/events (NOT r82 logistics)
GH_ROTATE_83_QUERIES = [
    "ashbyhq.com org:hospitality",
    "hospitality engineer ashbyhq.com in:file",
    "ashbyhq.com org:travel",
    "travel engineer ashbyhq.com in:file",
    "ashbyhq.com hotel in:file",
    "hotel engineer ashbyhq.com in:file",
    "ashbyhq.com airline in:file",
    "airline engineer ashbyhq.com in:file",
    "ashbyhq.com tourism in:file",
    "tourism engineer ashbyhq.com in:file",
    "ashbyhq.com events in:file",
    "events engineer ashbyhq.com in:file",
    "ashbyhq.com org:events",
    "conference platform ashbyhq.com in:file",
    "jobs.ashbyhq.com hospitality",
    "jobs.ashbyhq.com travel",
]

# round82+ rotate@82 — logistics/shipping/freight/warehouse/last-mile/3pl (NOT r81 web3)
GH_ROTATE_82_QUERIES = [
    "ashbyhq.com org:logistics",
    "logistics engineer ashbyhq.com in:file",
    "ashbyhq.com shipping in:file",
    "shipping engineer ashbyhq.com in:file",
    "ashbyhq.com freight in:file",
    "freight engineer ashbyhq.com in:file",
    "ashbyhq.com warehouse in:file",
    "warehouse engineer ashbyhq.com in:file",
    "ashbyhq.com last-mile in:file",
    "last mile engineer ashbyhq.com in:file",
    "ashbyhq.com 3pl in:file",
    "3pl engineer ashbyhq.com in:file",
    "ashbyhq.com org:supply-chain",
    "supply chain engineer ashbyhq.com in:file",
    "jobs.ashbyhq.com logistics",
    "jobs.ashbyhq.com shipping",
]

# round97+ rotate@97 slice1 — payments/fintech-infra/banking-api/treasury/billing (R95 replay)
GH_ROTATE_97_SLICE1_QUERIES = list(GH_ROTATE_95_SLICE1_QUERIES)

# round97+ rotate@97 slice2 — fintech/biotech/edtech/robotics (R74 replay)
GH_ROTATE_97_SLICE2_QUERIES = list(GH_ROTATE_74_QUERIES)

# round97+ rotate@97 slice3 — logistics/shipping/freight/warehouse/last-mile/3pl (R82 replay)
GH_ROTATE_97_SLICE3_QUERIES = list(GH_ROTATE_82_QUERIES)

# round99+ rotate@100 slice1 — payments/fintech-infra/banking-api/treasury/billing (R95 replay)
GH_ROTATE_100_SLICE1_QUERIES = list(GH_ROTATE_95_SLICE1_QUERIES)

# round99+ rotate@100 slice2 — fintech/biotech/edtech/robotics (R74 replay)
GH_ROTATE_100_SLICE2_QUERIES = list(GH_ROTATE_74_QUERIES)

# round102+ rotate@102 slice1 — payments/fintech-infra/banking-api/treasury/billing (R95 replay)
GH_ROTATE_102_SLICE1_QUERIES = list(GH_ROTATE_95_SLICE1_QUERIES)
# round102+ rotate@102 slice2 — fintech/biotech/edtech/robotics (R74 replay)
GH_ROTATE_102_SLICE2_QUERIES = list(GH_ROTATE_74_QUERIES)
# round102+ rotate@102 slice3 — logistics/shipping/freight/warehouse (R82 replay)
GH_ROTATE_102_SLICE3_QUERIES = list(GH_ROTATE_82_QUERIES)

# round103+ rotate@103 slice1 — payments/fintech-infra/banking-api/treasury/billing (R95 replay)
GH_ROTATE_103_SLICE1_QUERIES = list(GH_ROTATE_95_SLICE1_QUERIES)
# round103+ rotate@103 slice2 — fintech/biotech/edtech/robotics (R74 replay)
GH_ROTATE_103_SLICE2_QUERIES = list(GH_ROTATE_74_QUERIES)
# round103+ rotate@103 slice3 — logistics/shipping/freight/warehouse (R82 replay)
GH_ROTATE_103_SLICE3_QUERIES = list(GH_ROTATE_82_QUERIES)
# round103+ rotate@103 slice4 — security/identity/IAM/SSO/zero-trust (R96 slice1 NEW)
GH_ROTATE_103_SLICE4_QUERIES = list(GH_ROTATE_96_SLICE1_QUERIES)

# round104+ rotate@104 slice1 — payments/fintech-infra/banking-api/treasury/billing (R95 replay)
GH_ROTATE_104_SLICE1_QUERIES = list(GH_ROTATE_95_SLICE1_QUERIES)
# round104+ rotate@104 slice2 — fintech/biotech/edtech/robotics (R74 replay)
GH_ROTATE_104_SLICE2_QUERIES = list(GH_ROTATE_74_QUERIES)
# round104+ rotate@104 slice3 — logistics/shipping/freight/warehouse (R82 replay)
GH_ROTATE_104_SLICE3_QUERIES = list(GH_ROTATE_82_QUERIES)
# round104+ rotate@104 slice4 — security/identity/IAM/SSO/zero-trust (R96 slice1 replay)
GH_ROTATE_104_SLICE4_QUERIES = list(GH_ROTATE_96_SLICE1_QUERIES)
# round104+ rotate@104 slice5 — devtools/observability/monitoring/logging/tracing (R96 slice2 NEW)
GH_ROTATE_104_SLICE5_QUERIES = list(GH_ROTATE_96_SLICE2_QUERIES)






# round108+ rotate@108 slice1 — AI engineer (FRESH)
GH_ROTATE_108_SLICE1_QUERIES = [
    "AI engineer ashbyhq.com in:file",
    "AI engineer jobs.ashbyhq.com in:file",
    "artificial intelligence engineer ashbyhq.com in:file",
    "AI software engineer ashbyhq.com in:file",
    "applied AI engineer ashbyhq.com in:file",
    "generative AI engineer ashbyhq.com in:file",
    "LLM engineer ashbyhq.com in:file",
    "inurl:jobs.ashbyhq.com AI engineer",
    "inurl:jobs.ashbyhq.com machine learning engineer",
    "AI engineer remote ashbyhq.com in:file",
    "AI platform engineer ashbyhq.com in:file",
    "AI infrastructure engineer ashbyhq.com in:file",
]

# round108+ rotate@108 slice2 — ML engineer (FRESH)
GH_ROTATE_108_SLICE2_QUERIES = [
    "machine learning engineer ashbyhq.com in:file",
    "ML engineer ashbyhq.com in:file",
    "ML engineer jobs.ashbyhq.com in:file",
    "machine learning jobs.ashbyhq.com in:file",
    "deep learning engineer ashbyhq.com in:file",
    "ML platform engineer ashbyhq.com in:file",
    "ML infrastructure engineer ashbyhq.com in:file",
    "inurl:jobs.ashbyhq.com ML engineer",
    "inurl:jobs.ashbyhq.com machine learning",
    "applied machine learning engineer ashbyhq.com in:file",
    "ML systems engineer ashbyhq.com in:file",
    "ML research engineer ashbyhq.com in:file",
]

# round108+ rotate@108 slice3 — research engineer (FRESH)
GH_ROTATE_108_SLICE3_QUERIES = [
    "research engineer ashbyhq.com in:file",
    "research engineer jobs.ashbyhq.com in:file",
    "research software engineer ashbyhq.com in:file",
    "research scientist engineer ashbyhq.com in:file",
    "AI research engineer ashbyhq.com in:file",
    "ML research engineer ashbyhq.com in:file",
    "inurl:jobs.ashbyhq.com research engineer",
    "inurl:jobs.ashbyhq.com research scientist",
    "research engineer remote ashbyhq.com in:file",
    "member of technical staff research ashbyhq.com in:file",
    "research engineer distributed ashbyhq.com in:file",
    "research engineer platform ashbyhq.com in:file",
]

# round108+ rotate@108 slice4 — applied scientist (FRESH)
GH_ROTATE_108_SLICE4_QUERIES = [
    "applied scientist ashbyhq.com in:file",
    "applied scientist jobs.ashbyhq.com in:file",
    "applied research scientist ashbyhq.com in:file",
    "applied AI scientist ashbyhq.com in:file",
    "applied ML scientist ashbyhq.com in:file",
    "inurl:jobs.ashbyhq.com applied scientist",
    "inurl:jobs.ashbyhq.com applied research",
    "applied scientist remote ashbyhq.com in:file",
    "staff applied scientist ashbyhq.com in:file",
    "senior applied scientist ashbyhq.com in:file",
    "applied scientist machine learning ashbyhq.com in:file",
    "applied scientist artificial intelligence ashbyhq.com in:file",
]


# round107+ rotate@107 slice1 — staff engineer (FRESH)
GH_ROTATE_107_SLICE1_QUERIES = [
    "staff engineer ashbyhq.com in:file",
    "staff software engineer ashbyhq.com in:file",
    "staff engineer jobs.ashbyhq.com in:file",
    "senior staff engineer ashbyhq.com in:file",
    "staff backend engineer ashbyhq.com in:file",
    "staff platform engineer ashbyhq.com in:file",
    "inurl:jobs.ashbyhq.com staff engineer",
    "inurl:jobs.ashbyhq.com staff software",
    "staff engineer remote ashbyhq.com in:file",
    "staff SWE ashbyhq.com in:file",
    "principal staff engineer ashbyhq.com in:file",
    "staff engineer distributed ashbyhq.com in:file",
]

# round107+ rotate@107 slice2 — founding engineer (FRESH)
GH_ROTATE_107_SLICE2_QUERIES = [
    "founding engineer ashbyhq.com in:file",
    "founding software engineer ashbyhq.com in:file",
    "founding fullstack ashbyhq.com in:file",
    "founding backend ashbyhq.com in:file",
    "founder engineer ashbyhq.com in:file",
    "founding engineer jobs.ashbyhq.com in:file",
    "inurl:jobs.ashbyhq.com founding engineer",
    "inurl:jobs.ashbyhq.com founding",
    "founding engineer remote ashbyhq.com in:file",
    "first engineer ashbyhq.com in:file",
    "founding team engineer ashbyhq.com in:file",
    "early engineer ashbyhq.com in:file",
]

# round107+ rotate@107 slice3 — senior backend remote (FRESH)
GH_ROTATE_107_SLICE3_QUERIES = [
    "senior backend engineer remote ashbyhq.com in:file",
    "senior backend remote ashbyhq.com in:file",
    "senior backend engineer ashbyhq.com in:file",
    "remote senior backend ashbyhq.com in:file",
    "senior backend jobs.ashbyhq.com remote",
    "inurl:jobs.ashbyhq.com senior backend remote",
    "inurl:jobs.ashbyhq.com senior backend",
    "senior backend software engineer remote ashbyhq.com in:file",
    "senior backend platform remote ashbyhq.com in:file",
    "senior backend distributed ashbyhq.com in:file",
    "senior backend work from home ashbyhq.com in:file",
    "senior backend engineer US remote ashbyhq.com in:file",
]

# round107+ rotate@107 slice4 — AI engineer (FRESH)
GH_ROTATE_107_SLICE4_QUERIES = [
    "AI engineer ashbyhq.com in:file",
    "AI engineer jobs.ashbyhq.com in:file",
    "artificial intelligence engineer ashbyhq.com in:file",
    "machine learning engineer ashbyhq.com in:file",
    "ML engineer ashbyhq.com in:file",
    "inurl:jobs.ashbyhq.com AI engineer",
    "inurl:jobs.ashbyhq.com machine learning engineer",
    "AI software engineer ashbyhq.com in:file",
    "applied AI engineer ashbyhq.com in:file",
    "generative AI engineer ashbyhq.com in:file",
    "LLM engineer ashbyhq.com in:file",
    "AI engineer remote ashbyhq.com in:file",
]



# round106+ rotate@106 slice1 — remote SWE (continue from r105)
GH_ROTATE_106_SLICE1_QUERIES = [
    "remote software engineer ashbyhq.com in:file",
    "remote SWE jobs.ashbyhq.com in:file",
    "remote engineer ashbyhq.com in:file",
    "fully remote ashbyhq.com in:file",
    "remote backend ashbyhq.com in:file",
    "remote fullstack ashbyhq.com in:file",
    "jobs.ashbyhq.com remote software",
    "jobs.ashbyhq.com remote engineer",
    "inurl:jobs.ashbyhq.com remote SWE",
    "inurl:jobs.ashbyhq.com remote software",
    "distributed remote ashbyhq.com in:file",
    "work from home ashbyhq.com in:file",
]

# round106+ rotate@106 slice2 — staff engineer (FRESH)
GH_ROTATE_106_SLICE2_QUERIES = [
    "staff engineer ashbyhq.com in:file",
    "staff software engineer ashbyhq.com in:file",
    "staff engineer jobs.ashbyhq.com in:file",
    "senior staff engineer ashbyhq.com in:file",
    "principal engineer ashbyhq.com in:file",
    "staff backend engineer ashbyhq.com in:file",
    "staff platform engineer ashbyhq.com in:file",
    "inurl:jobs.ashbyhq.com staff engineer",
    "inurl:jobs.ashbyhq.com staff software",
    "inurl:jobs.ashbyhq.com principal engineer",
    "staff engineer remote ashbyhq.com in:file",
    "staff SWE ashbyhq.com in:file",
]

# round106+ rotate@106 slice3 — founding engineer (FRESH)
GH_ROTATE_106_SLICE3_QUERIES = [
    "founding engineer ashbyhq.com in:file",
    "founding software engineer ashbyhq.com in:file",
    "founding fullstack ashbyhq.com in:file",
    "founding backend ashbyhq.com in:file",
    "founder engineer ashbyhq.com in:file",
    "founding engineer jobs.ashbyhq.com in:file",
    "inurl:jobs.ashbyhq.com founding engineer",
    "inurl:jobs.ashbyhq.com founding",
    "founding engineer remote ashbyhq.com in:file",
    "first engineer ashbyhq.com in:file",
    "founding team engineer ashbyhq.com in:file",
    "early engineer ashbyhq.com in:file",
]

# round106+ rotate@106 slice4 — backend engineer remote (FRESH)
GH_ROTATE_106_SLICE4_QUERIES = [
    "remote backend engineer ashbyhq.com in:file",
    "remote backend jobs.ashbyhq.com in:file",
    "backend engineer remote ashbyhq.com in:file",
    "remote backend ashbyhq.com in:file",
    "fully remote backend ashbyhq.com in:file",
    "inurl:jobs.ashbyhq.com remote backend",
    "inurl:jobs.ashbyhq.com backend remote",
    "remote backend software engineer ashbyhq.com in:file",
    "backend remote US ashbyhq.com in:file",
    "distributed backend engineer ashbyhq.com in:file",
    "remote backend platform ashbyhq.com in:file",
    "backend engineer work from home ashbyhq.com in:file",
]

# round105+ rotate@105 slice1 — remote SWE (FRESH, not replayed)
GH_ROTATE_105_SLICE1_QUERIES = [
    "remote software engineer ashbyhq.com in:file",
    "remote SWE jobs.ashbyhq.com in:file",
    "remote engineer ashbyhq.com in:file",
    "fully remote ashbyhq.com in:file",
    "remote backend ashbyhq.com in:file",
    "remote fullstack ashbyhq.com in:file",
    "jobs.ashbyhq.com remote software",
    "jobs.ashbyhq.com remote engineer",
    "inurl:jobs.ashbyhq.com remote SWE",
    "inurl:jobs.ashbyhq.com remote software",
    "distributed remote ashbyhq.com in:file",
    "work from home ashbyhq.com in:file",
]

# round105+ rotate@105 slice2 — MTS / member of technical staff (FRESH)
GH_ROTATE_105_SLICE2_QUERIES = [
    "MTS ashbyhq.com in:file",
    "member of technical staff ashbyhq.com in:file",
    "MTS jobs.ashbyhq.com in:file",
    "member technical staff ashbyhq.com in:file",
    "staff engineer MTS ashbyhq.com in:file",
    "principal MTS ashbyhq.com in:file",
    "inurl:jobs.ashbyhq.com MTS",
    "inurl:jobs.ashbyhq.com member technical staff",
    "inurl:jobs.ashbyhq.com staff engineer",
    "senior MTS ashbyhq.com in:file",
    "software MTS ashbyhq.com in:file",
    "research engineer MTS ashbyhq.com in:file",
]

# round105+ rotate@105 slice3 — platform engineer (FRESH)
GH_ROTATE_105_SLICE3_QUERIES = [
    "platform engineer ashbyhq.com in:file",
    "platform engineer jobs.ashbyhq.com in:file",
    "platform infrastructure ashbyhq.com in:file",
    "developer platform ashbyhq.com in:file",
    "internal platform ashbyhq.com in:file",
    "platform team ashbyhq.com in:file",
    "inurl:jobs.ashbyhq.com platform engineer",
    "inurl:jobs.ashbyhq.com platform",
    "inurl:jobs.ashbyhq.com developer platform",
    "platform software engineer ashbyhq.com in:file",
    "infra platform ashbyhq.com in:file",
    "platform services ashbyhq.com in:file",
]

# round105+ rotate@105 slice4 — inurl:jobs.ashbyhq.com broad (FRESH)
GH_ROTATE_105_SLICE4_QUERIES = [
    "inurl:jobs.ashbyhq.com remote",
    "inurl:jobs.ashbyhq.com software",
    "inurl:jobs.ashbyhq.com engineer",
    "inurl:jobs.ashbyhq.com backend",
    "inurl:jobs.ashbyhq.com senior",
    "inurl:jobs.ashbyhq.com staff",
    "inurl:jobs.ashbyhq.com platform",
    "inurl:jobs.ashbyhq.com fullstack",
    "inurl:jobs.ashbyhq.com infrastructure",
    "inurl:jobs.ashbyhq.com data",
    "inurl:jobs.ashbyhq.com ML",
    "inurl:jobs.ashbyhq.com hiring",
]


# round109+ rotate@109 slice1 — remote SWE (R105 replay)
GH_ROTATE_109_SLICE1_QUERIES = list(GH_ROTATE_105_SLICE1_QUERIES)
# round109+ rotate@109 slice2 — staff engineer (R106 replay)
GH_ROTATE_109_SLICE2_QUERIES = list(GH_ROTATE_106_SLICE2_QUERIES)
# round109+ rotate@109 slice3 — AI engineer (R107 replay)
GH_ROTATE_109_SLICE3_QUERIES = list(GH_ROTATE_107_SLICE4_QUERIES)

# round110+ rotate@110 slice1 — series/startup (NOVEL, not R105 replay)
GH_ROTATE_110_SLICE1_QUERIES = [
    '"jobs.ashbyhq.com" "Series" engineer',
    '"jobs.ashbyhq.com" "Series A" engineer',
    'ashbyhq.com startup "software"',
    'inurl:jobs.ashbyhq.com startup',
    'site:jobs.ashbyhq.com "early stage"',
    '"jobs.ashbyhq.com" "Seed" engineer',
    'ashbyhq.com "venture" engineer jobs',
    '"jobs.ashbyhq.com" "YC" engineer',
    'jobs.ashbyhq.com "growth stage" engineer',
    'inurl:jobs.ashbyhq.com "Series B"',
]

# round110+ rotate@110 slice2 — MTS/staff technical (NOVEL, not R106 replay)
GH_ROTATE_110_SLICE2_QUERIES = [
    '"Member of Technical Staff" remote site:jobs.ashbyhq.com',
    '"Member of Technical Staff" jobs.ashbyhq.com',
    'site:jobs.ashbyhq.com "technical staff"',
    '"staff engineer" site:jobs.ashbyhq.com remote',
    'inurl:jobs.ashbyhq.com "principal engineer"',
    '"senior staff" jobs.ashbyhq.com',
    '"MTS" site:jobs.ashbyhq.com',
    'jobs.ashbyhq.com "member of technical staff"',
    'site:jobs.ashbyhq.com "staff software"',
    'inurl:ashbyhq.com "Member of Technical Staff"',
]

# round110+ rotate@110 slice3 — infra/data/full-stack (NOVEL, not R107 replay)
GH_ROTATE_110_SLICE3_QUERIES = [
    '"infra engineer" OR "data engineer" jobs.ashbyhq.com',
    'inurl:ashbyhq.com "full stack"',
    'jobs.ashbyhq.com "infrastructure engineer"',
    'jobs.ashbyhq.com "data platform"',
    'site:jobs.ashbyhq.com "analytics engineer"',
    'inurl:jobs.ashbyhq.com devops',
    '"full-stack engineer" jobs.ashbyhq.com',
    'site:jobs.ashbyhq.com "platform engineer" remote',
    'jobs.ashbyhq.com "reliability engineer"',
    'inurl:jobs.ashbyhq.com "data engineer"',
]


# round101+ rotate@101 slice1 — payments/fintech-infra/banking-api/treasury/billing (R95 replay)
GH_ROTATE_101_SLICE1_QUERIES = list(GH_ROTATE_95_SLICE1_QUERIES)
# round101+ rotate@101 slice2 — fintech/biotech/edtech/robotics (R74 replay)
GH_ROTATE_101_SLICE2_QUERIES = list(GH_ROTATE_74_QUERIES)

# round98+ rotate@98 slice1 — payments/fintech-infra/banking-api/treasury/billing (R95 replay)
GH_ROTATE_98_SLICE1_QUERIES = list(GH_ROTATE_95_SLICE1_QUERIES)

# round98+ rotate@98 slice2 — fintech/biotech/edtech/robotics (R74 replay)
GH_ROTATE_98_SLICE2_QUERIES = list(GH_ROTATE_74_QUERIES)

# round81+ rotate@81 — web3/crypto/defi/nft (NOT r80 climate — r80 slice unused reserve)
GH_ROTATE_81_QUERIES = [
    "ashbyhq.com org:web3",
    "web3 engineer ashbyhq.com in:file",
    "ashbyhq.com org:crypto",
    "crypto engineer ashbyhq.com in:file",
    "ashbyhq.com defi in:file",
    "defi engineer ashbyhq.com in:file",
    "ashbyhq.com nft in:file",
    "nft platform ashbyhq.com in:file",
    "ashbyhq.com blockchain in:file",
    "blockchain engineer ashbyhq.com in:file",
    "ashbyhq.com token in:file",
    "token engineer ashbyhq.com in:file",
    "jobs.ashbyhq.com web3",
    "jobs.ashbyhq.com crypto",
]

# round80+ rotate@80 — climate-tech/carbon/EV/battery/grid/nuclear/fusion (NOT r79 gaming)
GH_ROTATE_80_QUERIES = [
    "ashbyhq.com org:climate",
    "climate tech ashbyhq.com in:file",
    "ashbyhq.com carbon in:file",
    "carbon engineer ashbyhq.com in:file",
    "ashbyhq.com org:ev",
    "ev engineer ashbyhq.com in:file",
    "ashbyhq.com battery in:file",
    "battery engineer ashbyhq.com in:file",
    "ashbyhq.com grid in:file",
    "grid engineer ashbyhq.com in:file",
    "ashbyhq.com nuclear in:file",
    "nuclear engineer ashbyhq.com in:file",
    "ashbyhq.com fusion in:file",
    "fusion engineer ashbyhq.com in:file",
    "jobs.ashbyhq.com climate",
    "jobs.ashbyhq.com energy",
]

# round80+ rotate@79 — gaming/social/marketplace/creator-economy/adtech/martech (NOT r78 deeptech)
GH_ROTATE_79_QUERIES = [
    "ashbyhq.com org:gaming",
    "gaming engineer ashbyhq.com in:file",
    "ashbyhq.com org:social",
    "social network ashbyhq.com in:file",
    "ashbyhq.com marketplace in:file",
    "marketplace engineer ashbyhq.com in:file",
    "ashbyhq.com creator economy in:file",
    "creator platform ashbyhq.com in:file",
    "ashbyhq.com org:adtech",
    "adtech engineer ashbyhq.com in:file",
    "ashbyhq.com org:martech",
    "martech engineer ashbyhq.com in:file",
    "jobs.ashbyhq.com gaming",
    "jobs.ashbyhq.com social",
]

# round76+ rotate@76 — healthcare-ai/legaltech/proptech/insurtech/supply-chain/voice-ai/recruiting-tech (NOT r74/r75)
GH_ROTATE_76_QUERIES = [
    "ashbyhq.com org:healthcare-ai",
    "healthcare ai ashbyhq.com in:file",
    "ashbyhq.com org:legaltech",
    "legaltech engineer ashbyhq.com in:file",
    "ashbyhq.com org:proptech",
    "proptech engineer ashbyhq.com in:file",
    "ashbyhq.com org:insurtech",
    "insurtech engineer ashbyhq.com in:file",
    "ashbyhq.com supply chain in:file",
    "supply chain engineer ashbyhq.com in:file",
    "ashbyhq.com voice ai in:file",
    "voice engineer ashbyhq.com in:file",
    "ashbyhq.com org:recruiting",
    "recruiting tech ashbyhq.com in:file",
    "jobs.ashbyhq.com healthcare",
    "jobs.ashbyhq.com legal",
]

# round75+ rotate@75 — defense/cybersecurity/devtools/data-infra/agent-framework (NOT r74 fintech/biotech)
GH_ROTATE_75_QUERIES = [
    "ashbyhq.com org:defense",
    "ashbyhq.com org:cybersecurity",
    "security engineer ashbyhq.com in:file",
    "ashbyhq.com org:devtools",
    "devtools ashbyhq.com in:file",
    "ashbyhq.com data pipeline in:file",
    "ashbyhq.com org:data-infra",
    "data infrastructure ashbyhq.com in:file",
    "ashbyhq.com agent framework in:file",
    "ashbyhq.com org:agent",
    "agent framework ashbyhq.com in:file",
    "LLM agent jobs.ashbyhq.com extension:py",
]

# round72+ rotate@72 fresh slice (NOT r71)
GH_ROTATE_72_QUERIES = [
    "ashbyhq.com org:hrtech",
    "ashbyhq.com org:traveltech",
    "ashbyhq.com org:media",
    "ashbyhq.com postgres in:file",
    "ashbyhq.com kafka in:file",
    "ashbyhq.com spark in:file",
    "jobs.ashbyhq.com toronto",
    "jobs.ashbyhq.com vancouver",
    "mobile engineer ashbyhq.com in:file",
    "ios engineer ashbyhq.com in:file",
    "android engineer ashbyhq.com in:file",
    "quant engineer ashbyhq.com in:file",
]

GH_QUERIES = [
    '"jobs.ashbyhq.com" "Series" engineer',
    'ashbyhq.com startup "software"',
    '"Member of Technical Staff" remote site:jobs.ashbyhq.com',
    'inurl:ashbyhq.com "full stack"',
    '"infra engineer" OR "data engineer" jobs.ashbyhq.com',
    'site:jobs.ashbyhq.com "software engineer" remote',
    '"founding engineer" jobs.ashbyhq.com',
    '"jobs.ashbyhq.com" "platform" remote',
    '"backend engineer" OR "systems engineer" site:jobs.ashbyhq.com',
    'inurl:jobs.ashbyhq.com "infrastructure"',
    'jobs.ashbyhq.com "data platform" engineer',
]

PRIORITY_KEYWORDS = (
    "ai", "labs", "infra", "software", "engineer", "foundation", "data",
    "robot", "defense", "space", "ml", "platform", "dev", "tech", "intelligence",
    "backend",
)

def norm_key(slug: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", slug.casefold())


def slug_priority(slug: str, tier: int) -> tuple:
    key = slug.casefold()
    kw_hits = sum(1 for kw in PRIORITY_KEYWORDS if kw in key)
    compound = 1 if "-" in slug else 0
    return (tier, -kw_hits, -compound, slug)


def load_all_prior_slugs(*, exclude_paths: tuple[Path, ...] = ()) -> set[str]:
    """Load known slugs; exclude_paths skips current-round output (prevents test self-pollution)."""
    slugs: set[str] = set()
    rx = re.compile(r"https://jobs\.ashbyhq\.com/([^/\s,\"]+)", re.I)
    exclude_resolved = {str(p.resolve()) for p in exclude_paths if p}

    if TRACKER.is_file():
        for row in csv.DictReader(TRACKER.open(encoding="utf-8")):
            url = row.get("JD_URL") or row.get("URL") or ""
            for m in rx.finditer(url):
                slugs.add(norm_key(urllib.parse.unquote(m.group(1))))

    if POOL_DIR.is_dir():
        patterns = (
            "*slug*.txt", "*slug*.csv", "ashby-round*-new-slugs*.txt",
            "ashby-github-slugs*.csv", "ashby-round*-all-slugs.txt",
        )
        seen_paths: set[str] = set()
        for pat in patterns:
            for path in POOL_DIR.glob(pat):
                if path.name.startswith("_tmp"):
                    continue
                pstr = str(path.resolve())
                if pstr in exclude_resolved or pstr in seen_paths:
                    continue
                seen_paths.add(pstr)
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if path.suffix == ".csv":
                    try:
                        for row in csv.DictReader(text.splitlines()):
                            for col in ("slug", "Slug", "company_slug"):
                                val = row.get(col) or ""
                                if val:
                                    slugs.add(norm_key(val))
                    except Exception:
                        pass
                for m in rx.finditer(text):
                    slugs.add(norm_key(urllib.parse.unquote(m.group(1))))
                for line in text.splitlines():
                    s = line.strip()
                    if s.startswith("#") or not s:
                        continue
                    if SLUG_LINE_RX.match(s):
                        slugs.add(norm_key(s))
    return slugs


def clean_slug(raw: str) -> str | None:
    slug = urllib.parse.unquote(raw).strip().rstrip(").,;\"'")
    if not slug or " " in slug or not SLUG_LINE_RX.match(slug):
        return None
    if UUID_RX.match(slug):
        return None
    key = norm_key(slug)
    if not key or key in INVALID_SLUGS or len(slug) < 2:
        return None
    return slug


def extract_slugs(text: str, seen: set[str]) -> list[str]:
    found: list[str] = []
    for m in SLUG_RX.finditer(text):
        slug = clean_slug(m.group(1))
        if not slug:
            continue
        key = norm_key(slug)
        if key in seen:
            continue
        seen.add(key)
        found.append(slug)
    return found


def gh_search_global(query: str, seen: set[str], *, limit: int = 50) -> list[str]:
    found: list[str] = []
    try:
        proc = subprocess.run(
            [
                "gh", "search", "code", query,
                "--limit", str(limit),
                "--json", "textMatches,path,repository",
            ],
            capture_output=True,
            text=True,
            timeout=90,
        )
        if proc.returncode != 0:
            return found
        items = json.loads(proc.stdout or "[]")
        for item in items:
            blob = json.dumps(item)
            for tm in item.get("textMatches") or []:
                blob += tm.get("fragment", "")
            found.extend(extract_slugs(blob, seen))
    except Exception:
        pass
    return found


def gh_rate_ok(*, max_retries: int = 4, base_timeout: int = 45) -> tuple[bool, dict]:
    last_meta: dict = {}
    for attempt in range(max_retries):
        try:
            proc = subprocess.run(
                ["gh", "api", "rate_limit"],
                capture_output=True,
                text=True,
                timeout=base_timeout + attempt * 15,
            )
            if proc.returncode != 0:
                last_meta = {"error": proc.stderr.strip(), "attempt": attempt + 1}
                time.sleep(min(60, 10 * (2 ** attempt)))
                continue
            data = json.loads(proc.stdout)
            search = data.get("resources", {}).get("search", {})
            remaining = search.get("remaining", 0)
            meta = {"search_remaining": remaining, "reset": search.get("reset"), "attempt": attempt + 1}
            if remaining >= 5:
                return True, meta
            last_meta = meta
            reset = search.get("reset") or 0
            if reset and attempt < max_retries - 1:
                wait = min(90, max(8, int(reset - time.time()) + 2))
                time.sleep(wait)
            else:
                time.sleep(min(60, 10 * (2 ** attempt)))
        except subprocess.TimeoutExpired:
            last_meta = {"error": f"gh api rate_limit timed out after {base_timeout + attempt * 15}s", "attempt": attempt + 1}
            time.sleep(min(60, 12 * (2 ** attempt)))
        except Exception as exc:
            last_meta = {"error": str(exc), "attempt": attempt + 1}
            time.sleep(min(60, 10 * (2 ** attempt)))
    return False, last_meta


def board_alive_posting_api(slug: str, timeout: int = 12) -> bool:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{urllib.parse.quote(slug, safe='')}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
            jobs = data.get("jobs") or []
            return bool(jobs)
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-verify", type=int, default=220)
    parser.add_argument("--gh-max-queries", type=int, default=10)
    parser.add_argument("--gh-global-fallback", action="store_true")
    parser.add_argument("--gh-global-rotate", type=int, default=95)
    parser.add_argument("--gh-rotate-slice", type=int, default=1)
    args = parser.parse_args()

    out = Path(args.output)
    prior = load_all_prior_slugs(exclude_paths=(out,))
    seen = set(prior)
    repo_hits: dict[str, int | str] = {}

    dict_new: list[str] = []
    if not args.gh_global_fallback:
        for slug in DICT_GUESSES[:DICT_LIMIT]:
            key = norm_key(slug)
            if key in seen:
                continue
            seen.add(key)
            dict_new.append(slug)
    repo_hits["dict_guesses_not_in_pool"] = len(dict_new)

    gh_slugs: list[str] = []
    gh_ok, gh_meta = gh_rate_ok()
    repo_hits["gh_rate_limit"] = gh_meta
    if gh_ok:
        queries_run = 0
        if args.gh_global_fallback:
            if args.gh_global_rotate == 110:
                if args.gh_rotate_slice == 3:
                    query_list = GH_ROTATE_110_SLICE3_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r110_fresh"
                    repo_hits["gh_rotate_mode"] = "r110_infra_data_fullstack"
                    repo_hits["gh_rotate_slice"] = 3
                elif args.gh_rotate_slice == 2:
                    query_list = GH_ROTATE_110_SLICE2_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r110_fresh"
                    repo_hits["gh_rotate_mode"] = "r110_mts_staff"
                    repo_hits["gh_rotate_slice"] = 2
                else:
                    query_list = GH_ROTATE_110_SLICE1_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r110_fresh"
                    repo_hits["gh_rotate_mode"] = "r110_series_startup"
                    repo_hits["gh_rotate_slice"] = 1
            elif args.gh_global_rotate == 108:
                if args.gh_rotate_slice == 4:
                    query_list = GH_ROTATE_108_SLICE4_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r108_fresh"
                    repo_hits["gh_rotate_mode"] = "r108_applied_scientist"
                    repo_hits["gh_rotate_slice"] = 4
                elif args.gh_rotate_slice == 3:
                    query_list = GH_ROTATE_108_SLICE3_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r108_fresh"
                    repo_hits["gh_rotate_mode"] = "r108_research_engineer"
                    repo_hits["gh_rotate_slice"] = 3
                elif args.gh_rotate_slice == 2:
                    query_list = GH_ROTATE_108_SLICE2_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r108_fresh"
                    repo_hits["gh_rotate_mode"] = "r108_ml_engineer"
                    repo_hits["gh_rotate_slice"] = 2
                else:
                    query_list = GH_ROTATE_108_SLICE1_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r108_fresh"
                    repo_hits["gh_rotate_mode"] = "r108_ai_engineer"
                    repo_hits["gh_rotate_slice"] = 1
            elif args.gh_global_rotate == 107:
                if args.gh_rotate_slice == 4:
                    query_list = GH_ROTATE_107_SLICE4_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r107_fresh"
                    repo_hits["gh_rotate_mode"] = "r107_ai_engineer"
                    repo_hits["gh_rotate_slice"] = 4
                elif args.gh_rotate_slice == 3:
                    query_list = GH_ROTATE_107_SLICE3_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r107_fresh"
                    repo_hits["gh_rotate_mode"] = "r107_senior_backend_remote"
                    repo_hits["gh_rotate_slice"] = 3
                elif args.gh_rotate_slice == 2:
                    query_list = GH_ROTATE_107_SLICE2_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r107_fresh"
                    repo_hits["gh_rotate_mode"] = "r107_founding_engineer"
                    repo_hits["gh_rotate_slice"] = 2
                else:
                    query_list = GH_ROTATE_107_SLICE1_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r107_fresh"
                    repo_hits["gh_rotate_mode"] = "r107_staff_engineer"
                    repo_hits["gh_rotate_slice"] = 1
            elif args.gh_global_rotate == 106:
                if args.gh_rotate_slice == 4:
                    query_list = GH_ROTATE_106_SLICE4_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r106_fresh"
                    repo_hits["gh_rotate_mode"] = "r106_backend_engineer_remote"
                    repo_hits["gh_rotate_slice"] = 4
                elif args.gh_rotate_slice == 3:
                    query_list = GH_ROTATE_106_SLICE3_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r106_fresh"
                    repo_hits["gh_rotate_mode"] = "r106_founding_engineer"
                    repo_hits["gh_rotate_slice"] = 3
                elif args.gh_rotate_slice == 2:
                    query_list = GH_ROTATE_106_SLICE2_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r106_fresh"
                    repo_hits["gh_rotate_mode"] = "r106_staff_engineer"
                    repo_hits["gh_rotate_slice"] = 2
                else:
                    query_list = GH_ROTATE_106_SLICE1_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r106_fresh"
                    repo_hits["gh_rotate_mode"] = "r106_remote_swe"
                    repo_hits["gh_rotate_slice"] = 1
            elif args.gh_global_rotate == 105:
                if args.gh_rotate_slice == 4:
                    query_list = GH_ROTATE_105_SLICE4_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r105_fresh"
                    repo_hits["gh_rotate_mode"] = "r105_inurl_jobs_ashbyhq_broad"
                    repo_hits["gh_rotate_slice"] = 4
                elif args.gh_rotate_slice == 3:
                    query_list = GH_ROTATE_105_SLICE3_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r105_fresh"
                    repo_hits["gh_rotate_mode"] = "r105_platform_engineer"
                    repo_hits["gh_rotate_slice"] = 3
                elif args.gh_rotate_slice == 2:
                    query_list = GH_ROTATE_105_SLICE2_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r105_fresh"
                    repo_hits["gh_rotate_mode"] = "r105_mts_member_technical_staff"
                    repo_hits["gh_rotate_slice"] = 2
                else:
                    query_list = GH_ROTATE_105_SLICE1_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r105_fresh"
                    repo_hits["gh_rotate_mode"] = "r105_remote_swe"
                    repo_hits["gh_rotate_slice"] = 1
            elif args.gh_global_rotate == 104:
                if args.gh_rotate_slice == 5:
                    query_list = GH_ROTATE_104_SLICE5_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r104_fresh"
                    repo_hits["gh_rotate_mode"] = "r104_devtools_observability_monitoring_logging_tracing"
                    repo_hits["gh_rotate_slice"] = 5
                elif args.gh_rotate_slice == 4:
                    query_list = GH_ROTATE_104_SLICE4_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r104_fresh"
                    repo_hits["gh_rotate_mode"] = "r104_security_identity_iam_sso_access_management_zero_trust"
                    repo_hits["gh_rotate_slice"] = 4
                elif args.gh_rotate_slice == 3:
                    query_list = GH_ROTATE_104_SLICE3_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r104_fresh"
                    repo_hits["gh_rotate_mode"] = "r104_logistics_shipping_freight_warehouse_lastmile_3pl"
                    repo_hits["gh_rotate_slice"] = 3
                elif args.gh_rotate_slice == 2:
                    query_list = GH_ROTATE_104_SLICE2_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r104_fresh"
                    repo_hits["gh_rotate_mode"] = "r104_r74_fintech_biotech_edtech_robotics"
                    repo_hits["gh_rotate_slice"] = 2
                else:
                    query_list = GH_ROTATE_104_SLICE1_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r104_fresh"
                    repo_hits["gh_rotate_mode"] = "r104_payments_fintech_infra_banking_api_treasury_billing"
                    repo_hits["gh_rotate_slice"] = 1
            elif args.gh_global_rotate == 103:
                if args.gh_rotate_slice == 4:
                    query_list = GH_ROTATE_103_SLICE4_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r103_fresh"
                    repo_hits["gh_rotate_mode"] = "r103_security_identity_iam_sso_access_management_zero_trust"
                    repo_hits["gh_rotate_slice"] = 4
                elif args.gh_rotate_slice == 3:
                    query_list = GH_ROTATE_103_SLICE3_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r103_fresh"
                    repo_hits["gh_rotate_mode"] = "r103_logistics_shipping_freight_warehouse_lastmile_3pl"
                    repo_hits["gh_rotate_slice"] = 3
                elif args.gh_rotate_slice == 2:
                    query_list = GH_ROTATE_103_SLICE2_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r103_fresh"
                    repo_hits["gh_rotate_mode"] = "r103_r74_fintech_biotech_edtech_robotics"
                    repo_hits["gh_rotate_slice"] = 2
                else:
                    query_list = GH_ROTATE_103_SLICE1_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r103_fresh"
                    repo_hits["gh_rotate_mode"] = "r103_payments_fintech_infra_banking_api_treasury_billing"
                    repo_hits["gh_rotate_slice"] = 1
            elif args.gh_global_rotate == 102:
                if args.gh_rotate_slice == 3:
                    query_list = GH_ROTATE_102_SLICE3_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r102_fresh"
                    repo_hits["gh_rotate_mode"] = "r102_logistics_shipping_freight_warehouse_lastmile_3pl"
                    repo_hits["gh_rotate_slice"] = 3
                elif args.gh_rotate_slice == 2:
                    query_list = GH_ROTATE_102_SLICE2_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r102_fresh"
                    repo_hits["gh_rotate_mode"] = "r102_r74_fintech_biotech_edtech_robotics"
                    repo_hits["gh_rotate_slice"] = 2
                else:
                    query_list = GH_ROTATE_102_SLICE1_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r102_fresh"
                    repo_hits["gh_rotate_mode"] = "r102_payments_fintech_infra_banking_api_treasury_billing"
                    repo_hits["gh_rotate_slice"] = 1
            elif args.gh_global_rotate == 101:
                if args.gh_rotate_slice == 2:
                    query_list = GH_ROTATE_101_SLICE2_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r101_fresh"
                    repo_hits["gh_rotate_mode"] = "r101_r74_fintech_biotech_edtech_robotics"
                    repo_hits["gh_rotate_slice"] = 2
                else:
                    query_list = GH_ROTATE_101_SLICE1_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r101_fresh"
                    repo_hits["gh_rotate_mode"] = "r101_payments_fintech_infra_banking_api_treasury_billing"
                    repo_hits["gh_rotate_slice"] = 1
            elif args.gh_global_rotate == 100:
                if args.gh_rotate_slice == 2:
                    query_list = GH_ROTATE_100_SLICE2_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r100_fresh"
                    repo_hits["gh_rotate_mode"] = "r100_r74_fintech_biotech_edtech_robotics"
                    repo_hits["gh_rotate_slice"] = 2
                else:
                    query_list = GH_ROTATE_100_SLICE1_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r100_fresh"
                    repo_hits["gh_rotate_mode"] = "r100_payments_fintech_infra_banking_api_treasury_billing"
                    repo_hits["gh_rotate_slice"] = 1
            elif args.gh_global_rotate == 98:
                if args.gh_rotate_slice == 2:
                    query_list = GH_ROTATE_98_SLICE2_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r98_fresh"
                    repo_hits["gh_rotate_mode"] = "r98_r74_fintech_biotech_edtech_robotics"
                    repo_hits["gh_rotate_slice"] = 2
                else:
                    query_list = GH_ROTATE_98_SLICE1_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r98_fresh"
                    repo_hits["gh_rotate_mode"] = "r98_payments_fintech_infra_banking_api_treasury_billing"
                    repo_hits["gh_rotate_slice"] = 1
            elif args.gh_global_rotate == 97:
                if args.gh_rotate_slice == 3:
                    query_list = GH_ROTATE_97_SLICE3_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r97_fresh"
                    repo_hits["gh_rotate_mode"] = "r97_logistics_shipping_freight_warehouse_lastmile_3pl"
                    repo_hits["gh_rotate_slice"] = 3
                elif args.gh_rotate_slice == 2:
                    query_list = GH_ROTATE_97_SLICE2_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r97_fresh"
                    repo_hits["gh_rotate_mode"] = "r97_r74_fintech_biotech_edtech_robotics"
                    repo_hits["gh_rotate_slice"] = 2
                else:
                    query_list = GH_ROTATE_97_SLICE1_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r97_fresh"
                    repo_hits["gh_rotate_mode"] = "r97_payments_fintech_infra_banking_api_treasury_billing"
                    repo_hits["gh_rotate_slice"] = 1
            elif args.gh_global_rotate == 96:
                if args.gh_rotate_slice == 2:
                    query_list = GH_ROTATE_96_SLICE2_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r96_fresh"
                    repo_hits["gh_rotate_mode"] = "r96_devtools_observability_monitoring_logging_tracing"
                    repo_hits["gh_rotate_slice"] = 2
                else:
                    query_list = GH_ROTATE_96_SLICE1_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r96_fresh"
                    repo_hits["gh_rotate_mode"] = "r96_security_identity_iam_sso_access_management_zero_trust"
                    repo_hits["gh_rotate_slice"] = 1
            elif args.gh_global_rotate == 95:
                if args.gh_rotate_slice == 2:
                    query_list = GH_ROTATE_95_SLICE2_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r95_fresh"
                    repo_hits["gh_rotate_mode"] = "r95_devtools_observability_monitoring_logging_tracing"
                    repo_hits["gh_rotate_slice"] = 2
                else:
                    query_list = GH_ROTATE_95_SLICE1_QUERIES[: max(args.gh_max_queries, 12)]
                    repo_hits["gh_global_rotate_start"] = "r95_fresh"
                    repo_hits["gh_rotate_mode"] = "r95_payments_fintech_infra_banking_api_treasury_billing"
                    repo_hits["gh_rotate_slice"] = 1
            elif args.gh_global_rotate == 94:
                query_list = GH_ROTATE_94_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r94_fresh"
                repo_hits["gh_rotate_mode"] = "r94_automotive_mobility_ev_charging_fleet_autonomous_rideshare"
            elif args.gh_global_rotate == 93:
                query_list = GH_ROTATE_93_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r93_fresh"
                repo_hits["gh_rotate_mode"] = "r93_insurance_insurtech_underwriting_claims_actuarial_reinsurance"
            elif args.gh_global_rotate == 92:
                query_list = GH_ROTATE_92_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r92_fresh"
                repo_hits["gh_rotate_mode"] = "r92_media_streaming_podcast_video_audio_creator_tools_broadcast"
            elif args.gh_global_rotate == 91:
                query_list = GH_ROTATE_91_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r91_fresh"
                repo_hits["gh_rotate_mode"] = "r91_quantum_photonics_laser_optics_semiconductor_materials_science"
            elif args.gh_global_rotate == 90:
                query_list = GH_ROTATE_90_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r90_fresh"
                repo_hits["gh_rotate_mode"] = "r90_government_public_sector_civic_tech_defense_federal"
            elif args.gh_global_rotate == 89:
                query_list = GH_ROTATE_89_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r89_fresh"
                repo_hits["gh_rotate_mode"] = "r89_nonprofit_ngo_charity_foundation_social_impact"
            elif args.gh_global_rotate == 88:
                query_list = GH_ROTATE_88_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r88_fresh"
                repo_hits["gh_rotate_mode"] = "r88_sports_fitness_wellness_mental_health_therapy_coaching"
            elif args.gh_global_rotate == 87:
                query_list = GH_ROTATE_87_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r87_fresh"
                repo_hits["gh_rotate_mode"] = "r87_education_edtech_tutoring_learning_university_campus"
            elif args.gh_global_rotate == 86:
                query_list = GH_ROTATE_86_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r86_fresh"
                repo_hits["gh_rotate_mode"] = "r86_pharma_biopharma_medtech_clinical_diagnostics_life_sciences"
            elif args.gh_global_rotate == 85:
                query_list = GH_ROTATE_85_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r85_fresh"
                repo_hits["gh_rotate_mode"] = "r85_agriculture_farming_agtech_foodtech_restaurant_grocery"
            elif args.gh_global_rotate == 84:
                query_list = GH_ROTATE_84_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r84_fresh"
                repo_hits["gh_rotate_mode"] = "r84_construction_real_estate_architecture_civil_infrastructure_planning"
            elif args.gh_global_rotate == 83:
                query_list = GH_ROTATE_83_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r83_fresh"
                repo_hits["gh_rotate_mode"] = "r83_hospitality_travel_hotel_airline_tourism_events"
            elif args.gh_global_rotate == 82:
                query_list = GH_ROTATE_82_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r82_fresh"
                repo_hits["gh_rotate_mode"] = "r82_logistics_shipping_freight_warehouse_lastmile_3pl"
            elif args.gh_global_rotate == 81:
                query_list = GH_ROTATE_81_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r81_fresh"
                repo_hits["gh_rotate_mode"] = "r81_web3_crypto_defi_nft"
            elif args.gh_global_rotate == 80:
                query_list = GH_ROTATE_80_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r80_fresh"
                repo_hits["gh_rotate_mode"] = "r80_climate_carbon_ev_battery_grid_nuclear_fusion"
            elif args.gh_global_rotate == 79:
                query_list = GH_ROTATE_79_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r79_fresh"
                repo_hits["gh_rotate_mode"] = "r79_gaming_social_marketplace_creator_adtech_martech"
            elif args.gh_global_rotate == 78:
                query_list = GH_ROTATE_78_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r78_fresh"
                repo_hits["gh_rotate_mode"] = "r78_deeptech_aerospace_semiconductor_energy_industrial"
            elif args.gh_global_rotate == 77:
                query_list = GH_ROTATE_77_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r77_fresh"
                repo_hits["gh_rotate_mode"] = "r77_martech_adtech_ecommerce_growth_consumer"
            elif args.gh_global_rotate == 76:
                query_list = GH_ROTATE_76_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r76_fresh"
                repo_hits["gh_rotate_mode"] = "r76_healthcare_legaltech_proptech_insurtech_supply_voice_recruiting"
            elif args.gh_global_rotate == 75:
                query_list = GH_ROTATE_75_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r75_fresh"
                repo_hits["gh_rotate_mode"] = "r75_defense_cyber_devtools_data_infra_agent_framework"
            elif args.gh_global_rotate == 74:
                query_list = GH_ROTATE_74_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r74_fresh"
                repo_hits["gh_rotate_mode"] = "r74_r65_biotech_edtech_r70_fintech_robotics"
            elif args.gh_global_rotate == 73:
                query_list = GH_ROTATE_73_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r73_fresh"
                repo_hits["gh_rotate_mode"] = "r73_agtech_retailtech_autotech_redis_elasticsearch_ts"
            elif args.gh_global_rotate == 72:
                query_list = GH_ROTATE_72_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r72_fresh"
                repo_hits["gh_rotate_mode"] = "r72_hrtech_traveltech_media_postgres_kafka_mobile"
            elif args.gh_global_rotate == 71:
                query_list = GH_ROTATE_71_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r71_fresh"
                repo_hits["gh_rotate_mode"] = "r71_edutech_govtech_search_analytics_network_terraform"
            elif args.gh_global_rotate == 70:
                query_list = GH_ROTATE_70_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r70_fresh"
                repo_hits["gh_rotate_mode"] = "r70_proptech_insurtech_observability_streaming_warehouse"
            elif args.gh_global_rotate == 69:
                query_list = GH_ROTATE_69_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r69_fresh"
                repo_hits["gh_rotate_mode"] = "r69_healthtech_logistics_distributed_realtime_embedded"
            elif args.gh_global_rotate == 68:
                query_list = GH_ROTATE_68_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r68_fresh"
                repo_hits["gh_rotate_mode"] = "r68_crypto_gaming_security_inference_gpu"
            elif args.gh_global_rotate == 67:
                query_list = GH_ROTATE_67_QUERIES[: max(args.gh_max_queries, 12)]
                repo_hits["gh_global_rotate_start"] = "r67_fresh"
                repo_hits["gh_rotate_mode"] = "r67_fintech_climate_robotics_agent_llm"
            else:
                n = len(GH_GLOBAL_QUERIES)
                start = args.gh_global_rotate % n if n else 0
                rotated = GH_GLOBAL_QUERIES[start:] + GH_GLOBAL_QUERIES[:start]
                query_list = rotated[: max(args.gh_max_queries, 10)]
                repo_hits["gh_global_rotate_start"] = start
        else:
            query_list = GH_QUERIES[: args.gh_max_queries]
        for query in query_list:
            if queries_run:
                time.sleep(6)
            batch = gh_search_global(query, seen)
            key = f"gh:global:{query[:48]}" if args.gh_global_fallback else f"gh:{query[:48]}"
            repo_hits[key] = len(batch)
            gh_slugs.extend(batch)
            queries_run += 1
        repo_hits["gh_queries_run"] = queries_run
        repo_hits["gh_mode"] = "global_fallback" if args.gh_global_fallback else "backend_platform"
    else:
        repo_hits["gh_api"] = "skipped_rate_limit"

    ordered: list[tuple[str, int]] = []
    for slug in dict_new:
        ordered.append((slug, 0))
    for slug in gh_slugs:
        ordered.append((slug, 1))
    ordered.sort(key=lambda x: slug_priority(x[0], x[1]))
    candidates = [s for s, _ in ordered]
    to_verify = candidates[: args.max_verify] if args.max_verify else candidates

    verified: list[str] = []
    posting_api_hits = 0
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = {pool.submit(board_alive_posting_api, slug): slug for slug in to_verify}
        for fut in as_completed(futures):
            slug = futures[fut]
            try:
                if fut.result():
                    verified.append(slug)
                    posting_api_hits += 1
            except Exception:
                pass
    verified.sort(key=lambda s: candidates.index(s) if s in candidates else 9999)
    repo_hits["posting_api_verified"] = posting_api_hits

    out.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# round80 dict200-batchAM+gh10 verified={len(verified)} "
        f"candidates={len(candidates)} exclude_prior={len(prior)} "
        f"strategies={'dict_brute,gh_global_fallback' if args.gh_global_fallback else 'dict_brute,gh_backend_platform'}"
    )
    out.write_text(header + "\n" + "\n".join(verified) + ("\n" if verified else ""), encoding="utf-8")
    print(json.dumps({
        "output": str(out),
        "exclude_known": len(prior),
        "candidates": len(candidates),
        "verified": len(verified),
        "repo_hits": repo_hits,
        "slugs": verified[:40],
        "new_slug_count": len(verified),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
