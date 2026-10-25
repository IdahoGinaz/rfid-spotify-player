#!/usr/bin/env bash
# Download the latest Spotify Soloist build; if it differs from the installed one, install it and restart.
# Runs as the normal user (no sudo); the binary lives in ~/.local/bin.
set -euo pipefail

case "$(uname -m)" in
  aarch64) arch=arm64 ;;
  armv7l) arch=arm32 ;;
  x86_64) arch=x86_64 ;;
  *) echo "Unsupported architecture $(uname -m)" >&2; exit 1 ;;
esac

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
curl --fail --silent --location -o "$tmp/soloist.tar.gz" \
  "https://soloist-builds.spotifycdn.com/soloist_release_${arch}.tar.gz"
tar -xzf "$tmp/soloist.tar.gz" -C "$tmp"
test -x "$tmp/soloist"

dest="$HOME/.local/bin/soloist"
mkdir -p "$(dirname "$dest")"
if [ -f "$dest" ] && cmp -s "$tmp/soloist" "$dest"; then
  echo "Soloist is up to date."
  exit 0
fi

install -m 755 "$tmp/soloist" "$dest.new"
mv "$dest.new" "$dest"
echo "Installed new Soloist build; restarting."
systemctl --user restart soloist
