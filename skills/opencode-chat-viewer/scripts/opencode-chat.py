# -*- coding: utf-8 -*-
"""opencode-chat - read-only viewer for OpenCode's local conversation database.

Data source: ~/.local/share/opencode/opencode.db (SQLite: session / message / part).

Commands:
  list   - list sessions (by day or most recent)
  view   - dump a session's conversation (by id / id-prefix / title)
  search - keyword search across session titles and all message parts
  export - batch-export sessions of a day/range to text files (daily-report material)

All access is read-only (mode=ro); safe to run while OpenCode is live.
"""
import argparse
import datetime
import io
import json
import re
import sqlite3
import sys
from pathlib import Path

MAX_TS = (1 << 62) - 1


def _stdout():
    try:
        if (sys.stdout.encoding or '').lower().startswith('utf'):
            return sys.stdout
        return io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        return sys.stdout


def default_db_path():
    return Path.home() / '.local' / 'share' / 'opencode' / 'opencode.db'


def connect(db_path):
    p = Path(db_path)
    if not p.exists():
        sys.exit('opencode.db not found: %s' % p)
    uri = 'file:%s?mode=ro' % p.as_posix()
    return sqlite3.connect(uri, uri=True)


def parse_day(s):
    return datetime.datetime.strptime(s, '%Y-%m-%d')


def fmt_ts(ms):
    return datetime.datetime.fromtimestamp(ms / 1000).strftime('%Y-%m-%d %H:%M:%S')


def fmt_short(ms):
    return datetime.datetime.fromtimestamp(ms / 1000).strftime('%m-%d %H:%M')


def fmt_time(ms):
    return datetime.datetime.fromtimestamp(ms / 1000).strftime('%H:%M:%S')


def get_window(args, allow_days=False):
    """Return (start_ms, end_ms); None means unbounded."""
    start = end = None
    if getattr(args, 'days', None):
        if not allow_days:
            sys.exit('--days is not supported here')
        now = int(datetime.datetime.now().timestamp() * 1000)
        start = now - args.days * 86400 * 1000
        end = now
    if getattr(args, 'date', None):
        d = parse_day(args.date)
        start = int(d.timestamp() * 1000)
        end = int((d + datetime.timedelta(days=1)).timestamp() * 1000) - 1
    if getattr(args, 'from_', None):
        start = int(parse_day(args.from_).timestamp() * 1000)
    if getattr(args, 'to', None):
        end = int((parse_day(args.to) + datetime.timedelta(days=1)).timestamp() * 1000) - 1
    return start, end


def time_clause(alias, start, end):
    parts, params = [], []
    if start is not None:
        parts.append('%s >= ?' % alias)
        params.append(start)
    if end is not None:
        parts.append('%s <= ?' % alias)
        params.append(end)
    if not parts:
        return '', []
    return ' AND ' + ' AND '.join(parts), params


def session_meta(db, sid):
    row = db.execute('SELECT title, directory, parent_id, model FROM session WHERE id=?', (sid,)).fetchone()
    if not row:
        return {'title': '(未知会话)', 'directory': '', 'parent': None, 'model': ''}
    title, directory, parent, model = row
    model_name = ''
    if model:
        try:
            mj = json.loads(model)
            model_name = '%s/%s' % (mj.get('providerID', '?'), mj.get('id', '?'))
        except Exception:
            model_name = str(model)[:40]
    return {'title': title or '(无标题)', 'directory': directory or '', 'parent': parent, 'model': model_name}


def resolve_session(db, key):
    row = db.execute('SELECT id FROM session WHERE id=?', (key,)).fetchone()
    if row:
        return row[0]
    row = db.execute('SELECT id FROM session WHERE id LIKE ? ORDER BY time_updated DESC LIMIT 1', (key + '%',)).fetchone()
    if row:
        return row[0]
    rows = db.execute('SELECT id, title FROM session WHERE title LIKE ? ORDER BY time_updated DESC LIMIT 8',
                      ('%' + key + '%',)).fetchall()
    if len(rows) == 1:
        return rows[0][0]
    if not rows:
        sys.exit('No session matches: %s' % key)
    print('Multiple sessions match "%s":' % key)
    for sid, title in rows:
        print('  %s | %s' % (sid, title))
    sys.exit('Please use a full session id.')


def truncate(text, max_chars):
    if max_chars and len(text) > max_chars:
        return text[:max_chars] + '...[TRUNC]'
    return text


def part_text(pd):
    """Human-readable text of a part (for search snippets)."""
    t = pd.get('type')
    if t in ('text', 'reasoning'):
        return pd.get('text') or ''
    if t == 'tool':
        st = pd.get('state') or {}
        try:
            ins = json.dumps(st.get('input'), ensure_ascii=False)
        except Exception:
            ins = ''
        return '[tool:%s] %s %s' % (pd.get('tool'), st.get('status', ''), ins)
    return ''


def snippet_of(text, kw, width=70):
    low = text.lower()
    i = low.find(kw.lower())
    if i < 0:
        s = text[:width * 2]
    else:
        s = text[max(0, i - width): i + width]
    return re.sub(r'\s+', ' ', s).strip()


def dump_session(db, sid, start, end, include_reasoning, include_tools, max_chars, w):
    mw, mp = time_clause('m.time_created', start, end)
    sql = ('SELECT m.time_created, m.data, p.data FROM message m JOIN part p ON p.message_id = m.id '
           'WHERE m.session_id = ?%s ORDER BY m.time_created, p.id' % mw)
    rows = db.execute(sql, [sid] + mp).fetchall()
    lines = []
    for m_ts, mdata, pdata in rows:
        md = json.loads(mdata)
        pd = json.loads(pdata)
        role = md.get('role', '?')
        ptype = pd.get('type')
        if ptype == 'text':
            text = pd.get('text') or ''
            if text.strip():
                lines.append('[%s %s] %s' % (role, fmt_time(m_ts), truncate(text, max_chars)))
        elif ptype == 'reasoning' and include_reasoning:
            text = pd.get('text') or ''
            if text.strip():
                lines.append('[%s:thinking %s] %s' % (role, fmt_time(m_ts), truncate(text, max_chars)))
        elif ptype == 'tool' and include_tools:
            st = pd.get('state') or {}
            try:
                ins = json.dumps(st.get('input'), ensure_ascii=False)[:200]
            except Exception:
                ins = ''
            lines.append('[tool %s] %s [%s] %s' % (fmt_time(m_ts), pd.get('tool'), st.get('status', ''), ins))
    return lines, len(rows)


def cmd_list(db, args, w):
    start, end = get_window(args)
    if start is None and end is None:
        rows = db.execute('SELECT id, time_updated FROM session ORDER BY time_updated DESC LIMIT ?',
                          (args.limit,)).fetchall()
        print('最近 %d 个会话:' % len(rows))
        for sid, _ in rows:
            meta = session_meta(db, sid)
            times = db.execute('SELECT MIN(time_created), MAX(time_created), COUNT(*) FROM message WHERE session_id=?',
                               (sid,)).fetchone()
            t0 = fmt_short(times[0]) if times[0] else '-'
            t1 = fmt_short(times[1]) if times[1] else '-'
            n = times[2]
            mark = '↳ ' if meta['parent'] else ''
            print('%s%s | %s | %s~%s | %d msgs | %s' % (mark, sid, meta['title'], t0, t1, n, meta['directory']))
        return
    mw, mp = time_clause('time_created', start, end)
    rows = db.execute('SELECT session_id, MIN(time_created), MAX(time_created), COUNT(*) FROM message '
                      'WHERE 1=1%s GROUP BY session_id ORDER BY MIN(time_created)' % mw, mp).fetchall()
    print('%s 共 %d 个会话（按时间升序）:' % (args.date or ('%s~%s' % (args.from_ or '-', args.to or '-')), len(rows)))
    for sid, t0, t1, n in rows:
        meta = session_meta(db, sid)
        mark = '↳ ' if meta['parent'] else ''
        print('%s%s | %s | %s~%s | %d msgs | %s' % (mark, sid, meta['title'], fmt_short(t0), fmt_short(t1), n, meta['directory']))


def cmd_view(db, args, w):
    sid = resolve_session(db, args.key)
    meta = session_meta(db, sid)
    start, end = get_window(args)
    lines, _ = dump_session(db, sid, start, end, args.include_reasoning, args.include_tools, args.max_chars, w)
    win = ''
    if args.date:
        win = ' (仅 %s)' % args.date
    elif args.from_ or args.to:
        win = ' (%s~%s)' % (args.from_ or '-', args.to or '-')
    print('Session: %s' % meta['title'])
    print('Id: %s' % sid)
    if meta['directory']:
        print('Directory: %s' % meta['directory'])
    if meta['model']:
        print('Model: %s' % meta['model'])
    print('Lines: %d%s' % (len(lines), win))
    print('-' * 60)
    for line in lines:
        print(line)


def cmd_search(db, args, w):
    kw = args.keyword
    esc = kw.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    like = '%' + esc + '%'
    hits = {}
    scanned = 0
    start, end = get_window(args, allow_days=True)
    mw, mp = time_clause('m.time_created', start, end)
    sql = ('SELECT m.session_id, m.time_created, m.data, p.data FROM message m JOIN part p ON p.message_id = m.id '
           'WHERE p.data LIKE ? ESCAPE \'\\\'%s ORDER BY m.time_created DESC' % mw)
    capped = False
    for sid, m_ts, mdata, pdata in db.execute(sql, [like] + mp):
        scanned += 1
        if scanned > args.max_hits:
            capped = True
            break
        md = json.loads(mdata)
        pd = json.loads(pdata)
        h = hits.setdefault(sid, {'n': 0, 'first': m_ts, 'last': m_ts, 'snips': []})
        h['n'] += 1
        h['first'] = min(h['first'], m_ts)
        h['last'] = max(h['last'], m_ts)
        if len(h['snips']) < args.snippets:
            text = part_text(pd)
            snip = snippet_of(text, kw) if text else ''
            if snip:
                tag = pd.get('type')
                h['snips'].append('    [%s %s %s] %s' % (fmt_short(m_ts), md.get('role', '?'), tag, snip))
    title_hits = db.execute('SELECT id FROM session WHERE title LIKE ? ESCAPE \'\\\' ORDER BY time_updated DESC LIMIT ?',
                            (like, args.limit)).fetchall()
    title_sids = [r[0] for r in title_hits if r[0] not in hits]
    order = sorted(hits.items(), key=lambda kv: (-kv[1]['n'], -kv[1]['last']))
    show = order[:args.limit]
    print('=== 关键词 "%s" 命中 %d 个会话%s ===' % (kw, len(hits) + len(title_sids),
          '（扫描达到上限 %d，计数可能不全）' % args.max_hits if capped else ''))
    for sid, h in show:
        meta = session_meta(db, sid)
        print('%s | %s | %s~%s | %d hits' % (sid, meta['title'], fmt_short(h['first']), fmt_short(h['last']), h['n']))
        for s in h['snips']:
            print(s)
    for sid in title_sids[:args.limit]:
        meta = session_meta(db, sid)
        print('%s | %s | [title] 标题命中' % (sid, meta['title']))


def slugify(title, sid, maxlen=24):
    s = re.sub(r'[^\w\u4e00-\u9fff-]+', '_', title or '').strip('_')
    return (s[:maxlen] or sid[-8:])


def cmd_export(db, args, w):
    start, end = get_window(args)
    if args.session:
        sid = resolve_session(db, args.session)
        sids = [(sid, None, None, None)]
    else:
        if start is None and end is None:
            sys.exit('export requires --date/--from/--to or --session')
        mw, mp = time_clause('time_created', start, end)
        rows = db.execute('SELECT session_id, MIN(time_created), MAX(time_created), COUNT(*) FROM message '
                          'WHERE 1=1%s GROUP BY session_id ORDER BY MIN(time_created)' % mw, mp).fetchall()
        sids = [(r[0], r[1], r[2], r[3]) for r in rows]
    if not sids:
        sys.exit('No sessions found in the given window.')
    outdir = Path(args.out or 'opencode-chat-export')
    outdir.mkdir(parents=True, exist_ok=True)
    if args.prefix:
        prefix = args.prefix
    elif args.date:
        prefix = 'oc_' + args.date.replace('-', '')
    elif args.from_ or args.to:
        prefix = 'oc_%s_%s' % ((args.from_ or 'start').replace('-', ''), (args.to or 'end').replace('-', ''))
    else:
        prefix = 'oc_export'
    index_lines = []
    for i, (sid, t0, t1, n) in enumerate(sids, 1):
        meta = session_meta(db, sid)
        lines, _ = dump_session(db, sid, start, end, args.include_reasoning, args.include_tools, args.max_chars, w)
        fname = '%s_%02d_%s.txt' % (prefix, i, slugify(meta['title'], sid))
        fpath = outdir / fname
        with io.open(fpath, 'w', encoding='utf-8') as f:
            f.write('Session: %s\nId: %s\nDirectory: %s\nModel: %s\n' % (meta['title'], sid, meta['directory'], meta['model']))
            if n is not None:
                f.write('Window: %s ~ %s | %d msgs\n' % (fmt_ts(t0), fmt_ts(t1), n))
            f.write('Lines: %d\n%s\n' % (len(lines), '-' * 60))
            for line in lines:
                f.write(line + '\n')
        range_str = '%s~%s' % (fmt_short(t0), fmt_short(t1)) if t0 else '-'
        index_lines.append('%s | %s | %s | %s lines | %s' % (sid, meta['title'], range_str, len(lines), fname))
        print('wrote %s (%d lines)' % (fpath, len(lines)))
    idx = outdir / ('%s_index.txt' % prefix)
    with io.open(idx, 'w', encoding='utf-8') as f:
        f.write('OpenCode conversation export\nPrefix: %s\nSessions: %d\n%s\n' % (prefix, len(sids), '-' * 60))
        for line in index_lines:
            f.write(line + '\n')
    print('index: %s' % idx)


def main():
    w = _stdout()
    p = argparse.ArgumentParser(description='Read-only viewer for OpenCode local conversation DB')
    p.add_argument('--db', default=str(default_db_path()), help='path to opencode.db (default: ~/.local/share/opencode/opencode.db)')
    sub = p.add_subparsers(dest='cmd', required=True)

    def add_window(sp):
        sp.add_argument('--date', help='single day YYYY-MM-DD')
        sp.add_argument('--from', dest='from_', help='start day YYYY-MM-DD')
        sp.add_argument('--to', help='end day YYYY-MM-DD (inclusive)')

    lp = sub.add_parser('list', help='list sessions')
    add_window(lp)
    lp.add_argument('--limit', type=int, default=30)

    vp = sub.add_parser('view', help='dump one session conversation')
    vp.add_argument('key', help='session id / id prefix / title substring')
    add_window(vp)
    vp.add_argument('--include-reasoning', action='store_true')
    vp.add_argument('--include-tools', action='store_true')
    vp.add_argument('--max-chars', type=int, default=6000, help='0 = unlimited')

    sp = sub.add_parser('search', help='keyword search (titles + parts)')
    sp.add_argument('keyword')
    add_window(sp)
    sp.add_argument('--days', type=int, help='search only the last N days')
    sp.add_argument('--limit', type=int, default=20, help='max sessions to show')
    sp.add_argument('--snippets', type=int, default=3, help='snippets per session')
    sp.add_argument('--max-hits', type=int, default=3000, help='cap on scanned hit rows')

    ep = sub.add_parser('export', help='export sessions of a day/range to text files')
    add_window(ep)
    ep.add_argument('--session', help='export a single session id')
    ep.add_argument('--out', help='output directory (default: ./opencode-chat-export)')
    ep.add_argument('--prefix', help='file prefix (default: oc_YYYYMMDD)')
    ep.add_argument('--include-reasoning', action='store_true')
    ep.add_argument('--include-tools', action='store_true')
    ep.add_argument('--max-chars', type=int, default=6000, help='0 = unlimited')

    args = p.parse_args()
    db = connect(args.db)
    if args.cmd == 'list':
        cmd_list(db, args, w)
    elif args.cmd == 'view':
        cmd_view(db, args, w)
    elif args.cmd == 'search':
        cmd_search(db, args, w)
    elif args.cmd == 'export':
        cmd_export(db, args, w)


if __name__ == '__main__':
    main()
