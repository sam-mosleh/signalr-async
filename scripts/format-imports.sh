#! /usr/bin/env sh

# Exit in case of error
set -x

# Sort imports one per line, so autoflake can remove unused imports
isort --recursive  --force-single-line-imports --apply .
sh ./scripts/format.sh
