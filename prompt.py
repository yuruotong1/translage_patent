api_key = "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"
base_url = "https://openrouter.ai/api/v1"

translation_prompt = """
请将以下 {src_lang} 语句翻译成 {tgt_lang}。

要求如下：
- 只输出**一种**最准确、最自然的翻译结果；
- 不要列出多个可能含义；
- 不要进行解释或分析；
- 输出内容要简洁、清晰，表达明确，不含歧义。

待翻译内容：
"{text}"

输出：

"""