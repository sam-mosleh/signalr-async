#! /usr/bin/env sh

# Exit in case of error
set -x

set -e

pytest --cov=signalr_async --cov-report=term-missing tests "${@}"
