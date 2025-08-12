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
{
"source_text": "5G网络",
"target_text": "5G network",
},
{
"source_text": "马桶防漏水干湿分离机构",
"target_text": "dry-wet separation mechanism",
},
{
"source_text": "技术服务合同",
"target_text": "technical service contract",
},
{
"source_text": "可靠性",
"target_text": "reliability",
}
]

"""