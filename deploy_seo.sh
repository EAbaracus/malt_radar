#!/usr/bin/env bash
# Malt Radar SEO deploy — deploy_web.sh deseninin kardeşi (spec §8, R3/R4).
# ssh -> pull seo kodu -> canlı DB'den üret -> doğrula -> no-op kontrol -> swap -> canlı check -> GSC gate
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SSH_KEY="$HOME/.ssh/mr_deploy"
VM="trblnfxn@34.60.144.38"
REPO="/srv/maltradar"
DB="$REPO/deploy/data/production.db"   # HOST yolu (container /srv/data'ya mount edilir — generator host'ta çalışır!)
WEB_SEO="$REPO/deploy/web-seo"
TMP="$REPO/deploy/web-seo.tmp"

echo "==> [1/7] sunucu: git pull + generator (canlı DB)"
ssh -i "$SSH_KEY" "$VM" "cd $REPO && git pull --ff-only origin main && \
  rm -rf $TMP && python3 -m seo.generator --db $DB --out $TMP" \
  || { echo "FAIL: üretim başarısız — eski sürüm canlı kalır"; exit 1; }

echo "==> [2/7] sunucu: uyum denetimi (seo.verify — TEMIZ şart)"
ssh -i "$SSH_KEY" "$VM" "cd $REPO && python3 -m seo.verify --dir $TMP" \
  || { echo "FAIL: uyum denetimi başarısız — eski sürüm canlı kalır"; exit 1; }

echo "==> [3/7] no-op kontrolü (çıktı hash'i değişmediyse atla)"
NEW_HASH=$(ssh -i "$SSH_KEY" "$VM" "find $TMP -type f | sort | xargs sha256sum | sha256sum | cut -d' ' -f1")
OLD_HASH="$(ssh -i "$SSH_KEY" "$VM" "cat $WEB_SEO/.build_sha256 2>/dev/null || true")"
if [ -n "$OLD_HASH" ] && [ "$OLD_HASH" = "$NEW_HASH" ]; then
  echo "==> değişiklik yok — deploy atlandı (no-op)"
  ssh -i "$SSH_KEY" "$VM" "rm -rf $TMP"
  exit 0
fi

echo "==> [4/7] swap (dizini DEĞİŞTİRME — bind-mount inode'u sabit kalmalı) + .prev rollback"
ssh -i "$SSH_KEY" "$VM" "mkdir -p $WEB_SEO && rm -rf $WEB_SEO.prev && cp -r $WEB_SEO $WEB_SEO.prev 2>/dev/null; \
  rm -rf $WEB_SEO/* $WEB_SEO/.[!.]* 2>/dev/null; cp -r $TMP/. $WEB_SEO/ && \
  echo '$NEW_HASH' > $WEB_SEO/.build_sha256 && rm -rf $TMP && echo SWAP_OK"

echo "==> [5/7] canlı doğrulama"
for u in /tr/ /en/ /sitemap.xml /robots.txt /llms.txt /tr/w/W000001/; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -m 15 "https://maltradar.com$u")
  [ "$code" = "200" ] || { echo "FAIL: $u -> $code — ROLLBACK"; \
    ssh -i "$SSH_KEY" "$VM" "rm -rf $WEB_SEO/* $WEB_SEO/.[!.]* 2>/dev/null; cp -r $WEB_SEO.prev/. $WEB_SEO/"; exit 1; }
done
echo "==> canlı kontrol OK"

echo "==> [6/7] GSC sitemap submit (env-gated — kimlik yoksa atla)"
if [ -f "$ROOT/deploy/.gsc_env" ]; then
  echo "(GSC kimliği mevcut — submit; insan adımı tamamlaninca bağlanır)"
else
  echo "==> GSC kimliği yok — submit atlandı (insan adımı bekliyor, deploy'u bloklamaz)"
fi

echo "==> [7/7] DONE — SEO build canlı ($NEW_HASH)"