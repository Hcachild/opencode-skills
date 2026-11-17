---
name: gitea-pr-merge
description: Merge, close, or otherwise act on Gitea pull requests on by_code_base (120.79.129.209:10093) as a specific user when local git credentials belong to the wrong account or lack permission. Uses the Gitea CLI inside the container to mint a short-lived scoped access token, drives the local API, then revokes the token and cleans traces. Use when the user says 合并PR、把这个PR合到dev、以我的账号操作Gitea、Gitea token、by_code_base 仓库、自己在Gitea上点合并, or when a merge is blocked by read-only/absent credentials.
---

# Gitea PR Merge (by_code_base)

Use when a merge must happen as a named Gitea user but the local machine has no usable credential for that account. Do not use it to impersonate without the user explicitly naming the target account.

## Hard Rules

1. Confirm the target account, repo, PR number, base branch, and merge style with the user before writing.
2. Never print, commit, or persist the token. Keep it in a server-side file with `chmod 600`, delete it when done.
3. Revoke the token immediately after the operation, in the same session.
4. Report what is irreversible: the PR record, the merge commit, MySQL binlog, and SSH auth log entries.
5. If the local credential belongs to a different user, stop and say so instead of acting as the wrong identity.

## Environment Facts

| Item | Value |
|---|---|
| SSH alias | `by_code_base` (`root@120.79.129.209`, key `~/.ssh/id_ed25519`) |
| Gitea container | `1Panel-gitea-DMTl` (`commitgo/gitea-ee`) |
| Host API base | `http://127.0.0.1:10093/api/v1` — **not** `:3000`; 3000 is the container port |
| Container paths | config `/data/gitea/conf/app.ini`, work path `/data/gitea` |
| DB | `DB_TYPE = mysql`; DB/user/pass read from `[database]` in `app.ini`; reachable via `docker exec 1Panel-mysql-uCyd` |
| Git SSH | `ssh://git@120.79.129.209:2222/<owner>/<repo>.git` |

Rediscover instead of trusting the table if the container name changed: `docker ps --format '{{.Names}}\t{{.Ports}}' | grep -i gitea`.

## Preflight

1. Resolve the account and permission:
   - Local identity: `git credential fill` with `protocol=http`, `host=120.79.129.209:10093`.
   - Anonymous `GET /api/v1/users/<login>` and `/api/v1/repos/<owner>/<repo>` to confirm the owner exists.
   - `GET /api/v1/repos/<owner>/<repo>/collaborators/<login>/permission` with the local credential. `read` means the local user cannot merge.
2. Confirm the PR is actionable: `state=open`, `mergeable=true`, and note `head`/`base` SHAs.
3. Check branch protection before assuming success: `GET /repos/<o>/<r>/branch_protections/<branch>` (404 = none).
4. Tell the user which account you will act as and why.

## Procedure

Run everything through `ssh by_code_base`, never by typing the token locally. On Windows PowerShell, ship scripts base64-encoded to avoid CRLF and quote mangling:

```powershell
$sh = @'
...bash here, end lines with \n only...
'@
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes(($sh -replace "`r`n","`n")))
ssh by_code_base "echo $b64 | base64 -d | bash -s"
```

### 1. Mint a short-lived token as the target user

```bash
TOKEN=$(docker exec -u git 1Panel-gitea-DMTl gitea admin user generate-access-token \
  -u <login> -t "opencode-merge-$(date +%s)" --scopes write:repository --raw)
echo "$TOKEN" > /root/.gitea_merge_token && chmod 600 /root/.gitea_merge_token
```

- `--scopes write:repository` is enough for repo/PR endpoints. `/api/v1/user` additionally needs `read:user`; do not add it unless required.
- Verify identity without leaking the token: `curl -s -H "Authorization: token $TOKEN" .../repos/<o>/<r>/pulls/<n>` and print `merged_by` after the merge.

### 2. Merge

```bash
curl -s -w '\nHTTP=%{http_code}\n' -X POST \
  -H "Authorization: token $TOKEN" -H 'Content-Type: application/json' \
  -d '{"Do":"merge"}' \
  http://127.0.0.1:10093/api/v1/repos/<o>/<r>/pulls/<n>/merge
```

- `Do` is **required** by this Gitea version; omitting it returns `422 [Do]: Required`.
- Values: `merge` (repo default, merge commit), `squash`, `rebase`, `rebase-merge`, `fast-forward-only`, `manually-merged`.
- Add `"delete_branch_after_merge": true` only if the user asked to delete the head branch.
- `200` = merged. `405`/`409` usually means branch protection, stale head, or conflicts.

### 3. Verify

```bash
curl -s -H "Authorization: token $TOKEN" .../pulls/<n>          # state=closed, merged=true, merged_by
curl -s -H "Authorization: token $TOKEN" .../branches/<base>    # head SHA == merge_commit_sha
```

Report: `state`, `merged_at`, `merged_by`, `merge_commit_sha`, new base-branch head subject.

### 4. Revoke and clean

```bash
DBPASS=$(docker exec 1Panel-gitea-DMTl sed -n '/^\[database\]/,/^\[/p' /data/gitea/conf/app.ini \
  | grep -E '^PASSWD' | cut -d= -f2- | tr -d ' \r')
docker exec 1Panel-mysql-uCyd mysql -u<dbuser> -p"$DBPASS" -h127.0.0.1 <dbname> \
  -e "delete from access_token where name like 'opencode-merge-%';"
docker exec 1Panel-mysql-uCyd mysql -u<dbuser> -p"$DBPASS" -h127.0.0.1 <dbname> \
  -e "select count(*) from access_token where name like 'opencode-merge-%';"   # expect 0
rm -f /root/.gitea_merge_token /tmp/<any-scratch-files>
```

- Substitute `<dbuser>`/`<dbname>` from `NAME` and `USER` in `app.ini`.
- The stored row holds only a hash and salt, never the raw token.
- Non-interactive `ssh host "cmd"` does not touch `.bash_history`; no cleanup needed there.

## Residual Traces (state, never promise removal)

- PR merged record and merge commit on the base branch — the intended result, permanent.
- Gitea `action` / feed entries for the merge.
- MySQL binlog (`log_bin=ON`): insert+delete of the `access_token` row. Purging it affects the whole instance; do not do it without explicit approval.
- `/var/log/auth.log` or journal: SSH logins from the operator IP.
- `/data/gitea/log` is typically empty; check before claiming nothing was logged.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `422 [Do]: Required` | Merge API needs explicit style | Send `{"Do":"merge"}` |
| `json.decoder.JSONDecodeError: Expecting value` | curl hit the wrong port and returned empty | Use `127.0.0.1:10093`, check with `-w '%{http_code}'` |
| `bash: line N: 'echo\r': command not found` | PowerShell here-string sent CRLF | Base64-pipe the script, or strip `\r` |
| `syntax error near unexpected token '('` | Nested quotes inside `ssh "..."` | Move the script into base64 payload; avoid nested `python3 -c` |
| `403 token does not have ... required=[read:user]` | Scope too narrow for `/user` | Use a repo/PR endpoint to verify, or add scope |
| Local credential belongs to another user | Shared machine | Stop, ask the user for their own token |
| `405` on merge with owner token | Protected branch / stale head | Re-fetch PR, check `mergeable`, disable force-merge requirements only with approval |

## Safety Notes

Running `gitea admin user generate-access-token` as root grants a token for **any** account on the instance. Treat it as privileged: act only on the account the user names, keep the token's lifetime to seconds, revoke in the same session, and say so in the final report.
