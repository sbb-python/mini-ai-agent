import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
import httpx

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

    def test_rejects_non_github_hosts(self):
        with self.assertRaises(HTTPException) as raised:
            parse_repository_url("https://example.com/owner/repository")
        self.assertEqual(raised.exception.status_code, 400)

    def test_rejects_repository_subpages(self):
        with self.assertRaises(HTTPException) as raised:
            parse_repository_url("https://github.com/owner/repository/tree/main")
        self.assertEqual(raised.exception.status_code, 400)


class RankRepositoryPathsTests(unittest.TestCase):
    def test_prefers_relevant_text_and_excludes_generated_files(self):
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
        self.assertIn("GitHub URL", response.json()["detail"])

    def test_chat_returns_ai_answer_for_repository(self):
        response = httpx.Response(
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
        model_client.post.return_value = response
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
        request_kwargs = model_client.post.await_args.kwargs
        request_body = request_kwargs["json"]
        self.assertEqual(request_body["model"], "openrouter/free")
        self.assertIn("A Python project.", request_body["messages"][0]["content"])
        self.assertEqual(
            request_kwargs["headers"]["Authorization"], "Bearer test-key"
        )

    def test_chat_reports_missing_openrouter_key(self):
        with patch.dict("os.environ", {}, clear=True):
            response = client.post(
                "/api/chat",
                json={
                    "repository": "https://github.com/owner/repository",
                    "question": "What language is this?",
                },
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("OPENROUTER_API_KEY", response.json()["detail"])

    def test_chat_explains_empty_github_repository(self):
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
