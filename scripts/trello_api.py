#!/usr/bin/env python3
"""Guarded Trello REST API CLI for OpenCode."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import requests


BASE_URL = "https://api.trello.com/1"
TIMEOUT_SECONDS = 30
MUTATING_METHODS = {"post", "put"}


class TrelloError(RuntimeError):
    pass


class TrelloClient:
    def __init__(self) -> None:
        api_key = os.environ.get("TRELLO_API_KEY")
        api_token = os.environ.get("TRELLO_API_TOKEN")
        if not api_key or not api_token:
            raise TrelloError(
                "TRELLO_API_KEY dan TRELLO_API_TOKEN belum tersedia di environment."
            )

        self.session = requests.Session()
        self.auth = {"key": api_key, "token": api_token}

    def request(self, method: str, endpoint: str, **params: Any) -> Any:
        method = method.lower()
        if method == "delete":
            raise TrelloError("Permanent delete dinonaktifkan. Gunakan archive.")
        if method not in {"get", *MUTATING_METHODS}:
            raise TrelloError(f"HTTP method tidak diizinkan: {method}")

        try:
            response = self.session.request(
                method,
                f"{BASE_URL}/{endpoint.lstrip('/')}",
                params={**self.auth, **params},
                timeout=TIMEOUT_SECONDS,
            )
        except requests.Timeout as exc:
            raise TrelloError("Trello API timeout setelah 30 detik.") from exc
        except requests.RequestException as exc:
            # Do not include exception text because it may contain the authenticated URL.
            raise TrelloError("Gagal terhubung ke Trello API.") from exc

        if not response.ok:
            message = "request ditolak"
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    message = str(payload.get("message") or payload.get("error") or message)
            except ValueError:
                if response.text and len(response.text) <= 300:
                    message = response.text
            raise TrelloError(f"Trello API HTTP {response.status_code}: {message}")

        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise TrelloError("Trello mengembalikan respons non-JSON.") from exc


def require_confirmation(args: argparse.Namespace) -> None:
    if not getattr(args, "confirm", False):
        raise TrelloError(
            "Operasi tulis diblokir. Minta persetujuan pengguna, lalu ulangi dengan --confirm."
        )


import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def compact(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Safe Trello CLI")
    commands = root.add_subparsers(dest="command", required=True)

    commands.add_parser("test_connection")
    commands.add_parser("list_boards")

    p = commands.add_parser("list_lists")
    p.add_argument("board_id")
    p = commands.add_parser("list_cards")
    p.add_argument("list_id")
    p = commands.add_parser("get_card")
    p.add_argument("card_id")
    p = commands.add_parser("list_labels")
    p.add_argument("board_id")
    p = commands.add_parser("list_checklists")
    p.add_argument("card_id")

    def mutation(name: str) -> argparse.ArgumentParser:
        item = commands.add_parser(name)
        item.add_argument("--confirm", action="store_true")
        return item

    p = mutation("create_board")
    p.add_argument("name")
    p.add_argument("--desc", default="")
    p = mutation("create_list")
    p.add_argument("board_id")
    p.add_argument("name")
    p = mutation("rename_list")
    p.add_argument("list_id")
    p.add_argument("name")
    p = mutation("create_card")
    p.add_argument("list_id")
    p.add_argument("name")
    p.add_argument("--desc", default="")
    p = mutation("move_card")
    p.add_argument("card_id")
    p.add_argument("list_id")
    p = mutation("update_card_desc")
    p.add_argument("card_id")
    p.add_argument("description")
    p = mutation("rename_card")
    p.add_argument("card_id")
    p.add_argument("name")
    for name in ("archive_card", "restore_card"):
        p = mutation(name)
        p.add_argument("card_id")
    for name in ("archive_list", "restore_list"):
        p = mutation(name)
        p.add_argument("list_id")
    p = mutation("rename_board")
    p.add_argument("board_id")
    p.add_argument("name")
    for name in ("archive_board", "restore_board"):
        p = mutation(name)
        p.add_argument("board_id")
    p = mutation("create_label")
    p.add_argument("board_id")
    p.add_argument("name")
    p.add_argument("color")
    p = mutation("add_label")
    p.add_argument("card_id")
    p.add_argument("label_id")
    p = mutation("remove_label")
    p.add_argument("card_id")
    p.add_argument("label_id")
    p = mutation("create_checklist")
    p.add_argument("card_id")
    p.add_argument("--name", default="Checklist")
    p = mutation("add_checkitem")
    p.add_argument("checklist_id")
    p.add_argument("name")
    p = mutation("set_checkitem")
    p.add_argument("card_id")
    p.add_argument("checklist_id")
    p.add_argument("item_id")
    p.add_argument("state", choices=("complete", "incomplete"))
    return root


def execute(client: TrelloClient, args: argparse.Namespace) -> Any:
    command = args.command
    if command == "test_connection":
        return client.request("get", "members/me", fields="id,username,fullName")
    if command == "list_boards":
        return client.request("get", "members/me/boards", fields="id,name,url,closed")
    if command == "list_lists":
        return client.request("get", f"boards/{args.board_id}/lists", fields="id,name,closed")
    if command == "list_cards":
        return client.request("get", f"lists/{args.list_id}/cards", fields="id,name,desc,url,closed")
    if command == "get_card":
        return client.request("get", f"cards/{args.card_id}", checklists="all")
    if command == "list_labels":
        return client.request("get", f"boards/{args.board_id}/labels", fields="id,name,color")
    if command == "list_checklists":
        return client.request("get", f"cards/{args.card_id}", fields="id,name", checklists="all")

    require_confirmation(args)
    if command == "create_board":
        return client.request("post", "boards", name=args.name, desc=args.desc)
    if command == "create_list":
        return client.request("post", "lists", idBoard=args.board_id, name=args.name)
    if command == "rename_board":
        return client.request("put", f"boards/{args.board_id}", name=args.name)
    if command == "archive_board":
        return client.request("put", f"boards/{args.board_id}", closed="true")
    if command == "restore_board":
        return client.request("put", f"boards/{args.board_id}", closed="false")
    if command == "rename_list":
        return client.request("put", f"lists/{args.list_id}", name=args.name)
    if command == "create_card":
        return client.request("post", "cards", idList=args.list_id, name=args.name, desc=args.desc)
    if command == "move_card":
        return client.request("put", f"cards/{args.card_id}", idList=args.list_id)
    if command == "update_card_desc":
        return client.request("put", f"cards/{args.card_id}", desc=args.description)
    if command == "rename_card":
        return client.request("put", f"cards/{args.card_id}", name=args.name)
    if command == "archive_card":
        return client.request("put", f"cards/{args.card_id}", closed="true")
    if command == "restore_card":
        return client.request("put", f"cards/{args.card_id}", closed="false")
    if command == "archive_list":
        return client.request("put", f"lists/{args.list_id}", closed="true")
    if command == "restore_list":
        return client.request("put", f"lists/{args.list_id}", closed="false")
    if command == "create_label":
        return client.request("post", "labels", idBoard=args.board_id, name=args.name, color=args.color)
    if command == "add_label":
        return client.request("post", f"cards/{args.card_id}/idLabels", value=args.label_id)
    if command == "remove_label":
        card = client.request("get", f"cards/{args.card_id}", fields="idLabels")
        remaining = [label for label in card.get("idLabels", []) if label != args.label_id]
        return client.request("put", f"cards/{args.card_id}", idLabels=",".join(remaining))
    if command == "create_checklist":
        return client.request("post", "checklists", idCard=args.card_id, name=args.name)
    if command == "add_checkitem":
        return client.request("post", f"checklists/{args.checklist_id}/checkItems", name=args.name)
    if command == "set_checkitem":
        return client.request(
            "put",
            f"cards/{args.card_id}/checklist/{args.checklist_id}/checkItem/{args.item_id}",
            state=args.state,
        )
    raise TrelloError(f"Command tidak didukung: {command}")


def main() -> int:
    try:
        args = parser().parse_args()
        compact(execute(TrelloClient(), args))
        return 0
    except TrelloError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
