#!/bin/bash

JOB=()
RESET=false

CONTRAST=1
BRIGHTNESS=0
SATURATION=1
WBMODE=1
EXPOSURETIMERANGE="'null'"
GAINRANGE="'null'"
ISPDIGITALGAINRANGE="'null'"
EXPOSURECOMPENSATION=0
AELOCK=false
AWBLOCK=false
WIDTH=1296
HEIGHT=730
FRAMERATE=30

MODEL='None'
OVERLAY="'box,labels,conf'"
ALPHA=120
THRESHOLD=0.5
VISUALIZE='overlay'
FILTERMODE='linear'

while [[ $# -gt 0 ]]; do
  case $1 in
    -c|--contrast)
      CONTRAST="$2"
      shift # past argument
      shift # past value
      ;;
    -b|--brightness)
      BRIGHTNESS="$2"
      shift # past argument
      shift # past value
      ;;
    -s|--saturation)
      SATURATION="$2"
      shift # past argument
      shift # past value
      ;;
    -wb|--wbmode)
      WBMODE="$2"
      shift # past argument
      shift # past value
      ;;
    -et|--exposuretimerange)
      EXPOSURETIMERANGE="$2"
      shift # past argument
      shift # past value
      ;;
    -gr|--gainrange)
      GAINRANGE="$2"
      shift # past argument
      shift # past value
      ;;
    -igr|--ispdigitalgainrange)
      ISPDIGITALGAINRANGE="$2"
      shift # past argument
      shift # past value
      ;;
    -ec|--exposurecompensation)
      EXPOSURECOMPENSATION="$2"
      shift # past argument
      shift # past value
      ;;
    --aelock)
      AELOCK=true
      shift # past argument
      ;;
    --awblock)
      AWBLOCK=true
      shift # past argument
      ;;
    --width)
      WIDTH="$2"
      shift # past argument
      shift # past value
      ;;
    --height)
      HEIGHT="$2"
      shift # past argument
      shift # past value
      ;;
    --framerate)
      FRAMERATE="$2"
      shift # past argument
      shift # past value
      ;;
    --RESET)
      RESET=true
      shift # past argument
      ;;
    -m|--model)
      MODEL="$2"
      shift # past argument
      shift # past value
      ;;
    --overlay)
      OVERLAY="$2"
      shift # past argument
      shift # past value
      ;;
    --alpha)
      ALPHA="$2"
      shift # past argument
      shift # past value
      ;;
    --threshold)
      THRESHOLD="$2"
      shift # past argument
      shift # past value
      ;;
    --visualize)
      VISUALIZE="$2"
      shift # past argument
      shift # past value
      ;;
    --filter-mode)
      FILTERMODE="$2"
      shift # past argument
      shift # past value
      ;;
    -*|--*)
      echo "Unknown option $1"
      exit 1
      ;;
    *)
      JOB+=("$1") # save positional arg
      shift # past argument
      ;;
  esac
done

set -- "${JOB[@]}" # restore positional parameters

if $RESET; then
    ./camera-config.py --RESET
    exit 0
fi

python3 camera-config.py -c $CONTRAST -b $BRIGHTNESS -s $SATURATION -wb $WBMODE -et "$EXPOSURETIMERANGE" -gr "$GAINRANGE" -igr "$ISPDIGITALGAINRANGE" -ec $EXPOSURECOMPENSATION --width $WIDTH --height $HEIGHT --framerate $FRAMERATE $([ $AELOCK == true ] && echo '--aelock' || echo '') $([ $AWBLOCK == true ] && echo '--awblock' || echo '')

python3 camera-build.py

python3 camera-inference.py $JOB -m $MODEL --overlay $OVERLAY --alpha $ALPHA --threshold $THRESHOLD --visualize $VISUALIZE --filtermode $FILTERMODE
