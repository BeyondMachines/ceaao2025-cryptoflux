set -u

services=(
  "cryptoflux-postgres"
  "cryptoflux-postgres-dr"
  "cryptoflux-ext_api"
  "cryptoflux-trading_data"
  "cryptoflux-liquidity_calculator"
  "cryptoflux-trading_ui"
  "cryptoflux-data_ingestion_service"
  "cryptoflux-dr_sync"
  "cryptoflux-dozzle"
)

LOG_FILE="${HOME}/cryptoflux/docker_monitor.log"
INTERVAL_SECONDS=60

if [ -t 1 ]; then
  RED="$(tput setaf 1)"; YEL="$(tput setaf 3)"; CYN="$(tput setaf 6)"; GRN="$(tput setaf 2)"; RST="$(tput sgr0)"
else
  RED=""; YEL=""; CYN=""; GRN=""; RST=""
fi

echo -e "${CYN}Monitoring: ${services[*]}${RST}"
echo -e "${CYN}Logging to: ${LOG_FILE}${RST}"

mkdir -p "$(dirname "$LOG_FILE")"

timestamp() { date '+%Y-%m-%d %H:%M:%S'; }

get_field() {
  # $1 = container name, $2 = go-template (e.g., .State.Status)
  docker inspect --format "{{${2}}}" "$1" 2>/dev/null
}

while true; do
  ts="$(timestamp)"

  for svc in "${services[@]}"; do
    # Skip Dozzle health (no built-in healthcheck)
    if [[ "$svc" == "cryptoflux-dozzle" ]]; then
      # Still warn if the container is down
      status="$(get_field "$svc" ".State.Status")"
      if [[ -z "$status" || "$status" != "running" ]]; then
        msg="[$ts] ALERT: $svc stopped (Status: ${status:-unknown})"
        echo -e "${RED}${msg}${RST}"
        echo "$msg" >> "$LOG_FILE"
      fi
      continue
    fi

    status="$(get_field "$svc" ".State.Status")"

    if [[ -z "$status" || "$status" != "running" ]]; then
      msg="[$ts] ALERT: $svc stopped (Status: ${status:-unknown})"
      echo -e "${RED}${msg}${RST}"
      echo "$msg" >> "$LOG_FILE"
      continue
    fi

    # Health may not exist -> this will print "<no value>" if key missing; normalize to empty
    health="$(get_field "$svc" ".State.Health.Status")"
    if [[ "$health" == "<no value>" ]]; then health=""; fi

    # Only alert if explicitly bad (ignore empty or 'starting')
    if [[ -n "$health" && "$health" != "healthy" && "$health" != "starting" ]]; then
      msg="[$ts] ALERT: $svc unhealthy (Health: $health)"
      echo -e "${YEL}${msg}${RST}"
      echo "$msg" >> "$LOG_FILE"
    # else
      # Uncomment to log OK lines:
      # echo -e "${GRN}[$ts] OK: $svc ($status/${health:-none})${RST}"
    fi
  done

  sleep "$INTERVAL_SECONDS"
done
