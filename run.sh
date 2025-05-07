#!/bin/bash

ACTION=$1       # build | run | down | buildx
TARGET=$2       # mongo | mongo+ | mongo++ | es | es+ | es++ | ui | mongodb | esdb
PUSH_FLAG=$3    # optional: --push
COMPOSE="docker compose"
VERSION=$(cat .version 2>/dev/null || echo "latest")

is_running() {
  docker compose ps --status=running --services | grep -q "^$1$"
}

ensure_running() {
  local name="$1"
  local port=""

  case $name in
    backend_mongo|backend_es) port=5500 ;;
    ui_angular) port=4200 ;;
    mongodb) port=27017 ;;
    elasticsearch) port=9200 ;;
  esac

  if [[ -n "$port" ]]; then
    check_and_clear_port "$port" || return
  fi

  if is_running "$name"; then
    echo "✅ $name already running"
  else
    echo "▶ Starting $name..."
    $COMPOSE up -d "$name" || echo "❌ Failed to start $name"
  fi
}

check_and_clear_port() {
  local port=$1
  echo "🔍 Checking if port $port is in use..."

  local pid
  pid=$(lsof -ti :$port)

  if [[ -z "$pid" ]]; then
    echo "✅ Port $port is free."
    return 0
  fi

  local process_name
  process_name=$(ps -p "$pid" -o comm=)

  if [[ "$process_name" == *"docker"* || "$process_name" == *"com.docker.backend"* ]]; then
    echo "⚠️  Port $port appears held by Docker ($process_name)"

    container_id=$(docker ps -aq --filter "publish=$port")

    if [[ -n "$container_id" ]]; then
      echo "🗑  Removing container $container_id using port $port..."
      docker rm -f "$container_id"
    else
      echo "⚠️  No container found using port $port, running 'docker network prune'..."
      docker network prune -f
    fi
  else
    echo "❌ Port $port is in use by non-Docker process:"
    echo "    PID: $pid, COMMAND: $process_name"
    return 1
  fi
}

parse_target() {
  BASE="" UI="" DB=""

  case "$1" in
    mongo)     BASE="backend_mongo" ;;
    mongo+)    BASE="backend_mongo"; UI="ui_angular" ;;
    mongo++)   BASE="backend_mongo"; UI="ui_angular"; DB="mongodb" ;;
    es)        BASE="backend_es" ;;
    es+)       BASE="backend_es"; UI="ui_angular" ;;
    es++)      BASE="backend_es"; UI="ui_angular"; DB="elasticsearch" ;;
    ui)        UI="ui_angular" ;;
    mongodb)   DB="mongodb" ;;
    esdb)      DB="elasticsearch" ;;
    *)
      echo "❌ Invalid target: $1"
      echo "Usage: $0 [build|run|down] [mongo|mongo+|mongo++|es|es+|es++|ui|mongodb|esdb] [--push]"
      exit 1 ;;
  esac
}

build_service() {
  local name="$1"
  local context="$2"
  local tag="events-$name:$VERSION"

  if [[ "$PUSH_FLAG" == "--push" ]]; then
    echo "📦 Building and pushing $tag (multi-platform)..."
    docker buildx build \
      --platform linux/amd64,linux/arm64 \
      -t "$tag" \
      --push "$context"
  else
    echo "🔧 Building $tag locally..."
    docker build -t "$tag" "$context"
  fi
}

build() {
  parse_target "$1"

  [[ -n "$BASE" ]] && build_service "$BASE" "./${TARGET%%+*}"
  [[ -n "$UI" ]] && {
    npm run build -- --configuration production || exit 1
    build_service "$UI" "./ui"
  }
  [[ -n "$DB" ]] && build_service "$DB" "./"
}

run() {
  parse_target "$1"
  [[ -n "$BASE" ]] && ensure_running "$BASE"
  [[ -n "$UI" ]] && ensure_running "$UI"
  [[ -n "$DB" ]] && ensure_running "$DB"
}

down() {
  parse_target "$1"
  [[ -n "$BASE" && $(is_running $BASE) ]] && $COMPOSE stop $BASE || [[ -n "$BASE" ]] && echo "🛑 $BASE already stopped"
  [[ -n "$UI" && $(is_running $UI) ]] && $COMPOSE stop $UI || [[ -n "$UI" ]] && echo "🛑 $UI already stopped"
  [[ -n "$DB" && $(is_running $DB) ]] && $COMPOSE stop $DB || [[ -n "$DB" ]] && echo "🛑 $DB already stopped"
}

case $ACTION in
  build) build "$TARGET" ;;
  run)   run "$TARGET" ;;
  down)  down "$TARGET" ;;
  buildx) PUSH_FLAG="--push"; build "$TARGET" ;;
  *)
    echo "Usage:"
    echo "  $0 build <target>        # Build locally"
    echo "  $0 buildx <target>       # Build multi-arch and push"
    echo "  $0 run <target>          # Run containers"
    echo "  $0 down <target>         # Stop containers"
    echo "Targets: mongo mongo+ mongo++ es es+ es++ ui mongodb esdb"
    exit 1 ;;
esac

