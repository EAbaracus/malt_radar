"""social/cli.py — Malta Radar sosyal boru hattı komut satırı yüzü.

Kullanım (backend venv ile, AGENTS Backend pytest notuna uygun):
  python social/cli.py preview            # GO için onay bekleyen (ready) taslaklar
  python social/cli.py approve --ids A,B  # İNSAN GO: ready -> approved
  python social/cli.py schedule --ids A,B --at 2026-08-09T18:00:00Z  # akşam slotu
  python social/cli.py dump               # zamanı gelen onaylıları çıktı dosyasına döker
  python social/cli.py status             # kuyruk özeti

Üretim otomatiktir; YAYIN insan GO'sa + elle/entegrasyonla yürütülür.
"""

from __future__ import annotations

import argparse
import json as _json
import sys
from social import queue as _queue
from social.content import render_preview
from social.metrics import collect
from social.content import DraftBuilder

import dataclasses


def _ids(raw: str) -> list[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def cmd_preview(args) -> int:
    from social.content import Post
    q = _queue.pending_go(args.queue)
    if not q:
        print("GO bekleyen onaylı taslak yok. Önce: python social/cli.py generate")
        return 0
    print(f"İNSAN GO bekleyen {len(q)} taslak:\n")
    for d in q:
        print(render_preview(Post(**{k: d[k] for k in
             ("id", "handle", "platform", "template", "body", "created_utc",
              "source_sha256", "day", "lang", "status") if k in d})))
    print("\nOnaylamak için:")
    ln = " ".join(d["id"] for d in q)
    print(f"  python social/cli.py approve --ids {ln}")
    return 0


def cmd_generate(args) -> int:
    from social.metrics import DEFAULT_DB
    m = collect(args.db or str(DEFAULT_DB))
    # args.day: takvim günü indeksi. --day N üretir; hepsi stage+ready olur.
    day = getattr(args, "day", 0) or 0
    lang = getattr(args, "lang", "tr") or "tr"
    posts = DraftBuilder(handle=args.handle).build(m, day=day, lang=lang)
    st = [dataclasses.asdict(x) for x in posts]
    res = _queue.stage(st, args.queue)
    _queue.to_ready([p["id"] for p in st], args.queue)
    print(f"Uretilen + ready (day={day}, lang={lang}): {res['added']} taslak (toplam kuyruktaki {res['total']})")
    for post in posts:
        print(f"  [{post.id}] {post.platform} / {post.template} / lang={post.lang} / day={post.day}")
    print("\nOnay oncesi goruntulemek: python social/cli.py --queue <path> preview")
    return 0


def cmd_approve(args) -> int:
    ids = _ids(args.ids or "")
    if not ids:
        print("--ids A,B gerekiyor", file=sys.stderr)
        return 2
    res = _queue.go(ids, approver=args.approver, path=args.queue)
    print(f"GO verildi / approved: {res['approved']}")
    if not res["approved"]:
        print("Hiçbiri approved olmadı — id'ler 'ready' durumda mı? (preview ile kontrol)")
    return 0


def cmd_schedule(args) -> int:
    ids = _ids(args.ids or "")
    if not ids or not args.at:
        print("--ids A,B --at ISO-UTC gerekiyor (orn 2026-08-09T18:00:00Z)", file=sys.stderr)
        return 2
    listing = {iid: args.at for iid in ids}
    res = _queue.schedule(listing, args.queue)
    print(f"Zamanlandi: {res['scheduled']} post -> {args.at}")
    return 0


def cmd_dump(args) -> int:
    from social.publisher import dump_outgoing
    res = dump_outgoing(args.queue)
    if res["file"]:
        print(f"Yayin icin {res['due']} post ciktisi: {res['file']}")
        print("(queue statüsü henüz published DEĞİL — apply_post/publish ile yayınlanır)")
    else:
        print("Zamanı gelmiş onaylı post yok. schedule ile slot verin.")
    return 0


def cmd_publish(args) -> int:
    """Zamanı gelen onaylı (approved) x-postlarını X API v2'ye gönderir.

    dry_run ile kimlik/imza kontrolü yapılabilir. Kimlik eksikse fail-closed.
    """
    from social.queue import publish_due
    from social.publisher import PublishError, load_env
    load_env()  # social/.env -> os.environ (gerçek secret'lar diskten)
    due = publish_due(args.queue)
    if not due:
        print("Zamanı gelmiş onaylı post yok (önce approve + schedule).")
        return 0
    if args.dry_run:
        print(f"[dry-run] {len(due)} post için X kimliği/imza denetimi:")
        for p in due:
            r = _publisher_dry(p, args.queue)
            print(f"  [{p['id']}] {p['platform']}: {r}")
        return 0
    if args.ids:
        due = [p for p in due if p["id"] in _ids(args.ids)]
    ok, fail = 0, 0
    for p in due:
        try:
            r = _publisher_apply(p, args.queue)
            print(f"  [YAYINLANDI] {p['id']} -> tweet {r.get('tweet_id')}")
            ok += 1
        except PublishError as e:
            print(f"  [FAIL-closed] {p['id']}: {e}")
            fail += 1
    print(f"\nYayınlanan: {ok}, başarısız: {fail} (başarısızlar queue'da 'approved' kalır).")
    return 0 if fail == 0 else 1


def _publisher_dry(post, qpath):
    from social import publisher
    try:
        r = publisher.apply_post(post, qpath, dry_run=True)
        return f"dry_run OK, auth={'EVET' if r.get('authorization_ready') else 'HAYIR'}"
    except publisher.PublishError as e:
        return f"FAIL: {e}"


def _publisher_apply(post, qpath):
    from social.publisher import apply_post
    return apply_post(post, qpath, dry_run=False)


def cmd_status(args) -> int:
    print(_json.dumps(_queue.status(args.queue), ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="social.cli")
    ap.add_argument("--db", default=None)
    ap.add_argument("--queue", default=None)
    ap.add_argument("--handle", default="MaltRadar")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name, fn, help_txt in [
        ("preview", cmd_preview, "GO için ready taslakları göster"),
        ("generate", cmd_generate, "metriklerden yeni taslak üret ve ready'ye al"),
        ("approve", cmd_approve, "insan GO: ready -> approved"),
        ("schedule", cmd_schedule, "approved postlara yayın zamanı yaz"),
        ("dump", cmd_dump, "zamanı gelen onaylıları çıktı dosyasına dök"),
        ("publish", cmd_publish, "zamanı gelen onaylı x-postlarını X API v2'ye gönder (fail-closed)"),
        ("status", cmd_status, "kuyruk özeti"),
    ]:
        p = sub.add_parser(name, help=help_txt)
        p.set_defaults(func=fn)
        p.add_argument("--queue", default=None,
                       help="özel kuyruk yolu (varsayılan: social_queue.json)")
        if name == "generate":
            p.add_argument("--day", type=int, default=0, help="takvim günü indeksi (0=ilk)")
            p.add_argument("--lang", default="tr", choices=["tr", "en"],
                           help="dil: tr (varsayılan) | en")

    sub.choices["approve"].add_argument("--ids", default=None)
    sub.choices["approve"].add_argument("--approver", default="human")
    sub.choices["schedule"].add_argument("--ids", default=None)
    sub.choices["schedule"].add_argument("--at", default=None)
    pub = sub.choices["publish"]
    pub.add_argument("--ids", default=None)
    pub.add_argument("--dry-run", action="store_true")
    return ap


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
