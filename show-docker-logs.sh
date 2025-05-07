#!/bin/bash
docker ps -a --filter "status=exited"
docker logs `docker ps -a --filter "status=exited" | grep "events-ui" | awk '{print $1}'`
