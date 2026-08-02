"""``/device-tokens`` — parent-facing management of extension credentials.

Called by the dashboard (with the parent's Clerk session). Minting lives here in
the core so all token logic + hashing sit next to the resolver that validates
them. Every route is scoped to the caller's Clerk account, so a token can only be
created/listed/revoked by its owner.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from lockdown_core.auth.clerk import AuthContext
from lockdown_core.persistence.device_tokens import DeviceTokenRepository


class CreateTokenRequest(BaseModel):
    name: str = Field(default="", max_length=120)


class TokenView(BaseModel):
    id: str
    name: str
    created_at: str
    last_used_at: str | None = None
    revoked: bool = False


class CreatedToken(TokenView):
    # The one and only time the plaintext is returned.
    token: str


def build_device_token_router(
    repository: DeviceTokenRepository | None,
    authorize: Callable[[Request], Awaitable[AuthContext]],
) -> APIRouter:
    router = APIRouter(prefix="/device-tokens", tags=["device-tokens"])

    def _repo() -> DeviceTokenRepository:
        if repository is None:
            raise HTTPException(status_code=503, detail="token store not configured")
        return repository

    @router.get("", response_model=list[TokenView])
    async def list_tokens(auth: AuthContext = Depends(authorize)) -> list[TokenView]:
        infos = await _repo().list(clerk_user_id=auth.user_id)
        return [TokenView(**vars(i)) for i in infos]

    @router.post("", response_model=CreatedToken, status_code=201)
    async def create_token(
        body: CreateTokenRequest, auth: AuthContext = Depends(authorize)
    ) -> CreatedToken:
        plaintext, info = await _repo().create(
            clerk_user_id=auth.user_id, clerk_org_id=auth.org_id, name=body.name
        )
        return CreatedToken(token=plaintext, **vars(info))

    @router.delete("/{token_id}", status_code=204)
    async def revoke_token(token_id: str, auth: AuthContext = Depends(authorize)) -> Response:
        ok = await _repo().revoke(clerk_user_id=auth.user_id, token_id=token_id)
        if not ok:
            raise HTTPException(status_code=404, detail="token not found")
        return Response(status_code=204)

    return router
