#!/bin/bash

function usage() {
cat <<_EOT_
Usage:
  $0 [-a] [-b] [-f filename] arg1 ...

Description:
  hogehogehoge

Options:
  -r    Feed reciever
  -p    Data Sender
  -k    Sender killer

_EOT_
exit 1
}

if [ "$OPTIND" = 1 ]; then
  while getopts abf:h OPT
  do
    case $OPT in
      r)
        process="receiver"
        echo "Lunch Receiver"
        ;;
      p)
        process="sender"
        echo "Lunch Sender"
        ;;
      k)
        process="killer"
        echo "Lunch killer"
        ;;
      h)
        echo "h option. display help"       # for debug
        usage
        ;;
      \?)
        echo "Try to enter the h option." 1>&2
        ;;
    esac
  done
else
  echo "No installed getopts-command." 1>&2
  exit 1
fi

echo "before shift"                       # for debug
shift $((OPTIND - 1))
echo "display other arguments [$*]"       # for debug
echo "after shift"                        # for debug

source activate py37

PARENT_PATH=`dirname $0`
SHELL_PATH="{PARENT_PATH}/execute"
command="{SHELL_PATH}/feedAgentController.py"
cd SHELL_PATH
if [ process = "killer" ] then
    command="${command} --process killer"
if [ process = "provider" ] then
    command="${command} --process provider"
if [ process = "sender" ] then
    command="${command} --process sender"

eval command
echo "DONE"




