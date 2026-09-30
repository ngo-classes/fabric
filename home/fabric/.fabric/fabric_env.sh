#!/usr/bin/env bash

export FABRIC_CREDMGR_HOST=cm.fabric-testbed.net
export FABRIC_ORCHESTRATOR_HOST=orchestrator.fabric-testbed.net
export FABRIC_PROJECT_ID=__FABRIC_PROJECT_ID__
export FABRIC_TOKEN_LOCATION=$HOME/.fabric/id_token.json

export FABRIC_BASTION_HOST=bastion.fabric-testbed.net
export FABRIC_BASTION_USERNAME=__FABRIC_BASTION_USERNAME__
export FABRIC_BASTION_KEY_LOCATION=$HOME/.ssh/fabric-bastion-key

export FABRIC_SLICE_PRIVATE_KEY_FILE=$HOME/.ssh/slice_key
export FABRIC_SLICE_PUBLIC_KEY_FILE=$HOME/.ssh/slice_key.pub

export SHELL=/bin/bash