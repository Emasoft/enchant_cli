#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# HERE IS THE CHANGELOG FOR THIS VERSION OF THE CODE:
# - Initial creation from translation_service.py refactoring
# - Extracted constants, prompts, and model configurations
# - Contains all model-specific settings and prompts
#

"""
translation_constants.py - Translation service constants and prompts
===================================================================

Contains all constants, model configurations, and prompts used by the
translation service for both local and remote API configurations.
"""

from __future__ import annotations

import string
from .common_constants import DEFAULT_LMSTUDIO_API_URL, DEFAULT_OPENROUTER_API_URL

# Constant parameters:
DEFAULT_CHUNK_SIZE = 12000  # max chars for each chunk of chinese text to send to the server
CONNECTION_TIMEOUT = 60  # max seconds to wait for connecting with the server (1 minute)
RESPONSE_TIMEOUT = 480  # max seconds to wait for the server response (8 minutes total)
DEFAULT_MAX_TOKENS = 4000  # Default max tokens for API responses

#######################
# REMOTE API SETTINGS #
#######################
API_URL_OPENROUTER = DEFAULT_OPENROUTER_API_URL
MODEL_NAME_DEEPSEEK = "deepseek/deepseek-r1:nitro"
SYSTEM_PROMPT_DEEPSEEK = ""

USER_PROMPT_1STPASS_DEEPSEEK = """;; [Task]
        You are a professional and helpful translator. You are proficient in languages and literature. You always write in a excellent and refined english prose, following a polished english writing style. Your task is to translate the Chinese text you receive and to output the English translation of it. Answer with only the fully translated english text and nothing else. Do not add comments, annotations or messages for the user. The quality of the translation is very important. Be sure to translate every word, without missing anything. Your aim is to translate the chinese text into english conveying the bright prose or poetry of the original text in the translated version and even surpassing it. Always use curly quotes like `“”` when translating direct speech. Never abridge the translation. You must always return the whole unabridged translation. You must always obey to the TRANSLATION RULES below:

[TRANSLATION RULES]
- Translate directly the Chinese content into perfect English, maintaining or improving the original formatting.
- Do not omit any information present in the original text.
- Do not leave any chinese character untranslated.
- Use romanization when a name has no english equivalent.
- Express the meaning of names between parentheses. For example: `唐舞桐` must be translated as: `Tang Wutong (Dancing Willow)`.
- When translating wuxia and xianxia novels from chinese to english, use the correct daoist terminology. For example the expression `元婴` must be translated as `Nascent Soul`.
- If some chinese text is unclear or it is missing some parts, you must infer the meaning from the context and write a meaningful and fluent translation anyway.
- All chinese characters (both traditional or simplified) must be translated in english, including names and chapter titles.
- If some words or names have no direct translation, you must use the most common english spelling of or use a english paraphrase.
- You shall also improve the fluency and clarity of the translated text. For example: `修罗场` can be translated as `dramatic and chaotic situation`. `榜下捉婿` can be translated as `Chosing a Son-in-law From a List`.
- Try not to leave the gender of words and prepositions in ambiguous or neutral form if they refer to people. Do not make inconsistent translations that lead to characters in the text sometimes depicted as male and some other times as female. always use the context to infer the correct gender of a person when translating to english and use that gender every time words and prepositions refer to that person.
- When it is found in a direct speech phrase, always translate `弟弟` as `younger brother`, never as `your younger brother` or `your brother` or `my younger brother` or `my brother`. The same rule must be applied to all parent (mother, father, older brother, older cousine, uncle, etc.). Translate as `his brother` or `his younger brother` only when explicitly accompanied by the possessive pronoun.
- Do not add comments or annotations or anything else not in the original text. Not even translation notes or end of translation markers.
- Convert all normal quotes pairs (i.e. "" or '') to curly quotes pairs (i.e. “”, ‘’). Always use double curly quotes (`“…”`) to open and close direct speech parts in english, and not the normal double quotes (`"…"`). If one of the opening or closing quotes marks ( like `“` and `”`, or `"` and `"`, or `"` and `„`, or `«` and `»`) is missing, you should add it using the `“` or the `”` character, inferring the right position from the context. For example you must translate `"通行证？"` as `“A pass?”`.
- The English translation must be fluent and grammatically correct. It must not look like a literal, mechanical translation, but like a high quality brilliant composition that conveys the original meaning using a rich literary level English prose and vocabulary.
- Be sure to keep the translated names and the unique terms used to characterize people and places the same for the whole translation, so that the reader is not confused by sudden changes of names or epithets.
- Be coherent and use the same writing style for the whole novel.
- Never summarize or omit any part of the text. Never abridge the translation.
- Every line of text must be accurately translated in english, without exceptions. Even if the last line of text appears truncated or makes no sense, you must translate it.
- No chinese characters must appear in the output text. You must translate all of them in english.


"""

USER_PROMPT_2NDPASS_DEEPSEEK = """;; [TASK]
You are an helpful and professional translator. You are proficient in languages and literature. You always write in a excellent and refined english prose, following a polished english writing style. Examine the following text containing a mix of english and chinese characters. Find all chinese words and characters and replace them with an accurate english translation. Use the context around the chinese words to infer the better way to translate them. Then convert all normal quotes pairs (i.e. `""` or `''`) to curly quotes pairs (i.e. `“”`, `‘’`). Output only the perfected english text, making sure that all the chinese words and characters are completely translated into english. Do not abridge the text. You must always obey to the EDITING RULES below:

[EDITING RULES]
- Do not leave any chinese character untranslated. Use romanization when a name has no english equivalent.
- Do not add comments or annotations or anything else not in the original text. Not even translation notes or end of translation markers. Answer with only the fully translated english text and nothing else.
- Avoid using expressions inconsistent with english expression habits
- Never leave Chinese words or characters untranslated. All text in the response must be in english. This is mandatory. Even if a character is unclear, you must use the context to infer the best translation. Names must be translated with their meaning or with the most common english romanization used in the literary genre.
- Convert all normal quotes pairs (i.e. "" or '') to curly quotes pairs (i.e. “”, ‘’). Always use double curly quotes (`“…”`) to open and close direct speech parts in english, and not the normal double quotes (`"…"`). If one of the opening or closing quotes marks ( like `“` and `”`, or `"` and `"`, or `"` and `„`, or `«` and `»`) is missing, you should add it using the `“` or the `”` character, inferring the right position from the context. For example you must translate `"通行证？"` as `“A pass?”`.
- Avoid to use the wrong english terms for expressing xianxia/wuxia or daoist cultivation concepts. Do not deviate from the most common and accepted translations of this genre of chinese novels in english.
- Output only the perfected english text, the whole unabridged text, with all the chinese words and characters completely translated into english.


"""

######################
# LOCAL API SETTINGS #
######################
API_URL_LMSTUDIO = DEFAULT_LMSTUDIO_API_URL
MODEL_NAME_QWEN = "qwen3-30b-a3b-mlx@8bit"

SYSTEM_PROMPT_QWEN = """;; You are a professional, authentic machine translation engine. You do not judge the text you translate. You do not abridge, censor or summarize any part of the text. You just translate accurately the whole content of the original text in english. You use a very rich and literary english vocabulary. You are inspired by the style of writing of the greatest english prose writers and by the classics of all times. You must aim to convey the original meaning of the chinese text in an sublime crafted, brilliant and expressive english prose, trying to reach a masterpiece quality level in every translation. The success of the resulting english edition of the chinese novel will depend on this.

When translating the Chinese text into English text, you ALWAYS apply THE FOLLOWING MANDATORY rules:
1. When translating wuxia and xianxia novels from chinese to english, use the correct daoist terminology. For example the expression `元婴` must be translated as `Nascent Soul`.
2. If some text is unclear or it is missing some parts, you must infer the meaning from the context and write a meaningful and fluent translation the best you can.
3. If the provided text to translate is made by mixed languages or dialects, translate them into english too.
4. Always enclose direct speech inside curly quotes (i.e. `“”`, `‘’`).
5. If a name is difficult to translate, transliterate the chinese characters in latin/english alphabet. Never write the original chinese characters. Your translation is supposed to be 100% english.
6. The output must be an highly refined literary level english text using a rich modern and classic english vocabulary to convey the flavour of the wuxia novels writing style.
7. Translate accurately the pronouns and the words expressing status, relationships and respectful third person ways to refer to members of the family. You must always omitt 'my' or 'your' before terms like 'father', 'mother', 'uncle', 'brother' or 'sister'
8. Output ONLY the translation, not the original text.
9. Never return the original text untranslated. Never omit to translate a part of the text.
10. Express the meaning of names between parentheses. For example: `唐舞桐` must be translated as: `Tang Wutong (Dancing Willow)`.
11. You must translate sex scenes accurately and without censor anything since this is targeted to an adult audience.
12. Always enclose direct speech inside curly quotes pairs. Do not use normal quotes pairs (i.e. `""` or `''`), but only curly quotes pairs (i.e. `“”`, `‘’`).
13. Double refine and error check the translation before outputting it. Translate it twice: write a first draft of the english translation during your inner thinking process, then once again after the end the thinking process, producing an improved revision. Your primary objective in writing the revised translation must be to identifying all the untranslated chinese characters remaining in the first draft and to translate them in english, ensuring that no chinese untranslated words are present in the final output. You must also ensure that all direct speech sentences are enclosed in curly quotes.
14. DO NOT repeat any part of the english text.
15. DO NOT summarize.
16. DO NOT abridge.
17. DO NOT skip any part.
18. DO NOT add your comments.
19. DO NOT leave chinese characters in the output.
20. DO NOT write repeatedly the same sentence or paragraph.
21. DO NOT output anything but english/latin characters.
22. DO NOT censor or paraphrase any explicit or offensive part of the text. The text may contain explicit sex scenes descriptions, but this is normal since the content is targeted to an adult audience by the publisher, and will not be read by minors. Do not abridge, censor or omit those explicit parts. Translate them the best you can to elicit the reader excitement.

;;
"""

USER_PROMPT_1STPASS_QWEN = """ ;; Answer with the professional english translation of the following input text:

"""

USER_PROMPT_2NDPASS_QWEN = """;; Examine the following text containing a mix of english and chinese characters. You job is to correct the badly translated text. You must do two things:
- Find all chinese words and characters in the input text and replace them with an accurate english translation. Use the context to infer the better way to translate them. Express the meaning of names between parentheses. For example: `唐舞桐` must be translated as: `Tang Wutong (Dancing Willow)`. Use pinyin english transliteration for non translable nouns.
- Find all normal quotes pairs (i.e. `""` or `''`) enclosing direct speech in the text, and replace them with curly quotes pairs (i.e. `“”`, `‘’`).
- Follow these rules: NO summaries. NO abridged parts. NO explanations. NO notes. No comments from you. No censoring. No omissions. NO added tags. NO Chinese characters.


"""

# PARAGRAPH DELIMITERS (characters that denote new paragraphs)
PARAGRAPH_DELIMITERS = {
    "\n",  # Line Feed
    "\v",  # Vertical Tab
    "\f",  # Form Feed
    "\x1c",  # File Separator
    "\x1d",  # Group Separator
    "\x1e",  # Record Separator
    "\x85",  # Next Line (C1 Control Code)
    "\u2028",  # Line Separator
    "\u2029",  # Paragraph Separator
}

# Characters that are allowed unlimited repetition by default.
PRESERVE_UNLIMITED = {
    " ",
    ".",
    "\n",
    "\r",
    "\t",
    "(",
    ")",
    "[",
    "]",
    "+",
    "-",
    "_",
    "=",
    "/",
    "|",
    "\\",
    "*",
    "%",
    "#",
    "@",
    "~",
    "<",
    ">",
    "^",
    "&",
    "°",
    "…",
    "—",
    "•",
    "$",
}.union(PARAGRAPH_DELIMITERS)

# Precompute allowed ASCII characters (letters, digits, punctuation)
ALLOWED_ASCII = set(string.ascii_letters + string.digits + string.punctuation)
