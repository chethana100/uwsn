#!/usr/bin/env bash

set -u

repository_root=$(git rev-parse --show-toplevel) || exit 1
cd "$repository_root" || exit 1

status_snapshot() {
    git status --porcelain=v1
}

last_snapshot=$(status_snapshot)
printf 'Git watcher started. Existing changes will not be pushed.\n'

while true; do
    current_snapshot=$(status_snapshot)

    if [[ "$current_snapshot" != "$last_snapshot" ]]; then
        printf '\nDetected workspace changes:\n%s\n' "$current_snapshot"
        read -r -p 'Commit and push these changes? [y/N] ' answer

        if [[ "$answer" =~ ^[Yy]$ ]]; then
            git add -A && \
                git commit -m "Update workspace files" && \
                git push origin HEAD
        else
            printf 'Changes left uncommitted.\n'
        fi

        last_snapshot=$(status_snapshot)
    fi

    sleep 2
done