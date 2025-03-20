#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import Any, Dict, List, Optional

import gitlab
from gitlab.v4.objects import MergeRequest, Project

from src.utils.git_utils import get_diff_from_base


# GitLab URLの取得
def get_gitlab_url() -> str:
    """
    環境変数からGitLabのURLを取得します。

    Returns:
        str: GitLabのURL

    Raises:
        ValueError: 環境変数が設定されていない場合
    """
    gitlab_url = os.environ.get("GITLAB_URL")
    if not gitlab_url:
        raise ValueError("GITLAB_URL環境変数が設定されていません。")
    return gitlab_url


# プロジェクトID
def get_gitlab_project_id() -> str:
    """
    環境変数からGitLabのプロジェクトIDを取得します。

    Returns:
        str: GitLabのプロジェクトID

    Raises:
        ValueError: 環境変数が設定されていない場合
    """
    project_id = os.environ.get("GITLAB_PROJECT_NAME")
    if not project_id:
        raise ValueError("GITLAB_PROJECT_ID環境変数が設定されていません。")
    return project_id


def get_gitlab_client() -> gitlab.Gitlab:
    """
    GitLabクライアントを取得します。

    Returns:
        gitlab.Gitlab: GitLabクライアントインスタンス

    Raises:
        ValueError: GitLab APIキーが見つからない場合や接続に失敗した場合
    """
    # 環境変数からGitLab APIキーを取得
    gitlab_api_key = os.environ.get("GITLAB_API_KEY")

    if not gitlab_api_key:
        raise ValueError("GITLAB_API_KEY環境変数が設定されていません。")

    # GitLabのURLを取得
    gitlab_url = get_gitlab_url()

    # 接続方法を順番に試行
    connection_urls = [
        gitlab_url,
    ]

    last_error = None
    for url in connection_urls:
        try:
            gl = gitlab.Gitlab(url, private_token=gitlab_api_key)
            gl.auth()
            return gl
        except Exception as e:
            last_error = e
            continue

    # すべての接続方法が失敗した場合
    raise ValueError(f"GitLabへの接続に失敗しました: {str(last_error)}")


def get_gitlab_project() -> Project:
    """
    GitLabプロジェクトを取得します。

    Returns:
        Project: GitLabプロジェクトインスタンス

    Raises:
        ValueError: プロジェクトの取得に失敗した場合
    """
    try:
        gl = get_gitlab_client()
        project_id = get_gitlab_project_id()

        # プロジェクトIDを使用してプロジェクトを取得
        try:
            project = gl.projects.get(project_id)
            return project
        except gitlab.exceptions.GitlabGetError:
            # IDでの取得に失敗した場合は検索を試行
            projects = gl.projects.list(search=project_id)
            if projects:
                return projects[0]

            # 検索でも見つからない場合
            raise ValueError(f"プロジェクト '{project_id}' が見つかりません。")
    except ValueError as e:
        # 既存のValueErrorを再送出
        raise e
    except Exception as e:
        # その他の例外は新しいValueErrorでラップ
        raise ValueError(f"GitLabプロジェクトの取得に失敗しました: {str(e)}")


def get_merge_request(
    branch_name: str,
) -> Optional[MergeRequest]:
    """
    指定したブランチ名に関連するMerge Requestを取得します。

    Args:
        branch_name (str): ブランチ名

    Returns:
        Optional[MergeRequest]: Merge Request情報。見つからない場合はNone

    Raises:
        ValueError: Merge Requestの取得に失敗した場合
    """
    try:
        project = get_gitlab_project()

        # 各状態のMRを順番に検索
        for state in ["opened", "merged", "closed"]:
            mrs = project.mergerequests.list(source_branch=branch_name, state=state)
            if mrs:
                # 最新のMRを使用
                mr = mrs[0]

                # パイプライン情報も取得
                if hasattr(mr, "pipeline") and mr.pipeline:
                    mr.pipeline = project.pipelines.get(mr.pipeline["id"])

                return mr

        # どの状態でもMRが見つからない場合
        return None
    except ValueError as e:
        # 既存のValueErrorを再送出
        raise e
    except Exception as e:
        # その他の例外は新しいValueErrorでラップ
        raise ValueError(f"Merge Requestの取得に失敗しました: {str(e)}")


def get_failed_jobs_output(mr_id: int) -> str:
    """
    指定したMR IDに関連する最後のパイプラインで失敗したジョブのコンソール出力を取得します。

    最後のパイプラインに失敗したジョブがなければ、空の文字列を返します。

    Args:
        mr_id (int): Merge Request ID

    Returns:
        str: 失敗したジョブのコンソール出力、または空文字列

    Raises:
        ValueError: ジョブ出力の取得に失敗した場合
    """
    try:
        project = get_gitlab_project()

        # MRを取得
        mr = project.mergerequests.get(mr_id)

        # パイプライン情報を取得
        if not hasattr(mr, "pipelines") or not mr.pipelines:
            return ""

        # パイプラインを取得し、最新のものを選択
        pipelines = mr.pipelines.list()
        if not pipelines:
            return ""

        # 最新のパイプラインを取得 (GitLabのAPIはデフォルトで降順)
        latest_pipeline = pipelines[0]
        pipeline_detail = project.pipelines.get(latest_pipeline.id)

        # 失敗したジョブを検索
        failed_jobs = [
            job for job in pipeline_detail.jobs.list() if job.status == "failed"
        ]

        if not failed_jobs:
            return ""  # 失敗したジョブがない場合は空文字列を返す

        # 失敗したジョブのコンソール出力を取得
        outputs = []
        for job in failed_jobs:
            job_detail = project.jobs.get(job.id)
            job_output = job_detail.trace()
            outputs.append(
                f"# ジョブ: {job.name}\n- ステータス: {job.status}\n- 出力:\n```\n{job_output}\n```"
            )

        return "\n\n".join(outputs)
    except gitlab.exceptions.GitlabGetError:
        raise ValueError(f"MR ID #{mr_id} が見つかりません。")
    except Exception as e:
        raise ValueError(f"失敗したジョブの出力取得に失敗しました: {str(e)}")


def get_mr_comments(mr_id: int) -> str:
    """
    指定したMR IDに関連するMRの指摘事項（コメント）を取得します。
    解決済み（resolved）のコメントは除外されます。
    ファイルに紐づいているコメントのみが取得されます。

    Args:
        mr_id (int): Merge Request ID

    Returns:
        str: MRへの指摘事項（AIが理解しやすい形式に整形）

    Raises:
        ValueError: コメントの取得に失敗した場合
    """
    try:
        project = get_gitlab_project()

        # MRを取得
        try:
            mr: MergeRequest = project.mergerequests.get(mr_id)
        except gitlab.exceptions.GitlabGetError:
            return f"MR ID #{mr_id} が見つかりません。"

        # MRのディスカッション（スレッド）を取得
        discussions = mr.discussions.list()

        if not discussions:
            return f"MR #{mr.iid} へのコメントはありません。"

        comments: List[str] = []

        # 各ディスカッションを処理
        for discussion in discussions:
            # 個々のディスカッション内のノートを処理
            discussion_comments = process_discussion(discussion)
            if discussion_comments:
                comments.extend(discussion_comments)

        if not comments:
            return f"MR #{mr.iid} への未解決の指摘事項はありません。"

        return "\n---\n".join(comments)

    except Exception as e:
        raise ValueError(f"MRへの指摘事項の取得に失敗しました: {str(e)}")


def process_discussion(discussion: Dict[str, Any]) -> List[str]:
    """
    ディスカッション（スレッド）内のノートを処理し、未解決のコメントを抽出します。
    ファイルに紐づいているコメントのみを抽出します。

    Args:
        discussion: GitLabディスカッションオブジェクト

    Returns:
        List[str]: 未解決のコメント文字列のリスト
    """
    discussion_comments = []
    has_unresolved_notes = False

    # ディスカッションにはノートの配列が含まれています
    notes = (
        discussion.attributes.get("notes", [])
        if hasattr(discussion, "attributes")
        else discussion.get("notes", [])
    )

    for note in notes:
        # システムノートは除外
        if note.get("system", False):
            continue

        # 解決可能で、かつ解決済みのノートは除外
        if note.get("resolvable", False) and note.get("resolved", False):
            continue

        # コードとの関連付けがあるか確認
        position = note.get("position", {})
        file_path = position.get("new_path", "") if position else ""

        # ファイルに紐づいていないコメントは除外
        if not file_path:
            continue

        # ここに到達したノートは未解決かつファイルに紐づいている
        has_unresolved_notes = True

        author = note.get("author", {}).get("name", "不明なユーザー")
        body = note.get("body", "")
        line = position.get("new_line", "") if position else ""

        location = (
            f" (ファイル: {file_path}, 行: {line})"
            if file_path and line
            else f" (ファイル: {file_path})"
        )

        discussion_comments.append(
            f"# 対象: {location}\n- コメント者: {author}\n- コメント:\n```\n{body}\n```"
        )

    # ディスカッションに未解決のノートがある場合のみ、そのコメントを返す
    if has_unresolved_notes:
        return discussion_comments
    return []


def get_mr_changes(mr_id: int) -> str:
    """
    指定したMR IDに関連するMRのベースコミット（base_sha）から現在のローカルの状態までの差分を取得します。
    リモートの差分ではなく、ローカルの最新状態との差分を取得します。

    Args:
        mr_id (int): Merge Request ID

    Returns:
        str: MRのベースコミットから現在のローカル状態までの変更内容（差分）

    Raises:
        ValueError: 変更内容の取得に失敗した場合
    """
    try:
        project = get_gitlab_project()

        # MRを取得
        try:
            mr: MergeRequest = project.mergerequests.get(mr_id)
        except gitlab.exceptions.GitlabGetError:
            return f"MR ID #{mr_id} が見つかりません。"

        # MRのdiff_refsからbase_shaを取得
        if not hasattr(mr, "diff_refs") or not mr.diff_refs:
            return f"MR #{mr.iid} の差分情報が取得できません。"

        base_sha: Optional[str] = mr.diff_refs.get("base_sha")
        if not base_sha:
            return f"MR #{mr.iid} のベースコミットが特定できません。"

        # ローカルリポジトリでbase_shaからの差分を取得
        try:
            diff_output = get_diff_from_base(base_sha)
            if not diff_output or diff_output == "変更されたファイルはありません。":
                return f"MR #{mr.iid} (ベースコミット: {base_sha}) からの変更はありません。"

            return diff_output
        except Exception as e:
            return f"ローカルリポジトリからの差分取得に失敗しました: {str(e)}"

    except Exception as e:
        raise ValueError(f"MRの変更内容の取得に失敗しました: {str(e)}")
