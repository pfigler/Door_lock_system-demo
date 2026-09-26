#!/bin/bash

ps aux | grep python3 | grep pts | awk '{print $2}' | xargs kill