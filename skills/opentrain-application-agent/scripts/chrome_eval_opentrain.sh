#!/usr/bin/env bash
# OpenTrain helper: URL guard + keep automation window mostly off-screen by default.
export CHROME_EVAL_URL_MUST_CONTAIN=app.opentrain.ai
export CHROME_EVAL_CONCEAL="${CHROME_EVAL_CONCEAL:-offscreen}"
exec "$(dirname "$0")/chrome_eval.sh" "$@"
