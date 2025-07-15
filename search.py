import requests
from bs4 import BeautifulSoup
import re
import time
import json
import urllib.parse
import os
import random


def search_bing_for_model_params(model_name):
    """使用必应搜索查询指定模型的参数大小"""
    # 准备更精确的搜索查询
    query = f"{model_name} parameter size OR parameters OR billion OR million OR 亿 OR 百万 -date -year -version"
    encoded_query = urllib.parse.quote_plus(query)

    # 设置请求头（模拟浏览器）
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.bing.com/",
        "DNT": "1",
    }

    # 发送搜索请求
    try:
        response = requests.get(
            f"https://www.bing.com/search?q={encoded_query}&setlang=en",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return f"搜索请求失败: {str(e)}", []

    # 解析HTML内容
    soup = BeautifulSoup(response.text, 'html.parser')

    # 查找搜索结果项
    results = []
    search_items = soup.find_all('li', class_='b_algo')

    if not search_items:
        return "未找到搜索结果，请尝试其他模型名称", []

    # 从搜索结果中提取信息
    for item in search_items:
        title_elem = item.find('h2')
        link_elem = item.find('a')
        desc_elem = item.find('p') or item.find('div', class_='b_caption')

        title = title_elem.get_text(strip=True) if title_elem else "无标题"
        link = link_elem['href'] if link_elem and 'href' in link_elem.attrs else "无链接"
        desc = desc_elem.get_text(strip=True) if desc_elem else "无描述"

        # 在描述中搜索参数大小 - 使用改进后的识别方法
        param_size = find_parameter_size(model_name, desc)

        results.append({
            "title": title,
            "link": link,
            "desc": desc,
            "param_size": param_size
        })

    # 返回结果
    return "搜索成功", results


def find_parameter_size(model_name, text):
    """改进的参数大小识别方法，避免误识别日期等数字"""
    # 首先尝试在文本中寻找明确的参数大小模式
    patterns = [
        # 带单位的模式
        r'(\d+\.?\d*)\s*(billion|B|bn|亿|百万|million|M)\s*parameters?',
        r'(\d+\.?\d*)\s*(billion|B|bn|亿|百万|million|M)\s*param',
        r'(\d+\.?\d*)\s*(B|bn)\s*model',
        r'参数规模[:：]\s*(\d+\.?\d*)\s*(billion|B|bn|亿|百万|million|M)?',
        r'(\d+\.?\d*)\s*(billion|B|bn|亿|百万|million|M)\s*参数',
        r'(\d+)\s*亿\s*参数',

        # 不带单位但上下文明确的模式
        r'parameter size:?\s*(\d+\.?\d*[BM]?)',
        r'parameters:?\s*(\d+\.?\d*[BM]?)',
        r'模型大小:?\s*(\d+\.?\d*[BM]?)',
        r'参数数量:?\s*(\d+\.?\d*[BM]?)',
    ]

    # 模型名称中的数字模式（用于排除版本号）
    model_number_pattern = r'\b\d{1,4}\b'

    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            size_str = match.group(1)
            unit = match.group(2).lower() if len(match.groups()) > 1 and match.group(2) else ""

            # 检查是否为模型版本号（避免误识别）
            if is_version_number(model_name, size_str):
                continue

            # 检查是否为日期（避免误识别）
            if is_date(size_str):
                continue

            # 尝试转换为浮点数
            try:
                size = float(size_str)
            except ValueError:
                continue

            # 转换为统一单位 (B = billion)
            if unit in ["b", "bn", "billion", "亿"] or 'B' in size_str:
                return f"{size}B"
            elif unit in ["million", "m", "百万"] or 'M' in size_str:
                return f"{size / 1000:.2f}B"  # 转换为billion
            else:
                # 根据上下文确定单位
                # 如果数字很大（>1000），假设是百万单位
                if size > 1000:
                    return f"{size / 1000:.1f}B"
                # 如果数字在10-1000之间，假设是十亿单位
                elif size >= 10:
                    return f"{size:.1f}B"
                # 如果数字很小但有参数上下文，假设是十亿单位
                elif size > 0:
                    return f"{size}B"

    # 如果未找到明确模式，尝试寻找大数字
    large_numbers = re.findall(r'\b(\d{3,})\b', text)
    if large_numbers:
        # 过滤掉可能不是参数的数字（年份、版本号等）
        valid_numbers = []
        for num_str in large_numbers:
            num = int(num_str)
            # 排除明显是年份的数字
            if 1900 <= num <= 2100:
                continue
            # 排除可能是版本号的数字（如果模型名称中有类似数字）
            if is_version_number(model_name, num_str):
                continue
            valid_numbers.append(num)

        if valid_numbers:
            largest = max(valid_numbers)
            # 根据数字大小确定单位
            if largest >= 1000000:  # 百万以上
                return f"{largest / 1000000:.2f}B"
            elif largest >= 1000:  # 千以上
                return f"{largest / 1000:.2f}B"
            else:  # 千以下
                return f"{largest / 1000:.3f}B"

    return "未找到参数信息"


def is_version_number(model_name, number_str):
    """检查数字是否是模型版本号的一部分"""
    # 检查数字是否出现在模型名称中
    if number_str in model_name:
        return True

    # 检查数字是否符合常见版本号模式
    version_patterns = [
        r'\b\d{4}\b',  # 4位数字（年份）
        r'\b\d\.\d\b',  # 版本号如1.5
        r'\bv\d+\b',  # v1, v2等
    ]

    for pattern in version_patterns:
        if re.search(pattern, number_str):
            return True

    return False


def is_date(number_str):
    """检查数字是否符合日期格式"""
    date_patterns = [
        r'\b\d{4}\b',  # 年份 2023
        r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # 日期格式 12/31/2023
        r'\b\d{4}-\d{1,2}-\d{1,2}\b',  # 日期格式 2023-12-31
    ]

    for pattern in date_patterns:
        if re.search(pattern, number_str):
            return True

    return False

def display_results(results):
    """显示搜索结果并提取参数大小信息"""
    if not results:
        print("未找到相关信息")
        return

    print("\n" + "=" * 80)
    print(f"{'模型参数搜索结果':^80}")
    print("=" * 80)

    # 收集所有找到的参数大小
    found_params = {}

    for i, result in enumerate(results, 1):
        print(f"\n结果 #{i}:")
        print(f"标题: {result['title']}")
        print(f"链接: {result['link']}")
        print(f"描述: {result['desc'][:200]}...")
        print(f"参数大小: {result['param_size']}")

        # 收集找到的参数大小
        if result['param_size'] != "未找到参数信息":
            model_name = result['title'].split()[0]
            found_params[model_name] = result['param_size']

    # 显示汇总信息
    if found_params:
        print("\n" + "-" * 80)
        print(f"{'参数大小汇总':^80}")
        print("-" * 80)
        for _, size in found_params.items():
            print(f"{size}")
        print("-" * 80)
    else:
        print("\n未在搜索结果中找到明确的参数大小信息")

    return found_params


def save_results(model_name, results, found_params):
    """保存结果到文件"""
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"model_params_{model_name}_{timestamp}"

    # 保存为文本文件
    with open(f"{filename}.txt", "w", encoding="utf-8") as f:
        f.write(f"模型参数搜索报告: {model_name}\n")
        f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        f.write("搜索结果:\n")
        for i, result in enumerate(results, 1):
            f.write(f"\n结果 #{i}:\n")
            f.write(f"标题: {result['title']}\n")
            f.write(f"链接: {result['link']}\n")
            f.write(f"描述: {result['desc']}\n")
            f.write(f"参数大小: {result['param_size']}\n")

        if found_params:
            f.write("\n\n参数大小汇总:\n")
            for model, size in found_params.items():
                f.write(f"{model}: {size}\n")

    # 保存为JSON文件
    with open(f"{filename}.json", "w", encoding="utf-8") as f:
        json.dump({
            "model": model_name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results,
            "params_summary": found_params
        }, f, indent=2, ensure_ascii=False)

    print(f"\n结果已保存到文件: {filename}.txt 和 {filename}.json")


def main():
    """主函数"""
    print("=" * 80)
    print(f"{'AI模型参数搜索引擎':^80}")
    print("=" * 80)
    print("此工具通过必应搜索查询AI模型的参数大小信息")
    print("支持搜索的模型示例: GPT-3, Claude-3, LLaMA-2, Mistral-7B")

    # 预定义模型列表
    popular_models = [
        "GPT-4", "Claude-3-Opus", "LLaMA-2-70B",
        "Mistral-7B", "Gemini-1.5-Pro", "Mixtral-8x7B"
    ]

    # 用户输入模型名称
    model_name = input("\n请输入要查询的模型名称: ").strip()

    if not model_name:
        model_name = random.choice(popular_models)
        print(f"\n未输入模型名称，将随机选择一个流行模型: {model_name}")

    print(f"\n正在搜索 {model_name} 的参数大小，请稍候...")

    # 执行搜索
    status, results = search_bing_for_model_params(model_name)

    if status != "搜索成功":
        print(f"\n错误: {status}")
        return

    # 显示结果
    found_params = display_results(results)


if __name__ == "__main__":
    main()