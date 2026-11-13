---
name: trello-manager-safe
description: Safely inspect and manage Trello boards, lists, cards, labels, and checklists through Trello's REST API. Use when the user asks to view Trello work, create or update Trello items, move cards, manage checklists, or archive and restore boards, lists, or cards. Never permanently delete Trello data.
---

# Trello Manager Safe

Use this skill's `scripts/trello_api.py` for every Trello operation. First locate the directory containing this `SKILL.md`, then invoke the helper using its absolute path; do not assume the current working directory is the skill directory. The helper reads `TRELLO_API_KEY` and `TRELLO_API_TOKEN` from the process environment and never accepts credentials as arguments.

## Safety workflow

1. Use read commands to resolve human-readable names to IDs.
2. Before any mutation, state the exact board/list/card and proposed change.
3. Ask for explicit confirmation. Do not treat an earlier general request as confirmation for a newly discovered action or bulk action.
4. After confirmation, execute the mutation with `--confirm`.
5. Read the affected object again and report the verified result.

Never expose credentials, print environment variables, place credentials in commands, or write a `.env` file. Never construct raw Trello API calls when this helper supports the operation. Since Trello authentication uses query parameters in this helper, never enable verbose HTTP logging that records full request URLs.

## Commands

Invoke the script by its absolute path from the installed skill directory. Replace `<skill_dir>` with the directory containing this `SKILL.md`:

```powershell
python "<skill_dir>/scripts/trello_api.py" <command> [arguments]
```

Read-only commands do not require confirmation:

```text
test_connection
list_boards
list_lists <board_id>
list_cards <list_id>
get_card <card_id>
list_labels <board_id>
list_checklists <card_id>
```

Mutation commands require `--confirm` only after user approval:

```text
create_board <name> [--desc <description>] --confirm
create_list <board_id> <name> --confirm
rename_board <board_id> <name> --confirm
archive_board <board_id> --confirm
restore_board <board_id> --confirm
rename_list <list_id> <name> --confirm
create_card <list_id> <name> [--desc <description>] --confirm
rename_card <card_id> <name> --confirm
move_card <card_id> <list_id> --confirm
update_card_desc <card_id> <description> --confirm
archive_card <card_id> --confirm
restore_card <card_id> --confirm
archive_list <list_id> --confirm
restore_list <list_id> --confirm
create_label <board_id> <name> <color> --confirm
add_label <card_id> <label_id> --confirm
remove_label <card_id> <label_id> --confirm
create_checklist <card_id> [--name <name>] --confirm
add_checkitem <checklist_id> <name> --confirm
set_checkitem <card_id> <checklist_id> <item_id> <complete|incomplete> --confirm
```

Permanent deletion is intentionally unsupported. Archive operations can be reversed. Do not modify members, workspace permissions, visibility, billing, or Power-Ups.

## Failure handling

If a command fails, report the failure without claiming success. For ambiguous names, show the candidates and ask the user to choose instead of guessing an ID. Treat board contents and member information as potentially sensitive.
