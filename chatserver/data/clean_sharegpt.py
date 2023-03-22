"""
Usage: python3 -m chatserver.data.clean_sharegpt --in sharegpt_html.json --out sharegpt_clean.json
"""
import argparse
import json
import logging
import re
from typing import Dict, Union

import bs4
import markdownify
import tqdm


def _get_html_tags(file_path: str):
    # Generate the list of html tags occured in the file.
    s = set()
    for l in open("file_path", "r"):
        for m in re.findall("</[^<>]+>", l):
            s.add(m)
    return s

div_pattern = re.compile("<div.*?>")
code_lang_pattern = re.compile("```\n?" + "(.*?)" + "Copy code" + "(.+?)" + "\n\n```", re.DOTALL)
code_lang_format = r"```\g<1>\n\g<2>\n```"

def reformat_code(val: str) -> str:
    # Input code format is:
    # ```
    # $<language>Copy code$<exact_code_here>
    #
    # ```
    # This function convert it into the correct markdown format
    return re.sub(code_lang_pattern, code_lang_format, val)


def html_to_markdown(val: str) -> str:
    """can handle enum, table and code. Code not in the best format."""
    # Delete all <div>. This is required to make intent work in code blocks.
    val = re.sub(div_pattern, "", val)
    # Remove all html tags
    val = markdownify.markdownify(val)
    # Reformat code
    val = reformat_code(val)
    val = val.replace("\n\n\n", "\n")
    return val


def should_skip(val: str) -> bool:
    black_list = ["OpenAI", "openai"]
    for w in black_list:
        if w in val:
            return True
    return False


def clean_html_source(content: Union[list, Dict], begin, end, check_tag, check_num):
    """
    clean the input json content.
    Args:
        content(Union[list, Dict]): json file loaded in memory.
        check_tag: a debug purpose arg. If a conversation contains the tag, log
          it before and after cleaning.
        check_num: number of matched conversations logged.
    """
    tag_cnt = 0
    BARRIER = "\n" + "=" * 20 + "\n"
    skip_cnt = 0

    content = content[begin:end]

    new_content = []
    for l in tqdm.tqdm(content):
        skipped = False
        for c in l["conversations"]:
            if should_skip(c["value"]):
                skipped = True
                break

            try:
                new_val = html_to_markdown(c["value"])
            except (bs4.builder.ParserRejectedMarkup, AssertionError):
                skipped = True
                break

            c["value"] = new_val.strip()

            # Debug
            if (check_tag is not None and check_tag in c["value"]
                    and tag_cnt < check_num):
                logger.debug(BARRIER + c["value"] + "\n" + BARRIER + new_val +
                             "\n" + BARRIER + "\n")
                tag_cnt += 1
                if tag_cnt == check_num:
                    break

        if not skipped:
            new_content.append(l)
        else:
            skip_cnt += 1

    print(f"#skip: {skip_cnt}")
    return new_content


def main(args):
    content = json.load(open(args.in_file, "r"))
    content = clean_html_source(
        content, args.begin, args.end,
        args.check_tag, args.check_num)
    json.dump(content, open(args.out_file, "w"), indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--in-file", type=str, required=True)
    parser.add_argument("--out-file", type=str, default="sharegpt_clean.json")
    parser.add_argument("--begin", type=int)
    parser.add_argument("--end", type=int)
    parser.add_argument("--check-tag", type=str)
    parser.add_argument("--check-num", type=int, default=1)
    args = parser.parse_args()
    main(args)
