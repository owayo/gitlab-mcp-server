#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from mcp.server.fastmcp import FastMCP

from src.utils.git_utils import get_current_branch
from src.utils.gitlab_utils import (
    get_failed_jobs_output,
    get_merge_request,
    get_mr_changes,
    get_mr_comments,
)

# Initialize MCP server
mcp = FastMCP("gitlab-mcp")


def get_current_branch_name() -> str:
    """
    現在のブランチ名を取得します。

    Returns:
        str: 現在のブランチ名
    """
    return get_current_branch()


# カレントのブランチのMRIDを取得
def get_current_mr_id() -> int:
    """
    現在のブランチのMRIDを取得します。

    Returns:
        int: 現在のブランチのMRID
    """
    branch_name = get_current_branch()
    mr = get_merge_request(branch_name)
    if mr:
        return mr.iid
    else:
        return "現在のブランチに関連するMerge Requestが見つかりません。"


@mcp.tool()
def get_pipeline_failed_jobs() -> str:
    """GitLabパイプラインで失敗したジョブのコンソール出力を取得"""
    mr_id = get_current_mr_id()

    failed_jobs_output = get_failed_jobs_output(mr_id=mr_id)
    if failed_jobs_output:
        return f"""
パイプラインで以下のエラーが出ています。
プロダクトコードの修正で対応が可能な場合は修正を行ってください。

{failed_jobs_output}
"""
    else:
        return "パイプラインで失敗したジョブが見つかりません。"


@mcp.tool()
def get_review_changes() -> str:
    """GitLab MRで修正したファイルの差分を取得"""
    mr_id = get_current_mr_id()

    changes = get_mr_changes(mr_id=mr_id)
    if changes:
        return f"""
以下の変更について @Codebase を考慮してレビューし、コードの問題点や改善点を出してください。

{changes}
"""
    else:
        return "変更内容を取得できません。"


@mcp.tool()
def get_review_comments() -> str:
    """GitLab MRの未解決の指摘事項（コメント）を取得"""
    mr_id = get_current_mr_id()

    mr_comments = get_mr_comments(mr_id=mr_id)
    if mr_comments:
        return f"""
以下の指摘事項に対応してください。対応後は今後へのアドバイスを出力してください。

{mr_comments}
"""
    else:
        return f"MR #{mr_id} への未解決の指摘事項はありません。"


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        mcp.run(transport="stdio")
    elif args[0] == "test" and len(args) >= 2:
        if args[1] == "branch":
            print(get_current_branch_name())
        elif args[1] == "mr-id":
            print(get_current_mr_id())
        elif args[1] == "failed-jobs":
            if len(args) == 2:
                print(get_pipeline_failed_jobs())
            else:
                print("無効な引数です。使用方法: test failed-jobs [<mr_id>]")
        elif args[1] == "review-comments":
            if len(args) == 2:
                print(get_review_comments())
            else:
                print("無効な引数です。使用方法: test review-comments [<mr_id>]")
        elif args[1] == "review-changes":
            if len(args) == 2:
                print(get_review_changes())
            else:
                print("無効な引数です。使用方法: test review-changes [<mr_id>]")
        else:
            print("無効なテスト引数です。")
    else:
        print("""使用方法:
python main.py                           # MCPサーバーを起動
python main.py test branch               # 現在のブランチ名を取得
python main.py test failed-jobs [<mr_id>] # MR IDの失敗したジョブの出力を取得
python main.py test review-comments [<mr_id>] # MR IDの未解決の指摘事項を取得
python main.py test review-changes [<mr_id>] # MR IDの変更内容を取得
""")
