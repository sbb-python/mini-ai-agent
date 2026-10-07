import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.main import app, parse_repository_url, rank_repository_paths


client = TestClient(app)


class ParseRepositoryUrlTests(unittest.TestCase):
    def test_accepts_public_repository_url(self):
        self.assertEqual(
            parse_repository_url("https://github.com/pallets/flask/"),
            ("pallets", "flask"),
        )

    def test_strips_git_suffix(self):
        self.assertEqual(
            parse_repository_url("https://github.com/pallets/flask.git"),
            ("pallets", "flask"),
        )

    def test_rejects_non_github_hosts_and_subpages(self):
        for url in (
            "https://example.com/owner/repository",
            "https://github.com/owner/repository/tree/main",
        ):
            with self.subTest(url=url), self.assertRaises(HTTPException):
                parse_repository_url(url)


class RankRepositoryPathsTests(unittest.TestCase):
    def test_ranks_relevant_sources_and_skips_generated_files(self):
        paths = [
            "README.md",
            "src/authentication.py",
            "src/billing.py",
            "node_modules/authentication/index.js",
            "src/authentication.lock",
            "assets/logo.png",
        ]

        ranked = rank_repository_paths(paths, "How does authentication work?")

        self.assertIn("README.md", ranked)
        self.assertLess(ranked.index("src/authentication.py"), ranked.index("src/billing.py"))
        self.assertNotIn("node_modules/authentication/index.js", ranked)
        self.assertNotIn("src/authentication.lock", ranked)
        self.assertNotIn("assets/logo.png", ranked)


class ApiRouteTests(unittest.TestCase):
    def test_health_endpoint(self):
        response = client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_chat_rejects_non_github_url(self):
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}):
            response = client.post(
                "/api/chat",
                json={"repository": "https://example.com/owner/repository", "question": "Hello"},
            )

        self.assertEqual(response.status_code, 400)

    def test_chat_reports_missing_openrouter_key(self):
        with patch.dict("os.environ", {}, clear=True):
            response = client.post(
                "/api/chat",
                json={
                    "repository": "https://github.com/owner/repository",
                    "question": "What does this do?",
                },
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("OPENROUTER_API_KEY", response.json()["detail"])

    def test_chat_returns_answer_from_openrouter(self):
        openrouter_response = httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "The project uses Python.",
                        }
                    }
                ]
            },
            request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions"),
        )
        model_client = AsyncMock()
        model_client.post.return_value = openrouter_response
        async_client = AsyncMock()
        async_client.__aenter__.return_value = model_client
        with (
            patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}),
            patch(
                "backend.main.fetch_repository_context",
                new_callable=AsyncMock,
                return_value=("owner/repository", "--- README.md ---\nA Python project."),
            ),
            patch("backend.main.httpx.AsyncClient", return_value=async_client),
        ):
            response = client.post(
                "/api/chat",
                json={
                    "repository": "https://github.com/owner/repository",
                    "question": "What language is this?",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"repository": "owner/repository", "answer": "The project uses Python."},
        )
        sent_request = model_client.post.await_args.kwargs
        self.assertEqual(
            sent_request["headers"]["Authorization"],
            "Bearer test-key",
        )
        self.assertEqual(sent_request["json"]["model"], "openrouter/free")

    def test_chat_explains_empty_repository(self):
        repository_response = httpx.Response(
            200,
            json={"default_branch": "main", "full_name": "owner/repository"},
            request=httpx.Request("GET", "https://api.github.com/repos/owner/repository"),
        )
        empty_tree_response = httpx.Response(
            409,
            json={"message": "Git Repository is empty."},
            request=httpx.Request(
                "GET", "https://api.github.com/repos/owner/repository/git/trees/main"
            ),
        )
        github_client = AsyncMock()
        github_client.get.side_effect = [repository_response, empty_tree_response]
        async_client = AsyncMock()
        async_client.__aenter__.return_value = github_client

        with (
            patch.dict("os.environ", {"OPENROUTER_API_KEY": "test-key"}),
            patch("backend.main.httpx.AsyncClient", return_value=async_client),
        ):
            response = client.post(
                "/api/chat",
                json={
                    "repository": "https://github.com/owner/repository",
                    "question": "What does this project do?",
                },
            )

        self.assertEqual(response.status_code, 422)
        self.assertIn("repository is empty", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
