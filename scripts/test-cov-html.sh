#! /usr/bin/env sh

# Exit in case of error
set -x

set -e

sh scripts/test.sh --cov-report=html "${@}"
