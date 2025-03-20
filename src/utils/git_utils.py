#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import git


def get_git_repo_path() -> str:
    """
    環境変数からGitリポジトリのパスを取得します。

    Returns:
        str: Gitリポジトリのパス

    Raises:
        ValueError: リポジトリパスが環境変数に設定されていない場合、または指定されたパスが存在しない場合
    """
    # 環境変数からリポジトリパスを取得
    repo_path = os.environ.get("GIT_REPO_PATH")

    # 環境変数が設定されていない場合はエラーを発生させる
    if not repo_path:
        raise ValueError("BIZTEL_GIT_REPO_PATH環境変数が設定されていません。")

    # パスが存在するか確認
    if not os.path.exists(repo_path):
        raise ValueError(f"指定されたリポジトリパス {repo_path} が存在しません。")

    # パスがGitリポジトリかどうか確認
    try:
        git.Repo(repo_path)
    except git.exc.InvalidGitRepositoryError:
        raise ValueError(f"指定されたパス {repo_path} はGitリポジトリではありません。")

    return repo_path


def get_current_branch() -> str:
    """
    現在のGitリポジトリのブランチ名を取得します。

    Returns:
        str: 現在のブランチ名

    Raises:
        ValueError: ブランチ名の取得に失敗した場合
    """
    try:
        repo_path = get_git_repo_path()
        repo = git.Repo(repo_path)

        # アクティブなブランチ名を取得
        branch_name = repo.active_branch.name
        return branch_name
    except Exception as e:
        raise ValueError(f"ブランチ名の取得に失敗しました: {str(e)}")


def get_remote_url() -> str:
    """
    リモートリポジトリのURLを取得します。

    Returns:
        str: リモートリポジトリのURL

    Raises:
        ValueError: リモートリポジトリのURLの取得に失敗した場合
    """
    try:
        repo_path = get_git_repo_path()
        repo = git.Repo(repo_path)

        # originリモートを取得
        for remote in repo.remotes:
            if remote.name == "origin":
                # リモートURLを取得（最初のURLを使用）
                return remote.urls.__next__()

        raise ValueError("'origin'リモートが見つかりません。")
    except Exception as e:
        raise ValueError(f"リモートURLの取得に失敗しました: {str(e)}")


def get_project_name_from_remote() -> str:
    """
    リモートURLからプロジェクト名を抽出します。

    Returns:
        str: プロジェクト名

    Raises:
        ValueError: プロジェクト名の抽出に失敗した場合
    """
    try:
        remote_url = get_remote_url()

        # SSHまたはHTTPSのURLから最後の部分を取得
        if remote_url.endswith(".git"):
            remote_url = remote_url[:-4]  # .gitを除去

        # 最後の/以降をプロジェクト名として取得
        project_name = remote_url.split("/")[-1]
        return project_name
    except Exception as e:
        raise ValueError(f"プロジェクト名の抽出に失敗しました: {str(e)}")


def get_diff_from_base(base_sha: str) -> str:
    """
    指定されたベースSHAから現在の状態までの差分を取得します。
    ローカルリポジトリの変更を含みます。

    Args:
        base_sha (str): 比較の基点となるコミットのSHA

    Returns:
        str: ベースSHAから現在までの差分

    Raises:
        ValueError: 差分の取得に失敗した場合
    """
    try:
        repo_path = get_git_repo_path()
        repo = git.Repo(repo_path)

        # 変更されたファイルのリストを取得
        change_details = []

        # リポジトリの現在の状態（インデックスと作業ディレクトリ）をベースSHAと比較
        diff_index = repo.git.diff(base_sha, name_status=True).strip()

        if not diff_index:
            return "変更されたファイルはありません。"

        # 変更されたファイルごとに詳細な差分を取得
        for line in diff_index.split("\n"):
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) < 2:
                continue

            change_type_code = parts[0]
            file_path = parts[1]

            # 変更の種類を判定
            change_type = "変更"
            if change_type_code.startswith("A"):
                change_type = "新規追加"
            elif change_type_code.startswith("D"):
                change_type = "削除"
            elif change_type_code.startswith("R"):
                change_type = "名前変更"

            # ファイルの差分を取得
            try:
                file_diff = repo.git.diff(base_sha, file_path, unified=3)
                change_details.append(
                    f"# ファイル: {file_path} ({change_type})\n```diff\n{file_diff}\n```"
                )
            except Exception as e:
                # 特定のファイルの差分取得に失敗した場合はエラーメッセージを追加
                change_details.append(
                    f"# ファイル: {file_path} ({change_type})\n```\n差分の取得に失敗しました: {str(e)}\n```"
                )

        return "\n\n".join(change_details)

    except Exception as e:
        raise ValueError(f"差分の取得に失敗しました: {str(e)}")
