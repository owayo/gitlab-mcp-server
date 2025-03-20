# GitLab-MCP-Server

GitLabとの連携機能を提供するModel Context Protocol (MCP) サーバーです。GitLabの特定のプロジェクトからパイプラインの失敗情報やマージリクエストへの指摘事項を取得し、AIアシスタントに提供します。

## 概要

このMCPサーバーは、GitLabのAPIを利用して以下の情報をAIアシスタントに提供します：

1. GitLabパイプラインで失敗したジョブのコンソール出力
2. GitLab MRへの未解決の指摘事項（コメント）
3. GitLab MRの変更内容（ローカルリポジトリの現在の状態との差分）

MCPの機能を使用することで、AIアシスタントはGitLabの情報を直接取得し、より的確な支援を提供できます。

## インストール

```bash
# uvのインストール
$ curl -LsSf https://astral.sh/uv/install.sh | sh

$ cd /path/to/this-mcp-server
# ライブラリのインストール
$ uv sync
```

## 準備

GitLabのアクセストークンが必要です。
アクセストークンはGitLabの設定→アクセストークンにて発行してください。
発行する際、`read_api` にチェックを入れてください。

## 機能

### 1. パイプラインの失敗情報を取得して修正 (`get_pipeline_failed_jobs`)

GitLabパイプラインで失敗したジョブのコンソール出力を取得します。
取得した情報をもとにAIアシスタントによる修正が行われます。

**出力**:
- 失敗したジョブのコンソール出力（ジョブ名、ステータス、詳細なログを含む）

### 2. MRの指摘事項を取得して修正 (`get_review_comments`)

GitLab MRの未解決の指摘事項（コメント）を取得して対応します。
解決済みのコメントやファイルに紐づいていないコメントは除外されます。

**出力**:
- MRへの未解決かつファイルに紐づいている指摘事項（コメント者、時間、コメント内容、ファイル位置情報などを含む）

### 3. MRの変更内容を取得してレビュー (`get_review_changes`)

GitLab MRのベースコミット（base_sha）から現在のローカルリポジトリの状態までの差分を取得します。
リモートの差分ではなく、ローカルの最新状態（作業中の未コミット変更を含む）との差分を取得できます。
取得した差分でレビューが行われます。

**出力**:
- MRのベースコミットから現在のローカル状態までの変更内容（各ファイルの変更タイプと差分）


## AIアシスタントとの連携

AIアシスタント（Claude等）は、このMCPサーバーに対して以下の関数を呼び出すことができます：

- `get_pipeline_failed_jobs()`: パイプラインの失敗情報取得
- `get_review_comments()`: MRの指摘事項取得
- `get_review_changes()`: MRの変更内容取得

これらの関数は、現在のブランチに関連するMRの情報を自動的に取得します。

## Claude for Desktopでの設定

`claude_desktop_config.json` に以下の設定を追加してください：

```json
{
    "mcpServers": {
        "gitlab-mcp": {
            "command": "uv",
            "args": [
                "--directory",
                "/path/to/this-mcp-server",
                "run",
                "main.py"
            ],
            "env": {
                "GITLAB_URL": "your_gitlab_url",
                "GITLAB_PROJECT_NAME": "gitlab_project_name",
                "GITLAB_API_KEY": "your_gitlab_api_key",
                "GIT_REPO_PATH": "/path/to/git/repo"
            }
        }
    }
}
```

## Cursorでの設定

プロジェクトルートの `.cursor/mcp.json` に以下の設定を追加してください：

```json
{
    "mcpServers": {
        "gitlab-mcp": {
            "command": "env",
            "args": [
                "GITLAB_URL=your_gitlab_url",
                "GITLAB_PROJECT_NAME=gitlab_project_name",
                "GITLAB_API_KEY=your_gitlab_api_key",
                "GIT_REPO_PATH=/path/to/git/repo",
                "uv",
                "--directory",
                "/path/to/this-mcp-server",
                "run",
                "main.py"
            ]
        }
    }
}
```

注意：上記の設定例で、以下の値を適切に置き換えてください：
- `your_gitlab_api_key`: GitLab APIのアクセストークン
- `/path/to/git/repo`: ローカルGitリポジトリの絶対パス
- `/path/to/this-mcp-server`: このMCPサーバーのディレクトリの絶対パス
