#!/bin/sh
set -eu

exec flask --app wsgi run-judge-worker