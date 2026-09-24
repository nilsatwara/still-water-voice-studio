import unittest
import uuid

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from backend.app.api.dependencies import require_any_permission, require_permission
from backend.app.core.authentication import AuthenticationContextMiddleware
from backend.app.core.security import Principal
from backend.app.services.rbac_service import user_with_permissions_statement


class FixedResolver:
    def __init__(self, principal: Principal | None):
        self.principal = principal

    async def resolve(self, request):
        return self.principal


def test_application() -> FastAPI:
    app = FastAPI()
    app.add_middleware(AuthenticationContextMiddleware)

    @app.get('/pages', dependencies=[Depends(require_permission('pages.create'))])
    def protected_page():
        return {'ok': True}

    @app.get('/content', dependencies=[Depends(require_any_permission('pages.edit', 'posts.edit'))])
    def protected_content():
        return {'ok': True}

    return app


class RBACGuardTests(unittest.TestCase):
    def setUp(self):
        self.app = test_application()
        self.client = TestClient(self.app)

    def principal(self, *permissions: str, active: bool = True) -> Principal:
        return Principal(uuid.uuid4(), frozenset({'EDITOR'}), frozenset(permissions), active)

    def test_anonymous_and_spoofed_headers_are_rejected(self):
        response = self.client.get('/pages', headers={
            'X-User-Id': str(uuid.uuid4()),
            'X-Role': 'SUPER_ADMIN',
            'X-Permissions': '*',
        })
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('traceback', response.text.lower())

    def test_permission_is_enforced_independently(self):
        self.app.state.identity_resolver = FixedResolver(self.principal('posts.create'))
        self.assertEqual(self.client.get('/pages').status_code, 403)
        self.app.state.identity_resolver = FixedResolver(self.principal('pages.create'))
        self.assertEqual(self.client.get('/pages').status_code, 200)

    def test_inactive_account_is_rejected(self):
        self.app.state.identity_resolver = FixedResolver(self.principal('pages.create', active=False))
        self.assertEqual(self.client.get('/pages').status_code, 403)

    def test_any_permission_guard_accepts_one_match(self):
        self.app.state.identity_resolver = FixedResolver(self.principal('posts.edit'))
        self.assertEqual(self.client.get('/content').status_code, 200)

    def test_wildcard_permission_is_centralized(self):
        self.app.state.identity_resolver = FixedResolver(self.principal('*'))
        self.assertEqual(self.client.get('/pages').status_code, 200)

    def test_rbac_query_eager_loads_roles_and_permissions(self):
        statement = user_with_permissions_statement(uuid.uuid4())
        compiled = str(statement.compile(dialect=postgresql.dialect()))
        self.assertIn('FROM users', compiled)
        self.assertEqual(len(statement._with_options), 1)

    def test_invalid_permission_code_fails_during_route_definition(self):
        with self.assertRaises(ValueError):
            require_permission('SUPER ADMIN')


if __name__ == '__main__':
    unittest.main()
