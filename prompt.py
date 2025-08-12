api_key = "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"
base_url = "https://openrouter.ai/api/v1"


term_prompt = """
你现在扮演“术语抽取器”。只做名词级术语抽取与翻译，不要解释。对我提供的文本进行分词与术语识别，抽取名词、名词短语、专有名词、缩略词/首字母词（如“5G”“API”“NLP”），并翻译为{tgt_lang}。
如果文本中没有可用术语，返回空列表。

## 任务要求
1. 仅返回术语级名词：排除动词、形容词、副词、整句、空洞词（如“问题”“方面”“情况”）与纯数字。
2. 允许多词术语（保留完整搭配，如“干湿分离机构”“技术服务合同”“数据资产管理平台”）。
3. 规格化与去重：统一单复数、大小写与变体，输出一个“规范术语”，同时列出可能的“变体”。
4. 专名与品牌：人名、地名、机构名、产品名保留原文；若存在行业通行译名，在 translation 中给出该通行译名，并在 notes 标注“通行译名”。
5. 术语优先级：领域相关 > 通用词。遇到边界不清时，宁可多收，不要漏收。
6. 输出格式：只输出 JSON，不要额外文本、不要 Markdown、不要代码块围栏。

## 案例

输入："我们在5G网络下测试马桶防漏水干湿分离机构的可靠性，并更新技术服务合同。"
输出：
[
{{
"source_text": "5G网络",
"target_text": "5G network",
}},
{{
"source_text": "马桶防漏水干湿分离机构",
"target_text": "dry-wet separation mechanism",
}},
{{
"source_text": "技术服务合同",
"target_text": "technical service contract",
}},
{{
"source_text": "可靠性",
"target_text": "reliability",
}}
]

"""


translation_prompt = """
参考以下术语翻译：

{ref_text}

请将用户给出的文本翻译为{target_language}，只输出译文，不要输出任何其他内容：
"""